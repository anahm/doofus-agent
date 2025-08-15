from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from api.db import get_session
from .models import ChatMessagePayload, ChatMessage, ChatMessageListItem

# APIRouter similar to an @app.get() command
router = APIRouter()

# /api/chats/
@router.get("/")
def chat_health():
    return {"status": "ok"}

# /api/chats/recent/
# curl http://localhost:8080/api/chats/recent/
@router.get("/recent", response_model=List[ChatMessageListItem])
def chat_list_messages(session: Session = Depends(get_session)):
    # Creating a SQL query via Python using the built-in features of SQLModel
    query = select(ChatMessage)

    results = session.exec(query).fetchall()[:10]
    return results

# HTTP POST request where payload = {"message": "Hello World"} --> {"message": "Hello World", "id": 1}
# curl -X POST -d '{"message": "Hello world"}' -H "Content-Type: application/json" http://localhost:8080/api/chats/
# Returns back the data that was received and the ID of the database
@router.post("/", response_model=ChatMessage)
def chat_create_message(
    payload: ChatMessagePayload,
    session: Session = Depends(get_session) # database session, defaults to the api.db session
):
    # Pydantic function that takes the payload and converts into a Python dict
    data = payload.model_dump()
    print(data)

    # Database-level validation
    # Makes sure all fields defined are available
    # Verify that the incoming data is valid for the table we want to write to
    obj = ChatMessage.model_validate(data)

    # Ready to store into the database
    # You can add a lot of them before committing
    session.add(obj)

    # Put everything in the table
    session.commit()

    # Ensure that ID/primary key added to the obj instance
    session.refresh(obj)

    return obj