#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot.py — بلوك هَب (Block Hub)

يقوم هذا السكربت بـ:
  Modrinth API  ->  bot.py  ->  index.html

- يجلب بيانات المودات و Resource Packs و Shaders و Data Packs من Modrinth API.
- يبني ملف index.html النهائي مباشرة (بدون أي ملف وسيط مثل mods_data.json).
- لا يحتوي على أي مفاتيح سرية. الـ User-Agent يُقرأ من متغير البيئة
  MODRINTH_USER_AGENT (يُضبط عبر GitHub Secrets).
- في حال فشل الاتصال بالكامل (صفر عناصر من كل الأقسام)، لا يتم لمس
  index.html الحالي إطلاقًا حتى لا يتحول الموقع إلى صفحة فارغة.

لا يعتمد هذا السكربت على أي قاعدة بيانات خارجية ولا Firebase ولا GitLab.
"""

import os
import sys
import json
import time
import html
import logging
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================================
# الإعدادات العامة
# ============================================================

MODRINTH_API_BASE = "https://api.modrinth.com/v2"

# يمكن ضبط هذه القيمة من GitHub Secrets باسم MODRINTH_USER_AGENT
# مثال: username/block-hub/1.0 (your-email@example.com)
DEFAULT_USER_AGENT = "block-hub-user/block-hub/1.0"
USER_AGENT = os.environ.get("MODRINTH_USER_AGENT", DEFAULT_USER_AGENT)

REQUEST_TIMEOUT = 15  # ثواني
ITEMS_PER_SECTION = 24  # بين 20 و 30 عنصرًا لكل قسم
MAX_RETRIES = 5
BACKOFF_FACTOR = 1.5

KNOWN_LOADERS = {"fabric", "forge", "neoforge", "quilt"}

# project_type في Modrinth يطابق مباشرة مسار الصفحة على الموقع:
# https://modrinth.com/{project_type}/{slug}
SECTIONS = [
    {"key": "mods", "project_type": "mod", "label_ar": "مودات"},
    {"key": "resourcepacks", "project_type": "resourcepack", "label_ar": "Resource Packs"},
    {"key": "shaders", "project_type": "shader", "label_ar": "Shaders"},
    {"key": "datapacks", "project_type": "datapack", "label_ar": "Data Packs"},
]

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("block-hub-bot")


# ============================================================
# جلسة HTTP مع إعادة المحاولة (Retry)
# ============================================================

def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        connect=MAX_RETRIES,
        read=MAX_RETRIES,
        status=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }
    )
    return session


SESSION = build_session()


# ============================================================
# جلب البيانات من Modrinth
# ============================================================

def fetch_section(section: dict) -> list:
    """
    يجلب قائمة عناصر لقسم واحد (mod / resourcepack / shader / datapack)
    مرتبة حسب عدد التنزيلات. عند أي خطأ يُعاد إرجاع قائمة فارغة بدل تعطيل
    البوت بالكامل.
    """
    project_type = section["project_type"]
    facets = json.dumps([[f"project_type:{project_type}"]])

    params = {
        "query": "",
        "facets": facets,
        "index": "downloads",
        "limit": ITEMS_PER_SECTION,
        "offset": 0,
    }

    url = f"{MODRINTH_API_BASE}/search"

    try:
        response = SESSION.get(url, params=params, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.Timeout:
        log.error("انتهت مهلة الاتصال أثناء جلب قسم: %s", project_type)
        return []
    except requests.exceptions.ConnectionError:
        log.error("فشل الاتصال بالشبكة أثناء جلب قسم: %s", project_type)
        return []
    except requests.exceptions.RequestException as exc:
        log.error("خطأ غير متوقع أثناء جلب قسم %s: %s", project_type, exc)
        return []

    if response.status_code == 429:
        log.error("تم تجاوز الحد المسموح (429) لقسم: %s", project_type)
        return []

    if response.status_code != 200:
        log.error(
            "استجابة غير ناجحة (%s) من Modrinth لقسم: %s",
            response.status_code,
            project_type,
        )
        return []

    try:
        data = response.json()
    except ValueError:
        log.error("تعذّر تحليل استجابة JSON لقسم: %s", project_type)
        return []

    hits = data.get("hits", [])
    if not isinstance(hits, list):
        return []

    seen_slugs = set()
    items = []

    for hit in hits:
        slug = hit.get("slug") or hit.get("project_id")
        if not slug or slug in seen_slugs:
            # تجنّب أي تكرار (idempotent)
            continue
        seen_slugs.add(slug)

        categories = hit.get("categories") or []
        loaders = sorted({c for c in categories if c in KNOWN_LOADERS})

        game_versions = hit.get("versions") or []
        # أحدث 6 إصدارات فقط لعرض مرتب وخفيف
        recent_versions = game_versions[-6:] if len(game_versions) > 6 else game_versions
        recent_versions = list(reversed(recent_versions))

        title = (hit.get("title") or slug or "").strip()
        author = (hit.get("author") or "غير معروف").strip()
        description = (hit.get("description") or "").strip()
        icon_url = hit.get("icon_url") or ""
        downloads = hit.get("downloads") or 0

        item = {
            "id": slug,
            "title": title,
            "author": author,
            "description": description,
            "icon_url": icon_url,
            "downloads": downloads,
            "loaders": loaders,
            "versions": recent_versions,
            "project_type": project_type,
            "url": f"https://modrinth.com/{project_type}/{slug}",
        }
        items.append(item)

    # ترتيب نهائي حسب التنزيلات (تأكيدًا، حتى لو غيّرت Modrinth الترتيب)
    items.sort(key=lambda x: x["downloads"], reverse=True)

    log.info("تم جلب %d عنصر من قسم %s", len(items), project_type)
    return items


def fetch_all_sections() -> dict:
    result = {}
    for section in SECTIONS:
        key = section["key"]
        items = fetch_section(section)
        result[key] = items
        # مهلة صغيرة بين الطلبات تقليلًا لاحتمال 429
        time.sleep(0.5)
    return result


# ============================================================
# بناء HTML
# ============================================================

def esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def render_index_html(sections_data: dict) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    total_items = sum(len(v) for v in sections_data.values())

    sections_meta = [
        {"key": s["key"], "label": s["label_ar"], "count": len(sections_data.get(s["key"], []))}
        for s in SECTIONS
    ]

    tabs_html = "\n".join(
        f'<button class="tab{ " active" if i == 0 else "" }" data-section="{esc(s["key"])}" '
        f'role="tab" aria-selected="{"true" if i == 0 else "false"}">'
        f'{esc(s["label"])}</button>'
        for i, s in enumerate(sections_meta)
    )

    data_json = json.dumps(sections_data, ensure_ascii=False)

    html_doc = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>بلوك هَب | دليلك لمودات Minecraft</title>
<meta name="description" content="بلوك هَب: منصة عربية خفيفة وسريعة لاكتشاف مودات Minecraft، Resource Packs، Shaders، وData Packs، مع بحث وفلترة حسب الإصدار واللودر.">
<meta name="keywords" content="Minecraft, مودات ماينكرافت, Resource Packs, Shaders, Data Packs, Fabric, Forge, Modrinth">
<link rel="canonical" href="https://block-hub.pages.dev/">

<meta property="og:type" content="website">
<meta property="og:title" content="بلوك هَب | دليلك لمودات Minecraft">
<meta property="og:description" content="اكتشف أفضل مودات Minecraft وResource Packs وShaders وData Packs بسهولة وسرعة.">
<meta property="og:locale" content="ar_AR">
<meta name="twitter:card" content="summary">

<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='18' fill='%2322c55e'/%3E%3Ctext x='50' y='68' font-size='55' text-anchor='middle' fill='%23111'%3EB%3C/text%3E%3C/svg%3E">

<style>
:root {{
  --bg: #0d1117;
  --bg-alt: #151b23;
  --card: #171d26;
  --border: #262c36;
  --text: #e6edf3;
  --text-dim: #9aa4b2;
  --accent: #22c55e;
  --accent-dim: #16803c;
  --radius: 12px;
}}

* {{ box-sizing: border-box; }}

html, body {{
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: "Segoe UI", Tahoma, Arial, sans-serif;
  scroll-behavior: smooth;
}}

a {{ color: inherit; text-decoration: none; }}

header.site-header {{
  padding: 28px 16px 18px;
  text-align: center;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(180deg, var(--bg-alt), var(--bg));
}}

header.site-header h1 {{
  margin: 0 0 6px;
  font-size: 1.9rem;
  color: var(--accent);
}}

header.site-header p {{
  margin: 0;
  color: var(--text-dim);
  font-size: 0.95rem;
}}

.container {{
  max-width: 1100px;
  margin: 0 auto;
  padding: 18px 14px 60px;
}}

.search-wrap {{
  margin: 18px 0 14px;
}}

#search-input {{
  width: 100%;
  padding: 12px 14px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--bg-alt);
  color: var(--text);
  font-size: 1rem;
}}

#search-input:focus {{
  outline: 2px solid var(--accent-dim);
}}

.tabs {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}}

.tab {{
  padding: 9px 16px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--bg-alt);
  color: var(--text-dim);
  cursor: pointer;
  font-size: 0.9rem;
}}

.tab.active {{
  background: var(--accent);
  color: #062b12;
  border-color: var(--accent);
  font-weight: bold;
}}

.filters {{
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 20px;
}}

.filters select {{
  padding: 9px 12px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--bg-alt);
  color: var(--text);
  font-size: 0.9rem;
  min-width: 150px;
}}

.grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 14px;
}}

.card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}}

.card-top {{
  display: flex;
  align-items: center;
  gap: 10px;
}}

.card-icon {{
  width: 44px;
  height: 44px;
  border-radius: 8px;
  object-fit: cover;
  background: var(--bg-alt);
  flex-shrink: 0;
}}

.card-title {{
  font-size: 1.02rem;
  font-weight: bold;
  margin: 0;
}}

.card-author {{
  font-size: 0.8rem;
  color: var(--text-dim);
  margin: 0;
}}

.card-desc {{
  font-size: 0.85rem;
  color: var(--text-dim);
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}}

.card-meta {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 0.72rem;
}}

.badge {{
  background: var(--bg-alt);
  border: 1px solid var(--border);
  color: var(--text-dim);
  padding: 3px 8px;
  border-radius: 999px;
}}

.card-downloads {{
  font-size: 0.78rem;
  color: var(--text-dim);
}}

.card-btn {{
  margin-top: auto;
  text-align: center;
  padding: 9px;
  border-radius: 8px;
  background: var(--accent);
  color: #062b12;
  font-weight: bold;
  font-size: 0.88rem;
}}

.card-btn:hover {{
  background: #34d374;
}}

.empty-state {{
  text-align: center;
  color: var(--text-dim);
  padding: 40px 10px;
}}

footer {{
  text-align: center;
  color: var(--text-dim);
  font-size: 0.78rem;
  padding: 20px 10px 40px;
  border-top: 1px solid var(--border);
}}

@media (max-width: 480px) {{
  header.site-header h1 {{ font-size: 1.5rem; }}
  .grid {{ grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); }}
}}
</style>
</head>
<body>

<header class="site-header">
  <h1>بلوك هَب</h1>
  <p>دليلك لمودات Minecraft — Resource Packs، Shaders، وData Packs</p>
</header>

<main class="container">

  <div class="search-wrap">
    <input type="search" id="search-input" placeholder="🔎 ابحث عن إضافة..." aria-label="بحث">
  </div>

  <nav class="tabs" role="tablist" aria-label="أقسام الموقع">
    {tabs_html}
  </nav>

  <div class="filters">
    <select id="loader-filter" aria-label="فلترة حسب اللودر">
      <option value="">كل اللودرات</option>
      <option value="fabric">Fabric</option>
      <option value="forge">Forge</option>
      <option value="neoforge">NeoForge</option>
      <option value="quilt">Quilt</option>
    </select>

    <select id="version-filter" aria-label="فلترة حسب الإصدار">
      <option value="">كل الإصدارات</option>
    </select>
  </div>

  <section id="grid" class="grid" aria-live="polite"></section>

  <p id="empty-msg" class="empty-state" hidden>لا توجد نتائج مطابقة لبحثك.</p>

</main>

<footer>
  <p>بلوك هَب — البيانات مصدرها Modrinth API. آخر تحديث: {esc(generated_at)} · إجمالي العناصر: {total_items}</p>
  <p>روابط التحميل تقودك مباشرة إلى الصفحة الرسمية للمشروع على Modrinth.</p>
</footer>

<script id="site-data" type="application/json">{data_json}</script>
<script>
(function () {{
  "use strict";

  var rawData = JSON.parse(document.getElementById("site-data").textContent || "{{}}");
  var currentSection = Object.keys(rawData)[0] || "mods";

  var gridEl = document.getElementById("grid");
  var emptyMsg = document.getElementById("empty-msg");
  var searchInput = document.getElementById("search-input");
  var loaderFilter = document.getElementById("loader-filter");
  var versionFilter = document.getElementById("version-filter");
  var tabs = document.querySelectorAll(".tab");

  function collectVersions(items) {{
    var set = {{}};
    items.forEach(function (item) {{
      (item.versions || []).forEach(function (v) {{ set[v] = true; }});
    }});
    return Object.keys(set).sort().reverse();
  }}

  function populateVersionFilter() {{
    var items = rawData[currentSection] || [];
    var versions = collectVersions(items);
    var current = versionFilter.value;
    versionFilter.innerHTML = '<option value="">كل الإصدارات</option>';
    versions.forEach(function (v) {{
      var opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      versionFilter.appendChild(opt);
    }});
    if (versions.indexOf(current) !== -1) {{
      versionFilter.value = current;
    }}
  }}

  function formatDownloads(n) {{
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "م";
    if (n >= 1000) return (n / 1000).toFixed(1) + "ألف";
    return String(n);
  }}

  function escapeHtml(str) {{
    var div = document.createElement("div");
    div.textContent = str == null ? "" : str;
    return div.innerHTML;
  }}

  function renderCards() {{
    var items = rawData[currentSection] || [];
    var query = (searchInput.value || "").trim().toLowerCase();
    var loader = loaderFilter.value;
    var version = versionFilter.value;

    var filtered = items.filter(function (item) {{
      if (query) {{
        var haystack = (item.title + " " + item.author + " " + item.description).toLowerCase();
        if (haystack.indexOf(query) === -1) return false;
      }}
      if (loader && (item.loaders || []).indexOf(loader) === -1) return false;
      if (version && (item.versions || []).indexOf(version) === -1) return false;
      return true;
    }});

    gridEl.innerHTML = "";

    if (filtered.length === 0) {{
      emptyMsg.hidden = false;
      return;
    }}
    emptyMsg.hidden = true;

    var frag = document.createDocumentFragment();

    filtered.forEach(function (item) {{
      var card = document.createElement("article");
      card.className = "card";

      var loadersHtml = (item.loaders || [])
        .map(function (l) {{ return '<span class="badge">' + escapeHtml(l) + "</span>"; }})
        .join("");

      var versionsHtml = (item.versions || [])
        .slice(0, 3)
        .map(function (v) {{ return '<span class="badge">' + escapeHtml(v) + "</span>"; }})
        .join("");

      var iconSrc = item.icon_url ? item.icon_url : "";

      card.innerHTML =
        '<div class="card-top">' +
          (iconSrc
            ? '<img class="card-icon" src="' + escapeHtml(iconSrc) + '" alt="" loading="lazy" width="44" height="44">'
            : '<div class="card-icon"></div>') +
          '<div>' +
            '<p class="card-title">' + escapeHtml(item.title) + '</p>' +
            '<p class="card-author">بواسطة ' + escapeHtml(item.author) + '</p>' +
          '</div>' +
        '</div>' +
        '<p class="card-desc">' + escapeHtml(item.description) + '</p>' +
        '<div class="card-meta">' + loadersHtml + versionsHtml + '</div>' +
        '<p class="card-downloads">⬇ ' + formatDownloads(item.downloads || 0) + ' تنزيل</p>' +
        '<a class="card-btn" href="' + escapeHtml(item.url) + '" target="_blank" rel="noopener noreferrer">عرض وتحميل</a>';

      frag.appendChild(card);
    }});

    gridEl.appendChild(frag);
  }}

  tabs.forEach(function (tab) {{
    tab.addEventListener("click", function () {{
      tabs.forEach(function (t) {{
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
      }});
      tab.classList.add("active");
      tab.setAttribute("aria-selected", "true");
      currentSection = tab.getAttribute("data-section");
      versionFilter.value = "";
      populateVersionFilter();
      renderCards();
    }});
  }});

  searchInput.addEventListener("input", renderCards);
  loaderFilter.addEventListener("change", renderCards);
  versionFilter.addEventListener("change", renderCards);

  populateVersionFilter();
  renderCards();
}})();
</script>

</body>
</html>
"""
    return html_doc


# ============================================================
# التنفيذ الرئيسي
# ============================================================

def main() -> int:
    log.info("بدء تشغيل بوت بلوك هَب. User-Agent المستخدم: %s", USER_AGENT)

    sections_data = fetch_all_sections()
    total_items = sum(len(v) for v in sections_data.values())

    if total_items == 0:
        log.error(
            "لم يتم جلب أي بيانات من أي قسم. سيتم إيقاف العملية دون "
            "المساس بملف index.html الحالي حتى لا يتحول الموقع إلى صفحة فارغة."
        )
        return 1

    html_content = render_index_html(sections_data)

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(html_content)
    except OSError as exc:
        log.error("فشل كتابة index.html: %s", exc)
        return 1

    log.info("تم توليد index.html بنجاح. إجمالي العناصر: %d", total_items)
    for section in SECTIONS:
        key = section["key"]
        log.info(" - %s: %d عنصر", section["label_ar"], len(sections_data.get(key, [])))

    return 0


if __name__ == "__main__":
    sys.exit(main())
