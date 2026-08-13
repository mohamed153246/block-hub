import html
import os
import time
from pathlib import Path

import requests

OUTPUT = Path("index.html")
API = "https://api.modrinth.com/v2"
LIMIT_PER_CATEGORY = 20

CATEGORIES = {
    "mod": "🛠️ مودات",
    "resourcepack": "🎨 ريسورس باكات",
    "shader": "🌌 شيدرز",
    "datapack": "📜 داتا باكات",
}

USER_AGENT = os.getenv("MODRINTH_USER_AGENT", "block-hub/1.0")

session = requests.Session()
session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
})


def get_json(url, params=None, tries=3):
    for attempt in range(tries):
        try:
            response = session.get(url, params=params, timeout=20)

            if response.status_code == 429:
                wait = min(int(response.headers.get("Retry-After", "10")), 60)
                print(f"Rate limit: waiting {wait}s")
                time.sleep(wait)
                continue

            response.raise_for_status()
            return response.json()

        except requests.RequestException as exc:
            if attempt == tries - 1:
                raise
            wait = 2 ** attempt
            print(f"Network error: {exc}; retrying in {wait}s")
            time.sleep(wait)

    raise RuntimeError("Request failed")


def version_key(value):
    parts = []
    for part in str(value).replace("-", ".").split("."):
        digits = "".join(c for c in part if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def fetch_category(category):
    print(f"Fetching {category}...")

    data = get_json(
        f"{API}/search",
        params={
            "limit": LIMIT_PER_CATEGORY,
            "offset": 0,
            "index": "downloads",
            "facets": __import__("json").dumps(
                [[f"project_type:{category}"]]
            ),
        },
    )

    items = []

    for hit in data.get("hits", []):
        project_id = hit.get("project_id")
        slug = hit.get("slug") or project_id

        if not project_id:
            continue

        try:
            versions = get_json(
                f"{API}/project/{project_id}/version",
                params={"include_changelog": "false"},
            ) or []

            loaders = set()
            game_versions = set()

            download_url = f"https://modrinth.com/{category}/{slug}"

            for version in versions:
                loaders.update(
                    str(loader).lower()
                    for loader in version.get("loaders", [])
                )
                game_versions.update(version.get("game_versions", []))

            if versions:
                files = versions[0].get("files", [])
                if files and files[0].get("url"):
                    download_url = files[0]["url"]

            description = hit.get("description") or "لا يوجد وصف متاح حالياً."
            if len(description) > 180:
                description = description[:180] + "..."

            items.append({
                "title": hit.get("title") or "بدون اسم",
                "description": description,
                "icon": hit.get("icon_url") or "",
                "download_url": download_url,
                "page_url": f"https://modrinth.com/{category}/{slug}",
                "author": hit.get("author") or "غير معروف",
                "downloads": int(hit.get("downloads") or 0),
                "category": category,
                "loaders": sorted(loaders),
                "versions": sorted(
                    game_versions,
                    key=version_key,
                    reverse=True,
                ),
            })

        except Exception as exc:
            print(f"Skipping {slug}: {exc}")

    return items


def esc(value):
    return html.escape(str(value or ""), quote=True)


def render_card(item):
    loader_badges = "".join(
        f'<span class="badge loader">{esc(x)}</span>'
        for x in item["loaders"][:3]
    )

    version_badges = "".join(
        f'<span class="badge">{esc(x)}</span>'
        for x in item["versions"][:2]
    )

    return f"""
<article class="card"
 data-category="{esc(item['category'])}"
 data-loaders="{esc(','.join(item['loaders']))}"
 data-versions="{esc(','.join(item['versions']))}">
  <div class="top">
    <img class="icon"
         src="{esc(item['icon'])}"
         alt=""
         loading="lazy"
         onerror="this.style.visibility='hidden'">
    <div>
      <h2>{esc(item['title'])}</h2>
      <div class="author">بواسطة {esc(item['author'])}</div>
    </div>
  </div>

  <p class="desc">{esc(item['description'])}</p>

  <div class="badges">
    {loader_badges}
    {version_badges}
  </div>

  <a class="download"
     href="{esc(item['page_url'])}"
     target="_blank"
     rel="noopener noreferrer">
     صفحة المود ↗
  </a>
</article>
"""


def build_site(items):
    cards = "\n".join(render_card(item) for item in items)

    loader_values = sorted({
        loader
        for item in items
        for loader in item["loaders"]
        if loader
    })

    version_values = sorted(
        {
            version
            for item in items
            for version in item["versions"]
            if version
        },
        key=version_key,
        reverse=True,
    )

    loader_options = "".join(
        f'<option value="{esc(v)}">{esc(v.title())}</option>'
        for v in loader_values
    )

    version_options = "".join(
        f'<option value="{esc(v)}">{esc(v)}</option>'
        for v in version_values
    )

    tabs = "".join(
        f'<button class="tab {"active" if idx == 0 else ""}" '
        f'data-cat="{esc(cat)}">{esc(label)}</button>'
        for idx, (cat, label) in enumerate(CATEGORIES.items())
    )

    site = f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>بلوك هَب | مودات ماين كرافت</title>
<meta name="description" content="بلوك هَب: مودات وشيدرز وريسورس باكات وداتا باكات ماين كرافت.">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#0d1117;color:#e6edf3;font-family:Arial,sans-serif}}
main{{max-width:1100px;margin:auto;padding:16px}}
header{{text-align:center;padding:25px 8px 18px}}
h1{{margin:0 0 8px;color:#66fcf1;font-size:32px}}
.sub{{color:#8b949e;font-size:14px}}
.search{{width:100%;margin:18px 0 12px;padding:13px 16px;background:#161b22;border:1px solid #30363d;border-radius:10px;color:#fff;font-size:15px;outline:none}}
.tabs,.filters{{display:flex;justify-content:center;gap:7px;flex-wrap:wrap;margin:8px 0}}
button,select{{background:#161b22;color:#e6edf3;border:1px solid #30363d;border-radius:8px;padding:9px 11px}}
button{{cursor:pointer}}
button.active{{border-color:#66fcf1;color:#66fcf1}}
#status{{color:#8b949e;font-size:12px;margin:14px 0}}
#mods{{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:14px}}
.top{{display:flex;gap:11px;align-items:center}}
.icon{{width:58px;height:58px;border-radius:9px;object-fit:cover;background:#21262d}}
h2{{margin:0 0 3px;font-size:17px}}
.author{{font-size:12px;color:#66fcf1}}
.desc{{color:#9da7b3;font-size:13px;line-height:1.55;min-height:42px}}
.badges{{display:flex;gap:5px;flex-wrap:wrap;margin:8px 0}}
.badge{{font-size:10px;padding:3px 7px;border-radius:20px;background:#21262d;color:#c9d1d9}}
.loader{{color:#66fcf1}}
.download{{display:block;text-align:center;text-decoration:none;background:#66fcf1;color:#071015;font-weight:700;padding:9px;border-radius:7px}}
.empty{{grid-column:1/-1;text-align:center;padding:40px;color:#8b949e}}
footer{{text-align:center;color:#6e7681;font-size:11px;padding:30px 0}}
@media(max-width:600px){{h1{{font-size:27px}}#mods{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<main>
<header>
<h1>⛏️ بلوك هَب</h1>
<div class="sub">دليل مودات ماين كرافت — تحديث تلقائي</div>

<input id="search" class="search"
       placeholder="🔎 ابحث عن مود أو إضافة..."
       autocomplete="off">

<div class="tabs">{tabs}</div>

<div class="filters">
<select id="loader">
<option value="">كل اللودرات</option>
{loader_options}
</select>

<select id="version">
<option value="">كل الإصدارات</option>
{version_options}
</select>
</div>

<div id="status"></div>
</header>

<section id="mods">
{cards}
</section>

<footer>
بلوك هَب © 2026 — بيانات الإضافات من Modrinth
</footer>
</main>

<script>
const cards=[...document.querySelectorAll(".card")];
const search=document.getElementById("search");
const loader=document.getElementById("loader");
const version=document.getElementById("version");
const status=document.getElementById("status");
let category="mod";

function render(){{
  const q=search.value.trim().toLowerCase();
  const l=loader.value;
  const v=version.value;
  let shown=0;

  cards.forEach(card=>{{
    const text=(
      card.querySelector("h2").textContent+" "+
      card.querySelector(".desc").textContent
    ).toLowerCase();

    const loaders=(card.dataset.loaders||"").split(",");
    const versions=(card.dataset.versions||"").split(",");

    const ok =
      card.dataset.category===category &&
      (!q || text.includes(q)) &&
      (!l || loaders.includes(l)) &&
      (!v || versions.includes(v));

    card.style.display=ok?"block":"none";
    if(ok) shown++;
  }});

  status.textContent=shown+" نتيجة";
}}

document.querySelectorAll(".tab").forEach(btn=>{{
  btn.addEventListener("click",()=>{{
    document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
    btn.classList.add("active");
    category=btn.dataset.cat;
    render();
  }});
}});

search.addEventListener("input",render);
loader.addEventListener("change",render);
version.addEventListener("change",render);

render();
</script>
</body>
</html>
"""

    OUTPUT.write_text(site, encoding="utf-8")


def main():
    all_items = []

    for category in CATEGORIES:
        all_items.extend(fetch_category(category))

    if not all_items:
        raise SystemExit(
            "لم يتم جلب بيانات من Modrinth؛ تم إيقاف التحديث حتى لا يتم إتلاف الموقع."
        )

    # إزالة التكرار
    unique = {}
    for item in all_items:
        unique[f"{item['category']}:{item['title'].lower()}"] = item

    all_items = sorted(
        unique.values(),
        key=lambda item: item["downloads"],
        reverse=True,
    )

    build_site(all_items)
    print(f"تم توليد index.html — {len(all_items)} إضافة")


if __name__ == "__main__":
    main()
