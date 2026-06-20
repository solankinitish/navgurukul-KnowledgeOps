import spacy
from backend.schemas.models import Chunk
from backend.utils.logger import get_logger

nlp = spacy.load("en_core_web_sm")
logger = get_logger(__name__)

def extract_nouns(query: str) -> set[str]:
    doc = nlp(query.lower())
    return {token.text for token in doc if token.pos_ == "NOUN"}

def compute_keyword_scores(chunks: list[Chunk], nouns: set[str]) -> list[float]:
    if not nouns:
        return [0.0] * len(chunks)
    scores = []
    for chunk in chunks:
        chunk_lower = chunk.text.lower()
        matches = sum(1 for noun in nouns if noun in chunk_lower)
        scores.append(matches / len(nouns))
    return scores

def rerank(query: str, candidates: list[Chunk], cosine_scores: list[float], top_k: int = 3) -> list[tuple[Chunk, float]]:
    nouns = extract_nouns(query)
    keyword_scores = compute_keyword_scores(candidates, nouns)

    scored = []
    for i, chunk in enumerate(candidates):
        final_score = 0.5 * cosine_scores[i] + 0.5 * keyword_scores[i]
        scored.append((final_score, chunk))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    logger.info(f"Reranked {len(candidates)} to top {top_k}")
    return [(chunk, score) for score, chunk in top]
