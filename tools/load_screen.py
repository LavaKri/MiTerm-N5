"""Load test of the screen model and the exchange point (roadmap milestone 2).

Usage: ``.venv\\Scripts\\python.exe tools\\load_screen.py [--mb 4] [--chunk 4096] [--block 16384]
[scenario ...]``. A program writes several megabytes to the terminal; the thread of the transport
feeds them through ``ScreenPump`` while a thread standing for the UI wakes every 50 ms and takes
what accumulated. Printed for each scenario:
- pyte's time: the whole feed, the throughput, the longest single block;
- the longest UI wait: how late the UI thread wakes up compared with the 50 ms it asked for,
  with and without the feed running (the difference is the cost of the GIL contention);
- what reached the UI (lines delivered and dropped).

Numbers depend on the machine; this is a measure for a decision (is a native module needed?), not a
test. The functional side is covered by ``tests/core/test_display_exchange.py``.
"""

import argparse
import statistics
import sys
import threading
import time
from collections.abc import Callable

from n5terminal.core.screen.display_exchange import BLOCK_SIZE, DisplayExchange, ScreenPump
from n5terminal.core.screen.pyte_screen_model import PyteScreenModel

TICK = 0.05  # the UI takes every 50 ms


def plain(number: int) -> str:
    return f"line {number:07d} " + "x" * 60 + "\r\n"


def colored(number: int) -> str:
    color = 31 + number % 7
    return f"\x1b[{color}mline {number:07d}\x1b[0m \x1b[1;4mbold\x1b[0m " + "y" * 50 + "\x1b[0m\r\n"


def repaint(number: int) -> str:
    """A full-screen program redrawing its 24 rows with cursor positioning, one frame."""
    rows = (
        f"\x1b[{row + 1};1H\x1b[7m row {row:2} frame {number:6} \x1b[0m " + "z" * 50
        for row in range(24)
    )
    return "\x1b[H" + "".join(rows)


SCENARIOS: dict[str, Callable[[int], str]] = {
    "plain": plain,
    "colored": colored,
    "repaint": repaint,
}


def make_chunks(scenario: Callable[[int], str], megabytes: float, chunk: int) -> list[bytes]:
    target = int(megabytes * 1024 * 1024)
    parts: list[bytes] = []
    size = number = 0
    while size < target:
        piece = scenario(number).encode("ascii")
        parts.append(piece)
        size += len(piece)
        number += 1
    data = b"".join(parts)
    return [data[start : start + chunk] for start in range(0, len(data), chunk)]


class UiThread(threading.Thread):
    """Stands for the UI: wakes every 50 ms, takes the exchange, builds the text it would show."""

    def __init__(self, exchange: DisplayExchange) -> None:
        super().__init__(daemon=True)
        self.exchange = exchange
        self.stop = threading.Event()
        self.lateness: list[float] = []
        self.lines = 0
        self.dropped = 0

    def run(self) -> None:
        expected = time.perf_counter() + TICK
        while not self.stop.is_set():
            time.sleep(max(expected - time.perf_counter(), 0))
            now = time.perf_counter()
            self.lateness.append(now - expected)
            expected = max(expected + TICK, now)
            self.take()
        self.take()

    def take(self) -> None:
        batch = self.exchange.take()
        if batch is not None:
            "\n".join(line.text for line in batch.update.fixed)  # the work of a text control
            self.lines += len(batch.update.fixed)
            self.dropped += batch.dropped_lines


def percentile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(int(len(ordered) * share), len(ordered) - 1)]


def ui_noise(seconds: float) -> list[float]:
    """The lateness of the UI thread with nothing else running."""
    ui = UiThread(DisplayExchange())
    ui.start()
    time.sleep(seconds)
    ui.stop.set()
    ui.join()
    return ui.lateness


def run(name: str, chunks: list[bytes], block: int) -> None:
    total = sum(len(chunk) for chunk in chunks)
    exchange = DisplayExchange(max_fixed_lines=10**9)
    pump = ScreenPump(PyteScreenModel(80, 24), exchange, block_size=block)

    started = time.perf_counter()
    for chunk in chunks:
        pump.feed(chunk)
    alone = time.perf_counter() - started

    exchange = DisplayExchange(max_fixed_lines=10**9)
    pump = ScreenPump(PyteScreenModel(80, 24), exchange, block_size=block)
    ui = UiThread(exchange)
    longest_feed = 0.0
    ui.start()
    time.sleep(0.2)
    started = time.perf_counter()
    for chunk in chunks:
        before = time.perf_counter()
        pump.feed(chunk)
        longest_feed = max(longest_feed, time.perf_counter() - before)
    shared = time.perf_counter() - started
    ui.stop.set()
    ui.join()

    late = ui.lateness
    print(f"== {name}: {total / 1024 / 1024:.1f} MB, chunks of {len(chunks[0])}, blocks of {block}")
    print(f"   pyte alone        {alone:6.2f} s  {total / 1024 / 1024 / alone:5.2f} MB/s")
    longest = longest_feed * 1000
    print(f"   pyte with the UI  {shared:6.2f} s  longest feed of a chunk {longest:6.1f} ms")
    mean, p95, worst = (
        statistics.fmean(late) * 1000,
        percentile(late, 0.95) * 1000,
        max(late) * 1000,
    )
    print(
        f"   UI wake-up lateness over {len(late)} ticks: "
        f"mean {mean:5.1f} ms, p95 {p95:5.1f} ms, max {worst:5.1f} ms"
    )
    print(f"   delivered {ui.lines} fixed lines, dropped {ui.dropped}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("scenarios", nargs="*", choices=list(SCENARIOS))
    parser.add_argument("--mb", type=float, default=4.0)
    parser.add_argument("--chunk", type=int, default=4096)
    parser.add_argument("--block", type=int, default=BLOCK_SIZE)
    parser.add_argument(
        "--switch-ms", type=float, help="thread switch interval in ms (Python's default is 5)"
    )
    args = parser.parse_args()
    if args.switch_ms:
        sys.setswitchinterval(args.switch_ms / 1000)

    noise = ui_noise(1.5)
    print(
        f"UI thread alone: {len(noise)} ticks, mean {statistics.fmean(noise) * 1000:.1f} ms, "
        f"max {max(noise) * 1000:.1f} ms late"
    )
    for name in args.scenarios or list(SCENARIOS):
        run(name, make_chunks(SCENARIOS[name], args.mb, args.chunk), args.block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
