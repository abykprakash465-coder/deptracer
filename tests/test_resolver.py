from pathlib import Path
from deptracer.resolver import (
    is_binary_dependency,
    environment_search_paths,
    hunt_missing_library,
    resolve_many,
)


def test_is_binary_dependency():
    assert is_binary_dependency("libsample.so")
    assert is_binary_dependency("libsample.so.1.2")
    assert is_binary_dependency("vendor.dll")
    assert is_binary_dependency("libfoo.dylib")
    assert is_binary_dependency("module.cpython-310-x86_64-linux-gnu.pyd")

    assert not is_binary_dependency("model.pt")
    assert not is_binary_dependency("config.yaml")
    assert not is_binary_dependency("dataset.csv")
    assert not is_binary_dependency("logo.png")


def test_environment_search_paths_skips_system_for_data(tmp_path):
    bin_paths = environment_search_paths(str(tmp_path), is_binary=True)
    data_paths = environment_search_paths(str(tmp_path), is_binary=False)

    bin_strs = [str(p) for p in bin_paths]
    data_strs = [str(p) for p in data_paths]

    assert any(s.startswith("/usr/lib") or s.startswith("/lib") for s in bin_strs)
    assert not any(s == "/usr/lib" or s == "/lib" or s == "/usr/local/lib" for s in data_strs)


def test_hunt_missing_library_and_data_file(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    lib_dir = project_dir / "lib"
    lib_dir.mkdir()
    assets_dir = project_dir / "assets"
    assets_dir.mkdir()

    target_so = lib_dir / "libcustom.so.2"
    target_so.write_text("binary_content")

    target_json = assets_dir / "config.json"
    target_json.write_text("{\"debug\": true}")

    found_so = hunt_missing_library("libcustom.so", project_dir=str(project_dir))
    assert found_so is not None
    assert Path(found_so).resolve() == target_so.resolve()

    found_json = hunt_missing_library("config.json", project_dir=str(project_dir))
    assert found_json is not None
    assert Path(found_json).resolve() == target_json.resolve()


def test_resolve_many(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    target = project_dir / "file.dat"
    target.write_text("data")

    res = resolve_many(["file.dat", "nonexistent.ext"], project_dir=str(project_dir), workers=2)
    assert "file.dat" in res and res["file.dat"] is not None
    assert "nonexistent.ext" in res and res["nonexistent.ext"] is None
