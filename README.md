# navgurukul-KnowledgeOps

A RAG chatbot that ingests large PDF corpora (text + scanned/image pages) and answers questions with source citations, hybrid retrieval, and sub-2-second latency.

---

## What it does

Load 10+ large PDFs (200+ pages each, mixed text and scanned pages). Ask questions in natural language. The system retrieves the most relevant content using a two-stage hybrid retrieval pipeline and generates grounded answers with exact source citations (PDF filename + page number) — within 2 seconds.

---

## Architecture

```
PDF Corpus (text + scanned/image pages)
       ↓
Ingestion Pipeline
  pdfplumber (native text extraction)
  Tesseract OCR (fallback for scanned/image pages)
  clean_text() normalization
  Chunking: 800 chars, 200 char overlap, with metadata
       ↓
sentence-transformers (all-MiniLM-L6-v2) — free, local embeddings
       ↓
ChromaDB (HNSW cosine index) — persistent vector store
       ↓
Two-Stage Retrieval
  ChromaDB top-10 candidates → Hybrid Reranker → top-3
       ↓
Groq LLM (llama-3.1-8b-instant) — streaming SSE response
       ↓
Answer + Source Citations + Retrieval Visualization + Latency
```

---

## Key Decisions

**Two-stage retrieval: ChromaDB top-10 → hybrid reranker top-3**
ChromaDB retrieves broadly for recall. The hybrid reranker narrows for precision. Single-stage retrieval either misses relevant chunks or returns noisy ones.

**Hybrid reranker: 0.5 cosine + 0.5 noun-only keyword overlap**
ChromaDB cosine scores capture semantics. Noun keyword overlap (via spaCy) catches exact term matches that embeddings generalize over. Nouns only — stopwords add noise.

**OCR fallback per page**
Each page is processed natively via pdfplumber first. Only pages with fewer than 100 chars of native text trigger Tesseract OCR. Avoids slow OCR on text-heavy pages.

**Chunk metadata enables zero-cost citations**
Every chunk tagged with `pdf_filename`, `page_number`, `chunk_index`, `extraction_method` at ingestion time. The LLM receives this metadata in context and cites it directly — no post-processing needed.

**ChromaDB for persistent storage**
Embeddings persist to disk across server restarts. No re-ingestion needed between sessions. HNSW index enables fast approximate nearest-neighbor search.

**clean_text() normalization**
Strips standalone page numbers (`isdigit()`), removes lines under 10 chars (headers/footers/noise), collapses excessive whitespace. No regex, no hardcoded patterns — works generically across any PDF.

---

## Local Setup

**Requirements:** Python 3.11+, Groq API key (free at console.groq.com), Tesseract, Poppler

```bash
# Install system dependencies (Mac)
brew install tesseract poppler

# Clone and install
git clone https://github.com/solankinitish/navgurukul-KnowledgeOps
cd navgurukul-KnowledgeOps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Create `.env`:
```
GROQ_API_KEY=your-key-here
```

```bash
# Terminal 1 — start backend
uvicorn backend.main:app --reload

# Terminal 2 — drop PDFs in data/ folder, then ingest
python scripts/ingest_all.py

# Terminal 3 — start frontend
streamlit run frontend/app.py
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Required. Free at console.groq.com |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/session/create` | Create chat session |
| POST | `/api/v1/ingest` | Ingest a PDF file |
| POST | `/api/v1/session/{id}/query` | Streaming RAG query (SSE) |
| GET | `/api/v1/pdfs` | List ingested PDFs |

---

## Evaluation

- **Latency**: displayed per query in UI — p95 observed under 2 seconds
- **Citation accuracy**: every answer includes PDF filename + page number, verifiable against source
- **Retrieval visualization**: top-3 chunks with scores, page numbers, and extraction method shown per query
- **Hallucination control**: strict grounding prompt — model says "I don't know" if answer not in context

---

## Tradeoffs

- Session state is in-memory — server restart clears sessions. Production would use Redis.
- OCR adds latency for scanned pages. Production would pre-process OCR offline before ingestion.
- Chunk size (800 chars) tunable via `CHUNK_SIZE` constant in `backend/ingestion/pdf.py`.