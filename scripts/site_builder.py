"""Строит HTML страницы для GitHub Pages."""
import json
from pathlib import Path
from datetime import datetime

DOCS = Path("docs")
NEWS_DIR = DOCS / "news"
NEWS_DIR.mkdir(parents=True, exist_ok=True)

CATEGORY_COLOR = {
    "Демография":     "#7b1fa2",
    "Экономика":      "#0d652d",
    "Промышленность": "#b5451b",
    "Цены":           "#e37400",
    "Торговля":       "#0d652d",
    "Здравоохранение":"#c62828",
    "Образование":    "#0277bd",
    "Спорт":          "#2e7d32",
    "Туризм":         "#00695c",
    "Статистика":     "#37474f",
}
CATEGORY_BG = {k: v + "18" for k, v in CATEGORY_COLOR.items()}


def build_article_page(article: dict, analysis: dict) -> str:
    """Строит страницу статьи, возвращает путь."""
    aid = article["id"]
    color = CATEGORY_COLOR.get(analysis.get("category", ""), "#37474f")
    img_path = analysis.get("img_path", "")
    img_html = f'<img src="{img_path}" alt="" style="width:100%;border-radius:12px 12px 0 0;display:block;max-height:340px;object-fit:cover;">' if img_path else ""

    stats_html = ""
    for s in analysis.get("key_stats", []):
        trend = {"up": "↑", "down": "↓", "neutral": "→"}.get(s.get("trend", ""), "")
        tc = {"up": "#0d652d", "down": "#c62828", "neutral": "#546e7a"}.get(s.get("trend", ""), "#546e7a")
        stats_html += f"""
        <div style="background:#f5f7fa;border-radius:10px;padding:14px 12px;position:relative;">
          <div style="font-size:22px;font-weight:700;color:{color};">{s.get('value','')} <span style="font-size:13px;opacity:.7">{s.get('unit','')}</span></div>
          <div style="font-size:12px;color:#546e7a;margin-top:4px;">{s.get('label','')}</div>
          <div style="position:absolute;top:10px;right:10px;font-size:16px;font-weight:700;color:{tc}">{trend}</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta property="og:image" content="{img_path}">
<title>{analysis.get('headline', article['title'])}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;color:#1a1a2e}}
.wrap{{max-width:700px;margin:0 auto;padding:16px}}
.card{{background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,.08)}}
.body{{padding:24px}}
.cat{{display:inline-block;background:{color}18;color:{color};font-size:12px;font-weight:600;padding:4px 12px;border-radius:20px;margin-bottom:12px}}
h1{{font-size:20px;font-weight:700;line-height:1.35;margin-bottom:8px}}
.period{{font-size:13px;color:#90a4ae;margin-bottom:16px}}
.big-stat{{background:{color}12;border-radius:12px;padding:16px 20px;margin-bottom:20px}}
.big-val{{font-size:36px;font-weight:800;color:{color}}}
.big-unit{{font-size:16px;font-weight:600;color:{color};opacity:.8}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-bottom:20px}}
.footer{{border-top:1px solid #eceff1;padding-top:16px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}}
.footer a{{color:{color};font-size:13px;font-weight:600;text-decoration:none}}
.back{{display:inline-block;margin-bottom:16px;color:{color};font-size:14px;font-weight:600;text-decoration:none}}
</style>
</head>
<body>
<div class="wrap">
  <a class="back" href="../index.html">← Все новости</a>
  <div class="card">
    {img_html}
    <div class="body">
      <div class="cat">{analysis.get('category','Статистика')}</div>
      <h1>{analysis.get('headline', article['title'])}</h1>
      <div class="period">{analysis.get('period','')}</div>

      {"<div class='big-stat'><div class='big-val'>" + analysis.get('main_value','') + " <span class='big-unit'>" + analysis.get('main_unit','') + "</span></div></div>" if analysis.get('main_value') else ""}

      <div class="grid">{stats_html}</div>

      <div class="footer">
        <a href="{article['url']}" target="_blank">Источник: stat.uz →</a>
        <span style="font-size:12px;color:#90a4ae">{article.get('date','')}</span>
      </div>
    </div>
  </div>
</div>
</body></html>"""

    path = NEWS_DIR / f"{aid}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


def build_index(articles: list):
    """Строит главную страницу — ленту новостей."""
    cards = ""
    for a in sorted(articles, key=lambda x: x.get("date",""), reverse=True)[:60]:
        analysis = a.get("analysis", {})
        color = CATEGORY_COLOR.get(analysis.get("category",""), "#37474f")
        img = analysis.get("img_path", "")
        img_html = f'<img src="news/{img}" style="width:100%;height:160px;object-fit:cover;border-radius:10px 10px 0 0;display:block;">' if img else f'<div style="height:8px;background:{color};border-radius:10px 10px 0 0;"></div>'

        cards += f"""
        <a href="news/{a['id']}.html" style="text-decoration:none;color:inherit;">
          <div style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 8px rgba(0,0,0,.07);transition:box-shadow .2s;" onmouseover="this.style.boxShadow='0 4px 20px rgba(0,0,0,.13)'" onmouseout="this.style.boxShadow='0 1px 8px rgba(0,0,0,.07)'">
            {img_html}
            <div style="padding:12px 14px 14px;">
              <div style="background:{color}18;color:{color};font-size:11px;font-weight:600;padding:3px 8px;border-radius:20px;display:inline-block;margin-bottom:6px;">{analysis.get('category','Статистика')}</div>
              <div style="font-size:13px;font-weight:600;line-height:1.35;color:#1a1a2e;margin-bottom:8px;">{analysis.get('headline', a.get('title',''))[:70]}</div>
              {"<div style='font-size:22px;font-weight:700;color:" + color + ";'>" + analysis.get('main_value','') + " <span style='font-size:13px;opacity:.7'>" + analysis.get('main_unit','') + "</span></div>" if analysis.get('main_value') else ""}
              <div style="font-size:11px;color:#90a4ae;margin-top:6px;">{a.get('date','')}</div>
            </div>
          </div>
        </a>"""

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    index = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Статистика Узбекистана</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;color:#1a1a2e}}
.header{{background:#1a56a0;color:#fff;padding:20px 24px;}}
.header h1{{font-size:20px;font-weight:600}}
.header p{{font-size:12px;opacity:.7;margin-top:4px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;padding:20px}}
</style>
</head>
<body>
<div class="header">
  <h1>📊 Статистика Узбекистана</h1>
  <p>Данные Национального комитета по статистике · Обновлено: {now}</p>
</div>
<div class="grid">{cards}</div>
</body></html>"""

    (DOCS / "index.html").write_text(index, encoding="utf-8")
    print(f"[site] index.html обновлён ({len(articles)} статей)")
