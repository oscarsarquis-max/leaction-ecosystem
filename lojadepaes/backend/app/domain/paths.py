from pathlib import Path

from app.core.config import Settings


def media_root(settings: Settings) -> Path:
    path = Path(settings.media_dir)
    if not path.is_absolute():
        path = (Path(__file__).resolve().parents[2] / path).resolve()
    else:
        path = path.resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path
