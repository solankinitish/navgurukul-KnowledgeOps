import os
import time
from groq import Groq
from backend.retrieval.store import query_chunks, add_chunks, get_ingested_pdfs, is_pdf_ingested
from backend.retrieval.reranker import rerank
from backend.ingestion.pdf import ingest_pdf
from backend.schemas.models import SessionState, Message, Chunk
from backend.utils.logger import get_logger
from dotenv import load_dotenv
import json

load_dotenv()

logger = get_logger(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a helpful assistant that answers questions strictly based on the provided context from PDF documents.

Rules:
1. Answer only from the provided context. If the answer is not in the context, say "I don't know based on the provided documents."
2. Always cite your sources at the end: mention the PDF filename and page number(s) you used.
3. Be precise and concise.
4. If multiple sources support the answer, cite all of them.

Context:
{context}
"""

def build_context(ranked_chunks: list[tuple[Chunk, float]]) -> str:
    context_parts = []
    for chunk, score in ranked_chunks:
        context_parts.append(
            f"[Source: {chunk.pdf_filename} | Page: {chunk.page_number} | Score: {score:.2f}]\n{chunk.text}"
        )
    return "\n\n".join(context_parts)

def ingest_documents(pdf_path: str, pdf_filename: str) -> dict:
    if is_pdf_ingested(pdf_filename):
        logger.info(f"{pdf_filename} already ingested, skipping")
        return {"message": f"{pdf_filename} already ingested", "chunks_added": 0}
    
    chunks = ingest_pdf(pdf_path, pdf_filename)
    add_chunks(chunks)
    return {"message": f"Successfully ingested {pdf_filename}", "chunks_added": len(chunks)}

async def stream_query(query: str, session: SessionState):
    start_time = time.time()
    logger.info(f"Query received: {query}")

    # Retrieve + rerank
    candidates, cosine_scores = query_chunks(query)
    ranked_chunks = rerank(query, candidates, cosine_scores)

    retrieval_time = time.time() - start_time
    logger.info(f"Retrieval completed in {retrieval_time:.2f}s")

    # Yield retrieved chunks for UI visualisation
    chunks_data = [
        {
            "text": chunk.text[:200],
            "pdf_filename": chunk.pdf_filename,
            "page_number": chunk.page_number,
            "score": round(score, 3),
            "extraction_method": chunk.extraction_method
        }
        for chunk, score in ranked_chunks
    ]
    yield f"data: CHUNKS:{json.dumps(chunks_data)}\n\n"

    # Build context and messages
    context = build_context(ranked_chunks)
    messages = [{"role": m.role, "content": m.content} for m in session.history]
    messages.append({"role": "user", "content": query})

    session.history.append(Message(role="user", content=query))
    
    # Stream LLM response
    full_response = ""
    stream = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
            *messages
        ],
        max_tokens=1000,
        stream=True
    )

    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            full_response += token
            yield f"data: {token}\n\n"
        
    session.history.append(Message(role="assistant", content=full_response))

    total_time = time.time() - start_time
    logger.info(f"Total query time: {total_time:.2f}s")
    yield f"data: LATENCY:{total_time:.2f}\n\n"
    yield "data: [DONE]\n\n"

def get_loaded_pdfs() -> list[str]:
    return get_ingested_pdfs()
