from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_texts(texts: list[str]) -> np.ndarray:
    return model.encode(texts, convert_to_numpy=True)

def embed_query(query: str) -> np.ndarray:
    return model.encode([query], convert_to_numpy=True)[0]
