"""Deterministic Turkish research comments with no advice or fraud labels."""
from __future__ import annotations

from p50k.research_reviews.contracts import eligible


def describe(d1: dict, flow: dict) -> tuple[str, str, int]:
    known = [eligible(d1), eligible(flow)]
    crossings = sum(ok and finding["research_screen"] == "CROSSING"
                    for ok, finding in zip(known, (d1, flow)))
    assessment = "FULL" if all(known) else "PARTIAL" if any(known) else "UNAVAILABLE"
    parts = []
    if d1["freshness"] == "STALE":
        parts.append("Benzer fonlarla getiri hesabının son gözlemi güncel değil; birleşik bulguya katılmadı.")
    elif not known[0]:
        parts.append("Benzer fonlarla getiri karşılaştırması için yeterli veri yok.")
    elif d1["research_screen"] == "CROSSING":
        parts.append("Son 60 veri konumundaki ortanca günlük fazla getiri, sabit araştırma eşiğinin üzerinde.")
    else:
        parts.append("Benzer fonlarla getiri farkı bu kesitte sabit araştırma eşiğini aşmadı.")
    if not known[1]:
        parts.append("Temmuz–Ağustos tahmini akış hesabı için karşılaştırılabilir veri yok.")
    elif flow["research_screen"] == "CROSSING":
        direction = "giriş" if flow["direction"] == "INFLOW_ESTIMATE" else "çıkış"
        parts.append(f"Temmuz–Ağustos uç değer hesabında tahmini {direction} oranı %10 sınırına ulaştı veya aştı.")
    else:
        parts.append("Temmuz–Ağustos tahmini akış oranı %10 sınırının altında.")
    if crossings == 2:
        parts.append("Farklı dönemleri kapsayan iki ayrı araştırma bulgusu var.")
    if assessment == "PARTIAL":
        parts.append("Değerlendirme eksik.")
    if flow["arithmetic_status"] == "AVAILABLE":
        parts.append("Akış, yatırımcının bildirilmiş nakdi değildir; kapsam ve fon işlemleri doğrulanmadan koşullu hesaplanmıştır.")
    return " ".join(parts), assessment, crossings


def finding_order(record: dict) -> tuple[int, str]:
    count = record["eligible_crossings"]
    group = 0 if count == 2 else 1 if count == 1 else 2 if record["assessment"] != "FULL" else 3
    return group, record["code"]


def summarize(records: list[dict]) -> dict:
    return {
        "total": len(records), "denominator": len(records),
        "fully_assessable": sum(r["assessment"] == "FULL" for r in records),
        "partially_assessable": sum(r["assessment"] == "PARTIAL" for r in records),
        "unavailable": sum(r["assessment"] == "UNAVAILABLE" for r in records),
        "two_findings": sum(r["eligible_crossings"] == 2 for r in records),
        "one_finding": sum(r["eligible_crossings"] == 1 for r in records),
        "unassessable_no_findings": sum(r["eligible_crossings"] == 0 and r["assessment"] != "FULL"
                                       for r in records),
        "no_findings": sum(r["eligible_crossings"] == 0 and r["assessment"] == "FULL" for r in records),
    }
