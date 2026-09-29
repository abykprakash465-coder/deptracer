from pathlib import Path

from deptracer.parser import TraceParser


def test_parser_detects_missing_and_does_not_drop_underscore_files(tmp_path):
    trace = tmp_path / "trace.log"
    trace.write_text(
        '123 openat(AT_FDCWD, "/tmp/_model.pt", O_RDONLY) = -1 ENOENT (No such file)\n'
        '123 openat(AT_FDCWD, "/tmp/ok.json", O_RDONLY) = 3\n'
        '123 openat(AT_FDCWD, "/tmp/libx.so.1", O_RDONLY) = -1 ENOENT (No such file)\n'
    )
    found = list(TraceParser.stream_missing_libraries(str(trace)))
    assert "/tmp/_model.pt" in found
    assert "/tmp/libx.so.1" in found


def test_system_noise_does_not_hide_normal_data():
    assert not TraceParser.is_system_noise("/tmp/_config.json")
