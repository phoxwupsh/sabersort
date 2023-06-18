from __future__ import annotations

from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SaberRecord(Base):
    __tablename__ = 'saberdb'

    hash = Column(String, primary_key=True)
    author = Column(String)
    author_id = Column(String)
    author_link = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    origin_link = Column(String)
    path = Column(String)
    size = Column(Integer)

    def __init__(
        self,
        hash: str,
        author: str,
        author_id: str,
        author_link: str,
        width: int,
        height: int,
        origin_link: str,
        path: str,
        size: int,
    ) -> None:
        self.hash = hash
        self.author = author
        self.author_id = author_id
        self.author_link = author_link
        self.width = width
        self.height = height
        self.origin_link = origin_link
        self.path = path
        self.size = size
