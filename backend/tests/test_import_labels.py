import csv
import json

import pytest

from marketlens.evaluation.import_labels import convert


def test_convert_writes_ids_and_labels_only(tmp_path):
    src = tmp_path / "labels"
    src.mkdir()
    (src / "a12-NVDA.json").write_text(
        json.dumps(
            {"data": {"label": "bullish", "labeled_at": "2026-11-21T10:00:00Z", "note": "private"}}
        )
    )
    (src / "a3-AMD.json").write_text(json.dumps({"label": "not_about"}))
    out = tmp_path / "labels.csv"
    assert convert(src, out) == 2
    rows = list(csv.DictReader(open(out)))
    assert rows[0] == {"article_id": "3", "ticker": "AMD", "label": "not_about", "labeled_at": ""}
    assert "private" not in out.read_text()


def test_convert_rejects_unknown_labels(tmp_path):
    (tmp_path / "a1-NVDA.json").write_text(json.dumps({"label": "moon"}))
    with pytest.raises(ValueError):
        convert(tmp_path, tmp_path / "o.csv")
