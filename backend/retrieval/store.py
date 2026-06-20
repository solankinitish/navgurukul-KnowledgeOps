import chromadb
import numpy as np
from backend.retrieval.embedder import embed_texts, embed_query
from backend.schemas.models import Chunk
from backend.utils.logger import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "knowledge_ops"
TOP_K = 10

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)

def add_chunks(chunks: list[Chunk]) -> None:
    if not chunks:
        return
    
    ids = []
    texts = []
    metadatas = []

    for c in chunks:
        ids.append(f"{c.pdf_filename}_{c.chunk_index}")
        texts.append(c.text)
        metadatas.append({
            "pdf_filename": c.pdf_filename,
            "page_number": c.page_number,
            "chunk_index": c.chunk_index,
            "extraction_method": c.extraction_method
        })
    
    embeddings = embed_texts(texts).tolist()

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )
    logger.info(f"Added {len(chunks)} chunks to ChromaDB")

def query_chunks(query: str, top_k: int = TOP_K) -> tuple[list[Chunk], list[float]]:
    query_embedding = embed_query(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    scores = []

    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        chunks.append(Chunk(
            text=doc,
            pdf_filename=meta["pdf_filename"],
            page_number=meta["page_number"],
            chunk_index=meta["chunk_index"],
            extraction_method=meta["extraction_method"]
        ))
        scores.append(1 - distance) # converting cosine distance to similarity
    
    return chunks, scores

def get_ingested_pdfs() -> list[str]:
    results = collection.get(include=["metadatas"])
    filenames = set()
    for meta in results["metadatas"]:
        filenames.add(meta["pdf_filename"])
    return list(filenames)

def is_pdf_ingested(pdf_filename: str) -> bool:
    return pdf_filename in get_ingested_pdfs()
