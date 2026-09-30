from deptracer.fixer import patch_spec_file


def test_spec_patch_supports_multiple_iterations(tmp_path):
    spec = tmp_path / "app.spec"
    spec.write_text(
        "a = Analysis(['app.py'], binaries=[], datas=[], hiddenimports=[])\n"
        "pyz = PYZ(a.pure)\n"
    )
    dep1 = tmp_path / "libx.so"
    dep2 = tmp_path / "liby.so"
    dep1.write_text("fake")
    dep2.write_text("fake")

    p1 = {"binaries": [("libx.so", str(dep1))], "data": [], "hidden_imports": []}
    p2 = {"binaries": [("liby.so", str(dep2))], "data": [], "hidden_imports": []}

    assert patch_spec_file(str(spec), p1)
    assert patch_spec_file(str(spec), p2)
    text = spec.read_text()
    assert str(dep1) in text and str(dep2) in text
    assert text.count("a.binaries +=") == 2
    assert "'BINARY'" in text


def test_spec_patch_preserves_relative_subpaths(tmp_path):
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    spec = project_dir / "app.spec"
    spec.write_text(
        "a = Analysis(['app.py'], binaries=[], datas=[], hiddenimports=[])\n"
        "pyz = PYZ(a.pure)\n"
    )
    asset_dir = project_dir / "assets" / "models"
    asset_dir.mkdir(parents=True)
    weights = asset_dir / "weights.pt"
    weights.write_text("model_bytes")

    payload = {
        "binaries": [],
        "data": [("weights.pt", str(weights))],
        "hidden_imports": [],
    }

    assert patch_spec_file(str(spec), payload, project_dir=project_dir)
    text = spec.read_text()
    assert "assets/models/weights.pt" in text
    assert "'DATA'" in text
