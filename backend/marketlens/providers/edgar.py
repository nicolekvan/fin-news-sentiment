"""SEC EDGAR submissions API. No key; requires a User-Agent with contact info; <= 10 req/s."""

from __future__ import annotations

from datetime import date

import httpx

from marketlens.config import get_settings
from marketlens.providers.base import Filing, ProviderNotConfigured
from marketlens.providers.http import ApiClient


class EdgarProvider:
    name = "sec_edgar"

    def __init__(self, transport: httpx.BaseTransport | None = None):
        ua = get_settings().sec_edgar_user_agent
        if not ua:
            raise ProviderNotConfigured("SEC_EDGAR_USER_AGENT not set (SEC requires contact info)")
        self.client = ApiClient(
            self.name,
            "https://data.sec.gov",
            300,
            headers={"User-Agent": ua},
            transport=transport,
        )

    def recent_filings(self, cik: str, forms: tuple[str, ...], since: date) -> list[Filing]:
        d = self.client.get(f"/submissions/CIK{cik}.json").json()
        r = d["filings"]["recent"]
        out = []
        for i, form in enumerate(r["form"]):
            filed = date.fromisoformat(r["filingDate"][i])
            if form not in forms or filed < since:
                continue
            acc = r["accessionNumber"][i]
            doc = r["primaryDocument"][i] or None
            report = r["reportDate"][i]
            folder = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}"
            out.append(
                Filing(
                    accession_number=acc,
                    form=form,
                    filed_date=filed,
                    report_date=date.fromisoformat(report) if report else None,
                    primary_document=doc,
                    url=f"{folder}/{doc}" if doc else f"{folder}/",
                )
            )
        return out
