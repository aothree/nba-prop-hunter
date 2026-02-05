# NBA Prop Hunter

Webapp to view a team's defensive performance over its last 10 games: points, rebounds, and assists allowed, plus the top 3 opponent scorers in each game with variance vs their season average.

---

**Checkpoint (Feb 2025)** — *prop-hunter-baseline*  
This version has: hero with “NBA Prop Hunter” + basketball art, OVERS/UNDERS sections (top 3 teams, green/red bars), summary tables with top 3 targets, ALL DATA heatmap, drill-down at bottom.  
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

## League data cache (fast app, works on Render)

League OVERS/UNDERS data is **pre-built once a day** by a GitHub Action and committed to `data/league-defense.json`. The app serves from this file, so:

- **No NBA API calls at request time** — page loads are fast.
- **Works on Render** — the NBA API often blocks cloud IPs; with cached data the app doesn’t need to call it.

**First-time setup:** In GitHub go to **Actions** → **Update league data** → **Run workflow**. Wait for it to finish (it fetches from the NBA API and commits `data/league-defense.json`). Then deploy (or redeploy) on Render so the service has the file. After that, the workflow runs daily on a schedule.

You can run the workflow manually anytime to refresh the cache.

## Deploy on Render (share a link)

1. Push this repo to **GitHub** (if you haven’t already).
2. Run the **Update league data** workflow once (Actions → Update league data → Run workflow) so `data/league-defense.json` exists.
3. Go to [render.com](https://render.com) and sign up / log in.
4. **New +** → **Web Service** → connect your GitHub and select this repo.
5. Set **Start Command** to `gunicorn -b 0.0.0.0:$PORT server:app --timeout 180` (see **[RENDER.md](RENDER.md)**).
6. Click **Create Web Service**. After deploy you’ll get a URL like `https://nba-prop-hunter.onrender.com`.

**Note:** On the free tier the app sleeps after ~15 minutes of no traffic; the first visit after that may take 30–60 seconds to wake up.

## API

- `GET /api/teams` — list of NBA teams (id, full_name, abbreviation)
- `GET /api/team/<team_id>/defense-last-10` — defensive summary and last 10 games with top 3 opponent scorers and variance vs season PPG
