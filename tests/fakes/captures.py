"""The ConPTY captures of ``tests/data/captures``: what real programs wrote to the terminal."""

from dataclasses import dataclass
from pathlib import Path

CAPTURES = Path(__file__).parent.parent / "data" / "captures"


@dataclass(slots=True, frozen=True)
class Capture:
    name: str
    columns: int
    rows: int
    text: str

    @property
    def data(self) -> bytes:
        return self.text.encode("utf-8")


def capture_names() -> list[str]:
    return sorted(path.stem for path in CAPTURES.glob("*.vt"))


def load_capture(name: str) -> Capture:
    path = CAPTURES / f"{name}.vt"
    size, _, text = path.read_text(encoding="utf-8", newline="").partition("\n")
    columns, rows = (int(value) for value in size.split("x"))
    return Capture(name, columns, rows, text)
