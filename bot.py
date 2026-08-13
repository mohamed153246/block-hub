import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

DATA_FILE = Path("mods_data.json")
ITEMS_PER_CATEGORY = 20

CATEGORIES = {
    "mod": "مودات",
    "resourcepack": "ريسورس باكات",
    "shader": "شيدرز",
    "datapack": "داتا باكات",
}

MODRINTH_API = "https://api.modrinth.com/v2"
USER_AGENT = os.getenv(
    "MODRINTH_USER_AGENT",
    "block-hub/github-actions/1.0"
)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
})


def get_json(url, params=None, retries=3):
    for attempt in range(retries):
        try:
            response = SESSION.get(url, params=params, timeout=20)

            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", "10"))
                print(f"⚠️ Rate Limit: الانتظار {wait} ثانية")
                time.sleep(min(wait, 60))
                continue

            response.raise_for_status()
            return response.json()

        except requests.RequestException as exc:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            print(f"⚠️ خطأ شبكة: {exc} — إعادة المحاولة بعد {wait} ثوانٍ")
            time.sleep(wait)

    return None


def version_key(value):
    parts = []
    for part in str(value).replace("-", ".").split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def fetch_category(category):
    print(f"🔎 جلب {CATEGORIES[category]}...")

    data = get_json(
        f"{MODRINTH_API}/search",
        params={
            "limit": ITEMS_PER_CATEGORY,
            "offset": 0,
            "index": "downloads",
            "facets": json.dumps([[f"project_type:{category}"]]),
        },
    )

    hits = data.get("hits", [])
    items = []

    for number, hit in enumerate(hits, start=1):
        project_id = hit.get("project_id")
        title = hit.get("title") or "بدون اسم"

        if not project_id:
            continue

        try:
            versions = get_json(
                f"{MODRINTH_API}/project/{project_id}/version",
                params={"include_changelog": "false"},
            ) or []

            loaders = set()
            game_versions = set()

            download_url = (
                f"https://modrinth.com/{category}/"
                f"{hit.get('slug', project_id)}"
            )

            for version in versions:
                loaders.update(
                    loader.lower() for loader in version.get("loaders", [])
                )
                game_versions.update(version.get("game_versions", []))

            if versions:
                files = versions[0].get("files", [])
                if files and files[0].get("url"):
                    download_url = files[0]["url"]

            sorted_versions = sorted(
                game_versions,
                key=version_key,
                reverse=True,
            )

            description = hit.get("description") or "لا يوجد وصف متاح حالياً."
            short_description = (
                description[:180] + "..."
                if len(description) > 180
                else description
            )

            items.append({
                "project_id": project_id,
                "title": title,
                "slug": hit.get("slug", ""),
                "description": short_description,
                "description_full": description,
                "icon_url": hit.get("icon_url") or "",
                "download_url": download_url,
                "author": hit.get("author") or "غير معروف",
                "downloads": int(hit.get("downloads") or 0),
                "category": category,
                "loaders": ",".join(sorted(loaders)),
                "game_versions": ",".join(sorted_versions),
                "gallery": "",
                "client_side": hit.get("client_side") or "unknown",
                "server_side": hit.get("server_side") or "unknown",
                "link_issues": (
                    f"https://modrinth.com/{category}/"
                    f"{hit.get('slug', project_id)}#issues"
                ),
                "link_source": "",
                "link_wiki": "",
                "link_discord": "",
            })

            print(f"   ✅ {number}/{len(hits)}: {title}")

        except Exception as exc:
            print(f"   ⚠️ تخطي {title}: {exc}")

    return items


def deduplicate(items):
    unique = {}

    for item in items:
        key = item.get("project_id") or (
            f"{item.get('category')}:{item.get('title')}"
        )
        unique[key] = item

    return list(unique.values())


def save_database(items):
    items = deduplicate(items)
    items.sort(key=lambda x: x.get("downloads", 0), reverse=True)

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "mods": items,
    }

    DATA_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"💾 تم حفظ {len(items)} إضافة")


def main():
    all_items = []

    for category in CATEGORIES:
        try:
            all_items.extend(fetch_category(category))
        except Exception as exc:
            print(f"❌ فشل تصنيف {category}: {exc}")

    if not all_items:
        raise SystemExit(
            "❌ لم يتم جلب أي محتوى، لذلك لن يتم استبدال قاعدة البيانات."
        )

    save_database(all_items)


if __name__ == "__main__":
    main()
