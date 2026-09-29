import sys
import time

from deptracer.process import run


def test_process_timeout():
    result = run(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        timeout=0.2,
    )
    assert result.timed_out
