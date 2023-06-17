from multiprocessing import cpu_count

class SabersortConfig:
    def __init__(self, src_dir:str, dist_dir:str, not_found_dir:str, except_dir:str, filename_fmt: str, threshold: int = 0, user_agent: str = None) -> None:
        self.src_dir = src_dir
        self.dist_dir = dist_dir
        self.not_found_dir = not_found_dir
        self.except_dir = except_dir
        self.filename_fmt = filename_fmt
        self.threads = cpu_count()
        self.threshold = threshold
        self.user_agent = user_agent