"""EARSHOT regression rig — the worldsim gauntlet, in-repo.

`world.py` is the worldsim behavioral harness copied verbatim.
`simulate.py` is the worldsim runner re-wired to import the SHIPPED engine
(`earshot.policy.engine`) — the regression can never test a dead copy.
Every policy change re-runs the 3,000-person gauntlet before merge.
"""
