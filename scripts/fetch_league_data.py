#!/usr/bin/env python3
"""
Fetch league defense data from NBA API and write to data/league-defense.json.
Run with FORCE_LEAGUE_FETCH=1 NBA_LONG_TIMEOUT=1 (e.g. in GitHub Actions).
Only overwrites file if fetch returns valid teams data.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["FORCE_LEAGUE_FETCH"] = "1"
os.environ["NBA_LONG_TIMEOUT"] = "1"

from server import get_league_defense_last_10, LEAGUE_CACHE_FILE

def main():
    print("[fetch] Fetching league defense data...")
    data = get_league_defense_last_10()
    if not data.get("teams") or len(data.get("teams", [])) < 10:
        print("[fetch] No valid teams data (got %s teams), not writing." % len(data.get("teams", [])))
        if data.get("error"):
            print("[fetch] Error:", data["error"])
        sys.exit(1)
    data["_fetched_at"] = int(time.time())
    os.makedirs(os.path.dirname(LEAGUE_CACHE_FILE), exist_ok=True)
    with open(LEAGUE_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("[fetch] Wrote %s teams to %s" % (len(data["teams"]), LEAGUE_CACHE_FILE))
    return 0

if __name__ == "__main__":
    sys.exit(main())
