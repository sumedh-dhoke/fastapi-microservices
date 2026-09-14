from sqlmodel import SQLModel,Field
from typing import Optional


class User(SQLModel,table=True): # table=True indicates that this model should be treated as a database table. This is used by SQLModel to generate the appropriate SQL statements for creating and interacting with the table in the database.
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str 
    password: str

class UserPublic(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str 
        