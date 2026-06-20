from pydantic import BaseModel
from typing import Literal, Any


class Chunk(BaseModel):
    text: str
    pdf_filename: str
    page_number: int
    chunk_index: int
    extraction_method: Literal["native", "ocr"]


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class SessionState(BaseModel):
    history: list[Message] = []
    ingested_pdfs: list[str] = []
