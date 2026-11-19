from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM mappings in the public Supabase schema."""

    metadata = MetaData(schema="public")
