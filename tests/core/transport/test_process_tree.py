import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from n5terminal.core.transport.process_tree import STOPPED_EXIT_CODE, ProcessTree

pytestmark = pytest.mark.slow

PROGRAM = Path(__file__).parents[2] / "fakes" / "program_cli.py"
WAIT_TIMEOUT = 10.0


@pytest.fixture
def sleeping() -> Iterator[subprocess.Popen[bytes]]:
    process = subprocess.Popen([sys.executable, str(PROGRAM), "sleep"])
    yield process
    process.kill()
    process.wait(WAIT_TIMEOUT)


def test_terminate_stops_the_program(sleeping: subprocess.Popen[bytes]) -> None:
    tree = ProcessTree(sleeping.pid)
    tree.terminate()
    assert sleeping.wait(WAIT_TIMEOUT) == STOPPED_EXIT_CODE
    tree.close()


def test_closing_the_job_while_the_program_runs_stops_it(
    sleeping: subprocess.Popen[bytes],
) -> None:
    # What happens when MiTerm-N5 ends or crashes: Windows closes the job.
    ProcessTree(sleeping.pid).close()
    sleeping.wait(WAIT_TIMEOUT)


def test_after_keep_after_close_the_processes_survive_the_job(
    sleeping: subprocess.Popen[bytes],
) -> None:
    tree = ProcessTree(sleeping.pid)
    tree.keep_after_close()
    tree.close()
    with pytest.raises(subprocess.TimeoutExpired):
        sleeping.wait(0.5)
