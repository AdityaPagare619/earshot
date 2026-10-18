"""Run the 3,000-person regression and assert 0 earshot leaks.

Mirrors the worldsim conditions that measured 0 leaks (wake-word fresh
presence re-sample before every decision), against the SHIPPED engine.

Usage: python -m earshot.regression.run_regression
Exit code: 0 on pass (0 leaks), 1 on any earshot leak.
"""
import sys
from pathlib import Path

# Allow direct invocation: python earshot/regression/run_regression.py
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from earshot.regression.simulate import run, summarize

N_PERSONAS = 3000
SEED = 99


def main():
    stats, leaks, catches, conflicts = run(
        n_personas=N_PERSONAS, seed=SEED, fresh_wake_snapshot=True)
    print(summarize(stats))
    earshot_leaks = stats["leak_high_earshot"] + stats["leak_med_earshot"]
    if earshot_leaks:
        print("REGRESSION FAIL: %d earshot leaks" % earshot_leaks)
        return 1
    print("REGRESSION PASS: 0 earshot leaks (%d/%d-person gauntlet)"
          % (stats["sensitive_requests"], N_PERSONAS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
