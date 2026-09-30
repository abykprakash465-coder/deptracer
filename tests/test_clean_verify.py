from pathlib import Path
from unittest.mock import patch
import deptracer.clean_verify as cv

def test_clean_verify_success(tmp_path):
    binary=tmp_path/'app'; binary.write_text('x')
    class R:
        returncode=0; stdout='APP OK\n'; stderr=''
    with patch.object(cv.shutil, 'which', side_effect=lambda x: '/usr/bin/docker' if x=='docker' else None), patch.object(cv.subprocess, 'run', return_value=R()):
        ok,out=cv.verify_clean(str(binary))
    assert ok and 'APP OK' in out


def test_clean_verify_onedir_directory(tmp_path):
    app_dir = tmp_path / 'my_app'
    app_dir.mkdir()
    (app_dir / 'my_app').write_text('executable')
    class R:
        returncode = 0
        stdout = 'DIRECTORY APP OK\n'
        stderr = ''
    with patch.object(cv.shutil, 'which', side_effect=lambda x: '/usr/bin/docker' if x=='docker' else None), patch.object(cv.subprocess, 'run', return_value=R()) as mock_run:
        ok, out = cv.verify_clean(str(app_dir))
        assert ok and 'DIRECTORY APP OK' in out
        cmd = mock_run.call_args[0][0]
        assert f"{app_dir}:/opt/app:ro" in cmd
        assert "/opt/app/my_app" in cmd
