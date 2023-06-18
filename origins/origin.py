from __future__ import annotations

from abc import ABCMeta, abstractmethod
from enum import Enum
from io import BytesIO


class Origin(metaclass=ABCMeta):
    @abstractmethod
    async def fetch_data(self, url: str) -> OriginData:
        raise NotImplementedError

    @abstractmethod
    async def fetch_img(self, url: str) -> BytesIO:
        raise NotImplementedError


class OriginData:
    def __init__(self, original: list[str], thumb: list[str], variant: int):
        self.original = original
        self.thumb = thumb
        self.variant = variant


class DeletedException(BaseException):
    pass


class OriginType(Enum):
    Twitter = 'twitter'
    Pixiv = 'pixiv'
    Niconico = 'niconico'
    Fanbox = 'fanbox'

    @classmethod
    def from_str(cls, s: str):
        for o in cls:
            if o.value == s.lower():
                return o
        raise ValueError
