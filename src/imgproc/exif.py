import tifffile
from dataclasses import dataclass
from typing import Final, Optional

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
T_SOFTWARE = 0x0131  # string
T_UNIQUE_CAM = 0xC614  # string UniqueCameraModel
T_SERIAL = 0xC62F  # string CameraSerialNumber
T_EXIF_IFD = 0x8769  # ExifOffset
# --- ExifIFD
T_EXPOSURE_TIME = 0x829A  # rational64u
T_FNUMBER = 0x829D  # rational64u
T_ISO = 0x8827  # int16u[n]
T_FOCAL_LENGTH = 0x920A  # rational64u
T_FOCAL_35MM = 0xA405  # int16u FocalLengthIn35mmFormat
T_FP_XRES = 0xA20E  # rational64u FocalPlaneXResolution
# T_FP_UNIT: (1 None, 2 inches, 3 cm, 4 mm, 5 um). values 1, 4 and 5 are not standard EXIF.
T_FP_UNIT = 0xA210  # int16u FocalPlaneResolutionUnit
T_PIXEL_X = 0xA002  # int16u: ExifImageWidth (PixelXDimension)
T_LENS_MODEL = 0xA434  # string
# --- ExifIFD -> ISO
T_SENSITIVITY_TYPE = 0x8830  # int16u SensitivityType
T_SOS = 0x8831  # int32u StandardOutputSensitivity
T_REI = 0x8832  # int32u RecommendedExposureIndex
T_ISO_SPEED = 0x8833  # int32u
# ---

# 只包含 ExifIFD Tag
_RATIONAL_TAGS = frozenset({T_EXPOSURE_TIME, T_FNUMBER, T_FOCAL_LENGTH, T_FP_XRES})

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
    iso: Optional[float] = None
    f_number: Optional[float] = None
    exposure_time: Optional[float] = None
    baseline_exposure: Optional[float] = None
    # 诊断：ISO 实际来自哪个标签
    iso_tag: Optional[int] = None
    # 诊断：34865 位掩码
    sensitivity_type: Optional[int] = None

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


def from_file(tf: tifffile.TiffFile) -> ExifInfo:

    # todo
    return ExifInfo(
        exposure_time=0.0,
        f_number=0.0,
        iso=0.0,
    )
