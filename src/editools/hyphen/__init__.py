"""Audit end-of-line hyphen breaks in a typeset book proof."""

__version__ = "1.0.0"

from .audit import AuditResult, run  # noqa: F401
from .dictionary import Dictionary  # noqa: F401
from .model import Break, Finding, Verdict  # noqa: F401
