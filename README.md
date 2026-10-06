# Finnish premieres for my Letterboxd watchlist

A daily GitHub Action builds `data.json` (watchlist + Finnish release dates); `index.html` displays it.

## Setup (about 10 minutes)
1. Create a GitHub repo and upload everything in this folder (keep the `.github/workflows` path).
2. Get a free TMDB API key: themoviedb.org → Settings → API.
3. Repo → Settings → Secrets and variables → Actions:
   - Secret `TMDB_API_KEY` = your key
   - Variable `LB_USER` = your Letterboxd username
4. Repo → Settings → Pages → Deploy from branch → `main` / root.
5. Repo → Actions → "Update premieres" → Run workflow. Check the log, then open your Pages URL.

## How dates are chosen
Finnkino first, then TMDB (Finland theatrical, else limited, else premiere), then `known_dates.json`
(hand-checked fallback; edit freely). If Finnkino and TMDB disagree, the page shows a "sources differ" note.

## If the Letterboxd scrape fails
Letterboxd may block GitHub's servers. Export your data (Letterboxd → Settings → Import & Export),
and put `watchlist.csv` from the zip in the repo root. The script falls back to it automatically.

## Untested parts
Written without live network access. If the log shows "Finnkino ... failed" or "0 titles", the Finnkino
feed fields may differ from what the script expects. Paste the log into Claude to get it fixed.
