from boss_career_ops.commands.recommend import run_recommend


def test_recommend_hints_no_security_id():
    import inspect
    source = inspect.getsource(run_recommend)
    assert "bco detail <security_id>" not in source, (
        "hints 中不应包含 'bco detail <security_id>'，应为 'bco detail <job_id>'"
    )


def test_recommend_hints_has_job_id():
    import inspect
    source = inspect.getsource(run_recommend)
    assert "bco detail <job_id>" in source, (
        "hints 中应包含 'bco detail <job_id>'"
    )
