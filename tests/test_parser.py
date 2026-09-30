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


def test_dynamic_linker_fallback_not_flagged_as_missing(tmp_path):
    trace = tmp_path / "trace.log"
    trace.write_text(
        '100 openat(AT_FDCWD, "/opt/app/libm.so.6", O_RDONLY) = -1 ENOENT (No such file)\n'
        '100 openat(AT_FDCWD, "/usr/local/lib/libm.so.6", O_RDONLY) = -1 ENOENT (No such file)\n'
        '100 openat(AT_FDCWD, "/lib/x86_64-linux-gnu/libm.so.6", O_RDONLY) = 3\n'
        '100 openat(AT_FDCWD, "/opt/app/missing.so", O_RDONLY) = -1 ENOENT (No such file)\n'
    )
    found = list(TraceParser.stream_missing_libraries(str(trace)))
    assert "/opt/app/missing.so" in found
    assert not any("libm.so" in x for x in found)


def test_hidden_import_detection_standard_traceback(tmp_path):
    from deptracer.parser import HiddenImportDetector

    stderr = tmp_path / "stderr.log"
    stderr.write_text(
        "Traceback (most recent call last):\n"
        '  File "app.py", line 2, in <module>\n'
        "ModuleNotFoundError: No module named 'scipy.optimize'\n"
        "ImportError: cannot import name 'foo_bar' from 'special_pkg'\n"
        "[DEPTRACER-PROBE] No module named 'probe_module'\n"
    )
    detected = HiddenImportDetector.detect_hidden_imports(str(stderr))
    assert "scipy.optimize" in detected
    assert "special_pkg.foo_bar" in detected
    assert "probe_module" in detected
