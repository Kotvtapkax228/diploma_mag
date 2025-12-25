from __future__ import annotations
import os
import datetime as dt
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

from app.services.recommender import TopicRec

@dataclass
class ReportEntry:
    rid: int
    title: str
    period: str
    fmt: str
    created_at: dt.datetime
    status: str
    filepath: str

class ReportService:
    def __init__(self, reports_dir: str):
        self.reports_dir = reports_dir
        os.makedirs(self.reports_dir, exist_ok=True)
        self._entries: List[ReportEntry] = []
        self._next_id = 1

    def entries(self) -> List[ReportEntry]:
        return list(self._entries)

    def build(self, template_name: str, period_from: dt.date, period_to: dt.date, fmt: str,
              recs: List[TopicRec], kpi: Dict[str, float], segments_df: pd.DataFrame) -> ReportEntry:
        now = dt.datetime.now()
        period = f\"{period_from:%d.%m}–{period_to:%d.%m}\"
        safe = \"\".join([c for c in template_name if c.isalnum() or c in \" _-\"]).strip().replace(\" \", \"_\")
        filename = f\"report_{safe}_{now:%Y%m%d_%H%M%S}.{fmt.lower()}\"
        path = os.path.join(self.reports_dir, filename)

        title = template_name
        if fmt.lower() == "pdf":
            self._to_pdf(path, title, period, recs, kpi, segments_df)
        elif fmt.lower() == "csv":
            self._to_csv(path, recs, kpi, segments_df)
        elif fmt.lower() == "html":
            self._to_html(path, title, period, recs, kpi, segments_df)
        else:
            raise ValueError(\"Unsupported format\") 

        entry = ReportEntry(
            rid=self._next_id,
            title=title,
            period=period,
            fmt=fmt.upper(),
            created_at=now,
            status=\"готовий\",
            filepath=path
        )
        self._next_id += 1
        self._entries.insert(0, entry)
        return entry

    def _to_csv(self, path: str, recs: List[TopicRec], kpi: Dict[str, float], segments_df: pd.DataFrame) -> None:
        df = pd.DataFrame([{
            \"№\": i+1,
            \"Тема\": r.topic,
            \"Ключові драйвери\": r.drivers,
            \"Прогноз ER\": round(r.er_pred*100, 1),
            \"Прогноз CTR\": round(r.ctr_pred*100, 1),
            \"Тренд\": r.trend,
            \"Статус\": r.status,
            \"Пояснюваність\": r.explain,
        } for i, r in enumerate(recs)])
        # Add KPI as header-like rows
        kpi_rows = pd.DataFrame([
            {\"№\": \"KPI\", \"Тема\": \"Середній ER (%)\", \"Ключові драйвери\": round(kpi.get(\"er\", 0.0)*100, 1)},
            {\"№\": \"KPI\", \"Тема\": \"Середній CTR (%)\", \"Ключові драйвери\": round(kpi.get(\"ctr\", 0.0)*100, 1)},
            {\"№\": \"KPI\", \"Тема\": \"К-сть трендів (росте)\", \"Ключові драйвери\": int(kpi.get(\"trends\", 0))},
            {\"№\": \"KPI\", \"Тема\": \"Якість моделі (F1)\", \"Ключові драйвери\": kpi.get(\"f1\", 0.0)},
        ])
        out = pd.concat([kpi_rows, df], ignore_index=True)
        out.to_csv(path, index=False, encoding=\"utf-8-sig\")

    def _to_html(self, path: str, title: str, period: str, recs: List[TopicRec], kpi: Dict[str, float], segments_df: pd.DataFrame) -> None:
        df = pd.DataFrame([{
            \"Тема\": r.topic,
            \"Прогноз ER (%)\": round(r.er_pred*100, 1),
            \"Прогноз CTR (%)\": round(r.ctr_pred*100, 1),
            \"Тренд\": r.trend,
            \"Статус\": r.status,
            \"Пояснюваність\": r.explain,
        } for r in recs])
        kpi_html = f\"\"\"
        <div style='display:flex;gap:12px;flex-wrap:wrap'>
          <div style='padding:12px;border:1px solid #d7e3f4;border-radius:12px;background:#fff'>
            <div style='color:#64748b'>Середній CTR</div><div style='font-size:20px;font-weight:700'>{kpi.get('ctr',0)*100:.1f}%</div>
          </div>
          <div style='padding:12px;border:1px solid #d7e3f4;border-radius:12px;background:#fff'>
            <div style='color:#64748b'>Середній ER</div><div style='font-size:20px;font-weight:700'>{kpi.get('er',0)*100:.1f}%</div>
          </div>
          <div style='padding:12px;border:1px solid #d7e3f4;border-radius:12px;background:#fff'>
            <div style='color:#64748b'>Трендів (зростає)</div><div style='font-size:20px;font-weight:700'>{int(kpi.get('trends',0))}</div>
          </div>
          <div style='padding:12px;border:1px solid #d7e3f4;border-radius:12px;background:#fff'>
            <div style='color:#64748b'>Якість моделі (F1)</div><div style='font-size:20px;font-weight:700'>{kpi.get('f1',0):.2f}</div>
          </div>
        </div>
        \"\"\"
        seg_html = segments_df.to_html(index=False, escape=False)
        html = f\"\"\"<!doctype html>
<html>
<head><meta charset='utf-8'/><title>{title}</title></head>
<body style='font-family:Segoe UI,Arial;background:#f4f7fb;padding:24px;color:#0f172a'>
  <h2 style='margin:0 0 6px 0'>{title}</h2>
  <div style='color:#64748b;margin-bottom:14px'>Період: {period}</div>
  {kpi_html}
  <h3 style='margin-top:22px'>Рекомендовані теми</h3>
  <div style='background:#fff;border:1px solid #d7e3f4;border-radius:12px;padding:12px'>
    {df.to_html(index=False, escape=False)}
  </div>
  <h3 style='margin-top:22px'>Сегменти аудиторії</h3>
  <div style='background:#fff;border:1px solid #d7e3f4;border-radius:12px;padding:12px'>
    {seg_html}
  </div>
</body></html>\"\"\"
        with open(path, \"w\", encoding=\"utf-8\") as f:
            f.write(html)

    def _to_pdf(self, path: str, title: str, period: str, recs: List[TopicRec], kpi: Dict[str, float], segments_df: pd.DataFrame) -> None:
        c = canvas.Canvas(path, pagesize=A4)
        w, h = A4
        x0, y = 2*cm, h - 2*cm

        def line(txt, dy=14, bold=False):
            nonlocal y
            c.setFont(\"Helvetica-Bold\" if bold else \"Helvetica\", 11 if not bold else 12)
            c.drawString(x0, y, txt)
            y -= dy

        line(title, dy=18, bold=True)
        line(f\"Період: {period}\", dy=16)
        line(f\"Середній CTR: {kpi.get('ctr',0)*100:.1f}% | Середній ER: {kpi.get('er',0)*100:.1f}% | Трендів (зростає): {int(kpi.get('trends',0))} | F1: {kpi.get('f1',0):.2f}\", dy=18)

        line(\"Рекомендовані теми:\", dy=16, bold=True)
        c.setFont(\"Helvetica\", 10)

        for i, r in enumerate(recs, start=1):
            text = f\"{i}. {r.topic} | ER: {r.er_pred*100:.1f}% | CTR: {r.ctr_pred*100:.1f}% | {r.trend} | {r.status}\"
            c.drawString(x0, y, text[:110])
            y -= 14
            c.setFillColorRGB(0.38,0.45,0.55)
            c.drawString(x0, y, (\"Пояснюваність: \" + r.explain)[:120])
            c.setFillColorRGB(0,0,0)
            y -= 14
            if y < 3*cm:
                c.showPage()
                y = h - 2*cm
                c.setFont(\"Helvetica\", 10)

        y -= 6
        c.setFont(\"Helvetica-Bold\", 11)
        c.drawString(x0, y, \"Сегменти аудиторії:\")
        y -= 16
        c.setFont(\"Helvetica\", 10)
        for _, row in segments_df.iterrows():
            c.drawString(x0, y, f\"- {row['Сегмент']}: {row['Частка']:.0f}% | Фокус: {row['Фокус інтересу']}\")
            y -= 14
            if y < 3*cm:
                c.showPage()
                y = h - 2*cm
                c.setFont(\"Helvetica\", 10)

        c.save()