import chromadb
from config import settings
from rag.embeddings import LocalEmbeddings

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
        self.collection_name = "sih_documents"
        
        # We use a custom embedding function since we have local sentence-transformers
        self.embeddings = LocalEmbeddings()
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )
        
    def add_documents(self, documents: list[dict], document_id: str = None):
        if not documents:
            return
            
        texts = [doc["text"] for doc in documents]
        metadatas = []
        ids = []
        for idx, doc in enumerate(documents):
            meta = dict(doc.get("metadata", {}))
            if document_id:
                meta["document_id"] = document_id
            metadatas.append(meta)
            doc_id_prefix = document_id or meta.get("source", "doc")
            ids.append(f"{doc_id_prefix}_{meta.get('page', 1)}_{meta.get('chunk', idx)}_{idx}")
        
        # We manually embed here
        embeddings_list = self.embeddings.embed_documents(texts)
        
        self.collection.add(
            embeddings=embeddings_list,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
    def search(self, query: str, n_results: int = 4, document_id: str = None):
        query_embedding = self.embeddings.embed_query(query)
        
        kwargs = {"query_embeddings": [query_embedding], "n_results": n_results}
        if document_id:
            kwargs["where"] = {"document_id": document_id}
            
        results = self.collection.query(**kwargs)
        
        # Format results
        formatted_results = []
        if results and results.get('documents') and len(results['documents']) > 0:
            docs = results['documents'][0]
            metas = results['metadatas'][0]
            for i in range(len(docs)):
                formatted_results.append({
                    "text": docs[i],
                    "metadata": metas[i]
                })
                
        return formatted_results
