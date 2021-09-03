from __future__ import annotations
import glob
import os
import logging
import tempfile
import imagehash
from PIL import Image
import requests
import argparse
import ascii2d
import saberdb
import shutil
import configparser
import pixiv
import twitter

class Sabersort:
    def __init__(self, img_path_list:list, setting:SabersortSetting, logger:logging.Logger=logging.getLogger('sabersort'), except_dir:str=None) -> None:

        self.logger:logging.Logger = logger
        self.setting = setting

        self.db = saberdb.SaberDb(setting.db_path, logger)
        self.img_path_list = img_path_list

        self.logger.debug('{} images found.'.format(len(self.img_path_list)))

        self.dist_dir = setting.dist_dir
        self.user_agent = setting.user_agent

        self.logger.debug('Using user agent "{}" currently.'.format(self.user_agent))

        self.except_dir = setting.except_dir

        self.pixiv = pixiv.Pixiv(setting.pixiv_setting, self.logger)
        self.twitter = twitter.Twitter(setting.twitter_setting, self.logger)
    
    def sort(self) -> None:
        
        if self.setting.check_db:
            self.db.check_db(self.setting.check_db_hash)
        self.check_path()

        for src_img in self.img_path_list:
            if self.db.is_img_exist(src_img):

                self.logger.info('"{}" already existed in "{}", skipped.'.format(src_img, self.db.get_path_of_img(src_img)))

            else:
                new_search = ascii2d.Ascii2dSearch(src_img, logger=self.logger)
                new_search.search()
                if not new_search.result_found():
                    
                    self.logger.debug('No result found for "{}".'.format(src_img))

                    self.not_found_handler(src_img)
                else:

                    self.logger.debug('{} result found for "{}".'.format(str(len(new_search.search_result)),src_img))

                    src_hash = get_phash(src_img)
                    check_list = ascii2d.Ascii2dResultList()
                    if self.setting.threshold > 0 and len(new_search.search_result) > self.setting.threshold: # put the first [threshold] results into a list to check
                        for i in range(self.setting.threshold):
                            check_list.append(new_search.search_result[i])
                    else:
                        check_list = new_search.search_result
                    

                    match_results = ascii2d.Ascii2dResultList()
                    for result in check_list: # check the thumbnail on ascii2d matches the source image to make sure that is the correct image
                        with tempfile.NamedTemporaryFile() as tmp:

                            self.logger.debug('Retrieving thumbnail from "{}"'.format(result.thumbnail_link))

                            with requests.get(result.thumbnail_link, stream=True) as thumb:
                                for c in thumb.iter_content():
                                    if c:
                                        tmp.write(c)
                            if get_phash(tmp) == src_hash:
                                match_results.append(result)

                    if len(match_results):
                        self.logger.debug('{} results match the source image for "{}".'.format(str(len(match_results)),src_img))
                        
                        match_results.sort(key=lambda r: r.width, reverse=True)
                        fail = 0
                        for target in match_results:
                            if target.site == 'Twitter':
                                if self.twitter_handler(src_img, target):
                                    break
                            elif target.site == 'Pixiv':
                                if self.pixiv_handler(src_img, target):
                                    break
                            fail += 1
                        if fail == len(match_results):
                            self.not_found_handler(src_img)

                    else:
                        self.logger.debug('No result found for "{}".'.format(src_img))

                        self.not_found_handler(src_img)

    def check_path(self):
        if not os.path.isdir(self.dist_dir):
            os.mkdir(self.dist_dir)

            self.logger.warning('Output directory "{}" doesn\'t existed, automatically created.'.format(self.except_dir))

        if not os.path.isdir(self.except_dir):
            os.mkdir(self.except_dir)

            self.logger.warning('Exception directory "{}" doesn\'t existed, automatically created.'.format(self.except_dir))


    def twitter_handler(self, src_path:str, result:ascii2d.Ascii2dResult) -> bool: # twitter and pixiv handler can be combined into one, not implemented yet
        author = Ascii2dResolve.resolve_author_link(result)
        title = Ascii2dResolve.resolve_title(result)
        link_id = Ascii2dResolve.resolve_link_id(result)

        target_link:str = None
        target_ext:str = None
        target_filename:str = None

        thumb_links = self.twitter.get_image_urls(result.link)
        if len(thumb_links) <= 0:
            return False
        if len(thumb_links) == 1:
            target_link = twitter.get_original_image_url(thumb_links[0])
            target_ext = Ascii2dResolve.resolve_extension(result, target_link)
            target_filename = 'Twitter_{}_{}_{}'.format(title, link_id, author)
        if len(thumb_links) > 1:
            for thumb in thumb_links:
                with tempfile.NamedTemporaryFile() as tmp:
                    with requests.get(thumb, stream=True) as f:
                        for c in f.iter_content(4096):
                            if f:
                                tmp.write(c)
                    if get_phash(src_path) == get_phash(tmp):
                        target_link = twitter.get_original_image_url(thumb)
                        break
            target_ext = Ascii2dResolve.resolve_extension(result, target_link)
            target_filename = 'Twitter_{}_{}_{}'.format(title, link_id, author)

        if self.is_filename_dup(target_filename): # duplicated files handle
            is_content_dup, dist_path = self.dup_filename_handler(src_path, target_filename, target_ext)
            if not is_content_dup:
                self.twitter.get_image(target_link, dist_path)
                self.db.add_img(dist_path)
                self.logger.info('"{}" -> "{}"'.format(src_path, dist_path)) # successfully found match and image
            else:
                self.logger.info('"{}" is already existed in "{}"'.format(src_path, dist_path))
        else: # not duplicated
            dist_path = os.path.join(self.dist_dir,'{}{}'.format(target_filename, target_ext))
            self.twitter.get_image(target_link, os.path.join(self.dist_dir,'{}{}'.format(target_filename, target_ext)))
            self.db.add_img(dist_path)
            self.logger.info('"{}" -> "{}"'.format(src_path, dist_path)) # successfully found match and image
        return True

    def pixiv_handler(self, src_path:str, result:ascii2d.Ascii2dResult) -> bool:
        author = Ascii2dResolve.resolve_author_link(result)
        title = Ascii2dResolve.resolve_title(result)
        link_id = Ascii2dResolve.resolve_link_id(result)

        target_links = self.pixiv.get_image_urls(link_id)
        if target_links.original is None:
            return False
        else:
            target_link = target_links.original
            target_ext = Ascii2dResolve.resolve_extension(result, target_link)
            target_filename = 'Pixiv_{}_{}'.format(link_id, author)

            if self.is_filename_dup(target_filename): # duplicated files handle
                is_content_dup, dist_path = self.dup_filename_handler(src_path, target_filename, target_ext)
                if not is_content_dup:
                    self.twitter.get_image(target_link, dist_path)
                    self.db.add_img(dist_path)
                    self.logger.info('"{}" -> "{}"'.format(src_path, dist_path))
                else:
                    self.logger.info('"{}" is already existed in "{}"'.format(src_path, dist_path))
            else:
                dist_path = os.path.join(self.dist_dir,'{}{}'.format(target_filename, target_ext))
                self.pixiv.get_image(target_link, dist_path)
                self.logger.info('"{}" -> "{}"'.format(src_path, dist_path))
        return True

    def is_filename_dup(self, targt_filename:str):
        return bool(len(glob.glob(os.path.join(self.dist_dir, '{}*'.format(targt_filename)))))

    def dup_filename_handler(self, src_path: str, target_filename:str, file_extension:str) -> tuple:
        src_hash = get_phash(src_path)
        dups_path = glob.glob(os.path.join(self.dist_dir, '{}*'.format(target_filename)))

        dups_hash = dict()
        for p in dups_path:
            dups_hash[get_phash(p)] = p

        if not src_hash in dups_hash.keys():
            n = len(dups_path)
            return False, os.path.join(self.dist_dir, '{}_{}{}'.format(target_filename, str(n+1), file_extension))
        else:
            return True, dups_hash[src_hash]

    def not_found_handler(self, src_path:str, dist_path:str=None) -> None:
        dist = self.except_dir if dist_path is None else dist_path
        if not os.path.isabs(dist):
            dist = os.path.join(self.dist_dir, dist)
        shutil.copy2(src_path, dist)
        self.logger.info('"{}" -> "{}"'.format(src_path, dist))

class SabersortSetting:
    def __init__(self, db_path:str, dist_dir:str, pixiv_setting:pixiv.PixivSetting, twitter_setting:twitter.TwitterSetting, \
    user_agent:str=None, except_dir:str=None, check_db:bool=False, check_db_hash:bool=False, threshold:int=0) -> None:
        self.db_path = db_path
        self.dist_dir = dist_dir
        self.except_dir = except_dir
        self.pixiv_setting = pixiv_setting
        self.twitter_setting = twitter_setting
        self.user_agent = user_agent
        self.check_db = check_db
        self.check_db_hash = check_db_hash
        self.threshold =threshold

class Ascii2dResolve:
    @staticmethod
    def resolve_link_id(result:ascii2d.Ascii2dResult) -> str:
        return result.link.split('/')[-1]
    
    @staticmethod
    def resolve_title(result:ascii2d.Ascii2dResult) -> str:
        return ''.join(result.title.split('.')) if result.site == 'Twitter' else result.title
    
    @staticmethod
    def resolve_author_link(result:ascii2d.Ascii2dResult) -> str:
        if result.site == 'Twitter':
            ra = result.author_link.split('=')
            if len(ra) > 1:
                return '{}({})'.format(ra[-1], result.author)
            else:
                return result.author_link.split('/')[-1]
        elif result.site == 'Pixiv':
            return '{}({})'.format(result.author_link.split('/')[-1], result.author)
        return ''
    
    @staticmethod
    def resolve_extension(result:ascii2d.Ascii2dResult, img_url:str):
        if result.site == 'Twitter':
            return '.{}'.format(img_url.split('format=')[-1].split('&')[0])
        if result.site == 'Pixiv':
            return '.{}'.format(img_url.split('/')[-1].split('.')[-1])
        return ''
        

def get_phash(img) -> imagehash.ImageHash:
    return imagehash.phash(Image.open(img))

if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-c', '--check-db', help='check if images in the database are still there',  action='store_true')
    argparser.add_argument('-ch', '--check-db-hash', help='check if image in the database are still there and correct.', action='store_true')
    argparser.add_argument('-sw','--show-window', help='show chrome window while fetching twitter image.', action='store_false')
    argparser.add_argument('-t', '--threshold', help='number of results to check while searching on ascii2d', default=0, type=int, action='store')
    argparser.add_argument('-v', '--verbose', help='increase output verbosity', action='store_true')

    args = argparser.parse_args()

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    loglvl = logging.DEBUG if args.verbose else logging.INFO

    logfile = logging.FileHandler('sabersort.log', 'a')
    logfile.setFormatter(formatter)

    consolelog = logging.StreamHandler()
    consolelog.setFormatter(formatter)
    consolelog.setLevel(loglvl)

    logger = logging.getLogger('sabersort')
    logger.setLevel(loglvl)
    logger.addHandler(logfile)
    logger.addHandler(consolelog)

    config = configparser.RawConfigParser()
    config.optionxform = str
    config.read('config.ini')

    sections = config.sections()
    if not os.path.isfile('config.ini'):
        with open('config.ini', 'w+') as cf:
            config.write(cf)
    if not 'sabersort' in sections:
        config['sabersort'] = {'Input directory': '', 'Output directory':'', 'Exception directory':'', 'Database path': 'saberdb.db', 'User-agent': ''}
        with open('config.ini', 'w+') as cf:
            config.write(cf)
    if not 'pixiv' in sections:
        config['pixiv'] = {'PHPSESSID': '', 'device_token': ''}
        with open('config.ini', 'w+') as cf:
            config.write(cf)
    if not 'twitter' in sections:
        config['twitter'] = {'Chrome webdriver path': ''}
        with open('config.ini', 'w+') as cf:
            config.write(cf)

    if not os.path.isdir(ind :=config.get('sabersort', 'Input directory')):
        logger.error('Input "{}" directory is not valid.'.format(ind))

    if not os.path.isdir(outd :=config.get('sabersort', 'Output directory')):
        try:
            os.mkdir(outd)
            logger.info('Output directory "{}" doesn\'t exists, has been automatically created.'.format(outd))
        except OSError:
            logger.error('Output directory is not valid.')

    if not os.path.isdir(excd :=config.get('sabersort', 'Exception directory')):
        try:
            os.mkdir(excd)
            logger.info('Exception directory "{}" doesn\'t exists, has been automatically created.'.format(excd))
        except OSError:
            logger.error('Exception directory is not valid, default exception directory will be used.')
    
    if not os.path.isfile(p :=config.get('sabersort', 'Database path')):
        try:
            config.set('sabersort', 'Database path', 'saberdb.db')
        except OSError:
            logger.error('Database path is not valid.')

    if os.path.isdir(ind := config.get('sabersort', 'Input directory')) and os.path.isdir(outd := config.get('sabersort', 'Output directory')):
        excd = os.path.join(outd, 'Exceptions') if not os.path.isdir(config.get('sabersort', 'Exception directory')) else config.get('sabersort', 'Exception directory')
        img_list = glob.glob('{}\\*'.format(ind))

        a = vars(args)
        ps = pixiv.PixivSetting(config.get('pixiv', 'PHPSESSID'), config.get('pixiv', 'device_token'), config.get('sabersort', 'User-agent'))
        ts = twitter.TwitterSetting(config.get('twitter', 'Chrome webdriver path'), config.get('sabersort', 'User-agent'))
        s = SabersortSetting(config.get('sabersort', 'Database path'), outd, ps, ts, config.get('sabersort', 'User-agent'), excd, a['check_db'], a['check_db_hash'], a['threshold'])

        saber = Sabersort(img_list, s, logger)
        saber.sort()