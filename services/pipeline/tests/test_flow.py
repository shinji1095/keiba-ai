from pipeline_service.flows import daily_train_flow


def test_flow_runs():
    r = daily_train_flow()
    assert r["status"] == "ok"
