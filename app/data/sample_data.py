from __future__ import annotations
import random
import math
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class TopicItem:
    topic: str
    keywords: List[str]
    base_popularity: float  # 0..1
    seasonality: float      # 0..1
    novelty: float          # 0..1

@dataclass
class AudienceSegment:
    name: str
    share: float  # 0..1
    focus: str

def _clamp(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return max(a, min(b, x))

def make_demo_topics(seed: int = 7) -> List[TopicItem]:
    rng = random.Random(seed)
    catalog = [
        ("AI-інструменти для креаторів", ["AI", "workflow", "automation", "генерація", "контент"], 0.78, 0.22, 0.62),
        ("Короткі навчальні формати", ["how-to", "мікро-уроки", "чек-лист", "гайд"], 0.70, 0.18, 0.55),
        ("Тренди цифрової безпеки", ["privacy", "2FA", "secure", "кібербезпека"], 0.62, 0.25, 0.48),
        ("Аналітика SMM та KPI", ["CTR", "ER", "A/B", "dashboards", "metrics"], 0.60, 0.14, 0.35),
        ("Креативні шаблони та UI-поради", ["design", "template", "minimalism", "UI"], 0.58, 0.16, 0.50),
        ("Нішеві інтерв'ю з експертами", ["інтерв'ю", "експерт", "кейс", "поради"], 0.54, 0.12, 0.40),
        ("AR/VR для освіти", ["AR", "VR", "edtech", "3D", "симуляції"], 0.49, 0.20, 0.60),
        ("Побутова продуктивність", ["productivity", "time", "habit", "tools"], 0.52, 0.08, 0.30),
        ("Розбір трендів платформ", ["Instagram", "TikTok", "YouTube", "алгоритми"], 0.65, 0.24, 0.42),
        ("Сторітелінг для брендів", ["story", "brand", "tone", "format"], 0.57, 0.10, 0.45),
        ("Інженерні добірки", ["hardware", "IoT", "edge", "sensors"], 0.44, 0.12, 0.58),
        ("Порівняння інструментів", ["vs", "comparison", "stack", "плюси/мінуси"], 0.59, 0.10, 0.38),
    ]
    items: List[TopicItem] = []
    for t in catalog:
        # add a tiny noise to look live
        items.append(TopicItem(
            topic=t[0],
            keywords=t[1],
            base_popularity=_clamp(t[2] + rng.uniform(-0.05, 0.05)),
            seasonality=_clamp(t[3] + rng.uniform(-0.05, 0.05)),
            novelty=_clamp(t[4] + rng.uniform(-0.05, 0.05)),
        ))
    return items

def make_demo_segments(seed: int = 11) -> List[AudienceSegment]:
    rng = random.Random(seed)
    segments = [
        ("S2 Practical learners", 0.34, "how-to, мікро-уроки, чек-листи"),
        ("S1 Tech-aware", 0.28, "AI, безпека, аналітика"),
        ("S3 Visual-first", 0.21, "дизайн, шаблони, UI-поради"),
        ("S4 Mixed casual", 0.17, "легкі огляди, мікс тем"),
    ]
    # small perturbation and renormalize
    pert = [max(0.05, s[1] + rng.uniform(-0.03, 0.03)) for s in segments]
    total = sum(pert)
    pert = [p/total for p in pert]
    out = [AudienceSegment(segments[i][0], pert[i], segments[i][2]) for i in range(len(segments))]
    # sort by share desc
    out.sort(key=lambda x: x.share, reverse=True)
    return out