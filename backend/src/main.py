import os
from fastapi import FastAPI

app = FastAPI()

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
        "project name": MY_PROJECT
    }