# Deploying on Render

## League data: use the cache

The app serves league OVERS/UNDERS from **`data/league-defense.json`**, so it does not call the NBA API from Render (the NBA API blocks cloud IPs).

**You must create that file from your own computer** (where the NBA API works). In the project directory, with venv activated, run the fetch script (see README “Morning routine”), then `git add data/league-defense.json`, `git commit`, and `git push`.

Then deploy (or redeploy) on Render so the service has the file. Re-run the script and push whenever you want to refresh the data. The GitHub Action (“Update league data”) often fails because the NBA API blocks GitHub; use the local run above as the reliable method.

## Start Command (optional but recommended)

1. Open [Render Dashboard](https://dashboard.render.com) → your **nba-prop-hunter** service.
2. Go to **Settings** → **Start Command**.
3. Set to: `gunicorn -b 0.0.0.0:$PORT server:app --timeout 180`
4. Save and redeploy if needed.

With cached league data, the app works even without this; the timeout helps for any remaining live API calls (e.g. team drill-down, players).
