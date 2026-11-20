"""Turn FinBERT probabilities into a company-level label with a source-grounded explanation.

Rules (versioned in DECISION_CONFIG and stored with every prediction):
- Map positive -> bullish, negative -> bearish, neutral -> neutral.
- If the top probability < MIN_CONFIDENCE or the margin to the runner-up < MIN_MARGIN,
  the label is `insufficient_evidence` (never forced into a direction).
- If the passage also names other tracked companies and the label is directional, the
  prediction is flagged `needs_review`: the tone may belong to another company.
- Evidence quotes are verbatim sentences from the passage (checked), chosen by sentence-level
  FinBERT scores in the direction of the label.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from marketlens.models.finbert import Probs

DECISION_CONFIG = {"min_confidence": 0.60, "min_margin": 0.15, "max_evidence": 2}
_MAP = {"positive": "bullish", "negative": "bearish", "neutral": "neutral"}


@dataclass
class Decision:
    label: str
    confidence: float
    explanation: str
    evidence_quotes: list[str] = field(default_factory=list)
    needs_review: bool = False


def decide(
    company_name: str,
    passage: str,
    passage_probs: Probs,
    sentences: list[str],
    sentence_probs: list[Probs],
    other_companies: tuple[str, ...] = (),
) -> Decision:
    ranked = sorted(
        [
            ("positive", passage_probs.positive),
            ("negative", passage_probs.negative),
            ("neutral", passage_probs.neutral),
        ],
        key=lambda kv: -kv[1],
    )
    (top, p_top), (_, p_second) = ranked[0], ranked[1]
    probs_txt = (
        f"P(positive)={passage_probs.positive:.2f}, "
        f"P(negative)={passage_probs.negative:.2f}, "
        f"P(neutral)={passage_probs.neutral:.2f}"
    )

    unclear = p_top < DECISION_CONFIG["min_confidence"]
    unclear = unclear or p_top - p_second < DECISION_CONFIG["min_margin"]
    if unclear:
        return Decision(
            label="insufficient_evidence",
            confidence=p_top,
            needs_review=True,
            explanation=(
                f"The text about {company_name} is not clearly positive, negative or "
                f"neutral ({probs_txt}), so no direction is assigned."
            ),
            evidence_quotes=[sentences[0]] if sentences else [],
        )

    label = _MAP[top]
    key = {
        "positive": lambda p: p.positive,
        "negative": lambda p: p.negative,
        "neutral": lambda p: p.neutral,
    }[top]
    order = sorted(range(len(sentences)), key=lambda i: -key(sentence_probs[i]))
    evidence = [
        sentences[i] for i in order[: DECISION_CONFIG["max_evidence"]] if sentences[i] in passage
    ]
    tone = {"bullish": "positive", "bearish": "negative", "neutral": "neutral"}[label]
    explanation = (
        f"FinBERT reads the {company_name}-specific text as {tone} ({probs_txt}). "
        f"This describes the tone of the coverage, not a price forecast."
    )
    needs_review = False
    if other_companies and label != "neutral":
        needs_review = True
        explanation += (
            f" The same text also names {', '.join(other_companies)}, so the tone "
            f"may apply to another company; flagged for review."
        )
    return Decision(label, p_top, explanation, evidence, needs_review)
