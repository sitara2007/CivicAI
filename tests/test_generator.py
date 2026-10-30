from openai import OpenAI
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.services.rag.retriever import retrieve

class Generator:
    def __init__(self):
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key or "missing-api-key")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def get_answer(self, question):
        chunks = retrieve(question)
        context = "\n".join([c['text'] for c in chunks])
        prompt = f"Use this context to answer the question: {context}\n\nQuestion: {question}"

        response = self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

if __name__ == "__main__":
    gen = Generator()
    print(gen.get_answer("Who is eligible for this scheme?"))
