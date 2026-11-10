import numpy as np
import rawpy
import heapq
import tifffile
from rawpy import RawPy
from pathlib import Path
from . import exif


def process(p: Path):
    files = heapq.merge(
        p.glob("*.dng", case_sensitive=False),
        p.glob("*.nef", case_sensitive=False),
    )
    for f in files:
        print(f"正在处理: {f}")
        process_file(f)


def process_file(file: Path):
    with tifffile.TiffFile(file) as tf:
        e = exif.from_file(tf)

    with rawpy.imread(str(file)) as raw:
        process_file_raw(raw)
        pass


def process_file_raw(raw: RawPy):

    pass


# write here -------
