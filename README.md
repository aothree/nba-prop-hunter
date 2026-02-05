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

## Deploy on Render (share a link)

1. Push this repo to **GitHub** (if you haven’t already).
2. Go to [render.com](https://render.com) and sign up / log in.
3. **New +** → **Web Service** → connect your GitHub and select this repo.
4. Render will use **render.yaml** in the repo (build: `pip install -r requirements.txt`, start: `gunicorn -b 0.0.0.0:$PORT server:app --timeout 180`). If you created the service before that change, **update the Start Command** in the dashboard: **Settings → Build & Deploy → Start Command** set to `gunicorn -b 0.0.0.0:$PORT server:app --timeout 180`. Without `--timeout 180`, the league data request can be killed after 30 seconds.
5. Click **Create Web Service**. After the first deploy, you’ll get a URL like `https://nba-prop-hunter.onrender.com` — that’s the link you can share.

**Note:** On the free tier the app sleeps after ~15 minutes of no traffic; the first visit after that may take 30–60 seconds to wake up.

## API

- `GET /api/teams` — list of NBA teams (id, full_name, abbreviation)
- `GET /api/team/<team_id>/defense-last-10` — defensive summary and last 10 games with top 3 opponent scorers and variance vs season PPG
