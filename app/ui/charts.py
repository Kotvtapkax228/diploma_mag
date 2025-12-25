from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MplCanvas(FigureCanvas):
    def __init__(self, parent: Optional[QWidget] = None):
        fig = Figure(figsize=(5, 3), dpi=100)
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        if parent is not None:
            self.setParent(parent)

def clear_ax(ax):
    ax.clear()
    ax.set_facecolor("#ffffff")

def draw_line_er_ctr(canvas: MplCanvas, days: int = 30, seed: int = 1):
    import random
    rng = random.Random(seed)
    clear_ax(canvas.ax)
    xs = list(range(1, days+1))
    er = []
    ctr = []
    base_er = 0.06 + rng.uniform(-0.01, 0.01)
    base_ctr = 0.035 + rng.uniform(-0.008, 0.008)
    for i in xs:
        base_er = min(0.14, max(0.03, base_er + rng.uniform(-0.004, 0.006)))
        base_ctr = min(0.10, max(0.015, base_ctr + rng.uniform(-0.003, 0.004)))
        er.append(base_er)
        ctr.append(base_ctr)
    canvas.ax.plot(xs, [v*100 for v in er], label="Engagement Rate (ER)")
    canvas.ax.plot(xs, [v*100 for v in ctr], label="Click-Through Rate (CTR)")
    canvas.ax.set_title("Динаміка залученості та кліків")
    canvas.ax.set_xlabel("Дні")
    canvas.ax.set_ylabel("Показник, %")
    canvas.ax.grid(True, alpha=0.25)
    canvas.ax.legend(loc="lower right", frameon=False)
    canvas.draw()

def draw_bar_topics(canvas: MplCanvas, labels: List[str], values: List[float]):
    clear_ax(canvas.ax)
    canvas.ax.bar(range(len(labels)), [v*100 for v in values])
    canvas.ax.set_title("Топ тем за прогнозом ефективності")
    canvas.ax.set_ylabel("Прогнозований ER, %")
    canvas.ax.set_xticks(range(len(labels)))
    canvas.ax.set_xticklabels(labels, rotation=25, ha="right")
    canvas.ax.grid(True, axis="y", alpha=0.25)
    canvas.draw()

def draw_donut_segments(canvas: MplCanvas, labels: List[str], shares: List[float]):
    clear_ax(canvas.ax)
    canvas.ax.set_title("Структура аудиторії")
    wedges, _ = canvas.ax.pie(shares, labels=None, startangle=90, wedgeprops=dict(width=0.35))
    canvas.ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    canvas.draw()

def draw_radar_quality(canvas: MplCanvas, metrics: Dict[str, float]):
    import numpy as np
    labels = list(metrics.keys())
    values = list(metrics.values())
    N = len(labels)
    clear_ax(canvas.ax)
    canvas.figure.clf()
    ax = canvas.figure.add_subplot(111, polar=True)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    values2 = values + values[:1]
    angles2 = angles + angles[:1]
    ax.plot(angles2, values2, linewidth=2)
    ax.fill(angles2, values2, alpha=0.15)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.5", "0.75", "1.0"])
    ax.set_title("Профіль якості рекомендацій", pad=14)
    canvas.draw()