from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from cache import create_index_if_not_exists, get_cached_or_none, save_to_cache
from embedding_model import get_embedding

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_index_if_not_exists()  # runs on startup
    yield
    # anything after yield runs on shutdown (nothing needed here)

app = FastAPI(lifespan=lifespan)

class CheckRequest(BaseModel):
    text: str

class SaveRequest(BaseModel):
    prompt: str
    response: str

@app.post("/check")
def check(req: CheckRequest):
    embedding = get_embedding(req.text)
    cached = get_cached_or_none(embedding)
    return {"cached": cached}

@app.post("/save")
def save(req: SaveRequest):
    embedding = get_embedding(req.prompt)
    save_to_cache(req.prompt, req.response, embedding)
    return {"status": "saved"}

@app.get("/health")
def health():
    return {"status": "ok"}