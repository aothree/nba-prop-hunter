# NBA Prop Tool

Webapp to view a team's defensive performance over its last 10 games: points, rebounds, and assists allowed, plus the top 3 opponent scorers in each game with variance vs their season average.

---

**Checkpoint (Feb 2025)** — *prop-hunter-baseline*  
This version has: hero with “NBA Prop Tool” + basketball art, OVERS/UNDERS sections (top 3 teams, green/red bars), summary tables with top 3 targets, ALL DATA heatmap, drill-down at bottom.  
**To refer to it:** say *“go back to prop-hunter-baseline”* or *“restore the prop-hunter-baseline version”*.

---

## Run locally

**Quick start (Git Bash, already in project directory):**
```bash
source venv/Scripts/activate
python server.py
```
Then open **http://127.0.0.1:5000** in your browser.  
*(First time only: create the venv and install deps — see Option A below.)*

---

**Option A — Use a virtual environment (recommended if `pip install` fails with "Invalid version: 4.0.0-unsupported"):**

**Git Bash / MINGW64 (from any directory):**
```bash
cd ~/Aothree_repos/"Last 10 Games WebApp"
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
python server.py
```

**Command Prompt (cmd):**
```bash
cd "C:\Users\aorfa\Aothree_repos\Last 10 Games WebApp"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

**Option B — Install into your base environment:**

```bash
cd "C:\Users\aorfa\Aothree_repos\Last 10 Games WebApp"
pip install -r requirements.txt
python server.py
```

Open **http://127.0.0.1:5000** in your browser. Pick a team and click **View defense**.

---

## Where the data lives (fast site)

League OVERS/UNDERS data is stored in the repo at **`data/league-defense.json`**. The app serves from this file, so there are no live NBA API calls at request time — the site stays fast and works on Render. You run the scrape on your PC and push the file; Render uses whatever is in the repo.

### Morning routine (run on your PC)

In the project directory, with the venv activated, run the fetch script, then commit and push so the deployed site gets fresh data:

**Git Bash / macOS / Linux:**
```bash
FORCE_LEAGUE_FETCH=1 NBA_LONG_TIMEOUT=1 python scripts/fetch_league_data.py
git add data/league-defense.json data/players.json
git commit -m "chore: update league-defense cache"
git push
```

**Windows (PowerShell):**
```powershell
$env:FORCE_LEAGUE_FETCH="1"; $env:NBA_LONG_TIMEOUT="1"; python scripts/fetch_league_data.py
git add data/league-defense.json data/players.json
git commit -m "chore: update league-defense cache"
git push
```

The script takes a few minutes. When it succeeds, `data/league-defense.json` is updated; pushing deploys the new data to Render (Render redeploys on push to your main branch).

---

## Test locally (venv)

1. **Fetch data** (from your PC; NBA API often blocks cloud IPs):
   ```powershell
   # PowerShell, from project root with venv activated
   $env:FORCE_LEAGUE_FETCH="1"; $env:NBA_LONG_TIMEOUT="1"; python scripts/fetch_league_data.py
   ```
2. **Start the server:**
   ```powershell
   python server.py
   ```
3. **In the browser:** open **http://127.0.0.1:5000**. Pick a team and open “View defense”.  
   **Optional:** open **http://127.0.0.1:5000/api/health** — you should see `{"ok": true, "league_cache_ready": true}` when the cache file is present and valid.

---

## Deploy to Render

1. Push the repo to **GitHub** (include `data/league-defense.json` — run the morning routine once so the file exists and is pushed).
2. Go to [render.com](https://render.com) → **New +** → **Web Service** → connect GitHub and select this repo.
3. **Build command:** `pip install -r requirements.txt`  
   **Start command:** `gunicorn -b 0.0.0.0:$PORT server:app --timeout 180`  
   (Or use the values from **render.yaml**; see **[RENDER.md](RENDER.md)**.)
4. Click **Create Web Service**. After the first deploy, your site URL (e.g. `https://nba-prop-hunter.onrender.com`) will serve from the cached league data — fast.

**Note:** Free tier services sleep after ~15 minutes of no traffic; the first visit after that may take 30–60 seconds to wake up.

*Optional:* To have the cache update without your PC, you can add a paid proxy and the `NBA_PROXY_URL` secret so the GitHub Action “Update league data” can fetch successfully (see workflow file).

## API

- `GET /api/teams` — list of NBA teams (id, full_name, abbreviation)
- `GET /api/team/<team_id>/defense-last-10` — defensive summary and last 10 games with top 3 opponent scorers and variance vs season PPG
