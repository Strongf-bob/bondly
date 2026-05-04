from pathlib import Path

_SOURCE_PACKAGE = Path(__file__).resolve().parent.parent / "src" / "bondly"

if _SOURCE_PACKAGE.is_dir():
    __path__.append(str(_SOURCE_PACKAGE))
