"""finsent: classify financial news as bullish / bearish / neutral per company."""

LABELS = ("bearish", "neutral", "bullish")
LABEL2ID = {label: i for i, label in enumerate(LABELS)}
ID2LABEL = {i: label for label, i in LABEL2ID.items()}
