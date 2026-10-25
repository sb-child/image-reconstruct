import subprocess
from pathlib import Path
from typing import List, Union


def execute_bin(p: Path, args: Union[List[str], list] = []) -> bool:
    if not p.exists():
        raise FileNotFoundError(f"可执行文件不存在: {p}")
    cmd = [str(p)] + [str(arg) for arg in args]
    try:
        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=None,
            stderr=None,
            check=False,
        )
        if result.returncode != 0:
            print(f"execute_bin: {cmd} 错误码 {result.returncode}")
            return False
        return True
    except OSError:
        # 比如 PermissionError
        raise
