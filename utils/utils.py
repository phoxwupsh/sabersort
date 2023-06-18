from io import BufferedIOBase
from typing import Any
from pathlib import Path

import aiofiles
from aiofiles.threadpool.binary import AsyncBufferedIOBase
from imagehash import ImageHash, ImageMultiHash


def split_list(list_: list[Any], n: int) -> list[list[Any]]:
    k, m = divmod(len(list_), n)
    return [list_[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n)]


async def async_copyfile(src: str | Path, dst: str | Path, chunk_size: int = 4096):
    async with aiofiles.open(src, 'rb') as r:
        async with aiofiles.open(dst, 'wb+') as w:
            await async_copyfileobj(r, w, chunk_size)


async def async_copyfileobj(
    async_fsrc: AsyncBufferedIOBase, async_fdst: AsyncBufferedIOBase, chunk_size: int = 4096
):
    while True:
        chunk = await async_fsrc.read(chunk_size)
        if not chunk:
            break
        await async_fdst.write(chunk)


async def async_write_file(src: BufferedIOBase, dist: AsyncBufferedIOBase):
    while True:
        chunk = src.read(4096)
        if not chunk:
            break
        await dist.write(chunk)


def is_identical(hash_1: ImageHash | ImageMultiHash, hash_2: ImageHash | ImageMultiHash, threshold: int = 0) -> bool:
    return get_bias(hash_1, hash_2) <= threshold


def get_bias(hash_1: ImageHash | ImageMultiHash, hash_2: ImageHash | ImageMultiHash) -> int:
    if isinstance(hash_1, ImageHash) and isinstance(hash_2, ImageHash):
        return abs(hash_1 - hash_2)
    elif isinstance(hash_1, ImageMultiHash) and isinstance(hash_2, ImageMultiHash):
        return hash_1.hash_diff(hash_2)[1]
    else:
        raise TypeError
