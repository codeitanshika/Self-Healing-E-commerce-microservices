from experiments import sensitivity as s
from experiments.analyze_strategies import load


def test_replay_reproduces_measured_closed_loop():
    data = load()
    ok, total = s.validate_replay(data)
    assert ok == total


def test_closed_loop_never_worse_than_open_loop_on_random_tables():
    rows = s.llm_rows(load())
    mc = s.monte_carlo(rows, n=200)
    assert mc["closed_ge_open"] == mc["n"]


def test_score_blind_restart_depends_on_table():
    rows = [{"fault": "slow", "first_fix": "reduce_load", "diagnosed": "cpu_overload", "result": "RECOVERED"}]
    assert s.score(rows, {"slow": {"reduce_load"}, "crash": set(), "memory": set(), "error": set()})["blind"] == 0
    assert s.score(rows, {"slow": {"restart"}, "crash": set(), "memory": set(), "error": set()})["blind"] == 1
