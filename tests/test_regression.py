"""Regression: the 3,000-person worldsim gauntlet against the SHIPPED engine.

Pass criteria: 0 earshot leaks. The harness must also still detect leaks
(naive baseline leaks > 0) — a regression that cannot fail is theater.
"""
import pytest

from earshot.regression.simulate import run


@pytest.mark.slow
def test_regression_zero_leaks_3000_personas():
    stats, leaks, catches, conflicts = run(
        n_personas=3000, seed=99, fresh_wake_snapshot=True)
    assert stats["sensitive_requests"] > 5000, (
        "gauntlet ran too few sensitive requests: %d" % stats["sensitive_requests"])
    assert stats["leak_high_naive"] > 0, (
        "harness no longer detects leaks — regression is vacuous")
    assert stats["leak_high_earshot"] == 0, f"high leaks: {leaks[:3]}"
    assert stats["leak_med_earshot"] == 0, "medium leaks detected"
