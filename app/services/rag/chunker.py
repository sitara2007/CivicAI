import os
import sys

# Ye line tumhare 'civicos' folder ko Python path mein add kar degi
# taaki 'app.services.rag.loader' ko access kar sakein
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.services.rag.loader import load_pdf


def chunk_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


if __name__ == "__main__":
    # Ab ye path sahi se dhoondhega
    pdf_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "data", "documents", "scheme.pdf"
    )
    text = load_pdf(pdf_path)
    chunks = chunk_text(text)
    print(f"Total chunks: {len(chunks)}")
    print(f"First chunk: {chunks[0][:100]}...")
