"""FinBERT (ProsusAI/finbert) batch inference. Runs in jobs only, never on web requests."""
from __future__ import annotations

import os
from dataclasses import dataclass

# Plain HTTPS download from the Hugging Face CDN (works behind restrictive egress proxies).
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

MODEL_ID = "ProsusAI/finbert"


@dataclass(frozen=True)
class Probs:
    positive: float
    negative: float
    neutral: float

    @property
    def score(self) -> float:
        return self.positive - self.negative


class FinBert:
    def __init__(self, model_id: str = MODEL_ID, batch_size: int = 64, max_length: int = 128):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id).eval()
        self.labels = {i: lab.lower() for i, lab in self.model.config.id2label.items()}
        self.batch_size, self.max_length = batch_size, max_length
        self.model_id = model_id

    def predict(self, texts: list[str]) -> list[Probs]:
        out: list[Probs] = []
        torch = self._torch
        with torch.inference_mode():
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i : i + self.batch_size]
                enc = self.tokenizer(batch, padding=True, truncation=True,
                                     max_length=self.max_length, return_tensors="pt")
                probs = torch.softmax(self.model(**enc).logits, dim=-1).tolist()
                for row in probs:
                    d = {self.labels[j]: p for j, p in enumerate(row)}
                    out.append(Probs(d["positive"], d["negative"], d["neutral"]))
        return out
