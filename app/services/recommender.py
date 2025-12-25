from __future__ import annotations
import random
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

import numpy as np

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    from sklearn.ensemble import RandomForestRegressor
except Exception:  # pragma: no cover
    TfidfVectorizer = None
    KMeans = None
    RandomForestRegressor = None

from app.data.sample_data import TopicItem, make_demo_topics

@dataclass
class TopicRec:
    idx: int
    topic: str
    drivers: str
    er_pred: float
    trend: str  # "зростає" / "стабільно" / "спадає"
    explain: str
    status: str  # "кандидат" / "резерв" / "перегляд"
    ctr_pred: float

def _clamp(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return max(a, min(b, x))

def _trend_label(delta: float) -> str:
    if delta > 0.03:
        return "зростає"
    if delta < -0.03:
        return "спадає"
    return "стабільно"

def _status_by_score(score: float) -> str:
    if score >= 0.70:
        return "кандидат"
    if score >= 0.55:
        return "резерв"
    return "перегляд"

class RecommenderEngine:

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        self._init_models()

    def _init_models(self) -> None:
        # TF-IDF + KMeans
        if TfidfVectorizer is not None:
            self.vectorizer = TfidfVectorizer(ngram_range=(1,2))
        else:
            self.vectorizer = None

        self.kmeans = KMeans(n_clusters=4, random_state=self.seed, n_init=10) if KMeans is not None else None

        # Regressors
        self.er_model = RandomForestRegressor(
            n_estimators=200, random_state=self.seed, max_depth=6
        ) if RandomForestRegressor is not None else None
        self.ctr_model = RandomForestRegressor(
            n_estimators=200, random_state=self.seed + 1, max_depth=6
        ) if RandomForestRegressor is not None else None

        self._fit_synthetic_predictors()

    def _fit_synthetic_predictors(self) -> None:
        # Build synthetic dataset where features roughly map to ER/CTR.
        # Features: [base_popularity, seasonality, novelty, trend_boost, cluster_id]
        X, y_er, y_ctr = [], [], []
        topics = make_demo_topics(seed=7)
        for i in range(600):
            t = self.rng.choice(topics)
            cluster_id = self.rng.randrange(4)
            trend_boost = self.rng.uniform(-0.08, 0.10)
            base = t.base_popularity
            season = t.seasonality
            nov = t.novelty

            # latent "quality" + noise
            quality = 0.45*base + 0.25*nov + 0.20*season + 0.10*(cluster_id/3.0)
            er = _clamp(0.04 + 0.14*quality + trend_boost + self.rng.gauss(0, 0.015), 0.02, 0.16)
            ctr = _clamp(0.02 + 0.10*(0.55*base + 0.25*season + 0.20*nov) + 0.6*trend_boost + self.rng.gauss(0, 0.012), 0.01, 0.14)

            X.append([base, season, nov, trend_boost, cluster_id])
            y_er.append(er)
            y_ctr.append(ctr)

        X = np.asarray(X, dtype=float)
        y_er = np.asarray(y_er, dtype=float)
        y_ctr = np.asarray(y_ctr, dtype=float)

        if self.er_model is not None:
            self.er_model.fit(X, y_er)
        if self.ctr_model is not None:
            self.ctr_model.fit(X, y_ctr)

    def recommend(self, horizon_days: int = 7, platform: str = "усі", top_k: int = 6) -> Tuple[List[TopicRec], Dict[str, float]]:
        topics = make_demo_topics(seed=7 + self.rng.randrange(0, 10_000))
        # Prepare text for clustering
        texts = [" ".join([t.topic] + t.keywords) for t in topics]

        if self.vectorizer is not None and self.kmeans is not None:
            Xtxt = self.vectorizer.fit_transform(texts)
            clusters = self.kmeans.fit_predict(Xtxt)
            feature_names = np.array(self.vectorizer.get_feature_names_out())
        else:
            clusters = np.array([self.rng.randrange(4) for _ in topics])
            feature_names = None

        # Simulate weekly trend change
        deltas = [self.rng.uniform(-0.06, 0.08) for _ in topics]

        recs: List[TopicRec] = []
        for i, t in enumerate(topics):
            cluster_id = int(clusters[i])
            trend_boost = float(deltas[i])
            trend = _trend_label(trend_boost)

            feat = np.array([[t.base_popularity, t.seasonality, t.novelty, trend_boost, cluster_id]], dtype=float)

            if self.er_model is not None:
                er = float(self.er_model.predict(feat)[0])
            else:
                er = float(_clamp(0.06 + 0.06*t.base_popularity + 0.04*t.novelty + trend_boost, 0.02, 0.16))

            if self.ctr_model is not None:
                ctr = float(self.ctr_model.predict(feat)[0])
            else:
                ctr = float(_clamp(0.04 + 0.05*t.base_popularity + 0.03*t.seasonality + 0.6*trend_boost, 0.01, 0.14))

            score = 0.65*(er/0.16) + 0.35*(ctr/0.14)
            status = _status_by_score(score)

            drivers = ", ".join(t.keywords[:3])

            explain = self._explain_topic(i, t, clusters, feature_names)

            recs.append(TopicRec(
                idx=i+1,
                topic=t.topic,
                drivers=drivers,
                er_pred=er,
                trend=trend,
                explain=explain,
                status=status,
                ctr_pred=ctr
            ))

        # Sort by predicted ER (as in screenshot)
        recs.sort(key=lambda r: r.er_pred, reverse=True)
        recs = recs[:top_k]

        # KPIs summary (last 7 days)
        kpi = {
            "ctr": float(np.mean([r.ctr_pred for r in recs])),
            "er": float(np.mean([r.er_pred for r in recs])),
            "trends": float(len([r for r in recs if r.trend == "зростає"])),
            "f1": 0.82,  # demo
        }
        return recs, kpi

    def _explain_topic(self, i: int, t: TopicItem, clusters: np.ndarray, feature_names: Optional[np.ndarray]) -> str:
        # Simple explanation string:
        # - strongest TF‑IDF terms for this topic within its cluster (if available)
        # - feature importance proxy from models (if available)
        base_terms = [kw for kw in t.keywords[:3]]
        if self.vectorizer is None or self.kmeans is None or feature_names is None:
            return "Високий внесок: " + ", ".join(base_terms)

        # Identify top terms for the topic itself
        text = " ".join([t.topic] + t.keywords)
        v = self.vectorizer.transform([text]).toarray()[0]
        top_idx = np.argsort(v)[-3:][::-1]
        top_terms = [str(feature_names[j]) for j in top_idx if v[j] > 0]

        terms = top_terms if top_terms else base_terms

        # model feature importances (lightweight proxy)
        parts = []
        if getattr(self.er_model, "feature_importances_", None) is not None:
            fi = self.er_model.feature_importances_
            # map: 0 base,1 season,2 novelty,3 trend_boost,4 cluster_id
            best = int(np.argmax(fi))
            labels = ["популярність", "сезонність", "новизна", "тренд", "сегмент"]
            parts.append(f"ключовий фактор: {labels[best]}")
        return " / ".join([f"Терміни: {', '.join(terms)}"] + parts)