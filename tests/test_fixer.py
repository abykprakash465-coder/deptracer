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
