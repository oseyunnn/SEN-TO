"""Shared, limited prototype guardrails; not a comprehensive safety classifier."""
import re
from backend.security import is_filipino_or_taglish

NEUTRAL_RESPONSE = (
    "SEN’TO does not endorse, rank, or oppose senators, predict election results, "
    "or present unsupported accusations as facts. You can explore how to assess "
    "documented legislative records using the same criteria for every senator."
)
NEUTRAL_RESPONSE_FIL = (
    "Hindi nag-eendorso, nagraranggo, o kumokontra ang SEN’TO sa mga senador, at hindi ito "
    "naghuhula ng resulta ng halalan o naglalahad ng hindi suportadong paratang bilang katotohanan. "
    "Maaari mong suriin ang mga dokumentadong rekord gamit ang parehong pamantayan."
)


def policy_violation(query):
    text = query.casefold()
    patterns = (
        r"\b(vote for|endorse|best senator|worst senator|rank senators|who should .*vote)\b",
        r"\b(who will win|predict .*election|win the election)\b",
        r"\b(?:sino|hula(?:an)?|predict)\b.{0,80}\b(?:mananalo|manalo|halalan|eleksyon)\b",
        r"\b(prove|show|confirm|establish|declare|patunayan|kumpirmahin|ideklara)\b.{0,80}\b(corrupt|criminal|thief|stole|guilty|magnanakaw|kurakot|mandurugas)\b",
        r"\b(is|are|was|were)\s+(?:he|she|they|this senator|that senator|senator [a-z]+|[a-z]+)\s+(?:a\s+)?(?:corrupt|criminal|thief|guilty|magnanakaw|kurakot)\b",
        r"\b(pretend (to be|you are)|impersonate|as senator|speak as)\b",
        r"\b(?:pretend|act)\b.{0,60}\b(?:senador|senator)\b",
        r"\b(?:magpanggap|magkunwari|kunwari)\b.{0,60}\b(?:senador|senator)\b",
        r"\b(?:magsalita|sumagot)\b.{0,50}\b(?:bilang|as)\s+(?:isang\s+)?(?:senador|senator)\b",
        r"\b(sinong iboboto|sino.*ibo(?:bo)?to|pinakamagaling.*senador)\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def neutral_response(query):
    return NEUTRAL_RESPONSE_FIL if is_filipino_or_taglish(query) else NEUTRAL_RESPONSE
