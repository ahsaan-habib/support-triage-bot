"""Help-centre retrieval: one chunk per `##` section."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from . import config

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@dataclass
class Article:
    id: str
    source: str
    title: str
    text: str
    score: float

    @property
    def cite(self) -> str:
        return f"{self.source} › {self.title}"


@lru_cache(maxsize=1)
def _embed() -> SentenceTransformer:
    return SentenceTransformer(config.EMBED_MODEL)


@lru_cache(maxsize=1)
def _col():
    return chromadb.PersistentClient(path=config.INDEX_DIR).get_or_create_collection(
        "help", metadata={"hnsw:space": "cosine"})


def index(docs_dir: str = config.DOCS_DIR) -> int:
    ids, texts, metas = [], [], []
    for path in sorted(Path(docs_dir).glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        for i, part in enumerate(re.split(r"^## ", path.read_text(), flags=re.M)[1:]):
            title, _, body = part.partition("\n")
            ids.append(f"{path.stem}-{i}")
            texts.append(f"{title.strip()}\n{body.strip()}")
            metas.append({"source": path.name, "title": title.strip()})
    _col().upsert(ids=ids, documents=texts, metadatas=metas,
                  embeddings=_embed().encode(texts, normalize_embeddings=True).tolist())
    return len(ids)


def search(query: str, k: int = 4, min_score: float = 0.55) -> list[Article]:
    vec = _embed().encode(QUERY_PREFIX + query, normalize_embeddings=True).tolist()
    res = _col().query(query_embeddings=[vec], n_results=k)
    hits = [Article(i, m["source"], m["title"], d, 1 - dist) for i, d, m, dist in
            zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])]
    return [a for a in hits if a.score >= min_score]


if __name__ == "__main__":
    print(f"indexed {index()} help sections")
