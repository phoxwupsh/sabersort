from __future__ import annotations
from abc import ABCMeta, abstractmethod
from io import BufferedRandom

class Origin(metaclass=ABCMeta):
    @abstractmethod
    def fetch_data(self, url: str) -> OriginData:
        raise NotImplementedError
    
    @abstractmethod
    def fetch_img(self, url: str, dist: BufferedRandom):
        raise NotImplementedError

class OriginData:
    def __init__(self, original: list[str], thumb: list[str], variant: int):
        self.original = original
        self.thumb = thumb
        self.variant = variant

class DeletedException(BaseException):
    pass