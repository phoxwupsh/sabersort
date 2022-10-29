from __future__ import annotations
from dataclasses import dataclass
from genericpath import isfile
from sqlite3 import connect, Error
from imagehash import ImageHash, hex_to_hash, hex_to_flathash
if not __name__ == '__main__':
    from saberdb.hasher import Hasher
from utils import split_list
from PIL import Image
from os import stat
from threading import Thread, RLock
from multiprocessing import cpu_count

class SaberDB():
    def __init__(self, config: SaberDBConfig, hasher: Hasher) -> None:
        self.config = config
        self.hasher = hasher
        self.lock = RLock()
        self.conn = None
        self.cur = None
        try:
            self.conn = connect(self.config.db_path,check_same_thread=False)
            self.cur = self.conn.cursor()
        except Error as e:
            print(e)
        self.cur.execute('CREATE TABLE IF NOT EXISTS `saberdb` (hash text PRIMARY KEY, width integer, height integer, size integer, path text);')
        if self.config.check_db:
            self.check_db()
    
    def is_img_in_db(self, img: ImageHash | str) -> bool:
        hash_obj = self.__get_hash_obj(img)
        self.lock.acquire()
        self.cur.execute(f'SELECT hash FROM `saberdb` WHERE hash="{hash_obj}"')
        self.lock.release()
        return not self.cur.fetchone() is None
    
    def is_img_valid(self, img_hash: ImageHash | str, img_path) -> bool:
        hash_obj = self.__get_hash_obj(img_hash)
        if not isfile(img_path):
            return False
        with Image.open(img_path) as target_img:
            target_hash = self.hasher.hash(target_img)
            return hash_obj == target_hash
    
    def add_img(self, img_path:str):
        with Image.open(img_path) as img:
            img_hash = self.hasher.hash(img)
            self.cur.execute(f'INSERT INTO `saberdb` VALUES("{str(img_hash)}", {img.width}, {img.height}, {stat(img_path).st_size}, "{img_path}")')
            try:
                self.lock.acquire()
                self.conn.commit()
            finally:
                self.lock.release()
    
    def get_img(self, img: ImageHash | str) -> ImageEntry | None:
        hash_obj = self.__get_hash_obj(img)
        self.cur.execute(f'SELECT hash, width, height, size, path FROM `saberdb` WHERE hash="{str(hash_obj)}"')
        result = self.cur.fetchone()
        if result is None:
            return None
        return ImageEntry(hex_to_hash(result[0]),result[1],result[2],result[3],result[4])
    
    def del_img(self, img:ImageHash | str):
        hash_obj = self.__get_hash_obj(img)
        self.lock.acquire()
        self.cur.execute(f'DELETE FROM `saberdb` WHERE hash="{str(hash_obj)}"')
        self.conn.commit()
        self.lock.release()
    
    def check_db(self):
        threads = list[Thread]()
        
        def check_db_thread(check_list:list):
            for img in check_list:
                img_hash = self.__get_hash_obj(img[0])
                img_path = img[1]
                if not self.is_img_valid(img_hash, img_path):
                    self.lock.acquire()
                    self.del_img(img_hash)
                    self.lock.release()

        self.cur.execute('SELECT hash, path FROM `saberdb`')
        check_list = self.cur.fetchall()
        for l in split_list(check_list, self.config.threads):
            t = Thread(target=check_db_thread, args=(l,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    def __get_hash_obj(self, h: ImageHash | str):
        if isinstance(h, ImageHash):
            return h
        return hex_to_flathash(h, self.hasher.hash_size)
    
@dataclass
class ImageEntry:
    hash: ImageHash
    width: int
    height: int
    size: int
    path: str

class SaberDBConfig:
    def __init__(self, db_path: str = 'saberdb.db', check_db:bool=False, threads: int = 0) -> None:
        self.db_path = db_path
        self.check_db = check_db
        self.threads = threads if threads > 0 else cpu_count()

if __name__ == "__main__":
    pass