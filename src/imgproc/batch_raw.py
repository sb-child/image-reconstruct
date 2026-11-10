import heapq
import tifffile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import rawpy
from rawpy import RawPy

from . import exif


def process(p: Path) -> list["FileInfo"]:
    """读取目录下所有 DNG/NEF 的静态信息。

    目前只收集元数据，不写图；返回列表供后续批级校验和 COLMAP 使用。
    """
    files = heapq.merge(
        p.glob("*.dng", case_sensitive=False),
        p.glob("*.nef", case_sensitive=False),
    )
    result: list[FileInfo] = []
    for f in files:
        print(f"正在处理: {f}")
        result.append(process_file(f))
    return result


def process_file(file: Path) -> "FileInfo":
    """读取一张 RAW 的 EXIF 静态信息和 rawpy 解码参数。

    两个来源严格分工：
    - exif.from_file(tf): 身份、镜头、时间、方向、曝光、光学
    - read_raw(raw, orientation): 解码尺寸、裁切、电平、白平衡、色彩、CFA
    """
    with tifffile.TiffFile(file) as tf:
        e = exif.from_file(tf)

    with rawpy.imread(str(file)) as raw:
        r = read_raw(raw, e.orientation)

    return FileInfo(path=file, exif=e, raw=r)


# write here -------


@dataclass(frozen=True, slots=True)
class RawInfo:
    """rawpy/LibRaw 能可靠提供的“解码后几何与色彩”信息。

    这里刻意不包含曝光、ISO、焦距、相机型号、拍摄时间、方向：
    这些属于 EXIF 静态元数据，由 exif.ExifInfo 唯一负责。
    """

    # 最终输出尺寸（像素），已按 EXIF orientation 交换宽高。
    # 这是写图/COLMAP 的相机宽高，不是 raw 尺寸，也不是 crop 尺寸。
    # DNG: 3024x4032 (orientation=6)
    # NEF: 5584x3728 (orientation=1)
    width: int
    height: int

    # LibRaw 解包后的原始尺寸（含 margin）。
    # DNG: 4032x3024；NEF: 5584x3728
    raw_width: int
    raw_height: int

    # 去掉 margin 的可见区域（LibRaw iwidth/iheight）。
    # DNG: 4032x3024；NEF: 5584x3728
    visible_width: int
    visible_height: int
    top_margin: int
    left_margin: int
    pixel_aspect: float

    # LibRaw 的默认裁切框。
    # 注意：rawpy.postprocess() 默认不应用它。
    # DNG: crop=4016x3008，但输出仍是 4032x3024。
    # NEF: crop=5568x3712，但输出仍是 5584x3728。
    crop_left: int
    crop_top: int
    crop_width: int
    crop_height: int

    # 每通道黑电平/白电平；rawpy 返回整数，可能已做取整。
    # DNG: black=[63,63,63,64], white=1023
    # NEF: black=[400,400,400,400], white=16383
    black_level: tuple[int, int, int, int]
    white_level: int
    camera_white_level: Optional[tuple[int, int, int, int]]

    # 白平衡系数 [R, G1, B, G2]；G2 可能为 0，wb.py 会补。
    # camera_whitebalance: 拍摄时白平衡，逐张可能不同。
    # daylight_whitebalance: 日光白平衡，适合整批固定色彩基准。
    # DNG: camera=[2.0941, 1.0, 1.4183, 0.0]
    # NEF: camera=[2.0967, 1.0, 1.6411, 1.0]
    camera_whitebalance: tuple[float, float, float, float]
    daylight_whitebalance: tuple[float, float, float, float]

    # color_matrix: 3x4；rgb_xyz_matrix: 4x3。
    # LibRaw 不保证两个都非零：DNG 样本只有 color_matrix，
    # NEF 样本只有 rgb_xyz_matrix。
    color_matrix: tuple[tuple[float, ...], ...]
    rgb_xyz_matrix: tuple[tuple[float, ...], ...]

    # CFA：num_colors/color_desc 是颜色编号说明，
    # raw_pattern 是 2x2 相位。
    # DNG: num_colors=3, color_desc="RGBG", pattern=[[2,3],[1,0]]
    # NEF: num_colors=3, color_desc="RGBG", pattern=[[0,1],[3,2]]
    num_colors: int
    color_desc: str
    raw_pattern: Optional[tuple[tuple[int, ...], ...]]


@dataclass(frozen=True, slots=True)
class FileInfo:
    """一张 RAW 的完整静态信息：EXIF 元数据 + rawpy 解码参数。"""

    path: Path
    exif: exif.ExifInfo
    raw: RawInfo


def _output_size(sizes: rawpy.ImageSizes, orientation: int) -> tuple[int, int]:
    """把 LibRaw 的翻转前尺寸换算成最终输出尺寸。

    LibRaw 的 width/height 是翻转前尺寸；EXIF Orientation 5..8
    表示需要 90 度旋转，所以输出宽高要交换。

    DNG: 4032x3024, orientation=6 -> 3024x4032
    NEF: 5584x3728, orientation=1 -> 5584x3728
    """
    width, height = sizes.width, sizes.height
    if orientation in (5, 6, 7, 8):
        width, height = height, width
    return width, height


def read_raw(raw: RawPy, orientation: int) -> RawInfo:
    """读取 rawpy 的解码参数。

    orientation 来自 exif.ExifInfo，是方向的唯一来源；这里只用它
    换算输出尺寸。raw.sizes.flip 不读取，避免和 EXIF Orientation
    重叠，也避免写图时双重旋转。
    """
    sizes = raw.sizes
    width, height = _output_size(sizes, orientation)

    black = raw.black_level_per_channel
    camera_white = raw.camera_white_level_per_channel
    camera_wb = raw.camera_whitebalance
    daylight_wb = raw.daylight_whitebalance
    pattern = raw.raw_pattern

    return RawInfo(
        width=width,
        height=height,
        raw_width=sizes.raw_width,
        raw_height=sizes.raw_height,
        visible_width=sizes.iwidth,
        visible_height=sizes.iheight,
        top_margin=sizes.top_margin,
        left_margin=sizes.left_margin,
        pixel_aspect=sizes.pixel_aspect,
        crop_left=sizes.crop_left_margin,
        crop_top=sizes.crop_top_margin,
        crop_width=sizes.crop_width,
        crop_height=sizes.crop_height,
        black_level=(black[0], black[1], black[2], black[3]),
        white_level=raw.white_level,
        camera_white_level=(
            (camera_white[0], camera_white[1], camera_white[2], camera_white[3])
            if camera_white
            else None
        ),
        camera_whitebalance=(
            camera_wb[0],
            camera_wb[1],
            camera_wb[2],
            camera_wb[3],
        ),
        daylight_whitebalance=(
            daylight_wb[0],
            daylight_wb[1],
            daylight_wb[2],
            daylight_wb[3],
        ),
        color_matrix=tuple(
            tuple(float(value) for value in row) for row in raw.color_matrix
        ),
        rgb_xyz_matrix=tuple(
            tuple(float(value) for value in row) for row in raw.rgb_xyz_matrix
        ),
        num_colors=raw.num_colors,
        color_desc=raw.color_desc.decode("ascii", "replace"),
        raw_pattern=(
            tuple(tuple(int(value) for value in row) for row in pattern)
            if pattern is not None
            else None
        ),
    )
