from sentence_transformers import SentenceTransformer
import numpy as np

class SemanticEngine:
    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
    # Supports Arabic + English in one model | ~120MB | ~50ms per query

    def __init__(self):
        self.model = None
        self.doc_embeddings = None  # np.ndarray shape (N, 384)
        self.doc_ids = []

    def load(self):
        """Load model once at startup."""
        self.model = SentenceTransformer(self.MODEL_NAME)

    def build_index(self, documents: list[dict]):
        """
        Encode all documents once at startup.
        documents: list of dicts, each must have 'doc_id' and text fields.
        """
        texts = [
            (d.get("full_description") or d.get("cleaned_text") or d.get("title") or "")
            for d in documents
        ]
        self.doc_ids = [d["doc_id"] for d in documents]
        self.doc_embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            normalize_embeddings=True,  # L2-normalize → cosine = dot product
        )
        print(f"[Semantic] Index built: {len(self.doc_ids)} documents")

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        """
        Return top_k results sorted by cosine similarity.
        Each result: {"doc_id": int, "score": float}
        Score threshold 0.25 — below this is noise.
        """
        if self.model is None or self.doc_embeddings is None:
            return []
        query_vec = self.model.encode([query], normalize_embeddings=True)[0]
        scores = self.doc_embeddings @ query_vec
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [
            {"doc_id": self.doc_ids[i], "score": float(scores[i])}
            for i in top_indices
            if scores[i] > 0.25
        ]

# Singleton — import and use this instance everywhere
semantic_engine = SemanticEngine()
