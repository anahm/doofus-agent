from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, DateTime

def get_utc_now():
    return datetime.now().replace(tzinfo=timezone.utc)

# This is a Pydantic model for validation
class ChatMessagePayload(SQLModel):
    message: str

# Creating a model (that is also a table?) for saving, updating, getting, deleting AND serializing
class ChatMessage(SQLModel, table=True):
    # ID set as primary key, an auto-incrementing integer (b/c primary_key field) or defaults as None
    id: int | None = Field(default=None, primary_key=True)
    # Without None as a default option, this field is required
    message: str
    created_at: datetime = Field(
        default_factory=get_utc_now,
        # timezone-aware datetime
        sa_type=DateTime(timezone=True),
        primary_key=False,
        nullable=False
    )

class ChatMessageListItem(SQLModel):
    id: int | None = Field(default=None)
    message: str
    created_at: datetime = Field(default=None)