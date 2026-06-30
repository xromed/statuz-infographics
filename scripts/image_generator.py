"""
Генерирует чистую PNG-карточку для Telegram.
Дизайн: цветная шапка, большая цифра, мини-таблица показателей.
"""
import textwrap
from pathlib import Path

IMG_DIR = Path("docs/news/img")
IMG_DIR.mkdir(parents=True, exist_ok=True)

CATEGORY_COLOR = {
    "Демография":      "#7b1fa2",
    "Экономика":       "#1b5e20",
    "Промышленность":  "#bf360c",
    "Цены":            "#e65100",
    "Торговля":        "#1b5e20",
    "Здравоохранение": "#b71c1c",
    "Образование":     "#01579b",
    "Спорт":           "#2e7d32",
    "Туризм":          "#004d40",
    "Статистика":      "#263238",
    "Занятость":       "#0d47a1",
}

W, H = 1200, 630   # соотношение 1.9:1 — идеально для Telegram превью


def hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))


def generate(article_id: str, analysis: dict) -> str | None:
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

    color_hex = CATEGORY_COLOR.get(analysis.get("category", ""), "#263238")
    color_rgb = hex_to_rgb(color_hex)
    color_light = tuple(min(1.0, c + 0.45) for c in color_rgb)  # осветлённый фон

    headline  = analysis.get("headline", "Статистика Узбекистана")
    category  = analysis.get("category", "Статистика")
    main_val  = analysis.get("main_value", "")
    main_unit = analysis.get("main_unit", "")
    period    = analysis.get("period", "")
    key_stats = analysis.get("key_stats", [])[:4]

    # ── Создаём canvas ───────────────────────────────────────────────
    dpi = 150
    fig_w, fig_h = W / dpi, H / dpi
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(0, H)
    ax.axis("off")
    ax.set_facecolor("white")

    # ── Цветная шапка (верхние 38%) ──────────────────────────────────
    header_h = int(H * 0.38)
    ax.add_patch(plt.Rectangle((0, H - header_h), W, header_h,
                                color=color_rgb, zorder=1))

    # Тонкая полоска под шапкой (акцент)
    ax.add_patch(plt.Rectangle((0, H - header_h - 4), W, 4,
                                color=color_light, zorder=1))

    # Бейдж категории
    badge_x, badge_y = 48, H - 44
    ax.text(badge_x, badge_y, f"  {category.upper()}  ",
            color=color_rgb, fontsize=12, fontweight="bold",
            va="top", ha="left", zorder=3,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor="white", alpha=0.92))

    # Заголовок
    wrapped = textwrap.fill(headline, width=52)
    ax.text(48, H - 90, wrapped,
            color="white", fontsize=22, fontweight="bold",
            va="top", ha="left", linespacing=1.35, zorder=2)

    # Период
    if period:
        ax.text(W - 48, H - header_h + 18, period,
                color="white", fontsize=12, alpha=0.75,
                va="bottom", ha="right", zorder=2)

    # ── Тело: главная цифра (левая колонка) ──────────────────────────
    body_top = H - header_h - 16
    body_h = body_top - 60   # отступ снизу

    if main_val:
        # Светлый блок под цифрой
        block_w = 360
        ax.add_patch(plt.Rectangle((0, body_top - body_h), block_w, body_h,
                                    color=color_light + (0.18,), zorder=1))

        ax.text(block_w / 2, body_top - body_h / 2 + 14, main_val,
                color=color_rgb, fontsize=54, fontweight="bold",
                va="center", ha="center", zorder=2)
        ax.text(block_w / 2, body_top - body_h / 2 - 42, main_unit,
                color=color_rgb, fontsize=17, alpha=0.75,
                va="center", ha="center", zorder=2)

        stats_x_start = block_w + 20
    else:
        stats_x_start = 48

    # ── Ключевые показатели ──────────────────────────────────────────
    if key_stats:
        # Две колонки
        col_w = (W - stats_x_start - 48) / 2
        row_h = (body_h - 16) / 2

        for i, s in enumerate(key_stats):
            col = i % 2
            row = i // 2
            cx = stats_x_start + col * col_w + col * 12
            cy = body_top - row * row_h - 16

            trend = s.get("trend", "neutral")
            t_color = {"up": "#2e7d32", "down": "#c62828", "neutral": "#78909c"}.get(trend, "#78909c")
            t_icon  = {"up": "↑", "down": "↓", "neutral": "→"}.get(trend, "→")

            # Карточка
            card_h = row_h - 12
            ax.add_patch(FancyBboxPatch(
                (cx, cy - card_h), col_w - 8, card_h,
                boxstyle="round,pad=4", linewidth=0,
                facecolor="#f5f5f5", zorder=1
            ))
            # Цветная полоска сверху карточки
            ax.add_patch(plt.Rectangle(
                (cx + 4, cy - 6), col_w - 16, 5,
                color=color_rgb, zorder=2
            ))

            val_str = f"{s.get('value','')} {s.get('unit','')}".strip()
            ax.text(cx + 16, cy - 24, val_str,
                    color=color_rgb, fontsize=18, fontweight="bold",
                    va="top", ha="left", zorder=3)
            label = textwrap.fill(s.get("label", ""), width=22)
            ax.text(cx + 16, cy - 52, label,
                    color="#546e7a", fontsize=11,
                    va="top", ha="left", linespacing=1.2, zorder=3)
            # Стрелка тренда
            ax.text(cx + col_w - 22, cy - 28, t_icon,
                    color=t_color, fontsize=16, fontweight="bold",
                    va="top", ha="right", zorder=3)

    # ── Нижняя полоска ────────────────────────────────────────────────
    ax.add_patch(plt.Rectangle((0, 0), W, 56,
                                color="#eceff1", zorder=1))
    ax.text(24, 28, "Источник: stat.uz  •  Национальный комитет по статистике Республики Узбекистан",
            color="#90a4ae", fontsize=11, va="center", ha="left", zorder=2)

    # ── Сохраняем ─────────────────────────────────────────────────────
    fig.savefig(str(out_path), dpi=dpi, bbox_inches="tight",
                facecolor="white", edgecolor="none", pad_inches=0)
    plt.close(fig)
    print(f"[image] ✓ {out_path}")
    return f"img/{article_id}.png"
