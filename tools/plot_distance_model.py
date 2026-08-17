"""
Recreate assets/distance_model_analysis.png from calibration data.

Reads data/game_distance_samples_clean.csv, applies the fitted
GAME_DISTANCE_PARAMS from core/constants.py via predict_units(), and
plots the same two panels shown in the README: pixel-distance spread
per true distance, and predicted-vs-true for the shipped model.

Usage: python tools/plot_distance_model.py
"""

import os
import sys

import matplotlib.pyplot as plt

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from core.constants import GAME_DISTANCE_PARAMS
from tools.analyze_game_distances import CLEAN_PATH, predict_units, read_samples

OUT_PATH = os.path.join(_repo_root, "assets", "distance_model_analysis.png")

TRUE_DISTANCES = [125, 250, 550, 594, 647, 700]


def pixel_dist(px, py, ex, ey):
    return ((px - ex) ** 2 + (py - ey) ** 2) ** 0.5


def main():
    samples = read_samples(CLEAN_PATH)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Left: pixel distance spread per true distance
    by_true = {gd: [] for gd in TRUE_DISTANCES}
    for px, py, ex, ey, gd in samples:
        if gd in by_true:
            by_true[gd].append(pixel_dist(px, py, ex, ey))
    ax1.boxplot([by_true[gd] for gd in TRUE_DISTANCES], labels=[str(d) for d in TRUE_DISTANCES])
    ax1.set_xlabel("Known true distance (game units)")
    ax1.set_ylabel("Measured pixel distance (px)")
    ax1.set_title("Same true distance, different pixel gaps")

    # Right: shipped model predicted vs. true
    preds = [predict_units(GAME_DISTANCE_PARAMS, px, py, ex, ey) for px, py, ex, ey, gd in samples]
    trues = [gd for _, _, _, _, gd in samples]
    n = len(trues)
    mae = sum(abs(p - t) for p, t in zip(preds, trues)) / n
    rmse = (sum((p - t) ** 2 for p, t in zip(preds, trues)) / n) ** 0.5
    mean_t = sum(trues) / n
    ss_res = sum((t - p) ** 2 for t, p in zip(trues, preds))
    ss_tot = sum((t - mean_t) ** 2 for t in trues)
    r2 = 1 - ss_res / ss_tot

    ax2.scatter(trues, preds, alpha=0.15, s=10)
    lims = [0, max(max(trues), max(preds)) * 1.05]
    ax2.plot(lims, lims, "--", color="gray")
    ax2.set_xlabel("True distance (game units)")
    ax2.set_ylabel("Model-predicted distance (game units)")
    ax2.set_title("Shipped model: predicted vs. true")
    ax2.text(
        0.05, 0.95,
        f"RMSE {rmse:.0f}\nMAE {mae:.0f}\nR² {r2:.2f}",
        transform=ax2.transAxes, va="top",
    )

    fig.tight_layout()
    fig.savefig(OUT_PATH, dpi=150)
    print(f"n={n} rmse={rmse:.1f} mae={mae:.1f} r2={r2:.3f} -> {OUT_PATH}")


if __name__ == "__main__":
    main()
