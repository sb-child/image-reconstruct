from pathlib import Path

# image-reconstruct/src/
_script_dir = Path(__file__).resolve().parent.parent.resolve()

# image-reconstruct/
_project_dir = Path(__file__).resolve().parent.parent.parent.resolve()


def script() -> Path:
    return _script_dir


def project() -> Path:
    return _project_dir
