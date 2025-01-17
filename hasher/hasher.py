from __future__ import annotations

from enum import Enum

from imagehash import (
    ImageHash,
    ImageMultiHash,
    average_hash,
    colorhash,
    crop_resistant_hash,
    dhash,
    phash,
    phash_simple,
    whash,
)
from PIL import Image


class Hasher:
    def __init__(self, hash_alg: HashAlg, hash_size: int = 16) -> None:
        match hash_alg:
            case HashAlg.Average:
                self.__hasher__ = average_hash
            case HashAlg.Perceptual:
                self.__hasher__ = phash
            case HashAlg.PerceptualSimple:
                self.__hasher__ = phash_simple
            case HashAlg.Difference:
                self.__hasher__ = dhash
            case HashAlg.Wavelet:
                self.__hasher__ = whash
            case HashAlg.HSV:
                self.__hasher__ = colorhash
            case HashAlg.CropResistant:
                self.__hasher__ = crop_resistant_hash
        self.hash_size = hash_size

    def hash(self, img: Image.Image) -> ImageHash | ImageMultiHash:
        return self.__hasher__(img, self.hash_size)


class HashAlg(Enum):
    Average = 'average'
    Perceptual = 'perceptual'
    PerceptualSimple = 'perceptualsimple'
    Difference = 'difference'
    Wavelet = 'wavelet'
    HSV = 'hsv'
    CropResistant = 'cropresistant'

    @classmethod
    def from_str(cls, s: str):
        for o in cls:
            if o.value == s.lower():
                return o
        raise ValueError
