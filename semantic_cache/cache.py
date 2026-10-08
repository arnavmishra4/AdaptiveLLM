from sentence_transformers import SentenceTransformer
from redis.commands.search.query import Query
from redis.commands.search.field import TextField, TagField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.json.path import Path
import uuid
import numpy as np
import redis


# --- connection ---
r = redis.Redis(host="redis", port=6379, decode_responses=False)

EMBEDDING_DIM = 1024  # change this to match whatever embedding model you use later
INDEX_NAME = "cache_idx"
KEY_PREFIX = "cache:"


# --- Step 1: create the index once at startup ---
def create_index_if_not_exists():
    try:
        r.ft(INDEX_NAME).info()
        print("Redis cache index already exists")
    except Exception:
        schema = (
            TextField("prompt"),
            TextField("response"),
            VectorField(
                "embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": EMBEDDING_DIM,
                    "DISTANCE_METRIC": "COSINE",
                },
            ),
        )
        r.ft(INDEX_NAME).create_index(
            fields=schema,
            definition=IndexDefinition(prefix=[KEY_PREFIX], index_type=IndexType.HASH),
        )
        print("Redis cache index created")


# --- Step 2: save a prompt+response+embedding to the cache ---
def save_to_cache(prompt: str, response: str, embedding: list[float], ttl_seconds: int = 3600):
    key = f"{KEY_PREFIX}{uuid.uuid4()}"
    vector_bytes = np.array(embedding, dtype=np.float32).tobytes()

    r.hset(key, mapping={
        "prompt": prompt,
        "response": response,
        "embedding": vector_bytes,
    })
    r.expire(key, ttl_seconds)


# --- Step 3: search for the closest cached entry ---
def search_cache(query_embedding: list[float], top_k: int = 1):
    vector_bytes = np.array(query_embedding, dtype=np.float32).tobytes()

    query = (
        Query(f"*=>[KNN {top_k} @embedding $vec AS score]")
        .sort_by("score")
        .return_fields("prompt", "response", "score")
        .dialect(2)
    )

    results = r.ft(INDEX_NAME).search(query, query_params={"vec": vector_bytes})
    return results.docs


# --- Step 4: the actual "check cache" helper you call from app.py ---
def get_cached_or_none(embedding: list[float], threshold: float = 0.15):
    results = search_cache(embedding, top_k=1)

    if not results:
        return None

    best = results[0]
    score = float(best.score)  # lower = more similar, for COSINE distance

    if score < threshold:
        return best.response
    return None