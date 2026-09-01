from experiments.external_guoq_bqskit_pilot import _summarize_resynthesis


def test_resynthesis_summary_marks_active_request_as_censored():
    events = [
        {"event": "request_start", "request_id": 1, "started_unix": 10.0},
        {"event": "request_complete", "request_id": 1, "status": "ok",
         "wall_seconds": 2.0, "server_cpu_seconds": 1.5},
        {"event": "request_start", "request_id": 2, "started_unix": 15.0},
    ]
    result = _summarize_resynthesis(events, stopped_unix=20.0)
    assert result["resynthesis_requests_started"] == 2
    assert result["resynthesis_requests_completed"] == 1
    assert result["resynthesis_completed_wall_seconds"] == 2.0
    assert result["resynthesis_active_censored_wall_seconds"] == 5.0
    assert result["resynthesis_unfinished_at_timeout"] == 1
