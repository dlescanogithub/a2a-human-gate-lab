"""Local A2A-style lab: the planner proposes, a human gate releases effects."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("a2a-human-gate-lab")
except PackageNotFoundError:
    __version__ = "0.1.3"
