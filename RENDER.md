# Deploying on Render

## League data: use the cache

The app serves league OVERS/UNDERS from **`data/league-defense.json`**, which is updated once a day by a GitHub Action. That way the app does **not** call the NBA API from Render (which often blocks or times out).

- **First time:** In GitHub go to **Actions** → **Update league data** → **Run workflow**. When it finishes, `data/league-defense.json` will be in the repo. Deploy (or redeploy) on Render so the service has that file.
- After that, the workflow runs daily; redeploy on Render whenever you want the latest cache, or leave as-is for daily data.

## Start Command (optional but recommended)

1. Open [Render Dashboard](https://dashboard.render.com) → your **nba-prop-hunter** service.
2. Go to **Settings** → **Start Command**.
3. Set to: `gunicorn -b 0.0.0.0:$PORT server:app --timeout 180`
4. Save and redeploy if needed.

With cached league data, the app works even without this; the timeout helps for any remaining live API calls (e.g. team drill-down, players).
