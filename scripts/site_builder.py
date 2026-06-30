"""
Строит HTML-инфографики для GitHub Pages.
Дизайн: анимированные счётчики, KPI-карточки, Chart.js, градиенты.
"""
import json
from pathlib import Path
from datetime import datetime

DOCS = Path("docs")
NEWS_DIR = DOCS / "news"
NEWS_DIR.mkdir(parents=True, exist_ok=True)

# ── Цвета и иконки категорий ──────────────────────────────────────────────────
CATEGORIES = {
    "Демография":         {"color": "#7b1fa2", "light": "#f3e5f5", "icon": "👥"},
    "Экономика":          {"color": "#1565c0", "light": "#e3f2fd", "icon": "📈"},
    "Промышленность":     {"color": "#bf360c", "light": "#fbe9e7", "icon": "🏭"},
    "Цены":               {"color": "#e65100", "light": "#fff3e0", "icon": "💰"},
    "Торговля":           {"color": "#00695c", "light": "#e0f2f1", "icon": "🛒"},
    "Транспорт":          {"color": "#1565c0", "light": "#e3f2fd", "icon": "🚆"},
    "Здравоохранение":    {"color": "#b71c1c", "light": "#ffebee", "icon": "🏥"},
    "Образование":        {"color": "#0277bd", "light": "#e1f5fe", "icon": "🎓"},
    "Спорт":              {"color": "#2e7d32", "light": "#e8f5e9", "icon": "🏆"},
    "Туризм":             {"color": "#00695c", "light": "#e0f2f1", "icon": "✈️"},
    "Статистика":         {"color": "#37474f", "light": "#eceff1", "icon": "📊"},
    "Занятость":          {"color": "#0d47a1", "light": "#e8eaf6", "icon": "💼"},
    "Сельское хозяйство": {"color": "#33691e", "light": "#f1f8e9", "icon": "🌾"},
    "Строительство":      {"color": "#4e342e", "light": "#efebe9", "icon": "🏗️"},
}

def _cat(cat: str) -> dict:
    return CATEGORIES.get(cat, CATEGORIES["Статистика"])


def _trend_badge(trend: str) -> str:
    if trend == "up":
        return '<span class="trend up">↑</span>'
    elif trend == "down":
        return '<span class="trend down">↓</span>'
    return '<span class="trend neutral">→</span>'


def _fmt_value(val: str) -> str:
    """Форматирует число с пробелами-разделителями."""
    try:
        n = float(val)
        if n == int(n):
            return f"{int(n):,}".replace(",", " ")
        return f"{n:,.1f}".replace(",", " ")
    except (ValueError, TypeError):
        return val


def _kpi_cards(key_stats: list, color: str, light: str, headline: str = "") -> str:
    if not key_stats:
        return ""

    cards = ""
    for i, s in enumerate(key_stats[:6]):
        trend_html = _trend_badge(s.get("trend", "neutral"))
        val_fmt = _fmt_value(s["value"])
        # Метка: очищаем от обрывков предложений — берём только до первого глагола
        raw_label = s.get("label", "Показатель")
        label = raw_label[:55]
        unit = s.get("unit", "")[:20]

        # Первая карточка — большая героическая
        if i == 0:
            hero_label = headline[:80] if headline else label
            cards += f"""
      <div class="kpi-hero" style="--c:{color};--bg:{light}">
        <div class="kpi-hero-val">
          <span class="counter" data-target="{s['value']}">{val_fmt}</span>
          <span class="kpi-hero-unit">{unit}</span>
          {trend_html}
        </div>
        <div class="kpi-hero-label">{hero_label}</div>
      </div>"""
        else:
            cards += f"""
      <div class="kpi-card" style="--c:{color};--bg:{light}">
        <div class="kpi-val">
          <span class="counter" data-target="{s['value']}">{val_fmt}</span>
          <span class="kpi-unit">{unit}</span>
        </div>
        <div class="kpi-label">{label}</div>
        {trend_html}
      </div>"""

    return f'<div class="kpi-grid">{cards}</div>'


def _has_years(chart_data: list) -> bool:
    """Проверяет, содержат ли метки годы (временной ряд)."""
    import re
    return sum(1 for s in chart_data if re.search(r'\b(19|20)\d{2}\b', s.get("label", ""))) >= 2


def _chart_block(analysis: dict, color: str) -> str:
    chart_data = analysis.get("chart_data") or []
    if len(chart_data) < 2:
        return ""

    try:
        values = [float(s["value"]) for s in chart_data]
    except (ValueError, TypeError):
        return ""

    unit = chart_data[0].get("unit", "").split()[0] if chart_data else ""
    n = len(chart_data)
    is_timeseries = _has_years(chart_data)

    # Для временных рядов — line chart с градиентной заливкой
    if is_timeseries:
        import re
        raw_labels = []
        for s in chart_data:
            m = re.search(r'\b(19|20)\d{2}\b', s.get("label", ""))
            raw_labels.append(m.group() if m else s.get("label", "")[:12])
        labels = json.dumps(raw_labels, ensure_ascii=False)
        vals_js = json.dumps(values)
        return f"""
<div class="chart-wrap">
  <div class="section-label">Динамика по годам</div>
  <div style="position:relative;height:220px">
    <canvas id="mainChart"></canvas>
  </div>
</div>
<script>
(function(){{
  const ctx = document.getElementById('mainChart').getContext('2d');
  const c = "{color}";
  const grad = ctx.createLinearGradient(0,0,0,220);
  grad.addColorStop(0, c + '44');
  grad.addColorStop(1, c + '00');
  new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: {labels},
      datasets: [{{
        data: {vals_js},
        borderColor: c,
        borderWidth: 2.5,
        backgroundColor: grad,
        fill: true,
        tension: 0.35,
        pointBackgroundColor: c,
        pointRadius: 5,
        pointHoverRadius: 7,
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          backgroundColor: '#1a1a2e',
          padding: 10,
          cornerRadius: 8,
          callbacks: {{ label: ctx => '  ' + ctx.raw.toLocaleString('ru-RU') + ' {unit}' }}
        }}
      }},
      scales: {{
        x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 12, family: 'Inter', weight: '600' }}, color: '#546e7a' }} }},
        y: {{ grid: {{ color: 'rgba(0,0,0,.05)' }}, ticks: {{ font: {{ size: 11, family: 'Inter' }}, color: '#90a4ae' }} }}
      }},
      animation: {{ duration: 1000, easing: 'easeOutQuart' }}
    }}
  }});
}})();
</script>"""

    # Для сравнительных данных — горизонтальный бар
    is_horiz = n >= 4
    axis_param = '"y"' if is_horiz else '"x"'
    max_h = max(280, n * 40) if is_horiz else 220
    grad_coords = "0,0,0,300" if is_horiz else "0,0,300,0"
    labels = json.dumps([s.get("label", "")[:35] for s in chart_data], ensure_ascii=False)
    vals_js = json.dumps(values)

    return f"""
<div class="chart-wrap">
  <div class="section-label">Структура показателей</div>
  <div style="position:relative;height:{max_h}px">
    <canvas id="mainChart"></canvas>
  </div>
</div>
<script>
(function(){{
  const ctx = document.getElementById('mainChart').getContext('2d');
  const c = "{color}";
  const grad = ctx.createLinearGradient({grad_coords});
  grad.addColorStop(0, c + 'ff');
  grad.addColorStop(1, c + '88');
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels: {labels},
      datasets: [{{
        data: {vals_js},
        backgroundColor: grad,
        borderColor: c,
        borderWidth: 0,
        borderRadius: 5,
        borderSkipped: false,
      }}]
    }},
    options: {{
      indexAxis: {axis_param},
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          backgroundColor: '#1a1a2e',
          padding: 10,
          cornerRadius: 8,
          callbacks: {{ label: ctx => '  ' + ctx.raw.toLocaleString('ru-RU') + ' {unit}' }}
        }}
      }},
      scales: {{
        x: {{ grid: {{ color: 'rgba(0,0,0,.04)' }}, ticks: {{ font: {{ size: 11, family: 'Inter' }}, color: '#78909c' }} }},
        y: {{ grid: {{ display: {'false' if is_horiz else 'true'}, color: 'rgba(0,0,0,.04)' }}, ticks: {{ font: {{ size: 11, family: 'Inter' }}, color: '#546e7a' }} }}
      }},
      animation: {{ duration: 900, easing: 'easeOutQuart' }}
    }}
  }});
}})();
</script>"""


def _donut_chart(chart_data: list, color: str) -> str:
    if len(chart_data) < 2:
        return ""
    try:
        values = [float(s["value"]) for s in chart_data]
    except (ValueError, TypeError):
        return ""

    palette = [
        color + "ff", color + "cc", color + "99",
        color + "77", color + "55", color + "33",
    ]
    colors_js = json.dumps(palette[:len(chart_data)])
    labels = json.dumps([s.get("label", "")[:35] for s in chart_data], ensure_ascii=False)
    vals_js = json.dumps(values)
    unit = chart_data[0].get("unit", "").split()[0] if chart_data else ""

    return f"""
<div class="chart-wrap">
  <div class="section-label">Структура показателей</div>
  <div style="position:relative;height:240px">
    <canvas id="mainChart"></canvas>
  </div>
</div>
<script>
(function(){{
  new Chart(document.getElementById('mainChart'), {{
    type: 'doughnut',
    data: {{
      labels: {labels},
      datasets: [{{
        data: {vals_js},
        backgroundColor: {colors_js},
        borderWidth: 0,
        hoverOffset: 8,
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      cutout: '62%',
      plugins: {{
        legend: {{
          position: 'right',
          labels: {{ font: {{ size: 11, family: 'Inter' }}, color: '#546e7a', padding: 10 }}
        }},
        tooltip: {{
          backgroundColor: '#1a1a2e',
          padding: 10,
          cornerRadius: 8,
          callbacks: {{
            label: ctx => '  ' + ctx.raw.toLocaleString('ru-RU') + ' {unit}'
          }}
        }}
      }},
      animation: {{ animateRotate: true, duration: 900 }}
    }}
  }});
}})();
</script>"""


def _progress_section(analysis: dict, color: str) -> str:
    chart_data = analysis.get("chart_data") or []
    # Если данные временного ряда — прогресс-бары не нужны, график уже показывает динамику
    if _has_years(chart_data):
        return ""

    stats = analysis.get("key_stats", [])[1:]
    numeric = []
    for s in stats:
        try:
            numeric.append((float(s["value"]), s))
        except (ValueError, TypeError):
            pass
    if not numeric:
        return ""

    max_val = max(v for v, _ in numeric)
    if max_val == 0:
        return ""

    rows = ""
    for val, s in numeric[:5]:
        pct = round(val / max_val * 100)
        val_str = f"{_fmt_value(s['value'])} {s.get('unit','')[:20]}".strip()
        trend_badge = _trend_badge(s.get("trend", "neutral"))
        label = s.get("label", "Показатель")[:65]
        rows += f"""
      <div class="prow">
        <div class="prow-top">
          <span class="prow-label">{label}</span>
          <span class="prow-val" style="color:{color}">{val_str} {trend_badge}</span>
        </div>
        <div class="ptrack"><div class="pfill" style="width:0;background:{color}" data-w="{pct}"></div></div>
      </div>"""

    return f"""
<div class="prog-section">
  <div class="section-label">Сравнение показателей</div>
  {rows}
</div>"""


def _insights_block(analysis: dict, color: str, light: str) -> str:
    """Аналитический блок: выводы на основе данных статьи."""
    import re
    chart_data = analysis.get("chart_data") or []
    key_stats = analysis.get("key_stats") or []

    if not chart_data and not key_stats:
        return ""

    insights = []
    is_timeseries = _has_years(chart_data)

    if is_timeseries and len(chart_data) >= 2:
        # Временной ряд: считаем рост, CAGR, максимальный скачок
        try:
            vals = [float(s["value"]) for s in chart_data]
            import re as _re
            years = [int(_re.search(r'\b(19|20)\d{2}\b', s["label"]).group())
                     for s in chart_data if _re.search(r'\b(19|20)\d{2}\b', s["label"])]
            unit = chart_data[0].get("unit", "")

            first_val, last_val = vals[0], vals[-1]
            if first_val > 0:
                total_growth_pct = round((last_val - first_val) / first_val * 100, 1)
                if years and len(years) >= 2:
                    n_years = years[-1] - years[0]
                    if n_years > 0:
                        cagr = round(((last_val / first_val) ** (1 / n_years) - 1) * 100, 1)
                        insights.append(
                            f"За период {years[0]}–{years[-1]} показатель вырос "
                            f"на <b>{total_growth_pct:+.1f}%</b> — "
                            f"среднегодовой прирост составил <b>{cagr:+.1f}%</b> в год."
                        )

            # Максимальный однолетний скачок
            max_jump_val = 0
            max_jump_year = None
            for i in range(1, len(vals)):
                if vals[i - 1] > 0:
                    jump = abs((vals[i] - vals[i - 1]) / vals[i - 1] * 100)
                    if jump > max_jump_val:
                        max_jump_val = jump
                        max_jump_year = years[i] if i < len(years) else None
                        max_jump_dir = "рост" if vals[i] > vals[i - 1] else "падение"
                        max_jump_from = vals[i - 1]
                        max_jump_to = vals[i]

            if max_jump_year and max_jump_val > 5:
                insights.append(
                    f"Наибольший {max_jump_dir} зафиксирован в <b>{max_jump_year} году</b>: "
                    f"с {_fmt_value(str(max_jump_from))} до {_fmt_value(str(max_jump_to))} {unit} "
                    f"(<b>{max_jump_dir} {max_jump_val:.1f}%</b>)."
                )

            # Последний год — рост или падение?
            if len(vals) >= 2:
                delta = vals[-1] - vals[-2]
                delta_pct = round(delta / vals[-2] * 100, 1) if vals[-2] else 0
                direction = "вырос" if delta > 0 else "снизился"
                yr_last = years[-1] if years else ""
                yr_prev = years[-2] if len(years) >= 2 else ""
                insights.append(
                    f"В <b>{yr_last} году</b> по сравнению с {yr_prev}: "
                    f"показатель {direction} на <b>{abs(delta_pct):.1f}%</b> "
                    f"(с {_fmt_value(str(vals[-2]))} до {_fmt_value(str(vals[-1]))} {unit})."
                )
        except Exception:
            pass

    elif chart_data and not is_timeseries and len(chart_data) >= 2:
        # Региональные / структурные данные
        try:
            vals = [float(s["value"]) for s in chart_data]
            unit = chart_data[0].get("unit", "")
            total = sum(vals)
            max_i = vals.index(max(vals))
            min_i = vals.index(min(vals))
            leader = chart_data[max_i].get("label", "Лидер")[:45]
            laggard = chart_data[min_i].get("label", "Аутсайдер")[:45]
            leader_share = round(vals[max_i] / total * 100, 1) if total else 0

            insights.append(
                f"Лидер по показателю — <b>{leader}</b>: "
                f"{_fmt_value(str(vals[max_i]))} {unit}, "
                f"что составляет <b>{leader_share}%</b> от суммарного значения."
            )
            insights.append(
                f"Наименьшее значение у <b>{laggard}</b>: "
                f"{_fmt_value(str(vals[min_i]))} {unit} — "
                f"разрыв с лидером в <b>{round(vals[max_i]/vals[min_i], 1)}×</b>."
                if vals[min_i] > 0 else
                f"Наименьшее значение у <b>{laggard}</b>: {_fmt_value(str(vals[min_i]))} {unit}."
            )
            if len(vals) >= 3:
                top3_sum = sum(sorted(vals, reverse=True)[:3])
                top3_share = round(top3_sum / total * 100, 1) if total else 0
                insights.append(
                    f"Топ-3 региона/показателя формируют <b>{top3_share}%</b> "
                    f"от общего объёма ({_fmt_value(str(round(total, 1)))} {unit} суммарно)."
                )
        except Exception:
            pass

    if not insights:
        return ""

    items_html = "".join(f'<li class="insight-item">{ins}</li>' for ins in insights)

    return f"""
<div class="insights-block" style="--c:{color};--bg:{light}">
  <div class="insights-header">
    <span class="insights-icon">💡</span>
    <span class="insights-title">Аналитика</span>
  </div>
  <ul class="insights-list">
    {items_html}
  </ul>
</div>"""


def build_article_page(article: dict, analysis: dict) -> str:
    aid = article["id"]
    c = _cat(analysis.get("category", ""))
    color = c["color"]
    light = c["light"]
    icon = c["icon"]
    cat = analysis.get("category", "Статистика")

    key_stats = analysis.get("key_stats", [])
    chart_data = analysis.get("chart_data") or []
    headline = analysis.get("headline", article.get("title", ""))

    kpi_html = _kpi_cards(key_stats, color, light, headline)

    units = [s.get("unit", "").lower() for s in chart_data]
    use_donut = any("%" in u or "доля" in u or "процент" in u for u in units)
    chart_html = (_donut_chart(chart_data, color) if use_donut
                  else _chart_block(analysis, color))

    prog_html = _progress_section(analysis, color)
    insights_html = _insights_block(analysis, color, light)

    period = analysis.get("period", "")
    url = article.get("url", "")
    date = article.get("date", "")

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{headline}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --c: {color};
  --bg: {light};
  --radius: 16px;
  --shadow: 0 2px 24px rgba(0,0,0,.09);
}}
body {{
  font-family: 'Inter', -apple-system, sans-serif;
  background: #f0f2f5;
  color: #1a1a2e;
  min-height: 100vh;
}}

.nav {{
  background: {color};
  padding: 0 20px;
  height: 54px;
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 12px rgba(0,0,0,.18);
}}
.nav-back {{
  color: rgba(255,255,255,.9);
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: color .2s;
}}
.nav-back:hover {{ color: #fff; }}
.nav-title {{
  color: rgba(255,255,255,.7);
  font-size: 13px;
  margin-left: auto;
  letter-spacing: .2px;
}}

.page {{
  max-width: 820px;
  margin: 0 auto;
  padding: 20px 16px 60px;
}}

.hero-card {{
  background: {color};
  border-radius: var(--radius);
  overflow: hidden;
  margin-bottom: 14px;
  position: relative;
}}
.hero-card::before {{
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255,255,255,.08) 0%, transparent 60%);
  pointer-events: none;
}}
.hero-bg-icon {{
  position: absolute;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 80px;
  opacity: .1;
  line-height: 1;
  pointer-events: none;
  user-select: none;
}}
.hero-body {{
  padding: 28px 28px 24px;
  position: relative;
}}
.badge {{
  display: inline-block;
  background: rgba(255,255,255,.2);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 20px;
  letter-spacing: .6px;
  text-transform: uppercase;
  margin-bottom: 12px;
}}
.hero-title {{
  color: #fff;
  font-size: 20px;
  font-weight: 800;
  line-height: 1.35;
  max-width: 85%;
}}
.hero-period {{
  color: rgba(255,255,255,.65);
  font-size: 13px;
  margin-top: 8px;
  font-weight: 500;
}}

.kpi-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}}
.kpi-hero {{
  background: #fff;
  border-radius: var(--radius);
  padding: 20px 22px;
  box-shadow: var(--shadow);
  border-left: 4px solid var(--c);
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}}
.kpi-hero-val {{
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}}
.kpi-hero-val .counter {{
  font-size: 48px;
  font-weight: 900;
  color: var(--c);
  line-height: 1;
  letter-spacing: -1px;
}}
.kpi-hero-unit {{
  font-size: 20px;
  font-weight: 700;
  color: var(--c);
  opacity: .7;
}}
.kpi-hero-label {{
  font-size: 13px;
  color: #546e7a;
  font-weight: 500;
  flex: 1;
  min-width: 120px;
}}
.kpi-card {{
  background: #fff;
  border-radius: 12px;
  padding: 16px 18px;
  box-shadow: var(--shadow);
  border-top: 3px solid var(--c);
}}
.kpi-val {{
  display: flex;
  align-items: baseline;
  gap: 5px;
  margin-bottom: 4px;
}}
.kpi-val .counter {{
  font-size: 28px;
  font-weight: 800;
  color: var(--c);
  line-height: 1;
}}
.kpi-unit {{
  font-size: 12px;
  font-weight: 700;
  color: var(--c);
  opacity: .7;
}}
.kpi-label {{
  font-size: 11px;
  color: #78909c;
  font-weight: 500;
  line-height: 1.35;
}}

.trend {{
  font-size: 13px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 6px;
  display: inline-block;
  margin-left: 4px;
}}
.trend.up   {{ color: #2e7d32; background: #e8f5e9; }}
.trend.down {{ color: #c62828; background: #ffebee; }}
.trend.neutral {{ color: #78909c; background: #f5f5f5; }}

.chart-wrap {{
  background: #fff;
  border-radius: var(--radius);
  padding: 20px 22px 24px;
  box-shadow: var(--shadow);
  margin-bottom: 14px;
}}
.section-label {{
  font-size: 11px;
  font-weight: 700;
  color: #90a4ae;
  letter-spacing: .7px;
  text-transform: uppercase;
  margin-bottom: 14px;
}}

.prog-section {{
  background: #fff;
  border-radius: var(--radius);
  padding: 20px 22px 24px;
  box-shadow: var(--shadow);
  margin-bottom: 14px;
}}
.prow {{ margin-bottom: 14px; }}
.prow:last-child {{ margin-bottom: 0; }}
.prow-top {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 5px;
  gap: 8px;
}}
.prow-label {{
  font-size: 12px;
  color: #546e7a;
  font-weight: 500;
  flex: 1;
  line-height: 1.3;
}}
.prow-val {{
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}}
.ptrack {{
  background: #f0f2f5;
  border-radius: 6px;
  height: 8px;
  overflow: hidden;
}}
.pfill {{
  height: 100%;
  border-radius: 6px;
  transition: width .8s cubic-bezier(.4,0,.2,1);
}}

.insights-block {{
  background: var(--bg);
  border-radius: var(--radius);
  padding: 20px 22px 22px;
  box-shadow: var(--shadow);
  margin-bottom: 14px;
  border-left: 4px solid var(--c);
}}
.insights-header {{
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}}
.insights-icon {{
  font-size: 20px;
  line-height: 1;
}}
.insights-title {{
  font-size: 11px;
  font-weight: 700;
  color: #90a4ae;
  letter-spacing: .7px;
  text-transform: uppercase;
}}
.insights-list {{
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
}}
.insight-item {{
  font-size: 13px;
  color: #37474f;
  line-height: 1.55;
  padding-left: 14px;
  position: relative;
}}
.insight-item::before {{
  content: '▸';
  position: absolute;
  left: 0;
  color: var(--c);
  font-size: 11px;
  top: 1px;
}}
.insight-item b {{
  color: var(--c);
  font-weight: 700;
}}

.foot {{
  background: #fff;
  border-radius: var(--radius);
  padding: 16px 22px;
  box-shadow: var(--shadow);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}}
.foot a {{
  color: {color};
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 5px;
}}
.foot a:hover {{ text-decoration: underline; }}
.foot-date {{
  font-size: 12px;
  color: #90a4ae;
}}

@media (max-width: 500px) {{
  .hero-title {{ font-size: 17px; }}
  .kpi-hero-val .counter {{ font-size: 38px; }}
  .kpi-grid {{ grid-template-columns: 1fr 1fr; }}
  .kpi-hero {{ grid-column: 1 / -1; flex-direction: column; align-items: flex-start; }}
}}
</style>
</head>
<body>

<nav class="nav">
  <a class="nav-back" href="../index.html">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
    Все новости
  </a>
  <span class="nav-title">{icon} {cat}</span>
</nav>

<div class="page">

  <div class="hero-card">
    <div class="hero-bg-icon">{icon}</div>
    <div class="hero-body">
      <div class="badge">{cat}</div>
      <div class="hero-title">{headline}</div>
      {"<div class='hero-period'>" + period + "</div>" if period else ""}
    </div>
  </div>

  {kpi_html}
  {chart_html}
  {prog_html}
  {insights_html}

  <div class="foot">
    <a href="{url}" target="_blank" rel="noopener">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
        <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
      </svg>
      Источник: stat.uz
    </a>
    <span class="foot-date">{date}</span>
  </div>

</div>

<script>
(function() {{
  function animateCounter(el) {{
    const target = parseFloat(el.dataset.target);
    if (isNaN(target)) return;
    const isInt = Number.isInteger(target);
    const duration = 1200;
    const start = performance.now();
    function tick(now) {{
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      const val = target * ease;
      el.textContent = isInt
        ? Math.round(val).toLocaleString('ru-RU')
        : val.toLocaleString('ru-RU', {{minimumFractionDigits: 1, maximumFractionDigits: 1}});
      if (progress < 1) requestAnimationFrame(tick);
    }}
    requestAnimationFrame(tick);
  }}

  const obs = new IntersectionObserver(entries => {{
    entries.forEach(e => {{
      if (e.isIntersecting) {{
        animateCounter(e.target);
        obs.unobserve(e.target);
      }}
    }});
  }}, {{ threshold: 0.3 }});

  document.querySelectorAll('.counter').forEach(el => obs.observe(el));

  const pobs = new IntersectionObserver(entries => {{
    entries.forEach(e => {{
      if (e.isIntersecting) {{
        e.target.style.width = e.target.dataset.w + '%';
        pobs.unobserve(e.target);
      }}
    }});
  }}, {{ threshold: 0.2 }});

  document.querySelectorAll('.pfill').forEach(el => pobs.observe(el));
}})();
</script>

</body>
</html>"""

    path = NEWS_DIR / f"{aid}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


# ── Index page ────────────────────────────────────────────────────────────────

def build_index(articles: list):
    cards = ""
    for a in sorted(articles, key=lambda x: x.get("date", ""), reverse=True)[:100]:
        an = a.get("analysis", {})
        c = _cat(an.get("category", ""))
        color = c["color"]
        light = c["light"]
        icon = c["icon"]
        mv = an.get("main_value", "")
        mu = an.get("main_unit", "")
        mv_fmt = _fmt_value(mv) if mv else ""

        cards += f"""
    <a href="news/{a['id']}.html" class="card-link">
      <div class="card">
        <div class="card-stripe" style="background:{color}"></div>
        <div class="card-body">
          <div class="card-badge" style="background:{light};color:{color}">{icon} {an.get('category','Статистика')}</div>
          <div class="card-title">{an.get('headline', a.get('title',''))[:75]}</div>
          {"<div class='card-num' style='color:" + color + "'>" + mv_fmt + "<span class='card-unit'> " + mu[:18] + "</span></div>" if mv_fmt else "<div style='height:36px'></div>"}
          <div class="card-date">{a.get('date','')}</div>
        </div>
      </div>
    </a>"""

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    total = len(articles)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Статистика Узбекистана</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',-apple-system,sans-serif;background:#f0f2f5;color:#1a1a2e}}

.topbar{{
  background:linear-gradient(135deg,#1a3a6e 0%,#1565c0 100%);
  padding:20px 24px 18px;
  position:sticky;top:0;z-index:10;
  box-shadow:0 2px 16px rgba(0,0,0,.2);
}}
.topbar-inner{{max-width:1100px;margin:0 auto;display:flex;justify-content:space-between;align-items:center}}
.site-title{{color:#fff;font-size:20px;font-weight:800;letter-spacing:-.3px}}
.site-sub{{color:rgba(255,255,255,.55);font-size:11px;margin-top:2px;font-weight:500}}
.count-pill{{
  background:rgba(255,255,255,.15);color:#fff;
  font-size:12px;font-weight:700;padding:5px 14px;border-radius:20px;
}}

.grid{{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(220px,1fr));
  gap:14px;
  padding:20px 20px 40px;
  max-width:1100px;
  margin:0 auto;
}}
.card-link{{text-decoration:none;color:inherit;display:block}}
.card{{
  background:#fff;
  border-radius:12px;
  overflow:hidden;
  box-shadow:0 1px 8px rgba(0,0,0,.07);
  transition:transform .18s ease,box-shadow .18s ease;
  height:100%;
}}
.card:hover{{transform:translateY(-3px);box-shadow:0 8px 28px rgba(0,0,0,.13)}}
.card-stripe{{height:4px}}
.card-body{{padding:14px 16px 16px}}
.card-badge{{
  display:inline-flex;align-items:center;gap:4px;
  font-size:10px;font-weight:700;padding:3px 10px;
  border-radius:20px;margin-bottom:8px;letter-spacing:.3px;
}}
.card-title{{font-size:12px;font-weight:600;line-height:1.4;color:#1a1a2e;margin-bottom:8px;min-height:32px}}
.card-num{{font-size:28px;font-weight:900;line-height:1;margin-bottom:2px;letter-spacing:-.5px}}
.card-unit{{font-size:12px;font-weight:600;opacity:.65}}
.card-date{{font-size:10px;color:#90a4ae;margin-top:8px;font-weight:500}}

@media(max-width:480px){{
  .grid{{grid-template-columns:1fr 1fr;gap:10px;padding:12px 12px 40px}}
  .card-num{{font-size:22px}}
}}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-inner">
    <div>
      <div class="site-title">📊 Статистика Узбекистана</div>
      <div class="site-sub">Госкомстат УЗ · Обновлено {now}</div>
    </div>
    <div class="count-pill">{total} материалов</div>
  </div>
</div>

<div class="grid">{cards}</div>

</body>
</html>"""

    (DOCS / "index.html").write_text(html, encoding="utf-8")
    print(f"[site] index.html → {total} статей")
