#!/usr/bin/env python3
"""Builds data.json: Letterboxd watchlist + Finnish release dates (Finnkino, TMDB)."""
import csv, json, os, re, time, unicodedata, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from html import unescape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER = os.environ.get("LB_USER", "thfrcsstrng88")
KEY = os.environ.get("TMDB_API_KEY", "")
UA = {"User-Agent": "Mozilla/5.0 (compatible; fi-premieres/1.0)"}


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def split_name(name):
    m = re.match(r"^(.*?)\s*\((\d{4})\)$", unescape(name))
    return (m.group(1), int(m.group(2))) if m else (unescape(name), None)


def scrape_watchlist():
    films, page = [], 1
    while True:
        html = get(f"https://letterboxd.com/{USER}/watchlist/page/{page}/")
        tags = re.findall(r'<div[^>]*data-item-name="[^"]*"[^>]*>', html)
        if not tags:
            break
        for t in tags:
            name = re.search(r'data-item-name="([^"]*)"', t).group(1)
            link = re.search(r'data-(?:item|target)-link="([^"]*)"', t)
            title, year = split_name(name)
            films.append({"title": title, "year": year,
                          "url": "https://letterboxd.com" + link.group(1) if link else ""})
        page += 1
        time.sleep(1)
    if not films:
        raise RuntimeError("no films scraped")
    return films


def csv_watchlist():
    path = os.path.join(ROOT, "watchlist.csv")  # Letterboxd export: Date,Name,Year,Letterboxd URI
    with open(path, encoding="utf-8") as f:
        return [{"title": r["Name"], "year": int(r["Year"]) if r["Year"] else None,
                 "url": r.get("Letterboxd URI", "")} for r in csv.DictReader(f)]


def get_watchlist():
    try:
        films = scrape_watchlist()
        print(f"Scraped {len(films)} films from Letterboxd")
        return films
    except Exception as e:
        print(f"Scrape failed ({e}); using watchlist.csv")
        return csv_watchlist()


def tmdb(path, **p):
    p["api_key"] = KEY
    return json.loads(get(f"https://api.themoviedb.org/3{path}?{urllib.parse.urlencode(p)}"))


def tmdb_fi(title, year):
    """Returns (finnish_date_or_None, global_release_date_or_None)."""
    res = tmdb("/search/movie", query=title, include_adult="false")["results"]
    if not res:
        return None, None

    def score(r):
        y = (r.get("release_date") or "")[:4]
        gap = abs(int(y) - year) if year and y.isdigit() else 5
        exact = norm(title) in (norm(r.get("title")), norm(r.get("original_title")))
        return (not exact, gap, -r.get("popularity", 0))

    best = min(res, key=score)
    rd = tmdb(f"/movie/{best['id']}/release_dates")["results"]
    fi = next((c for c in rd if c["iso_3166_1"] == "FI"), None)
    by_type = {}
    for r in (fi["release_dates"] if fi else []):
        by_type.setdefault(r["type"], []).append(r["release_date"][:10])
    # 3 = theatrical, 2 = limited theatrical, 1 = premiere
    fi_date = next((min(by_type[t]) for t in (3, 2, 1) if t in by_type), None)
    return fi_date, best.get("release_date") or None


def finnkino():
    out = {}
    for lt in ("ComingSoon", "NowInTheatres"):
        try:
            xml = re.sub(r"^<\?xml[^>]*\?>", "", get(
                f"https://www.finnkino.fi/xml/Events/?listType={lt}&area=1029").strip())
            for ev in ET.fromstring(xml).iter("Event"):
                rel = (ev.findtext("dtLocalRelease") or "")[:10]
                for k in ("Title", "OriginalTitle"):
                    if ev.findtext(k) and rel:
                        out[norm(ev.findtext(k))] = rel
        except Exception as e:
            print(f"Finnkino {lt} failed: {e}")
    print(f"Finnkino: {len(out)} titles")
    return out


def main():
    if not KEY:
        raise SystemExit("Set TMDB_API_KEY")
    known_path = os.path.join(ROOT, "known_dates.json")
    known = {norm(k): v for k, v in json.load(open(known_path, encoding="utf-8")).items()} \
        if os.path.exists(known_path) else {}
    fk, today, items = finnkino(), date.today().isoformat(), []
    for f in get_watchlist():
        try:
            t_date, g_date = tmdb_fi(f["title"], f["year"])
        except Exception as e:
            print(f"TMDB failed for {f['title']}: {e}")
            t_date, g_date = None, None
        k_date = fk.get(norm(f["title"]))
        fallback = known.get(norm(f["title"]))
        chosen, source = next(((d, s) for d, s in
                               ((k_date, "Finnkino"), (t_date, "TMDB"), (fallback, "manual")) if d),
                              (None, None))
        items.append({**f, "date": chosen, "source": source, "finnkino_date": k_date,
                      "tmdb_date": t_date, "global_date": g_date,
                      "conflict": bool(k_date and t_date and k_date != t_date)})
        time.sleep(0.1)
    out = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "films": items}
    json.dump(out, open(os.path.join(ROOT, "data.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"Wrote {len(items)} films, {sum(1 for i in items if i['date'] and i['date'] >= today)} upcoming in FI")


if __name__ == "__main__":
    main()
