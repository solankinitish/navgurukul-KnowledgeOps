import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from backend.schemas.models import Chunk
from backend.utils.logger import get_logger

logger = get_logger(__name__)

CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
MIN_NATIVE_TEXT_LENGTH = 100

def extract_text_from_page(page, pdf_path: str, page_num: int) -> tuple[str, str]:
    native_text = page.extract_text() or ""
    native_text = native_text.strip()

    if len(native_text) >= MIN_NATIVE_TEXT_LENGTH:
        return native_text, "native"
    
    images = convert_from_path(pdf_path, first_page=page_num, last_page=page_num)
    if not images:
        return native_text, 'native'
    
    ocr_text = pytesseract.image_to_string(images[0]).strip()
    return ocr_text if ocr_text else native_text, "ocr"

def clean_text(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        if stripped.isdigit():
            continue
        if len(stripped) < 10:
            continue
        cleaned.append(stripped)
    return " ".join(cleaned).strip()

def chunk_text(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end].strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c) > 50]

def ingest_pdf(pdf_path: str, pdf_filename: str) -> list[Chunk]:
    chunks = []
    chunk_index = 0

    logger.info(f"Starting ingestion: {pdf_filename}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages, start=1):
                text, method = extract_text_from_page(page, pdf_path, page_num)
                text = clean_text(text)

                if not text:
                    continue

                page_chunks = chunk_text(text)
                for chunk_text_content in page_chunks:
                    chunks.append(Chunk(
                        text=chunk_text_content,
                        pdf_filename=pdf_filename,
                        page_number=page_num,
                        chunk_index=chunk_index,
                        extraction_method=method
                    ))
                    chunk_index += 1
        
        ocr_pages = sum(1 for c in chunks if c.extraction_method == "ocr")
        logger.info(f"Completed {pdf_filename}: {total_pages} pages, {len(chunks)}, {ocr_pages} OCR pages")
        return chunks
    
    except Exception as e:
        raise ValueError(f"Failed to ingest {pdf_filename}: {str(e)}")
