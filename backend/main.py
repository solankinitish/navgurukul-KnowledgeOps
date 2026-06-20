from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers.server import router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="navgurukul-KnowledgeOps",
    description="RAG chatbot over large PDF corpus with hybrid retrieval and source citations",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
