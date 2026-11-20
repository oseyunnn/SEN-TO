"""Shared, limited prototype guardrails; not a comprehensive safety classifier."""
import re

NEUTRAL_RESPONSE = (
    "SEN’TO does not endorse, rank, or oppose senators, predict election results, "
    "or present unsupported accusations as facts. You can explore how to assess "
    "documented legislative records using the same criteria for every senator."
)


def policy_violation(query):
    text = query.casefold()
    patterns = (
        r"\b(vote for|endorse|best senator|worst senator|rank senators|who should .*vote)\b",
        r"\b(who will win|predict .*election|win the election)\b",
        r"\b(corrupt|criminal|thief|stole|guilty|magnanakaw|kurakot)\b",
        r"\b(pretend (to be|you are)|impersonate|as senator|speak as)\b",
        r"\b(sinong iboboto|sino.*ibo(?:bo)?to|pinakamagaling.*senador)\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)
