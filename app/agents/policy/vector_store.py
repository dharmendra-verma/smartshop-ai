"""FAISS vector store for store policies."""
import json, logging, numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import faiss
from openai import OpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)
FAISS_INDEX_PATH = Path("./data/embeddings/faiss_index.bin")
FAISS_META_PATH  = Path("./data/embeddings/faiss_metadata.json")
TOP_K = 3

@dataclass
class PolicyChunk:
    policy_id: int
    policy_type: str
    text: str
    score: float
    description: str
    conditions: str

class PolicyVectorStore:
    def __init__(self):
        s = get_settings()
        self._client = OpenAI(api_key=s.OPENAI_API_KEY)
        self._model  = s.EMBEDDING_MODEL       # "text-embedding-3-small"
        self._dim    = s.EMBEDDING_DIMENSION   # 1536
        self._index: Optional[faiss.IndexFlatIP] = None
        self._metadata: list[dict] = []

    # ── Build / Load ──────────────────────────────────────────────────
    def build(self, policies: list) -> None:
        if not policies:
            return
        texts = [self._to_text(p) for p in policies]
        vecs  = self._embed_batch(texts)
        self._index = faiss.IndexFlatIP(self._dim)
        self._index.add(vecs)
        self._metadata = [
            {"policy_id": p.policy_id, "policy_type": p.policy_type,
             "text": texts[i], "description": p.description, "conditions": p.conditions}
            for i, p in enumerate(policies)
        ]
        self._save()
        logger.info("PolicyVectorStore: indexed %d policies", len(policies))

    def load_or_build(self, policies: list) -> None:
        if FAISS_INDEX_PATH.exists() and FAISS_META_PATH.exists():
            meta = json.loads(FAISS_META_PATH.read_text())
            if len(meta) == len(policies):
                self._load(); return
        self.build(policies)

    # ── Search ────────────────────────────────────────────────────────
    def search(self, query: str, k: int = TOP_K) -> list[PolicyChunk]:
        if self._index is None or self._index.ntotal == 0:
            return []
        q   = self._embed_batch([query])
        scores, idxs = self._index.search(q, min(k, self._index.ntotal))
        results = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < 0: continue
            m = self._metadata[idx]
            results.append(PolicyChunk(policy_id=m["policy_id"], policy_type=m["policy_type"],
                text=m["text"], score=float(score), description=m["description"], conditions=m["conditions"]))
        return results

    # ── Private ───────────────────────────────────────────────────────
    @staticmethod
    def _to_text(p) -> str:
        return f"{p.policy_type}: {p.description}\n{p.conditions}"

    def _embed_batch(self, texts: list[str]) -> np.ndarray:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        vecs = np.array([e.embedding for e in resp.data], dtype=np.float32)
        faiss.normalize_L2(vecs)
        return vecs

    def _save(self):
        FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(FAISS_INDEX_PATH))
        FAISS_META_PATH.write_text(json.dumps(self._metadata))

    def _load(self):
        self._index    = faiss.read_index(str(FAISS_INDEX_PATH))
        self._metadata = json.loads(FAISS_META_PATH.read_text())
        logger.info("PolicyVectorStore: loaded %d policies from disk", len(self._metadata))
