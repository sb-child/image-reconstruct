import tomllib
import dataclasses
import os
from pathlib import Path
from . import dirs

tools_file = "tools.toml"

# runs on import
with open(dirs.project() / tools_file, "rb") as f:
    _content = tomllib.load(f)


@dataclasses.dataclass
class ColmapConf:
    bin: Path


def _executable(p: Path) -> bool:
    return os.access(p, os.F_OK | os.R_OK | os.X_OK)


def colmap_conf() -> ColmapConf:
    colmap = _content["colmap"]
    colmap_bin = Path(colmap["bin"]).resolve()
    assert colmap_bin.is_file(), "colmap.bin must be a file"
    assert _executable(colmap_bin), "colmap.bin is not executable"
    r = ColmapConf(
        bin=Path(colmap["bin"]).resolve(),
    )
    return r
