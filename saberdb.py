import imagehash
from PIL import Image
import logging
import os
import sqlite3

class SaberDb:
    def __init__(self, db_path:str, logger:logging.Logger = logging.getLogger('saberdb')) -> None:

        self.logger = logger
        
        self.conn = sqlite3.connect(db_path)
        cur = self.conn.cursor()
        cur.execute('create table if not exists saberdb(phash text, size integer, width integer, height integer, path text)')
        self.conn.commit()

    def in_db(self, img_path:str) -> bool:
        cur = self.conn.cursor()
        cur.execute('select *  from saberdb where phash="{}"'.format(self.get_phash(img_path)))
        return bool(len(cur.fetchall()))

    def get_phash(self, img_path:str) -> str:
        return str(imagehash.phash(Image.open(img_path), 16))

    def add_img(self, img_path:str) -> None:
        hash = self.get_phash(img_path)
        w, h = Image.open(img_path).size
        s = os.stat(img_path).st_size
        cur = self.conn.cursor()
        cur.execute('insert into saberdb values("{}", {}, {}, {}, "{}")'.format(hash, s, w, h, img_path))
        
        self.logger.debug('Image with phash={}, size={}, integer={}, width={}, path={} added to the database.'.format(hash, s, w, h, img_path))

        self.conn.commit()
    
    def is_img_exist(self, img_path:str) ->bool:
        if self.in_db(img_path):
            img_in_db_path = self.get_path_of_img(img_path)
            if os.path.isfile(img_in_db_path):
                if self.get_phash(img_path) == self.get_phash(img_in_db_path):
                    return True
        return False

    def get_path_of_img(self, img_path) -> str:
        cur = self.conn.cursor()
        cur.execute('select * from saberdb where phash="{}"'.format(self.get_phash(img_path)))
        r = cur.fetchall()
        return r[0][4] if len(r) > 0 else ''
    
    def del_img(self, img_path:str) -> None:
        self.del_img_phash(self.get_phash(img_path))
    
    def del_img_phash(self, h: str):
        cur = self.conn.cursor()
        cur.execute('delete from saberdb where phash="{}"'.format(h))
        self.conn.commit()

        self.logger.debug('Image with phash={} deleted from the database.'.format(h))

    def check_db(self, check_hash:bool) -> None:
        cur = self.conn.cursor()
        cur.execute('select * from saberdb')
        r = cur.fetchall()
        for i in r:
            if not os.path.isfile(i[4]):
                self.del_img_phash(i[0])
                self.logger.debug('{} doesn\'t exists, deleted from database.'.format(i[4]))
            else:
                if check_hash:
                    if not self.get_phash(i[4]) == i[0]:
                        self.del_img_phash(i[0])
                        self.logger.debug('{} has been modified, deleted from database.'.format(i[4]))
                    else:
                        self.logger.debug('{} exists and the hash matches.'.format(i[4]))
                else:
                    self.logger.debug('{} exists, but the hash hasn\'t been checked.'.format(i[4]))


if __name__ == '__main__':
    pass