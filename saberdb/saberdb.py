from __future__ import annotations

import atexit

from genericpath import isfile
from imagehash import ImageHash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from saber.context import SaberContext
from saberdb.model import Base, SaberRecord


class SaberDB:
    def __init__(self, config: SaberDBConfig) -> None:
        self.config = config
        engine = create_engine(f'sqlite:///{self.config.db_path}')
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)
        self.db = session()
        atexit.register(self.__cleanup)

    def is_img_in_db_and_valid(self, ctx: SaberContext) -> tuple[bool, bool]:
        target = self.get(ctx.hash)
        if target is None:
            return False, False
        if not isfile(target.path):
            return True, False
        return True, target.hash == str(ctx.hash)

    def add(self, item: SaberRecord):
        self.db.add(item)
        self.db.commit()

    def get(self, img_hash: ImageHash) -> SaberRecord | None:
        res = self.db.query(SaberRecord).filter_by(hash=str(img_hash)).one_or_none()
        return res

    def delete(self, img_hash: ImageHash):
        self.db.query(SaberRecord).filter_by(hash=str(img_hash)).delete()
        self.db.commit()

    def __cleanup(self):
        self.db.close_all()


class SaberDBConfig:
    def __init__(self, db_path: str = 'saberdb.db') -> None:
        self.db_path = db_path
