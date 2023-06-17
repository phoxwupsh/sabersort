from saber import Saber
from saberdb import SaberDB, SaberDBConfig
from hasher import Hasher, HashAlg
from ascii2d import Ascii2d, Ascii2dConfig, OriginType, SortOrder
from origins.pixiv import Pixiv, PixivConfig
from origins.twitter import Twitter, TwitterConfig
from saber import SaberConfig
import asyncio
import rtoml


if __name__ == '__main__':
    with open('config.toml', 'r') as c:
        config = rtoml.load(c)
    
    in_dir: str = config['sabersort']['input']
    out_dir: str = config['sabersort']['found']
    nf_dir: str = config['sabersort']['not_found']
    exc_dir: str = config['sabersort']['exception']
    fmt: str = config['sabersort']['filename']
    threshold: int = config['sabersort']['threshold']
    user_agent: str = config['sabersort']['user_agent']
    sabersort_cfg = SaberConfig(in_dir, out_dir, nf_dir, exc_dir, fmt, threshold, user_agent)

    db_path: str = config['saberdb']['database_path']
    db_cfg = SaberDBConfig(db_path)
    db = SaberDB(db_cfg)

    hash_alg = HashAlg.from_str(config['hasher']['hash_algorithm'])
    hash_size: int = config['hasher']['hash_size']
    hasher = Hasher(hash_alg, hash_size)

    prefered = OriginType.from_str(config['ascii2d']['perfered_origin'])
    sort_order = SortOrder.from_str(config['ascii2d']['sort_order'])
    first: int = config['ascii2d']['first']
    ascii2d_cfg = Ascii2dConfig(user_agent, sort_order, first, prefered)
    ascii2d = Ascii2d(ascii2d_cfg)

    phpsessid: str = config['pixiv']['PHPSESSID']
    pixiv_cfg = PixivConfig(phpsessid,user_agent)
    pixiv = Pixiv(pixiv_cfg)

    auth_token: str = config['twitter']['auth_token']
    headless: bool = config['twitter']['headless']
    twitter_cfg = TwitterConfig(auth_token, user_agent, headless)
    twitter = Twitter(twitter_cfg)
    
    saber = Saber(sabersort_cfg, ascii2d, hasher, db, pixiv, twitter)
    
    asyncio.run(saber.sort())