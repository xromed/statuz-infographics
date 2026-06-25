"""
Генерирует инфографику как PNG через matplotlib.
Никакого DALL-E — только GPT для данных + Python для рендера.
"""
import os
import textwrap
from pathlib import Path

IMG_DIR = Path("docs/news/img")
IMG_DIR.mkdir(parents=True, exist_ok=True)

CATEGORY_COLOR = {
    "Демография":      "#7b1fa2",
    "Экономика":       "#0d652d",
    "Промышленность":  "#b5451b",
    "Цены":            "#e37400",
    "Торговля":        "#0d652d",
    "Здравоохранение": "#c62828",
    "Образование":     "#0277bd",
    "Спорт":           "#2e7d32",
    "Туризм":          "#00695c",
    "Статистика":      "#37474f",
}


def generate(article_id: str, analysis: dict) -> str | None:
    """
    Строит PNG инфографику из analysis-данных.
    Возвращает относительный путь img/ID.png или None.
    """
    out_path = IMG_DIR / f"{article_id}.png"
    if out_path.exists():
        return f"img/{article_id}.png"

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import FancyBboxPatch
    except ImportError:
        print("[image] matplotlib не установлен")
        return None

    color = CATEGORY_COLOR.get(analysis.get("category", ""), "#37474f")
    headline = analysis.get("headline", "Статистика")
    category = analysis.get("category", "Статистика")
    main_value = analysis.get("main_value", "")
    main_unit = analysis.get("main_unit", "")
    period = analysis.get("period", "")
    key_stats = analysis.get("key_stats", [])

    fig = plt.figure(figsize=(9, 5), facecolor="white")
    fig.patch.set_facecolor("white")

    # ── Верхняя полоса (заголовок) ──────────────────────────────────
    ax_head = fig.add_axes([0, 0.78, 1, 0.22])
    ax_head.set_xlim(0, 1); ax_head.set_ylim(0, 1)
    ax_head.axis("off")
    ax_head.add_patch(plt.Rectangle((0, 0), 1, 1, color=color, zorder=0))

    # Категория
    ax_head.text(0.03, 0.82, category.upper(),
                 color="white", fontsize=9, fontweight="bold",
                 alpha=0.75, va="top", transform=ax_head.transAxes)
    # Заголовок
    wrapped = textwrap.fill(headline, width=62)
    ax_head.text(0.03, 0.65, wrapped,
                 color="white", fontsize=13, fontweight="bold",
                 va="top", linespacing=1.3, transform=ax_head.transAxes)
    # Период
    if period:
        ax_head.text(0.97, 0.15, period,
                     color="white", fontsize=9, alpha=0.7,
                     ha="right", va="bottom", transform=ax_head.transAxes)

    # ── Главная цифра ────────────────────────────────────────────────
    ax_main = fig.add_axes([0, 0.35, 0.38, 0.43])
    ax_main.axis("off")
    ax_main.set_facecolor("#f8f9fa")
    ax_main.add_patch(plt.Rectangle((0, 0), 1, 1, color="#f0f2f5", zorder=0))

    if main_value:
        ax_main.text(0.5, 0.62, main_value,
                     color=color, fontsize=32, fontweight="bold",
                     ha="center", va="center", transform=ax_main.transAxes)
        ax_main.text(0.5, 0.28, main_unit,
                     color=color, fontsize=13, alpha=0.75,
                     ha="center", va="center", transform=ax_main.transAxes)
    else:
        ax_main.text(0.5, 0.5, "📊",
                     fontsize=40, ha="center", va="center",
                     transform=ax_main.transAxes)

    # ── Ключевые показатели (мини-бары) ──────────────────────────────
    ax_stats = fig.add_axes([0.40, 0.05, 0.58, 0.70])
    ax_stats.axis("off")
    ax_stats.set_facecolor("white")

    stats_to_show = key_stats[:5]
    if stats_to_show:
        n = len(stats_to_show)
        row_h = 1.0 / n
        for i, s in enumerate(stats_to_show):
            y = 1 - (i + 0.5) * row_h
            trend = s.get("trend", "neutral")
            t_color = {"up": "#0d652d", "down": "#c62828", "neutral": "#546e7a"}.get(trend, "#546e7a")
            t_icon = {"up": "▲", "down": "▼", "neutral": "→"}.get(trend, "→")

            # Полоска фона
            ax_stats.add_patch(plt.Rectangle(
                (0, y - row_h * 0.42), 1, row_h * 0.84,
                color="#f0f2f5", zorder=0, transform=ax_stats.transAxes
            ))
            # Акцентная полоска слева
            ax_stats.add_patch(plt.Rectangle(
                (0, y - row_h * 0.42), 0.012, row_h * 0.84,
                color=color, zorder=1, transform=ax_stats.transAxes
            ))

            val_str = f"{s.get('value','')} {s.get('unit','')}".strip()
            label_str = s.get("label", "")

            ax_stats.text(0.03, y + row_h * 0.12, val_str,
                          fontsize=12, fontweight="bold", color=color,
                          va="center", transform=ax_stats.transAxes)
            ax_stats.text(0.03, y - row_h * 0.18, label_str,
                          fontsize=8.5, color="#546e7a",
                          va="center", transform=ax_stats.transAxes)
            ax_stats.text(0.97, y, t_icon,
                          fontsize=11, color=t_color, ha="right",
                          va="center", transform=ax_stats.transAxes)

    # ── Нижняя строка (источник) ─────────────────────────────────────
    ax_foot = fig.add_axes([0, 0, 1, 0.07])
    ax_foot.axis("off")
    ax_foot.add_patch(plt.Rectangle((0, 0), 1, 1, color="#eceff1", zorder=0))
    ax_foot.text(0.02, 0.5, "Источник: Национальный комитет Республики Узбекистан по статистике  •  stat.uz",
                 fontsize=8, color="#90a4ae", va="center", transform=ax_foot.transAxes)

    plt.savefig(str(out_path), dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"[image] Инфографика: {out_path}")
    return f"img/{article_id}.png"
