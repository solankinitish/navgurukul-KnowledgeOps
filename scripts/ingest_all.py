import os
import sys
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://127.0.0.1:8000/api/v1"
DATA_DIR = "./data"

def ingest_all():
    pdfs = [f for f in os.listdir(DATA_DIR) if f.endswith(".pdf")]
    print(f"Found {len(pdfs)} PDFs in {DATA_DIR}")

    for pdf_name in pdfs:
        pdf_path = os.path.join(DATA_DIR, pdf_name)
        print(f"Ingesting {pdf_name}...")
        with open(pdf_path, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/ingest",
                files={"file": (pdf_name, f, "application/pdf")}
            )
        print(f"Result: {response.json()}")

if __name__ == "__main__":
    ingest_all()
