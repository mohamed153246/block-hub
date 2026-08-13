import html
import json
import os
import time
from pathlib import Path
import requests

OUTPUT = Path('index.html')
API = 'https://api.modrinth.com/v2'
LIMIT = 20
CATEGORIES = {
    'mod': '🛠️ مودات',
    'resourcepack': '🎨 ريسورس باكات',
    'shader': '🌌 شيدرز',
    'datapack': '📜 داتا باكات',
}
USER_AGENT = os.getenv('MODRINTH_USER_AGENT', 'block-hub/1.0')
S = requests.Session()
S.headers.update({'User-Agent': USER_AGENT, 'Accept': 'application/json'})

def get_json(url, params=None, tries=3):
    for attempt in range(tries):
        try:
            r = S.get(url, params=params, timeout=20)
            if r.status_code == 429:
                wait = min(int(r.headers.get('Retry-After', '10')), 60)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError('request failed')

def vkey(v):
    out = []
    for p in str(v).replace('-', '.').split('.'):
        d = ''.join(c for c in p if c.isdigit())
        out.append(int(d) if d else 0)
    return tuple(out)

def fetch_category(category):
    data = get_json(f'{API}/search', params={
        'limit': LIMIT,
        'offset': 0,
        'index': 'downloads',
        'facets': json.dumps([[f'project_type:{category}']]),
    })
    items = []
    for hit in data.get('hits', []):
        pid = hit.get('project_id')
        slug = hit.get('slug') or pid
        if not pid:
            continue
        try:
            versions = get_json(f'{API}/project/{pid}/version', params={'include_changelog': 'false'}) or []
            loaders, versions_set = set(), set()
            url = f'https://modrinth.com/{category}/{slug}'
            for ver in versions:
                loaders.update(str(x).lower() for x in ver.get('loaders', []))
                versions_set.update(ver.get('game_versions', []))
            if versions and versions[0].get('files'):
                url = versions[0]['files'][0].get('url') or url
            desc = hit.get('description') or 'لا يوجد وصف متاح حالياً.'
            if len(desc) > 170:
                desc = desc[:170] + '...'
            items.append({
                'title': hit.get('title') or 'بدون اسم',
                'description': desc,
                'icon': hit.get('icon_url') or '',
                'url': url,
                'author': hit.get('author') or 'غير معروف',
                'downloads': int(hit.get('downloads') or 0),
                'category': category,
                'loaders': sorted(loaders),
                'versions': sorted(versions_set, key=vkey, reverse=True),
            })
        except Exception as e:
            print(f'Skipped {slug}: {e}')
    return items

def esc(x):
    return html.escape(str(x or ''), quote=True)

def card(x):
    badges = ''.join(f'<span class="badge loader">{esc(a)}</span>' for a in x['loaders'][:3])
    badges += ''.join(f'<span class="badge">{esc(a)}</span>' for a in x['versions'][:2])
    return f'''<article class="card" data-category="{esc(x['category'])}" data-loaders="{esc(','.join(x['loaders']))}" data-versions="{esc(','.join(x['versions']))}">
<div class="top"><img class="icon" loading="lazy" src="{esc(x['icon'])}" alt=""><div><h2>{esc(x['title'])}</h2><div class="author">بواسطة {esc(x['author'])}</div></div></div>
<p>{esc(x['description'])}</p><div class="badges">{badges}</div>
<a class="download" href="{esc(x['url'])}" target="_blank" rel="noopener noreferrer">تحميل من Modrinth ↗</a></article>'''

def generate(items):
    items.sort(key=lambda x: x['downloads'], reverse=True)
    loaders = sorted({a for x in items for a in x['loaders'] if a})
    versions = sorted({a for x in items for a in x['versions'] if a}, key=vkey, reverse=True)
    lopts = ''.join(f'<option value="{esc(a)}">{esc(a.title())}</option>' for a in loaders)
    vopts = ''.join(f'<option value="{esc(a)}">{esc(a)}</option>' for a in versions)
    cards = ''.join(card(x) for x in items)
    tabs = ''.join(f'<button class="tab {"active" if i == 0 else ""}" data-cat="{k}">{esc(v)}</button>' for i,(k,v) in enumerate(CATEGORIES.items()))
    page = f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>بلوك هَب | مودات ماين كرافت</title><meta name="description" content="دليل خفيف وسريع لمودات وشيدرز وريسورس باكات ماين كرافت."><style>
*{{box-sizing:border-box}}body{{margin:0;background:#0d1117;color:#e6edf3;font-family:Arial,sans-serif}}main{{max-width:1050px;margin:auto;padding:18px 12px}}header{{text-align:center;padding:20px 8px}}h1{{margin:0 0 7px;color:#66fcf1;font-size:30px}}.sub{{color:#8b949e;font-size:14px}}.search{{width:100%;margin:15px 0;padding:12px 15px;border:1px solid #30363d;border-radius:9px;background:#161b22;color:#fff;outline:0}}.tabs,.filters{{display:flex;gap:7px;justify-content:center;flex-wrap:wrap;margin:8px 0}}button,select{{background:#161b22;color:#e6edf3;border:1px solid #30363d;border-radius:8px;padding:9px 11px}}button{{cursor:pointer}}button.active{{color:#66fcf1;border-color:#66fcf1}}#count{{color:#8b949e;font-size:12px;margin:12px 0}}#mods{{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:11px}}.card{{background:#161b22;border:1px solid #30363d;border-radius:11px;padding:13px}}.top{{display:flex;gap:10px;align-items:center}}.icon{{width:55px;height:55px;border-radius:9px;object-fit:cover;background:#21262d}}h2{{font-size:16px;margin:0 0 3px}}.author{{font-size:11px;color:#66fcf1}}.card p{{color:#9da7b3;font-size:13px;line-height:1.55;min-height:40px}}.badges{{display:flex;gap:5px;flex-wrap:wrap;margin:8px 0}}.badge{{font-size:10px;padding:3px 6px;background:#21262d;border-radius:20px;color:#c9d1d9}}.loader{{color:#66fcf1}}.download{{display:block;text-align:center;text-decoration:none;background:#66fcf1;color:#071015;font-weight:700;padding:8px;border-radius:7px}}.empty{{grid-column:1/-1;text-align:center;padding:35px;color:#8b949e}}footer{{padding:30px 0;text-align:center;color:#6e7681;font-size:11px}}@media(max-width:600px){{h1{{font-size:26px}}#mods{{grid-template-columns:1fr}}}}</style></head><body><main><header><h1>⛏️ بلوك هَب</h1><div class="sub">مودات وشيدرز وريسورس باكات ماين كرافت — يتحدث تلقائياً</div><input id="search" class="search" placeholder="🔎 ابحث عن إضافة..." autocomplete="off"><div class="tabs">{tabs}</div><div class="filters"><select id="loader"><option value="">كل اللودرات</option>{lopts}</select><select id="version"><option value="">كل الإصدارات</option>{vopts}</select></div><div id="count"></div></header><section id="mods">{cards}</section><footer>بلوك هَب © 2026 — روابط التحميل تقود إلى Modrinth.</footer></main><script>
const cards=[...document.querySelectorAll('.card')],s=document.getElementById('search'),l=document.getElementById('loader'),v=document.getElementById('version'),c=document.getElementById('count');let cat='mod';
function render(){{const q=s.value.trim().toLowerCase();let n=0;for(const x of cards){{const ok=x.dataset.category===cat&&(!q||(x.querySelector('h2').textContent+' '+x.querySelector('p').textContent).toLowerCase().includes(q))&&(!l.value||(x.dataset.loaders||'').split(',').includes(l.value))&&(!v.value||(x.dataset.versions||'').split(',').includes(v.value));x.style.display=ok?'block':'none';if(ok)n++}}c.textContent=n+' نتيجة';let e=document.getElementById('empty');if(!n&&!e){{e=document.createElement('div');e.id='empty';e.className='empty';e.textContent='لا توجد نتائج.';document.getElementById('mods').appendChild(e)}}if(n&&e)e.remove()}}
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');cat=b.dataset.cat;render()}});s.oninput=l.onchange=v.onchange=render;render();</script></body></html>'''
    OUTPUT.write_text(page, encoding='utf-8')

def main():
    all_items = []
    for category in CATEGORIES:
        print('Fetching', category)
        try:
            all_items += fetch_category(category)
        except Exception as e:
            print('Category failed:', category, e)
    if not all_items:
        raise SystemExit('No data fetched; index.html was not changed.')
    unique = {f"{x['category']}:{x['title'].lower()}": x for x in all_items}
    generate(list(unique.values()))
    print(f'Updated index.html with {len(unique)} items')

if __name__ == '__main__':
    main()
