from typing import List, Union
from . import tools, execute

_colmap_conf = tools.colmap_conf()


def run(args: Union[List[str], list]) -> bool:
    return execute.execute_bin(_colmap_conf.bin, args)
