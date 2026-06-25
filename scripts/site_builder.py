"""
Строит красивые HTML страницы для GitHub Pages.
Использует Chart.js — никакого matplotlib на сайте.
"""
import json
from pathlib import Path
from datetime import datetime

DOCS = Path("docs")
NEWS_DIR = DOCS / "news"
NEWS_DIR.mkdir(parents=True, exist_ok=True)

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
    "Занятость":       "#1565c0",
}


def _cat_color(cat):
    return CATEGORY_COLOR.get(cat, "#37474f")


def _chart_js(analysis: dict) -> str:
    """Генерирует Chart.js блок если есть данные."""
    stats = analysis.get("key_stats", [])
    if len(stats) < 2:
        return ""

    # Пытаемся извлечь числа из значений
    chart_data = []
    for s in stats[:6]:
        try:
            val_str = s.get("value", "").replace(",", ".").replace(" ", "")
            val = float(val_str)
            chart_data.append({"label": s.get("label", "")[:30], "value": val})
        except (ValueError, AttributeError):
            continue

    if len(chart_data) < 2:
        return ""

    labels = json.dumps([d["label"] for d in chart_data], ensure_ascii=False)
    values = json.dumps([d["value"] for d in chart_data])
    color = _cat_color(analysis.get("category", ""))

    return f"""
<div style="margin-top:24px;">
  <canvas id="chart" style="max-height:260px;"></canvas>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
new Chart(document.getElementById('chart'), {{
  type: 'bar',
  data: {{
    labels: {labels},
    datasets: [{{
      data: {values},
      backgroundColor: '{color}cc',
      borderColor: '{color}',
      borderWidth: 1,
      borderRadius: 6,
    }}]
  }},
  options: {{
    indexAxis: {json.dumps('y' if len(chart_data) > 3 else 'x')},
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ grid: {{ color: '#f0f0f0' }}, ticks: {{ font: {{ size: 11 }} }} }},
      y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 11 }} }} }}
    }}
  }}
}});
</script>"""


def build_article_page(article: dict, analysis: dict) -> str:
    aid = article["id"]
    color = _cat_color(analysis.get("category", ""))
    bg = color + "12"

    # Карточки статистики
    stats_html = ""
    for s in analysis.get("key_stats", []):
        trend = s.get("trend", "neutral")
        t_icon = {"up": "↑", "down": "↓", "neutral": "→"}.get(trend, "→")
        t_color = {"up": "#0d652d", "down": "#c62828", "neutral": "#78909c"}.get(trend, "#78909c")
        stats_html += f"""
      <div style="background:{bg};border-radius:12px;padding:16px 14px;position:relative;">
        <div style="font-size:22px;font-weight:700;color:{color};line-height:1.1;">
          {s.get('value','')} <span style="font-size:13px;opacity:.75">{s.get('unit','')}</span>
        </div>
        <div style="font-size:12px;color:#607d8b;margin-top:5px;line-height:1.3;">{s.get('label','')}</div>
        <div style="position:absolute;top:12px;right:12px;font-size:16px;font-weight:700;color:{t_color}">{t_icon}</div>
      </div>"""

    chart = _chart_js(analysis)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{analysis.get('headline', article.get('title',''))}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f0f2f5;color:#1a1a2e;min-height:100vh}}
.wrap{{max-width:720px;margin:0 auto;padding:20px 16px 48px}}
.back{{display:inline-flex;align-items:center;gap:6px;color:{color};font-size:14px;font-weight:600;text-decoration:none;margin-bottom:16px;}}
.card{{background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 2px 20px rgba(0,0,0,.07)}}
.header{{background:{color};padding:22px 24px 20px;}}
.cat-badge{{display:inline-block;background:rgba(255,255,255,.2);color:#fff;font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;letter-spacing:.4px;margin-bottom:10px}}
.headline{{color:#fff;font-size:20px;font-weight:700;line-height:1.35}}
.period{{color:rgba(255,255,255,.7);font-size:13px;margin-top:6px}}
.body{{padding:24px 24px 28px}}
.main-stat{{background:{bg};border-radius:12px;padding:18px 20px;margin-bottom:20px;}}
.main-val{{font-size:42px;font-weight:800;color:{color};line-height:1}}
.main-unit{{font-size:16px;font-weight:600;color:{color};opacity:.75}}
.stats-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:12px;margin-bottom:20px}}
.footer{{border-top:1px solid #eceff1;padding-top:16px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;align-items:center}}
.footer a{{color:{color};font-size:13px;font-weight:600;text-decoration:none}}
.footer a:hover{{text-decoration:underline}}
.date{{font-size:12px;color:#90a4ae}}
</style>
</head>
<body>
<div class="wrap">
  <a class="back" href="../index.html">← Все новости</a>
  <div class="card">
    <div class="header">
      <div class="cat-badge">{analysis.get('category','Статистика')}</div>
      <h1 class="headline">{analysis.get('headline', article.get('title',''))}</h1>
      {"<div class='period'>" + analysis.get('period','') + "</div>" if analysis.get('period') else ""}
    </div>
    <div class="body">
      {"<div class='main-stat'><div class='main-val'>" + analysis.get('main_value','') + " <span class='main-unit'>" + analysis.get('main_unit','') + "</span></div></div>" if analysis.get('main_value') else ""}
      <div class="stats-grid">{stats_html}</div>
      {chart}
      <div class="footer">
        <a href="{article.get('url','')}" target="_blank">Источник: stat.uz →</a>
        <span class="date">{article.get('date','')}</span>
      </div>
    </div>
  </div>
</div>
</body>
</html>"""

    path = NEWS_DIR / f"{aid}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


def build_index(articles: list):
    """Главная страница — лента карточек."""
    cards = ""
    for a in sorted(articles, key=lambda x: x.get("date",""), reverse=True)[:80]:
        an = a.get("analysis", {})
        color = _cat_color(an.get("category",""))
        bg = color + "12"

        cards += f"""
    <a href="news/{a['id']}.html" style="text-decoration:none;color:inherit;display:block;">
      <div class="card" onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 24px rgba(0,0,0,.12)'" onmouseout="this.style.transform='';this.style.boxShadow='0 2px 12px rgba(0,0,0,.07)'">
        <div style="height:6px;background:{color};border-radius:10px 10px 0 0;"></div>
        <div style="padding:14px 16px 16px;">
          <div style="display:inline-block;background:{bg};color:{color};font-size:11px;font-weight:600;padding:3px 9px;border-radius:20px;margin-bottom:8px;">{an.get('category','Статистика')}</div>
          <div style="font-size:13px;font-weight:600;line-height:1.4;color:#1a1a2e;margin-bottom:10px;min-height:36px;">{an.get('headline', a.get('title',''))[:72]}</div>
          {"<div style='font-size:28px;font-weight:800;color:" + color + ";line-height:1;margin-bottom:4px;'>" + an.get('main_value','') + " <span style='font-size:14px;opacity:.75'>" + an.get('main_unit','') + "</span></div>" if an.get('main_value') else "<div style='height:36px;'></div>"}
          <div style="font-size:11px;color:#90a4ae;margin-top:6px;">{a.get('date','')}</div>
        </div>
      </div>
    </a>"""

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Статистика Узбекистана</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f0f2f5;color:#1a1a2e}}
.header{{background:#1a56a0;padding:20px 24px;position:sticky;top:0;z-index:10}}
.header h1{{color:#fff;font-size:20px;font-weight:600}}
.header p{{color:rgba(255,255,255,.65);font-size:12px;margin-top:3px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;padding:20px}}
.card{{background:#fff;border-radius:10px;box-shadow:0 2px 12px rgba(0,0,0,.07);transition:transform .2s,box-shadow .2s;}}
</style>
</head>
<body>
<div class="header">
  <h1>📊 Статистика Узбекистана</h1>
  <p>Нацкомстат УЗ · Обновлено: {now}</p>
</div>
<div class="grid">{cards}</div>
</body>
</html>"""

    (DOCS / "index.html").write_text(html, encoding="utf-8")
    print(f"[site] index.html обновлён ({len(articles)} статей)")
