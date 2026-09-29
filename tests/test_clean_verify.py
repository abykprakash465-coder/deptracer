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
