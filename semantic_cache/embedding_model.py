from sentence_transformers import SentenceTransformer

model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")

def get_embedding(text: str) -> list[float]:
    embedding = model.encode(text)
    return embedding.tolist()