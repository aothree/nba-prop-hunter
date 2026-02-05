# Deploying on Render — required step

Render often **does not** use the start command from `render.yaml` for existing services. You must set it in the dashboard.

## Fix "WORKER TIMEOUT" / league data not loading

1. Open [Render Dashboard](https://dashboard.render.com) → your **nba-prop-hunter** service.
2. Go to **Settings** (left sidebar).
3. Find **Start Command**.
4. Set it to exactly:
   ```bash
   gunicorn -b 0.0.0.0:$PORT server:app --timeout 180
   ```
5. Click **Save Changes**, then **Manual Deploy** → **Deploy latest commit**.

Without `--timeout 180`, the worker is killed after 30 seconds while waiting for the NBA API, and league data will not load.
