import os

from contextlib import asynccontextmanager
from fastapi import FastAPI

# Anything from the fastapi application lives within the api/ directory
from api.db import init_db
from api.chat.routing import router as chat_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Before app startup...
    # Start the database before the app is initialized
    init_db()
    yield

    # After app startup...

app = FastAPI(lifespan=lifespan)

# Adding the chat module router with a prefix to all routes set within routing.py
app.include_router(chat_router, prefix="/api/chats")

# with a fallback
MY_PROJECT = os.environ.get("MY_PROJECT") or "fallback project name"

# for a secret, don't leak
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise NotImplementedError("API_KEY was not set")

@app.get("/")
def read_index():
    return {
        "hello": "are you there?",
        "project name": MY_PROJECT,
        "API_KEY": API_KEY
    }