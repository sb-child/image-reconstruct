from typing import List

import numpy as np


def norm_white_balance(
    camera_whitebalance: List[float], k: float = 1.0
) -> np.typing.NDArray:
    """
    归一化相机白平衡参数。

    - camera_whitebalance: 带有4个float值的数组。
    - k: raw_G2 / raw_G1 的灵敏度比。k=1.0 则 G2 等于 G1。
    """
    assert len(camera_whitebalance) == 4, "camera_whitebalance 的长度必须是 4"
    # wb = [R:f64, G1:f64, B:f64, G2:f64]
    wb = np.asarray(camera_whitebalance, dtype=np.float64).ravel()
    # np.isfinite() 返回相同shape的布尔数组，如果元素是无限值则为 True
    # np.all() 返回布尔值，如果所有元素都是无限值则返回 True
    assert np.all(np.isfinite(wb)), "数组元素不能都是无限值"
    assert wb[0] > 0, f"R 必须大于 0, 当前值 {wb[0]}"
    assert wb[1] > 0, f"G1 必须大于 0, 当前值 {wb[1]}"
    assert wb[2] > 0, f"B 必须大于 0, 当前值 {wb[2]}"
    # 有些 RAW 图像不带 G2
    has_g2 = wb[3] > 0
    if not has_g2:
        # 没有 G2，则通过 k 计算出
        wb[3] = wb[1] / k
    # 用 G1 归一化白平衡数组
    r: np.typing.NDArray = wb / wb[1]
    return r
