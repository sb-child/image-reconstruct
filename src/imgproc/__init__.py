import os
import numpy as np
import rawpy
from rawpy import ColorSpace
from pathlib import Path

import tifffile
from image_reconstruct import colmap
from . import batch_raw
from . import wb
from . import exif


def main() -> None:
    # print("Hello from imgproc!")
    # colmap.run([])
    open_file()
    # bp = Path("/home/sbchild/下载").resolve()
    # batch_raw.process(bp)


# def probe(path, chunk=1 << 16):
#     """返回 (文件大小, 首个失败偏移或None, 失败原因, 尾部是否可读)"""
#     size = os.path.getsize(path)
#     if size == 0:
#         return size, 0, "空文件"
#     fd = os.open(path, os.O_RDONLY)
#     try:
#         bad = None
#         for off in range(0, size, chunk):
#             want = min(chunk, size - off)
#             try:
#                 b = os.pread(fd, chunk, off)
#             except OSError as e:
#                 bad = (off, f"pread: {e.strerror}"); break
#             if len(b) < want:
#                 bad = (off + len(b), f"短读 {len(b)}/{want}"); break
#         tail_ok = None
#         if bad:
#             try:
#                 tail_ok = len(os.pread(fd, 4096, max(0, size - 4096))) > 0
#             except OSError as e:
#                 tail_ok = f"否 ({e.strerror})"
#         return size, bad, tail_ok
#     finally:
#         os.close(fd)


def open_file2():
    WANT = {33434, 33437, 34665, 34855, 34864, 34865, 34866, 34867, 50714, 50717}
    bp = Path("/run/media/sbchild/Ventoy/camera").resolve()
    for i in bp.glob("*.dng", case_sensitive=False):
        print(f"--- {i.name}")
        tf = tifffile.TiffFile(i)
        print("  byteorder:", tf.byteorder, " pages:", len(tf.pages))
        for i, page in enumerate(tf.pages):
            codes = {t.code for t in page.tags.values()}  # pyright: ignore[reportAttributeAccessIssue]
            print(
                f"  page{i} off={page.offset} ntags={len(codes)} "
                f"34665={34665 in codes} 34855={34855 in codes}"
            )
            for t in page.tags.values():  # pyright: ignore[reportAttributeAccessIssue]
                if t.code in WANT:
                    nm = getattr(t, "name", str(t.code))
                    if isinstance(t.value, dict):
                        print(
                            f"    {t.code:#06x} {nm:28s} {t.dtype} "
                            f"count={t.count} value=(dict)"
                        )
                        for k, v in t.value.items():
                            if isinstance(v, str):
                                print(
                                    f"    (str) key={k} value={v[: min(20, len(v))]} value_len={len(v)}"
                                )
                            elif isinstance(v, bytes):
                                print(
                                    f"    (bytes) key={k} value={v[: min(20, len(v))].hex()} value_len={len(v)}"
                                )
                            else:
                                print(f"    key={k} value={v!r}")
                    else:
                        print(
                            f"    {t.code:#06x} {nm:28s} {t.dtype} "
                            f"count={t.count} value={t.value!r}"
                        )
        tf.close()


def open_file():
    # bp = Path("/home/sbchild/下载").resolve()
    bp = Path("/run/media/sbchild/Ventoy/camera").resolve()
    # fn = "_DSC9130.NEF"
    # fn = "IMG_20261025_101414.030.dng"

    # bp = Path("/tmp").resolve()
    # bp = Path("/home/sbchild/下载/我的奶").resolve()

    for i in bp.glob("*.dng", case_sensitive=False):
        tf = tifffile.TiffFile(i)
        e = exif.from_file(tf)
        print(e, e.valid, e.brightness)
    # CFGS = {
    #     "A 默认(0.75)": dict(adjust_maximum_thr=0.75),
    #     "B thr=0": dict(adjust_maximum_thr=0.0),
    #     "C thr=0, no_scale": dict(adjust_maximum_thr=0.0, no_auto_scale=True),
    # }
    # RES: dict[str, dict[str, tuple[float, float]]] = {}
    # for name, cfg in CFGS.items():
    #     per: dict[str, tuple[float, float]] = {}
    #     for i in bp.glob("*.dng", case_sensitive=False):
    #         with rawpy.imread(str(i)) as raw:
    #             o = raw.other
    #             print(
    #                 "shutter_speed:",
    #                 o.shutter_speed,
    #                 "aperture:",
    #                 o.aperture,
    #                 "iso_speed:",
    #                 o.iso_speed,
    #             )
    #             calc_wb = list(wb.norm_white_balance(raw.camera_whitebalance))
    #             img = raw.postprocess(
    #                 user_wb=calc_wb,
    #                 no_auto_bright=True,
    #                 gamma=(1, 1),
    #                 output_bps=16,
    #                 output_color=ColorSpace.sRGB,
    #                 **cfg,  # pyright: ignore[reportArgumentType]
    #             )
    #         # 零额外内存；float64 累加避免 3600 万像素的 float32 求和误差
    #         per[i.name] = (img.mean(dtype=np.float64) / 65535.0, img.max() / 65535.0)
    #         print(
    #             f"--- {name} {i.name} "
    #             f"mean={per[i.name][0]:.8f} peak={per[i.name][1]:.5f}"
    #         )
    #     RES[name] = per
    # # ================= 配对比较 =================
    # names = list(CFGS)
    # base = names[0]
    # common = sorted(set.intersection(*(set(RES[n]) for n in names)))
    # print(f"\n共有 {len(common)} 张，基准 = {base}\n")
    # for name in names[1:]:
    #     r = np.array([RES[name][k][0] / RES[base][k][0] for k in common])
    #     pk = np.array([RES[base][k][1] for k in common])
    #     print(f"{name:18s} vs {base}")
    #     print(
    #         f"  r: median={np.median(r):.5f}  "
    #         f"CV={r.std(ddof=0) / r.mean() * 100:6.2f}%  "
    #         f"span={r.max() / r.min():6.2f}"
    #     )
    #     print(f"  corr(r, peak) = {np.corrcoef(pk, r)[0, 1]:+.3f}")
