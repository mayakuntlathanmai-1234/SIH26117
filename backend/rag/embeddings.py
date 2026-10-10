from sentence_transformers import SentenceTransformer
from config import settings

class LocalEmbeddings:
    def __init__(self):
        # This will download the model on first run if not present
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
        
    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode(text)
        return embedding.tolist()
