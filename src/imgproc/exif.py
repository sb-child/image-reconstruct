import math
import tifffile
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final, Optional

# Rationals
_RATS = frozenset({tifffile.DATATYPE.RATIONAL, tifffile.DATATYPE.SRATIONAL})

# https://exiftool.org/TagNames/EXIF.html
# https://helpx.adobe.com/content/dam/help/en/camera-raw/digital-negative/jcr_content/root/content/flex/items/position/position-par/download_section_733958301/download-1/DNG_Spec_1_7_1_0.pdf
T_SUB_IFD = 0x014A  # 类型没写
# --- SubIFD
T_BLACK_LEVEL = 0xC61A  # rational64u[n]! SHORT/LONG/RATIONAL
T_WHITE_LEVEL = 0xC61D  # int32u[n]! SHORT/LONG
T_ACTIVE_AREA = 0xC68D  # int32u[4]! SHORT/LONG
T_CROP_ORIGIN = 0xC61F  # int32u[2]! DefaultCropOrigin SHORT/LONG/RATIONAL
T_CROP_SIZE = 0xC620  # int32u[2]! DefaultCropSize SHORT/LONG/RATIONAL
# --- IFD0
T_IMAGE_WIDTH = 0x0100  # int32u!
T_IMAGE_HEIGHT = 0x0101  # int32u!
T_PHOTOMETRIC = 0x0106  # int16u!
T_MAKE = 0x010F  # string
T_MODEL = 0x0110  # string
T_ORIENTATION = 0x0112  # int16u，1..8；方向的唯一来源
T_SOFTWARE = 0x0131  # string
T_UNIQUE_CAM = 0xC614  # string UniqueCameraModel
T_SERIAL = 0xC62F  # string CameraSerialNumber
T_BASELINE = 0xC62A  # SRATIONAL BaselineExposure，允许负值
T_EXIF_IFD = 0x8769  # ExifOffset
# --- ExifIFD
T_EXPOSURE_TIME = 0x829A  # rational64u
T_FNUMBER = 0x829D  # rational64u
T_ISO = 0x8827  # int16u[n]
T_DATETIME_ORIGINAL = 0x9003  # string "YYYY:MM:DD HH:MM:SS"
T_OFFSET_TIME_ORIGINAL = 0x9011  # string "+08:00"
T_SUBSEC_TIME_ORIGINAL = 0x9291  # string，秒的小数部分
T_FOCAL_LENGTH = 0x920A  # rational64u，镜头实际焦距 mm
T_FOCAL_35MM = 0xA405  # int16u FocalLengthIn35mmFormat
T_FP_XRES = 0xA20E  # rational64u FocalPlaneXResolution
# T_FP_UNIT: (1 None, 2 inches, 3 cm, 4 mm, 5 um). values 1, 4 and 5 are not standard EXIF.
T_FP_UNIT = 0xA210  # int16u FocalPlaneResolutionUnit
T_PIXEL_X = 0xA002  # int16u: ExifImageWidth (PixelXDimension)
T_BODY_SERIAL = 0xA431  # string BodySerialNumber
T_LENS_MAKE = 0xA433  # string LensMake
T_LENS_MODEL = 0xA434  # string LensModel
T_LENS_SERIAL = 0xA435  # string LensSerialNumber
# --- ExifIFD -> ISO
T_SENSITIVITY_TYPE = 0x8830  # int16u SensitivityType
T_SOS = 0x8831  # int32u StandardOutputSensitivity
T_REI = 0x8832  # int32u RecommendedExposureIndex
T_ISO_SPEED = 0x8833  # int32u
# ---

# 只包含 ExifIFD Tag
_RATIONAL_TAGS = frozenset({T_EXPOSURE_TIME, T_FNUMBER, T_FOCAL_LENGTH, T_FP_XRES})

# ISO 回退顺序：标准标签优先，再试 REI / SOS / ISO Speed
_ISO_TAGS: Final[tuple[int, ...]] = (T_ISO, T_REI, T_SOS, T_ISO_SPEED)

# --- T_SENSITIVITY_TYPE 取值
_SENSITIVITY_TYPE_ENC: Final[dict[tuple[bool, bool, bool], int]] = {
    (False, False, False): 0,  # unknown
    (True, False, False): 1,  # SOS
    (False, True, False): 2,  # REI
    (False, False, True): 3,  # ISO
    (True, True, False): 4,  # SOS+REI
    (True, False, True): 5,  # SOS+ISO
    (False, True, True): 6,  # REI+ISO
    (True, True, True): 7,  # SOS+REI+ISO
}
_SENSITIVITY_TYPE_DEC: Final[dict[int, tuple[bool, bool, bool]]] = {
    v: k for k, v in _SENSITIVITY_TYPE_ENC.items()
}
_SENSITIVITY_TYPE_SHORT: Final[dict[int, str]] = {
    0: "unknown",
    1: "SOS",
    2: "REI",
    3: "ISO",
    4: "SOS+REI",
    5: "SOS+ISO",
    6: "REI+ISO",
    7: "SOS+REI+ISO",
}


# frozen 实现 __hash__
# slots 实现 __slots__
@dataclass(frozen=True, slots=True)
class SensitivityType:
    # Standard Output Sensitivity (T_SOS)
    sos: bool
    # Recommended Exposure Index (T_REI)
    rei: bool
    # ISO Speed (T_ISO_SPEED)
    iso: bool

    @property
    def code(self) -> int:
        return _SENSITIVITY_TYPE_ENC[(self.sos, self.rei, self.iso)]

    @classmethod
    def from_code(cls, i: int) -> SensitivityType:
        try:
            return cls(*_SENSITIVITY_TYPE_DEC[i])
        except KeyError:
            raise ValueError(f"预期 0..=7, 输入 {i}") from None

    @property
    def anchored(self) -> bool:
        """是否含物理锚点"""
        return self.sos or self.iso

    @property
    def tags(self) -> tuple[int, ...]:
        return tuple(
            t
            for flag, t in (
                (self.sos, T_SOS),
                (self.rei, T_REI),
                (self.iso, T_ISO_SPEED),
            )
            if flag
        )

    def __str__(self) -> str:
        return _SENSITIVITY_TYPE_SHORT[self.code]


def to_sensitivity_type(i: int) -> SensitivityType:
    sos = i == 1 or i == 4 or i == 5 or i == 7
    rei = i == 2 or i == 4 or i == 6 or i == 7
    iso = i == 3 or i == 5 or i == 6 or i == 7
    return SensitivityType(sos, rei, iso)


# ---


@dataclass
class ExifInfo:
    # --- 曝光三要素
    iso: Optional[float] = None
    f_number: Optional[float] = None
    exposure_time: Optional[float] = None
    # DNG BaselineExposure，单位 EV；正值表示默认渲染更亮。
    # 它不是拍摄时的 ExposureBiasValue，也不参与 brightness 计算。
    baseline_exposure: Optional[float] = None
    # 诊断：ISO 实际来自哪个标签
    iso_tag: Optional[int] = None
    # 诊断：0x8830 SensitivityType，枚举 0..7（不是位掩码）
    sensitivity_type: Optional[int] = None

    # --- 静态身份
    # Make/Model：相机厂商和型号，用于相机分组。
    make: Optional[str] = None
    model: Optional[str] = None
    # DNG 的 UniqueCameraModel；同机型的 DNG 通常相同。
    unique_camera_model: Optional[str] = None
    # DNG 0xC62F 与 EXIF 0xA431，可能只有一个存在。
    camera_serial: Optional[str] = None
    body_serial: Optional[str] = None

    # --- 镜头
    # 标准 EXIF 镜头标签；有些相机只把镜头信息写在 MakerNotes，
    # 此时这里会是 None，不能据此判断“没有镜头信息”。
    lens_make: Optional[str] = None
    lens_model: Optional[str] = None
    lens_serial: Optional[str] = None

    # --- 拍摄时间
    # 原始 EXIF 墙上时间字符串 "YYYY:MM:DD HH:MM:SS"。
    datetime_original: Optional[str] = None
    # 时区偏移字符串，例如 "+08:00"；缺失时为 None。
    offset_time_original: Optional[str] = None
    # 秒的小数部分字符串，例如 "73" 表示 0.73 秒。
    subsec_time_original: Optional[str] = None
    # 由上面三者解析出的带时区 datetime；解析失败或缺失时为 None。
    captured_at: Optional[datetime] = None

    # --- 方向
    # EXIF Orientation，1..8；缺失或非法时归一为 1。
    # 这是方向的唯一来源：rawpy 侧只消费它，不再读 raw.sizes.flip。
    orientation: int = 1

    # --- 光学
    # 镜头实际焦距，单位 mm。
    focal_length_mm: Optional[float] = None
    # 35mm 等效焦距，单位 mm-equivalent。
    focal_length_35mm: Optional[int] = None
    # FocalPlaneXResolution，单位是“像素 / focal_plane_res_unit”。
    focal_plane_x_res: Optional[float] = None
    # 2=inch, 3=cm, 4=mm, 5=um；1 表示无单位。
    focal_plane_res_unit: Optional[int] = None

    @property
    def valid(self) -> bool:
        return all(
            v is not None and v > 0
            for v in (self.exposure_time, self.f_number, self.iso)
        )

    @property
    def brightness(self) -> Optional[float]:
        """相对记录曝光量 a ∝ t·ISO/N²。相机内可比，跨机不可比。"""
        t, N, s = self.exposure_time, self.f_number, self.iso
        if t is None or N is None or s is None or t <= 0 or N <= 0 or s <= 0:
            return None
        return t * s / (N * N)

    def focal_px(self, width: int, height: int) -> Optional[float]:
        """按 COLMAP 的顺序估算输出图像的像素焦距。

        1. FocalLengthIn35mmFormat: f35 / 43.27 * sqrt(w² + h²)
        2. FocalLength + FocalPlaneXResolution + unit
        3. 返回 None，由 COLMAP 用传感器数据库或 1.2*max(w,h) 兜底

        width/height 必须是最终输出图像尺寸，不是 EXIF IFD0 里的尺寸。
        """
        if width <= 0 or height <= 0:
            return None

        if self.focal_length_35mm and self.focal_length_35mm > 0:
            return self.focal_length_35mm / 43.27 * math.hypot(width, height)

        mm = self.focal_length_mm
        res = self.focal_plane_x_res
        unit = self.focal_plane_res_unit
        if mm is None or mm <= 0 or res is None or res <= 0:
            return None

        if unit == 2:  # inches
            pixels_per_mm = res / 25.4
        elif unit == 3:  # cm
            pixels_per_mm = res / 10.0
        elif unit == 4:  # mm
            pixels_per_mm = res
        elif unit == 5:  # um
            pixels_per_mm = res * 1000.0
        else:
            return None
        return mm * pixels_per_mm


def _tags_of(page: tifffile.TiffPage) -> dict[int, Any]:
    """把 IFD0 和 ExifIFD 合并成统一的 标签号 -> 值。

    tifffile 对 IFD0 给 标签号->值，对 ExifIFD 给 标签名->值，
    所以先用 TIFF.EXIF_TAGS 反向映射；ExifIFD 覆盖 IFD0。
    """
    tags: dict[int, Any] = {t.code: t.value for t in page.tags.values()}
    # DNG样本 ExposureTime/FNumber/ISO 直接写在 IFD0
    #   33434: (42225216, 1000000000)  # ExposureTime
    #   33437: (180, 100)  # FNumber
    #   34855: 444  # ISOSpeedRatings
    #   50730: (141, 100)  # BaselineExposure
    #   ...
    #   没有 34665 (T_EXIF_IFD)
    # NEF样本 写在 0x8769 指向的 ExifIFD，tifffile 解析成 {标签名: 值}
    #   34665 (T_EXIF_IFD): {"ExposureTime": (10, 100), "FNumber": (28, 10),
    #           "ISOSpeedRatings": 1000, "SensitivityType": 2,
    #           "RecommendedExposureIndex": 1000, ...}
    #   没有 33434/33437/34855

    exif = page.tags.valueof(T_EXIF_IFD)
    # DNG样本: None（IFD0 没有 0x8769 (T_EXIF_IFD)）
    # NEF样本: {"ExposureTime": (10, 100), "FNumber": (28, 10),
    #           "ISOSpeedRatings": 1000, "SensitivityType": 2,
    #           "RecommendedExposureIndex": 1000, ...}

    if isinstance(exif, dict):
        # DNG样本: False，跳过
        # NEF样本: True
        # 遍历字典
        for name, value in exif.items():
            # 样本 name="ExposureTime" value=(10, 100)
            code = tifffile.TIFF.EXIF_TAGS.get(name)
            # 样本 code=33434
            if isinstance(code, int):
                tags[code] = value
                # tags 新增
                # 样本 33434 -> (10, 100)
    return tags


def _rational(value: Any) -> Optional[float]:
    """RATIONAL/SRATIONAL -> float。tifffile 返回 (分子, 分母)。"""
    # DNG: _rational((42225216, 1000000000)) -> 0.042225216
    # DNG: _rational((180, 100))             -> 1.8
    # DNG: _rational((141, 100))             -> 1.41
    # NEF: _rational((10, 100))              -> 0.1
    # NEF: _rational((28, 10))               -> 2.8
    # NEF: _rational(None)                   -> None
    if value is None:
        return None

    if hasattr(value, "tolist"):
        value = value.tolist()
        # 本样本走不到这里：tifffile 返回 tuple

    if isinstance(value, (int, float)):
        return float(value)
        # 本样本走不到这里：曝光相关值都是 tuple

    if not isinstance(value, (tuple, list)) or len(value) != 2:
        return None
        # 本样本走不到这里：长度都是 2

    num, den = value
    # DNG: 42225216 / 1000000000
    # NEF: 10 / 100
    return float(num) / float(den) if den else None


def _first_int(value: Any) -> Optional[int]:
    """SHORT/LONG 可能是数组，取第一个。"""
    # DNG: _first_int(444)  -> 444
    # NEF: _first_int(1000) -> 1000
    # DNG: _first_int(None) -> None
    if value is None:
        return None

    if hasattr(value, "tolist"):
        value = value.tolist()
        # 本样本走不到这里：ISO 是 int

    if isinstance(value, (tuple, list)):
        value = value[0] if value else None
        # 本样本走不到这里：ISO 是 int

    try:
        return int(value) if value is not None else None
    except TypeError, ValueError:
        return None


def _text(value: Any) -> Optional[str]:
    """EXIF ASCII 字符串 -> 去掉 NUL 和首尾空白的 str。

    tifffile 通常已经返回 str；少数文件会返回 bytes 或长度为 1 的数组。
    """
    if value is None:
        return None

    if isinstance(value, bytes):
        value = value.split(b"\x00", 1)[0].decode("utf-8", "replace")
    elif isinstance(value, (tuple, list)):
        value = value[0] if value else None

    if not isinstance(value, str):
        return None

    value = value.split("\x00", 1)[0].strip()
    return value or None


def _captured_at(
    date: Optional[str],
    offset: Optional[str],
    subsec: Optional[str],
) -> Optional[datetime]:
    """把 EXIF 的日期、时区、亚秒合成一个 datetime。

    DNG: date="2026:08:13 18:48:59", offset=None, subsec=None
         -> naive datetime(2026, 8, 13, 18, 48, 59)
    NEF: date="2025:12:04 23:30:17", offset="+08:00", subsec="73"
         -> aware datetime(2025, 12, 4, 23, 30, 17, 730000, tz=+08:00)
    """
    if not date:
        return None

    try:
        dt = datetime.strptime(date, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None

    if subsec:
        digits = "".join(c for c in subsec if c.isdigit())
        if digits:
            # "73" -> 0.73s -> 730000us
            dt = dt.replace(microsecond=int(digits.ljust(6, "0")[:6]))

    if offset:
        try:
            tz = datetime.fromisoformat("2000-01-01T00:00:00" + offset).tzinfo
            dt = dt.replace(tzinfo=tz)
        except ValueError:
            pass

    return dt


def _read_iso(tags: dict[int, Any]) -> tuple[Optional[float], Optional[int]]:
    """取 ISO 并返回来源标签号。

    0x8827 ISOSpeedRatings 是标准标签，优先使用。
    没有 0x8827 时，SensitivityType 告诉我们哪个标签才是相机的锚点：
      1=SOS(0x8831), 2=REI(0x8832), 3=ISO Speed(0x8833)，4..7 是组合。
    最后再按 REI/SOS/ISO Speed 的固定顺序兜底。
    """
    iso = _first_int(tags.get(T_ISO))
    # DNG: 444
    # NEF: 1000
    if iso:
        return float(iso), T_ISO

    candidates: tuple[int, ...] = _ISO_TAGS[1:]
    sensitivity_type = _first_int(tags.get(T_SENSITIVITY_TYPE))
    if sensitivity_type is not None:
        try:
            preferred = SensitivityType.from_code(sensitivity_type).tags
        except ValueError:
            pass
        else:
            candidates = (
                *preferred,
                *(t for t in candidates if t not in preferred),
            )

    for code in candidates:
        iso = _first_int(tags.get(code))
        if iso:
            return float(iso), code

    return None, None


def from_file(tf: tifffile.TiffFile) -> ExifInfo:
    """从 TIFF/DNG/NEF 的 IFD0 + ExifIFD 读取静态元数据。

    只放 EXIF 能可靠提供的信息：身份、镜头、时间、方向、曝光、光学。
    解码后的尺寸、裁切、黑/白电平、白平衡、色彩矩阵、CFA 不在这里读，
    它们由 batch_raw.read_raw() 从 rawpy 读取，避免两个来源重叠。
    """
    if not tf.pages:
        raise ValueError("TIFF 中没有 IFD")

    if not isinstance(tf.pages[0], tifffile.TiffPage):
        raise ValueError("TIFF page 0 不是 TiffPage")
    else:
        tags = _tags_of(tf.pages[0])  # pyright: ignore[reportArgumentType]
        # DNG: 54 项，ISO/曝光/光圈都在
        # NEF: 28 项，ExifIFD 的标签已并入

    iso, iso_tag = _read_iso(tags)
    # DNG: 444.0,  0x8827
    # NEF: 1000.0, 0x8827

    exposure_time = _rational(tags.get(T_EXPOSURE_TIME))
    # DNG: (42225216, 1000000000) -> 0.042225216
    # NEF: (10, 100)             -> 0.1

    f_number = _rational(tags.get(T_FNUMBER))
    # DNG: (180, 100) -> 1.8
    # NEF: (28, 10)   -> 2.8

    baseline_exposure = _rational(tags.get(T_BASELINE))
    # DNG: (141, 100) -> 1.41
    # NEF: None       -> None

    sensitivity_type = _first_int(tags.get(T_SENSITIVITY_TYPE))
    # DNG: None
    # NEF: 2（REI）

    orientation = _first_int(tags.get(T_ORIENTATION)) or 1
    if orientation not in range(1, 9):
        orientation = 1
    # DNG: 6 (RIGHTTOP)
    # NEF: 1 (TOPLEFT)

    datetime_original = _text(tags.get(T_DATETIME_ORIGINAL))
    # DNG: "2026:08:13 18:48:59"
    # NEF: "2025:12:04 23:30:17"

    offset_time_original = _text(tags.get(T_OFFSET_TIME_ORIGINAL))
    # DNG: None
    # NEF: "+08:00"

    subsec_time_original = _text(tags.get(T_SUBSEC_TIME_ORIGINAL))
    # DNG: None
    # NEF: "73"

    captured_at = _captured_at(
        datetime_original,
        offset_time_original,
        subsec_time_original,
    )
    # DNG: 2026-08-13 18:48:59（naive）
    # NEF: 2025-12-04 23:30:17.730000+08:00

    focal_length_mm = _rational(tags.get(T_FOCAL_LENGTH))
    # DNG: (444, 100) -> 4.44
    # NEF: (700, 10) -> 70.0

    focal_length_35mm = _first_int(tags.get(T_FOCAL_35MM))
    # DNG: None
    # NEF: 70

    focal_plane_x_res = _rational(tags.get(T_FP_XRES))
    # DNG: None
    # NEF: None

    focal_plane_res_unit = _first_int(tags.get(T_FP_UNIT))
    # DNG: None
    # NEF: None

    return ExifInfo(
        exposure_time=exposure_time,
        f_number=f_number,
        iso=iso,
        baseline_exposure=baseline_exposure,
        iso_tag=iso_tag,
        sensitivity_type=sensitivity_type,
        make=_text(tags.get(T_MAKE)),
        # DNG: "Google"
        # NEF: "NIKON CORPORATION"
        model=_text(tags.get(T_MODEL)),
        # DNG: "Pixel 3"
        # NEF: "NIKON D5"
        unique_camera_model=_text(tags.get(T_UNIQUE_CAM)),
        # DNG: "Pixel 3-Google-google"
        # NEF: None
        camera_serial=_text(tags.get(T_SERIAL)),
        # DNG: None
        # NEF: None
        body_serial=_text(tags.get(T_BODY_SERIAL)),
        # DNG: None
        # NEF: None
        lens_make=_text(tags.get(T_LENS_MAKE)),
        # DNG/NEF: None
        lens_model=_text(tags.get(T_LENS_MODEL)),
        # DNG/NEF: None
        lens_serial=_text(tags.get(T_LENS_SERIAL)),
        # DNG/NEF: None
        datetime_original=datetime_original,
        offset_time_original=offset_time_original,
        subsec_time_original=subsec_time_original,
        captured_at=captured_at,
        orientation=orientation,
        focal_length_mm=focal_length_mm,
        focal_length_35mm=focal_length_35mm,
        focal_plane_x_res=focal_plane_x_res,
        focal_plane_res_unit=focal_plane_res_unit,
        # DNG: ExifInfo(iso=444.0, f_number=1.8,
        #               exposure_time=0.042225216,
        #               baseline_exposure=1.41,
        #               orientation=6,
        #               make="Google", model="Pixel 3",
        #               focal_length_mm=4.44,
        #               focal_length_35mm=None,
        #               focal_plane_x_res=None)
        # NEF: ExifInfo(iso=1000.0, f_number=2.8,
        #               exposure_time=0.1,
        #               baseline_exposure=None,
        #               orientation=1,
        #               make="NIKON CORPORATION", model="NIKON D5",
        #               focal_length_mm=70.0,
        #               focal_length_35mm=70,
        #               focal_plane_x_res=None)
    )
