# File with all baseline configurations for the postgres database

import os

import sqlmodel

from sqlmodel import Session, SQLModel

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL == "":
    raise NotImplementedError("`DATABASE_URL` needs to be set")

# Create a database engine connection
engine = sqlmodel.create_engine(DATABASE_URL)

# Ensure database models are inside the database
# NOTE: This does not create db migrations, aka cannot change the database itself or change what's inside the model
def init_db():
    print("creating database tables...")
    SQLModel.metadata.create_all(engine)

# Useful for API routes
def get_session():
    with Session(engine) as session:
        yield session