from deptracer.history import History

def test_resume_repeats_inflight_iteration(tmp_path):
    h=History(tmp_path).load()
    assert h.start(False)==1
    h.record(1, status="running")
    h2=History(tmp_path).load()
    assert h2.start(True)==1


def test_completed_run_does_not_resume(tmp_path):
    h=History(tmp_path).load()
    assert h.start(False)==1
    h.finish("success")
    h2=History(tmp_path).load()
    assert h2.start(True)==1
