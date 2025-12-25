from __future__ import annotations
import os
import datetime as dt
from typing import List, Dict

import pandas as pd
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel, QPushButton,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QDateEdit, QMessageBox, QSizePolicy, QAbstractItemView
)

from app.ui.charts import MplCanvas, draw_line_er_ctr, draw_bar_topics, draw_donut_segments, draw_radar_quality
from app.services.recommender import RecommenderEngine, TopicRec
from app.services.reporting import ReportService
from app.data.sample_data import make_demo_segments

def _chip(label: str, kind: str = "info") -> QLabel:
    q = QLabel(label)
    if kind == "good":
        q.setObjectName("ChipGood")
    elif kind == "warn":
        q.setObjectName("ChipWarn")
    else:
        q.setObjectName("ChipInfo")
    q.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return q

class MainWindow(QMainWindow):
    def __init__(self, user_name: str, qss_path: str, reports_dir: str):
        super().__init__()
        self.user_name = user_name
        self.setWindowTitle("Рекомендаційна система тем контенту — Author Cabinet (PyQt6)")
        self.resize(1280, 780)

        self.engine = RecommenderEngine(seed=42)
        self.reporter = ReportService(reports_dir)

        self._load_qss(qss_path)
        self._build()

        self._refresh_all()

    def _load_qss(self, qss_path: str):
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception:
            pass

    def _build(self):
        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)

        outer = QHBoxLayout(root)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setMaximumWidth(240)
        sb = QVBoxLayout(self.sidebar)
        sb.setContentsMargins(14, 14, 14, 14)
        sb.setSpacing(10)

        brand = QLabel("◼︎  Аналітика автора")
        brand.setObjectName("H2")

        self.nav_btns: Dict[str, QPushButton] = {}
        def add_nav(key: str, title: str):
            b = QPushButton(title)
            b.setObjectName("NavBtn")
            b.setProperty("active", False)
            b.clicked.connect(lambda _, k=key: self._go(k))
            self.nav_btns[key] = b
            sb.addWidget(b)

        sb.addWidget(brand)
        sb.addWidget(_chip("Навігація", "info"))
        add_nav("overview", "Огляд")
        add_nav("analytics", "Аналітика")
        add_nav("reports", "Звіти та експорт")
        sb.addStretch(1)
        sb.addWidget(_chip("SLA ≤ 200 ms", "info"))
        sb.addWidget(QLabel("demo"))

        # Main column
        maincol = QVBoxLayout()
        maincol.setSpacing(12)

        # TopBar
        self.topbar = QFrame()
        self.topbar.setObjectName("TopBar")
        tb = QHBoxLayout(self.topbar)
        tb.setContentsMargins(14, 12, 14, 12)

        self.model_chip = _chip("Модель: Hybrid NLP + Trends", "info")
        self.sla_chip = _chip("SLA ≤ 200 ms", "info")
        self.user_chip = _chip(f"{self.user_name}", "good")

        tb.addWidget(self.model_chip)
        tb.addSpacing(6)
        tb.addWidget(self.sla_chip)
        tb.addStretch(1)
        tb.addWidget(self.user_chip)

        # Pages
        self.pages = QStackedWidget()
        self.page_overview = self._build_overview()
        self.page_analytics = self._build_analytics()
        self.page_reports = self._build_reports()

        self.pages.addWidget(self.page_overview)
        self.pages.addWidget(self.page_analytics)
        self.pages.addWidget(self.page_reports)

        maincol.addWidget(self.topbar, 0)
        maincol.addWidget(self.pages, 1)

        outer.addWidget(self.sidebar, 0)
        outer.addLayout(maincol, 1)

        self._go("overview")

    # ---------- Page: Overview ----------
    def _build_overview(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # KPIs row
        krow = QHBoxLayout()
        krow.setSpacing(12)
        self.kpi_ctr = self._kpi_card("CTR рекомендованих тем", "6,8%")
        self.kpi_er = self._kpi_card("Engagement Rate", "9,4%")
        self.kpi_trends = self._kpi_card("К-сть актуальних трендів", "14")
        self.kpi_f1 = self._kpi_card("Якість моделі (F1@10)", "0,82")
        for c in (self.kpi_ctr, self.kpi_er, self.kpi_trends, self.kpi_f1):
            krow.addWidget(c, 1)
        layout.addLayout(krow, 0)

        # Recommendations + short forecast
        row = QHBoxLayout()
        row.setSpacing(12)

        left = QFrame(); left.setObjectName("Card")
        l = QVBoxLayout(left); l.setContentsMargins(14, 14, 14, 14); l.setSpacing(10)

        head = QLabel("Рекомендовані теми на найближчий цикл\nпублікацій")
        head.setObjectName("H2")

        controls = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Пошук теми або ключового слова")
        self.platform = QComboBox(); self.platform.addItems(["усі", "Instagram", "TikTok", "YouTube"])
        self.horizon = QComboBox(); self.horizon.addItems(["7 днів", "14 днів", "30 днів"])
        refresh = QPushButton("Оновити")
        refresh.clicked.connect(self._refresh_all)
        controls.addWidget(self.search, 2)
        controls.addWidget(QLabel("Платформа:"), 0)
        controls.addWidget(self.platform, 0)
        controls.addWidget(QLabel("Горизонт:"), 0)
        controls.addWidget(self.horizon, 0)
        controls.addWidget(refresh, 0)

        self.tbl_recs = QTableWidget(0, 7)
        self.tbl_recs.setHorizontalHeaderLabels(["№", "Тема", "Ключові\nдрайвери", "Прогноз\nER", "Тренд", "Пояснюваність", "Статус"])
        self.tbl_recs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_recs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_recs.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_recs.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_recs.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_recs.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.tbl_recs.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_recs.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_recs.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_recs.itemSelectionChanged.connect(self._on_rec_selected)

        l.addWidget(head)
        l.addLayout(controls)
        l.addWidget(self.tbl_recs, 1)

        right = QFrame(); right.setObjectName("Card")
        r = QVBoxLayout(right); r.setContentsMargins(14, 14, 14, 14); r.setSpacing(10)
        rh = QLabel("Короткий зведений прогноз")
        rh.setObjectName("H2")
        self.short_forecast = QLabel("• Оберіть тему в таблиці для деталей прогнозу.")
        self.short_forecast.setWordWrap(True)
        self.short_forecast.setObjectName("Muted")

        self.ab_btn = QPushButton("Запланувати A/B тест")
        self.ab_btn.setObjectName("Secondary")
        self.ab_btn.clicked.connect(self._ab_test)

        self.plan_btn = QPushButton("Додати у планувальник")
        self.plan_btn.setObjectName("Secondary")
        self.plan_btn.clicked.connect(self._planner_add)

        r.addWidget(rh)
        r.addWidget(self.short_forecast, 1)
        r.addWidget(self.ab_btn)
        r.addWidget(self.plan_btn)
        r.addStretch(1)

        row.addWidget(left, 3)
        row.addWidget(right, 1)

        layout.addLayout(row, 1)
        return w

    def _kpi_card(self, title: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        t = QLabel(title); t.setObjectName("Muted")
        v = QLabel(value); v.setStyleSheet("font-size:22px; font-weight:700;")
        s = QLabel("")
        lay.addWidget(t)
        lay.addWidget(v)
        lay.addWidget(s)
        return card

    # ---------- Page: Analytics ----------
    def _build_analytics(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # KPI bar
        krow = QHBoxLayout()
        krow.setSpacing(12)
        self.kpi2_er = self._kpi_card("Середній ER", "9,1%")
        self.kpi2_ctr = self._kpi_card("Середній CTR", "6,4%")
        self.kpi2_topics = self._kpi_card("Теми з високим потенціалом", "12")
        self.kpi2_f1 = self._kpi_card("Точність топ-10 рекомендацій", "0,82")
        for c in (self.kpi2_er, self.kpi2_ctr, self.kpi2_topics, self.kpi2_f1):
            krow.addWidget(c, 1)
        layout.addLayout(krow, 0)

        row = QHBoxLayout()
        row.setSpacing(12)

        # Left: line chart + bar + table
        left = QFrame(); left.setObjectName("Card")
        l = QVBoxLayout(left); l.setContentsMargins(14, 14, 14, 14); l.setSpacing(10)

        self.line_canvas = MplCanvas()
        draw_line_er_ctr(self.line_canvas, days=30, seed=4)

        l.addWidget(self.line_canvas, 1)

        self.bar_canvas = MplCanvas()
        l.addWidget(self.bar_canvas, 1)

        self.tbl_top = QTableWidget(0, 4)
        self.tbl_top.setHorizontalHeaderLabels(["№", "Тема", "Прогноз ER", "Рекоменд. формат"])
        self.tbl_top.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_top.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_top.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_top.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_top.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        l.addWidget(self.tbl_top, 0)

        # Right: donut + radar + segments table
        right = QFrame(); right.setObjectName("Card")
        r = QVBoxLayout(right); r.setContentsMargins(14, 14, 14, 14); r.setSpacing(10)

        self.donut_canvas = MplCanvas()
        r.addWidget(self.donut_canvas, 1)

        self.seg_table = QTableWidget(0, 3)
        self.seg_table.setHorizontalHeaderLabels(["Сегмент", "Частка", "Фокус інтересу"])
        self.seg_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.seg_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.seg_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.seg_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        r.addWidget(self.seg_table, 0)

        self.radar_canvas = MplCanvas()
        r.addWidget(self.radar_canvas, 1)

        row.addWidget(left, 3)
        row.addWidget(right, 2)
        layout.addLayout(row, 1)
        return w

    # ---------- Page: Reports ----------
    def _build_reports(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        left = QFrame(); left.setObjectName("Card")
        l = QVBoxLayout(left); l.setContentsMargins(14, 14, 14, 14); l.setSpacing(10)

        h = QLabel("Швидке формування звіту")
        h.setObjectName("H2")

        form = QHBoxLayout()
        self.tpl = QComboBox()
        self.tpl.addItems(["Аналітика рекомендацій", "Ефективність контенту", "Сегменти аудиторії"])
        self.date_from = QDateEdit()
        self.date_to = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_to.setCalendarPopup(True)
        today = dt.date.today()
        self.date_to.setDate(today)
        self.date_from.setDate(today - dt.timedelta(days=30))
        self.fmt = QComboBox(); self.fmt.addItems(["PDF", "CSV", "HTML"])

        build_btn = QPushButton("Сформувати")
        build_btn.clicked.connect(self._build_report)
        preview_btn = QPushButton("Попередній перегляд")
        preview_btn.setObjectName("Secondary")
        preview_btn.clicked.connect(self._preview_last)

        form.addWidget(QLabel("Шаблон:"))
        form.addWidget(self.tpl, 1)
        form.addWidget(self.date_from, 0)
        form.addWidget(self.date_to, 0)
        form.addWidget(QLabel("Формат:"))
        form.addWidget(self.fmt, 0)
        form.addWidget(build_btn, 0)
        form.addWidget(preview_btn, 0)

        l.addWidget(h)
        l.addLayout(form)

        # Report log
        l.addWidget(QLabel("Журнал сформованих звітів"), 0)

        self.tbl_reports = QTableWidget(0, 6)
        self.tbl_reports.setHorizontalHeaderLabels(["№", "Назва звіту", "Період", "Формат", "Дата/час", "Дія"])
        self.tbl_reports.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_reports.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_reports.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_reports.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_reports.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_reports.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_reports.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        l.addWidget(self.tbl_reports, 1)

        right = QFrame(); right.setObjectName("Card")
        r = QVBoxLayout(right); r.setContentsMargins(14, 14, 14, 14); r.setSpacing(10)
        rh = QLabel("Шаблони звітів")
        rh.setObjectName("H2")
        r.addWidget(rh)
        r.addWidget(self._template_card("Аналітика рекомендацій", "топ тем, прогноз, пояснюваність, ризики", "PDF"))
        r.addWidget(self._template_card("Ефективність контенту", "CTR/ER, історія публікацій, порівняння форматів", "PDF/CSV"))
        r.addWidget(self._template_card("Сегменти аудиторії", "кластери профілів, часові вікна активності", "PDF"))
        r.addStretch(1)
        pack = QLabel("Пакетний експорт\n• Об’єднання PDF-звітів\n• Експорт таблиць у CSV\n• Генерація HTML для публікації")
        pack.setObjectName("Muted")
        r.addWidget(pack)

        layout.addWidget(left, 3)
        layout.addWidget(right, 1)
        return w

    def _template_card(self, title: str, desc: str, chip: str) -> QFrame:
        c = QFrame(); c.setObjectName("Card")
        c.setStyleSheet("QFrame#Card{border-radius:14px;}")
        lay = QHBoxLayout(c); lay.setContentsMargins(12, 12, 12, 12)
        v = QVBoxLayout()
        t = QLabel(title); t.setStyleSheet("font-weight:700;")
        d = QLabel(desc); d.setObjectName("Muted"); d.setWordWrap(True)
        v.addWidget(t); v.addWidget(d)
        lay.addLayout(v, 1)
        lay.addWidget(_chip(chip, "info"), 0)
        return c

    # ---------- Navigation ----------
    def _go(self, key: str):
        for k, b in self.nav_btns.items():
            b.setProperty("active", k == key)
            b.style().unpolish(b); b.style().polish(b)
        if key == "overview":
            self.pages.setCurrentWidget(self.page_overview)
        elif key == "analytics":
            self.pages.setCurrentWidget(self.page_analytics)
        elif key == "reports":
            self.pages.setCurrentWidget(self.page_reports)

    # ---------- Data refresh ----------
    def _refresh_all(self):
        # horizon
        horizon_text = self.horizon.currentText() if hasattr(self, "horizon") else "7 днів"
        days = int(horizon_text.split()[0])
        platform = self.platform.currentText() if hasattr(self, "platform") else "усі"
        self.recs, kpi = self.engine.recommend(horizon_days=days, platform=platform, top_k=6)
        self._fill_overview_table(self.recs)
        self._set_kpis(kpi)

        # analytics derived from recs
        self._fill_analytics(self.recs)

        # reports table refresh
        self._fill_report_log()

    def _set_kpis(self, kpi: Dict[str, float]):
        def set_card(card: QFrame, value: str, delta: str = ""):
            # second widget in layout is value label
            v = card.layout().itemAt(1).widget()
            v.setText(value)
            if delta:
                card.layout().itemAt(2).widget().setText(delta)

        set_card(self.kpi_ctr, f"{kpi.get('ctr',0)*100:.1f}%")
        set_card(self.kpi_er, f"{kpi.get('er',0)*100:.1f}%")
        set_card(self.kpi_trends, f"{int(kpi.get('trends',0))}")
        set_card(self.kpi_f1, f"{kpi.get('f1',0):.2f}")

        set_card(self.kpi2_er, f"{kpi.get('er',0)*100:.1f}%")
        set_card(self.kpi2_ctr, f"{kpi.get('ctr',0)*100:.1f}%")
        set_card(self.kpi2_topics, f"{len(self.recs)*2}")
        set_card(self.kpi2_f1, f"{kpi.get('f1',0):.2f}")

    def _fill_overview_table(self, recs: List[TopicRec]):
        self.tbl_recs.setRowCount(0)
        q = self.search.text().strip().lower()
        for r in recs:
            if q and (q not in r.topic.lower() and q not in r.drivers.lower() and q not in r.explain.lower()):
                continue
            row = self.tbl_recs.rowCount()
            self.tbl_recs.insertRow(row)
            self.tbl_recs.setItem(row, 0, QTableWidgetItem(str(row+1)))
            self.tbl_recs.setItem(row, 1, QTableWidgetItem(r.topic))
            self.tbl_recs.setItem(row, 2, QTableWidgetItem(r.drivers))
            self.tbl_recs.setItem(row, 3, QTableWidgetItem(f\"{r.er_pred*100:.1f}%\"))
            self.tbl_recs.setItem(row, 4, QTableWidgetItem(r.trend))
            self.tbl_recs.setItem(row, 5, QTableWidgetItem(r.explain))
            self.tbl_recs.setItem(row, 6, QTableWidgetItem(r.status))

        if self.tbl_recs.rowCount() > 0:
            self.tbl_recs.selectRow(0)

    def _on_rec_selected(self):
        items = self.tbl_recs.selectedItems()
        if not items:
            return
        row = self.tbl_recs.currentRow()
        # map selected row to recs by row index (after filtering may differ)
        topic = self.tbl_recs.item(row, 1).text()
        rec = next((x for x in self.recs if x.topic == topic), None)
        if not rec:
            return
        # Build a short forecast similar to screenshot
        # heuristics
        fmt = "short / карусель" if rec.ctr_pred > 0.055 else "гайд 30–45 с"
        peak = "12:00–14:00 / 19:00–21:00"
        ab = f\"Заплановано A/B: '{rec.topic}' vs 'Короткі навчальні формати'\"

        text = (
            f\"• Оптимальний формат: {fmt}\\n\"
            f\"• Рекомендовані вікна публікацій: {peak}\\n\"
            f\"• Прогноз ER у день: {rec.er_pred*100:.1f}%\\n\"
            f\"• Прогноз CTR у день: {rec.ctr_pred*100:.1f}%\\n\"
            f\"• Пояснюваність: {rec.explain}\\n\"
            f\"• Статус: {rec.status} (тренд: {rec.trend})\"
        )
        self.short_forecast.setText(text)

    def _fill_analytics(self, recs: List[TopicRec]):
        # bar chart
        labels = [r.topic.split()[0] if len(r.topic) > 18 else r.topic for r in recs]
        values = [r.er_pred for r in recs]
        draw_bar_topics(self.bar_canvas, labels, values)

        # top table
        self.tbl_top.setRowCount(0)
        for i, r in enumerate(recs, start=1):
            row = self.tbl_top.rowCount()
            self.tbl_top.insertRow(row)
            self.tbl_top.setItem(row, 0, QTableWidgetItem(str(i)))
            self.tbl_top.setItem(row, 1, QTableWidgetItem(r.topic))
            self.tbl_top.setItem(row, 2, QTableWidgetItem(f\"{r.er_pred*100:.1f}%\"))
            fmt = "short / карусель" if r.ctr_pred > 0.055 else "гайд 30–45 с"
            self.tbl_top.setItem(row, 3, QTableWidgetItem(fmt))

        # segments
        segs = make_demo_segments(seed=11)
        self.seg_df = pd.DataFrame([{
            "Сегмент": s.name,
            "Частка": round(s.share*100),
            "Фокус інтересу": s.focus
        } for s in segs])
        self.seg_table.setRowCount(0)
        for _, rowv in self.seg_df.iterrows():
            row = self.seg_table.rowCount()
            self.seg_table.insertRow(row)
            self.seg_table.setItem(row, 0, QTableWidgetItem(str(rowv["Сегмент"])))
            self.seg_table.setItem(row, 1, QTableWidgetItem(f\"{int(rowv['Частка'])}%\"))
            self.seg_table.setItem(row, 2, QTableWidgetItem(str(rowv["Фокус інтересу"])))

        # donut
        draw_donut_segments(self.donut_canvas, [s.name for s in segs], [s.share for s in segs])

        # radar
        metrics = {
            "Точність": 0.82,
            "Своєчасність": 0.74,
            "Персоналізація": 0.78,
            "Стабільність": 0.70,
            "Пояснюваність": 0.76,
            "Різноманітність": 0.68,
        }
        draw_radar_quality(self.radar_canvas, metrics)

    # ---------- Reports ----------
    def _build_report(self):
        try:
            template = self.tpl.currentText()
            d1 = self.date_from.date().toPyDate()
            d2 = self.date_to.date().toPyDate()
            fmt = self.fmt.currentText()
            # Ensure data exists
            if not hasattr(self, "recs"):
                self._refresh_all()
            entry = self.reporter.build(template, d1, d2, fmt, self.recs, {
                "ctr": sum([r.ctr_pred for r in self.recs]) / max(1, len(self.recs)),
                "er": sum([r.er_pred for r in self.recs]) / max(1, len(self.recs)),
                "trends": len([r for r in self.recs if r.trend == "зростає"]),
                "f1": 0.82,
            }, self.seg_df)
            self._fill_report_log()
            QMessageBox.information(self, "Звіт сформовано", f"Файл: {os.path.basename(entry.filepath)}")
        except Exception as e:
            QMessageBox.critical(self, "Помилка", str(e))

    def _fill_report_log(self):
        entries = self.reporter.entries()
        self.tbl_reports.setRowCount(0)
        for e in entries:
            row = self.tbl_reports.rowCount()
            self.tbl_reports.insertRow(row)
            self.tbl_reports.setItem(row, 0, QTableWidgetItem(str(e.rid)))
            self.tbl_reports.setItem(row, 1, QTableWidgetItem(e.title))
            self.tbl_reports.setItem(row, 2, QTableWidgetItem(e.period))
            self.tbl_reports.setItem(row, 3, QTableWidgetItem(e.fmt))
            self.tbl_reports.setItem(row, 4, QTableWidgetItem(e.created_at.strftime("%d.%m %H:%M")))

            btn = QPushButton("відкрити")
            btn.setObjectName("Secondary")
            btn.clicked.connect(lambda _, p=e.filepath: self._open_file(p))
            self.tbl_reports.setCellWidget(row, 5, btn)

    def _open_file(self, path: str):
        if not os.path.exists(path):
            QMessageBox.warning(self, "Файл не знайдено", "Файл звіту не існує.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _preview_last(self):
        entries = self.reporter.entries()
        if not entries:
            QMessageBox.information(self, "Немає звітів", "Спочатку сформуйте звіт.")
            return
        self._open_file(entries[0].filepath)

    # ---------- A/B + Planner (demo) ----------
    def _ab_test(self):
        QMessageBox.information(
            self, "A/B тестування (демо)",
            "Демо-модуль: A/B тест формується для обраної теми та контрольної теми.\n"
            "У повному продукті тут підключається збір подій (GA4/UTM), статистика та порівняння ER/CTR."
        )

    def _planner_add(self):
        items = self.tbl_recs.selectedItems()
        if not items:
            QMessageBox.information(self, "Планувальник", "Оберіть тему в таблиці.")
            return
        topic = self.tbl_recs.item(self.tbl_recs.currentRow(), 1).text()
        QMessageBox.information(
            self, "Планувальник (демо)",
            f"Тема додана у план публікацій: {topic}\n"
            "У повній версії: календар, нагадування, інтеграції з API платформ."
        )