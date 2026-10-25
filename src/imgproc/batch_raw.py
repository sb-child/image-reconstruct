import numpy as np
import rawpy
import heapq
import tifffile
from rawpy import RawPy  # pyright: ignore[reportPrivateImportUsage]
from pathlib import Path


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
        p0 = tf.pages[0]
        assert isinstance(p0, tifffile.TiffPage)
        t = p0.tags
        print(t["ExposureTime"])
        print(t["FNumber"])
        print(t["ISOSpeedRatings"])
        # num, den = t["ExposureTime"].value
        # t_val = num / den
        # num, den = t["FNumber"].value
        # N_val = num / den
        # iso = t["ISOSpeedRatings"].value
    with rawpy.imread(str(file)) as raw:
        process_file_raw(raw)
        pass


def process_file_raw(raw: RawPy):

    pass
