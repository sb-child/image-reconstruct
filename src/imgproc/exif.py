import tifffile
from dataclasses import dataclass
from typing import Optional

# https://www.itu.int/itudoc/itu-t/com16/tiff-fx/docs/tiff6.pdf
# TIFF Revision 6.0 Final — June 3, 1992
# 第 15, 16 页
(
    BYTE,  # 8-bit unsigned integer.
    ASCII,  # 8-bit byte that contains a 7-bit ASCII code; the last byte must be NUL (binary zero).
    SHORT,  # 16-bit (2-byte) unsigned integer.
    LONG,  # 32-bit (4-byte) unsigned integer.
    RATIONAL,  # Two LONGs: the first represents the numerator of a fraction; the second, the denominator.
    # --- TIFF 6.0 new
    SBYTE,  # An 8-bit signed (twos-complement) integer.
    UNDEFINED,  # An 8-bit byte that may contain anything, depending on the definition of the field.
    SSHORT,  # A 16-bit (2-byte) signed (twos-complement) integer.
    SLONG,  # A 32-bit (4-byte) signed (twos-complement) integer.
    SRATIONAL,  # Two SLONG’s: the first represents the numerator of a fraction, the second the denominator.
    FLOAT,  # Single precision (4-byte) IEEE format.
    DOUBLE,  # Double precision (8-byte) IEEE format.
    # ---
    # https://gitlab.com/libtiff/libtiff/-/blob/master/libtiff/tiff.h?ref_type=heads#L160
    # Warning: It is possible that other TIFF field types will be added in the future.
    #          Readers should skip over fields containing an unexpected field type.
) = range(1, 13)
_SIZE = {
    BYTE: 1,
    ASCII: 1,
    SHORT: 2,
    LONG: 4,
    RATIONAL: 8,
    SBYTE: 1,
    UNDEFINED: 1,
    SSHORT: 2,
    SLONG: 4,
    SRATIONAL: 8,
    FLOAT: 4,
    DOUBLE: 8,
}
_RATS = frozenset({tifffile.DATATYPE.RATIONAL, tifffile.DATATYPE.SRATIONAL})
_INTS = frozenset({BYTE, UNDEFINED, SHORT, LONG, SBYTE, SSHORT, SLONG})

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
