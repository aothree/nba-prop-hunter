"""
NBA Team Defense Webapp — Last 10 games: points/rebounds/assists allowed,
and top 3 opponent scorers with variance vs season average.
"""
import os
import time
from datetime import datetime, timezone
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from nba_api.stats.endpoints import (
    TeamGameLog,
    BoxScoreTraditionalV3,
    LeagueDashPlayerStats,
    LeagueDashTeamStats,
    LeagueGameLog,
    ScheduleLeagueV2,
    PlayerGameLog,
)
from nba_api.stats.static import teams
import pandas as pd

app = Flask(__name__, static_folder="static")
CORS(app)

# Current NBA season
SEASON = "2025-26"

# Cache season PPG for 5 minutes so repeat requests are faster
_season_ppg_cache = None
_season_ppg_cache_time = 0
_league_avg_cache = None
_league_avg_cache_time = 0
CACHE_SECONDS = 300

# Delay (seconds) between NBA API calls to reduce rate-limit/blocking
NBA_DELAY = 0.6

# Headers that help avoid NBA.com blocking (stats.nba.com)
NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://stats.nba.com/",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}


def get_team_list():
    """Return list of NBA teams for dropdown: { id, full_name, abbreviation }."""
    all_teams = teams.get_teams()
    return [
        {"id": str(t["id"]), "full_name": t["full_name"], "abbreviation": t["abbreviation"]}
        for t in all_teams
    ]


def get_season_ppg_map():
    """Fetch league-wide stats and return dict player_id -> PPG (season average). Cached 5 min."""
    import time
    global _season_ppg_cache, _season_ppg_cache_time
    now = time.time()
    if _season_ppg_cache is not None and (now - _season_ppg_cache_time) < CACHE_SECONDS:
        return _season_ppg_cache
    try:
        ld = LeagueDashPlayerStats(season=SEASON, timeout=60, headers=NBA_HEADERS)
        df = ld.get_data_frames()[0]
    except Exception:
        return _season_ppg_cache if _season_ppg_cache is not None else {}
    df.columns = [str(c).upper() if isinstance(c, str) else c for c in df.columns]
    if df is None or df.empty or "PTS" not in df.columns:
        return _season_ppg_cache if _season_ppg_cache is not None else {}
    if "GP" in df.columns:
        gp = pd.to_numeric(df["GP"], errors="coerce").replace(0, 1)
        df = df.copy()
        df["PPG"] = pd.to_numeric(df["PTS"], errors="coerce") / gp
    else:
        df = df.copy()
        df["PPG"] = pd.to_numeric(df["PTS"], errors="coerce")
    _season_ppg_cache = df.set_index("PLAYER_ID")["PPG"].to_dict()
    _season_ppg_cache_time = now
    return _season_ppg_cache


def get_league_averages():
    """League-wide per-game averages (PTS/REB/AST). Cached 5 min."""
    import time
    global _league_avg_cache, _league_avg_cache_time
    now = time.time()
    if _league_avg_cache is not None and (now - _league_avg_cache_time) < CACHE_SECONDS:
        return _league_avg_cache
    try:
        # 30s timeout; requires gunicorn --timeout 180 on Render (see RENDER.md)
        ld = LeagueDashTeamStats(season=SEASON, timeout=30, headers=NBA_HEADERS)
        df = ld.get_data_frames()[0]
    except Exception as e:
        print("[league-avg] LeagueDashTeamStats failed:", e)
        return _league_avg_cache if _league_avg_cache is not None else {}
    if df is None or df.empty:
        return _league_avg_cache if _league_avg_cache is not None else {}
    df.columns = [str(c).upper() if isinstance(c, str) else c for c in df.columns]
    if "PTS" not in df.columns:
        return _league_avg_cache if _league_avg_cache is not None else {}
    if "GP" in df.columns:
        gp = pd.to_numeric(df["GP"], errors="coerce").replace(0, 1)
        ppg = pd.to_numeric(df["PTS"], errors="coerce") / gp
        rpg = (pd.to_numeric(df["REB"], errors="coerce") / gp) if "REB" in df.columns else ppg * 0
        apg = (pd.to_numeric(df["AST"], errors="coerce") / gp) if "AST" in df.columns else ppg * 0
    else:
        ppg = pd.to_numeric(df["PTS"], errors="coerce")
        rpg = pd.to_numeric(df["REB"], errors="coerce") if "REB" in df.columns else ppg * 0
        apg = pd.to_numeric(df["AST"], errors="coerce") if "AST" in df.columns else ppg * 0
    _league_avg_cache = {
        "ppg": round(float(ppg.mean()), 1),
        "rpg": round(float(rpg.mean()), 1) if hasattr(rpg, "mean") else 0,
        "apg": round(float(apg.mean()), 1) if hasattr(apg, "mean") else 0,
    }
    _league_avg_cache_time = now
    return _league_avg_cache


def get_defense_last_10(team_id: str):
    """
    For the given team, return last 10 games defensive summary and per-game
    top 3 opponent scorers with variance vs season average.
    """
    team_id_int = int(team_id)
    team_list = [t for t in teams.get_teams() if t["id"] == team_id_int]
    if not team_list:
        return None
    team_name = team_list[0]["full_name"]
    team_abbr = team_list[0]["abbreviation"]

    season_ppg = get_season_ppg_map()
    league_avg = get_league_averages()

    try:
        tgl = TeamGameLog(team_id=team_id, season=SEASON, timeout=60, headers=NBA_HEADERS)
        gl_df = tgl.get_data_frames()[0]
        time.sleep(NBA_DELAY)
    except Exception as e:
        print("[defense] TeamGameLog failed:", e)
        return {"error": str(e), "team_name": team_name}

    if gl_df is None or gl_df.empty:
        print("[defense] TeamGameLog returned empty for team_id=%s season=%s" % (team_id, SEASON))
        lg = league_avg
        return {
            "team_id": team_id,
            "team_name": team_name,
            "team_abbreviation": team_abbr,
            "summary": {
                "ppg_allowed": 0, "rpg_allowed": 0, "apg_allowed": 0,
                "league_avg_ppg": lg.get("ppg", 0), "league_avg_rpg": lg.get("rpg", 0), "league_avg_apg": lg.get("apg", 0),
                "ppg_vs_league_pct": None, "rpg_vs_league_pct": None, "apg_vs_league_pct": None,
            },
            "games": [],
        }

    # Normalize column names (API may return Game_ID or GAME_ID depending on version)
    gl_df.columns = [str(c).upper() if isinstance(c, str) else c for c in gl_df.columns]
    if "GAME_ID" not in gl_df.columns:
        return {"error": "API returned no GAME_ID. Columns: " + ", ".join(str(c) for c in gl_df.columns), "team_name": team_name}
    date_col = "GAME_DATE" if "GAME_DATE" in gl_df.columns else None
    if not date_col:
        date_cols = [c for c in gl_df.columns if "DATE" in str(c)]
        date_col = date_cols[0] if date_cols else None
    if date_col:
        gl_df[date_col] = pd.to_datetime(gl_df[date_col], format="%b %d, %Y", errors="coerce")
        gl_df = gl_df.dropna(subset=[date_col]).sort_values(date_col, ascending=False).head(10)
    else:
        gl_df = gl_df.head(10)

    # LeagueGameLog has team-level PTS/REB/AST per game - use as fallback when V3 team_stats lacks them
    league_game_log_by_game = {}
    try:
        time.sleep(NBA_DELAY)
        lgl = LeagueGameLog(season=SEASON, timeout=60, headers=NBA_HEADERS)
        lgl_df = lgl.get_data_frames()[0]
        if lgl_df is not None and not lgl_df.empty:
            lgl_df.columns = [str(c).upper() if isinstance(c, str) else c for c in lgl_df.columns]
            for _, r in lgl_df.iterrows():
                gid = r.get("GAME_ID")
                if pd.isna(gid) or gid is None:
                    continue
                try:
                    gid_str = str(int(float(gid))).zfill(10)
                except (ValueError, TypeError):
                    continue
                tid = int(r.get("TEAM_ID") or 0)
                pts = int(r.get("PTS") or 0)
                reb = int(r.get("REB") or 0)
                ast = int(r.get("AST") or 0)
                if gid_str not in league_game_log_by_game:
                    league_game_log_by_game[gid_str] = {}
                league_game_log_by_game[gid_str][tid] = {"pts": pts, "reb": reb, "ast": ast}
        print("[defense] LeagueGameLog loaded for %s games" % len(league_game_log_by_game))
    except Exception as e:
        print("[defense] LeagueGameLog fallback failed:", e)

    total_pts_allowed = 0.0
    total_reb_allowed = 0.0
    total_ast_allowed = 0.0
    games_data = []

    for _, row in gl_df.iterrows():
        game_id_raw = row.get("GAME_ID")
        if pd.isna(game_id_raw) or game_id_raw is None:
            continue
        try:
            game_id = str(int(float(game_id_raw))).zfill(10)
        except (ValueError, TypeError):
            continue
        game_date = row.get(date_col, row.get("GAME_DATE", "")) if date_col else ""
        if hasattr(game_date, "strftime"):
            game_date_str = game_date.strftime("%b %d, %Y")
        else:
            game_date_str = str(game_date) if game_date else ""
        matchup = row.get("MATCHUP", "")
        our_pts = int(row.get("PTS", 0) or 0)

        def _fetch_box():
            time.sleep(NBA_DELAY)
            print("[defense] Fetching box score (V3) for game_id=%s" % game_id)
            box = BoxScoreTraditionalV3(game_id=game_id, timeout=60, headers=NBA_HEADERS)
            dfs = box.get_data_frames()
            print("[defense] Box score returned %s dataframes for game_id=%s" % (len(dfs) if dfs else 0, game_id))
            if not dfs:
                print("[defense] Box score returned no dataframes for game_id=%s" % game_id)
                return None, None
            
            # V3 returns: [0] player stats (26 rows), [1] team starter/bench (4 rows), [2] team totals (2 rows)
            # Columns are camelCase: gameId, teamId, playerId, playerName, points, rebounds, assists, etc.
            player_stats = None
            team_stats = None
            
            for i, df in enumerate(dfs):
                if df is None or df.empty:
                    continue
                # Normalize column names to uppercase for consistency
                df_copy = df.copy()
                # Map camelCase to UPPER_CASE
                col_map = {}
                for c in df_copy.columns:
                    # Convert camelCase to UPPER_SNAKE_CASE
                    upper = ''.join(['_' + ch if ch.isupper() else ch for ch in str(c)]).upper().lstrip('_')
                    col_map[c] = upper
                df_copy = df_copy.rename(columns=col_map)
                
                # Player stats has PLAYER_ID, PLAYER_NAME, or PERSON_ID (V3 uses PERSON_ID + FIRST_NAME/FAMILY_NAME)
                if "PLAYER_ID" in df_copy.columns or "PLAYER_NAME" in df_copy.columns or "PERSON_ID" in df_copy.columns:
                    if player_stats is None or len(df_copy) > len(player_stats):
                        player_stats = df_copy
                        print("[defense] Found player_stats with %s rows (df %s) for game_id=%s" % (len(player_stats), i, game_id))
                # Team totals (2 rows, one per team) with PTS/REB/AST - V3's 2-row df may NOT have stats
                elif "TEAM_ID" in df_copy.columns and len(df_copy) == 2 and ("PTS" in df_copy.columns or "POINTS" in df_copy.columns or "REB" in df_copy.columns or "REBOUNDS" in df_copy.columns):
                    team_stats = df_copy
                    print("[defense] Found team_stats with %s rows (df %s) for game_id=%s" % (len(team_stats), i, game_id))
            
            if player_stats is None or team_stats is None:
                print("[defense] Could not identify player/team stats for game_id=%s (player=%s, team=%s)" % (
                    game_id, player_stats is not None, team_stats is not None))
                # Try using the largest df as player stats, and the 2-row df as team stats
                non_empty = [df for df in dfs if df is not None and not df.empty]
                if player_stats is None and non_empty:
                    largest = max(non_empty, key=len)
                    player_stats = largest.copy()
                    col_map = {}
                    for c in player_stats.columns:
                        upper = ''.join(['_' + ch if ch.isupper() else ch for ch in str(c)]).upper().lstrip('_')
                        col_map[c] = upper
                    player_stats = player_stats.rename(columns=col_map)
                if team_stats is None:
                    for df in non_empty:
                        if len(df) == 2:
                            team_stats = df.copy()
                            col_map = {}
                            for c in team_stats.columns:
                                upper = ''.join(['_' + ch if ch.isupper() else ch for ch in str(c)]).upper().lstrip('_')
                                col_map[c] = upper
                            team_stats = team_stats.rename(columns=col_map)
                            break
            
            if player_stats is None or team_stats is None:
                print("[defense] Still missing data for game_id=%s" % game_id)
                return None, None
            
            # V3 uses full names (POINTS, REBOUNDS, ASSISTS) - alias to short names (PTS, REB, AST)
            alias_map = {
                "POINTS": "PTS",
                "REBOUNDS": "REB",
                "ASSISTS": "AST",
                "PLAYER_NAME": "PLAYER_NAME",
                "PLAYER_ID": "PLAYER_ID",
                "TEAM_ID": "TEAM_ID",
            }
            for df in [player_stats, team_stats]:
                for old_name, new_name in alias_map.items():
                    if old_name in df.columns and new_name not in df.columns:
                        df[new_name] = df[old_name]
            
            print("[defense] Successfully got box score for game_id=%s, columns: %s" % (game_id, list(player_stats.columns)[:10]))
            return player_stats, team_stats

        player_stats = None
        team_stats = None
        for attempt in range(3):
            try:
                player_stats, team_stats = _fetch_box()
                if player_stats is not None and team_stats is not None:
                    break
                else:
                    print("[defense] Attempt %s returned None for game_id=%s, retrying..." % (attempt + 1, game_id))
            except Exception as box_err:
                print("[defense] BoxScoreTraditionalV3 attempt %s game_id=%s ERROR: %s" % (attempt + 1, game_id, box_err))
            if attempt < 2:
                time.sleep(1.5)
        if player_stats is None or team_stats is None:
            games_data.append({
                "game_id": game_id,
                "date": game_date_str,
                "matchup": matchup,
                "our_pts": our_pts,
                "opp_pts": None,
                "opp_reb": None,
                "opp_ast": None,
                "top3_scorers": [],
            })
            continue

        our_team_id = team_id_int
        opp_pts = opp_reb = opp_ast = None
        opp_team_id = None

        # LeagueGameLog has reliable team PTS/REB/AST - prefer it over V3 team_stats (which may lack REB/AST)
        if game_id in league_game_log_by_game:
            for tid, stats in league_game_log_by_game[game_id].items():
                if int(tid) != our_team_id:
                    opp_team_id = int(tid)
                    opp_pts = stats["pts"]
                    opp_reb = stats["reb"]
                    opp_ast = stats["ast"]
                    break

        # Fallback to V3 team_stats if LeagueGameLog didn't have this game
        if opp_pts is None and team_stats is not None:
            for _, trow in team_stats.iterrows():
                tid = int(trow.get("TEAM_ID") or trow.get("TEAMID") or 0)
                if tid != our_team_id:
                    opp_team_id = tid
                    opp_pts = int(trow.get("PTS") or trow.get("POINTS") or 0)
                    opp_reb = int(trow.get("REB") or trow.get("REBOUNDS") or 0)
                    opp_ast = int(trow.get("AST") or trow.get("ASSISTS") or 0)
                    break

        if opp_pts is not None:
            total_pts_allowed += opp_pts
            total_reb_allowed += opp_reb
            total_ast_allowed += opp_ast

        team_id_col = "TEAM_ID" if "TEAM_ID" in player_stats.columns else "TEAMID" if "TEAMID" in player_stats.columns else None
        if opp_team_id is not None and team_id_col:
            opp_players = player_stats[player_stats[team_id_col] == opp_team_id].copy()
        elif team_id_col:
            opp_players = player_stats[player_stats[team_id_col] != our_team_id].copy()
        else:
            opp_players = pd.DataFrame()
        # Sort by points (handle both PTS and POINTS column names)
        pts_col = "PTS" if "PTS" in opp_players.columns else "POINTS" if "POINTS" in opp_players.columns else None
        if pts_col and not opp_players.empty:
            opp_players = opp_players.sort_values(pts_col, ascending=False).head(3)
        else:
            opp_players = opp_players.head(3)

        top3 = []
        for _, prow in opp_players.iterrows():
            pid = prow.get("PLAYER_ID") or prow.get("PLAYERID") or prow.get("PERSON_ID")
            # V3 uses FIRST_NAME + FAMILY_NAME instead of PLAYER_NAME
            pname = prow.get("PLAYER_NAME") or prow.get("PLAYERNAME")
            if not pname and prow.get("FIRST_NAME") is not None:
                first = str(prow.get("FIRST_NAME", "") or "")
                family = str(prow.get("FAMILY_NAME", "") or "")
                pname = (first + " " + family).strip() or "Unknown"
            pname = pname or "Unknown"
            game_pts = int(prow.get("PTS") or prow.get("POINTS") or 0)
            season_avg = season_ppg.get(pid)
            if season_avg is None or season_avg == 0:
                variance_pct = None
            else:
                variance_pct = round((game_pts - season_avg) / season_avg * 100, 1)
            top3.append({
                "player_name": pname,
                "player_id": pid,
                "points": game_pts,
                "season_avg_ppg": round(float(season_avg), 1) if season_avg is not None else None,
                "variance_pct": variance_pct,
            })
        games_data.append({
            "game_id": game_id,
            "date": game_date_str,
            "matchup": matchup,
            "our_pts": our_pts,
            "opp_pts": opp_pts,
            "opp_reb": opp_reb,
            "opp_ast": opp_ast,
            "top3_scorers": top3,
        })

    n = len(games_data)
    ppg_a = round(total_pts_allowed / n, 1) if n else 0
    rpg_a = round(total_reb_allowed / n, 1) if n else 0
    apg_a = round(total_ast_allowed / n, 1) if n else 0
    lg_ppg = league_avg.get("ppg") or 0
    lg_rpg = league_avg.get("rpg") or 0
    lg_apg = league_avg.get("apg") or 0

    def var_pct(team_val, league_val):
        if not league_val:
            return None
        return round((team_val - league_val) / league_val * 100, 1)

    summary = {
        "ppg_allowed": ppg_a,
        "rpg_allowed": rpg_a,
        "apg_allowed": apg_a,
        "league_avg_ppg": lg_ppg,
        "league_avg_rpg": lg_rpg,
        "league_avg_apg": lg_apg,
        "ppg_vs_league_pct": var_pct(ppg_a, lg_ppg),
        "rpg_vs_league_pct": var_pct(rpg_a, lg_rpg),
        "apg_vs_league_pct": var_pct(apg_a, lg_apg),
    }

    return {
        "team_id": team_id,
        "team_name": team_name,
        "team_abbreviation": team_abbr,
        "summary": summary,
        "games": games_data,
    }


def _normalize_cols(df):
    """Normalize dataframe columns to UPPER_SNAKE for consistent lookup."""
    if df is None or df.empty:
        return df
    df = df.copy()
    df.columns = [
        str(c).replace(" ", "_").upper() if isinstance(c, str) else c
        for c in df.columns
    ]
    return df


def get_next_opponents():
    """
    Return dict team_id (int) -> { "abbr": str, "name": str } for each team's next game opponent.
    Uses ScheduleLeagueV2; filters future games and picks earliest per team.
    """
    try:
        time.sleep(NBA_DELAY)
        sched = ScheduleLeagueV2(season=SEASON, timeout=60, headers=NBA_HEADERS)
        dfs = sched.get_data_frames()
    except Exception as e:
        print("[next-opponents] ScheduleLeagueV2 failed:", e)
        return {}
    if not dfs or dfs[0] is None or dfs[0].empty:
        return {}
    df = _normalize_cols(dfs[0])
    # Column names from API may be GAME_DATE_EST, HOMETEAM_TEAMID, AWAYTEAM_TEAMID after normalize
    date_col = None
    for c in df.columns:
        cu = str(c).upper()
        if "GAME" in cu and "DATE" in cu:
            date_col = c
            break
    home_id_col = next((c for c in df.columns if "HOME" in str(c).upper() and "TEAM" in str(c).upper() and "ID" in str(c).upper()), None)
    away_id_col = next((c for c in df.columns if "AWAY" in str(c).upper() and "TEAM" in str(c).upper() and "ID" in str(c).upper()), None)
    if not date_col or not home_id_col or not away_id_col:
        print("[next-opponents] Missing cols. Have:", list(df.columns)[:15])
        return {}
    df["_dt"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=["_dt"])
    now = datetime.now(timezone.utc)
    if df["_dt"].dt.tz is None:
        now = now.replace(tzinfo=None)
    future = df[df["_dt"] >= now].copy()
    if future.empty:
        return {}
    future = future.sort_values("_dt")
    team_list = teams.get_teams()
    id_to_abbr = {t["id"]: t["abbreviation"] for t in team_list}
    id_to_name = {t["id"]: t["full_name"] for t in team_list}
    next_opp = {}
    for _, row in future.iterrows():
        hid = int(row[home_id_col]) if pd.notna(row[home_id_col]) else None
        aid = int(row[away_id_col]) if pd.notna(row[away_id_col]) else None
        if hid is None or aid is None:
            continue
        if hid not in next_opp:
            next_opp[hid] = {"abbr": id_to_abbr.get(aid, "???"), "name": id_to_name.get(aid, "Unknown")}
        if aid not in next_opp:
            next_opp[aid] = {"abbr": id_to_abbr.get(hid, "???"), "name": id_to_name.get(hid, "Unknown")}
        if len(next_opp) >= 30:
            break
    return next_opp


def get_top_scorers_rebounders_assisters_per_team():
    """
    Return dict team_id (int) -> {
      "top_3_scorers": [{ "player_name", "ppg" }],
      "top_3_rebounders": [{ "player_name", "rpg" }],
      "top_3_assisters": [{ "player_name", "apg" }],
    }.
    """
    try:
        ld = LeagueDashPlayerStats(season=SEASON, timeout=60, headers=NBA_HEADERS)
        df = ld.get_data_frames()[0]
    except Exception as e:
        print("[top-per-team] LeagueDashPlayerStats failed:", e)
        return {}
    if df is None or df.empty:
        return {}
    df = _normalize_cols(df)
    if "TEAM_ID" not in df.columns or "PTS" not in df.columns:
        return {}
    gp_col = "GP" if "GP" in df.columns else None
    name_col = next((c for c in df.columns if "PLAYER" in str(c) and "NAME" in str(c)), None)
    if not name_col:
        first_col = next((c for c in df.columns if "FIRST" in str(c)), None)
        last_col = next((c for c in df.columns if "LAST" in str(c) or "FAMILY" in str(c)), None)
        if first_col and last_col:
            df["_NAME"] = (df[first_col].astype(str) + " " + df[last_col].astype(str)).str.strip()
            name_col = "_NAME"
    if not name_col:
        return {}
    pid_col = "PLAYER_ID" if "PLAYER_ID" in df.columns else None
    gp = pd.to_numeric(df[gp_col], errors="coerce").replace(0, 1) if gp_col else 1
    df["_PPG"] = pd.to_numeric(df["PTS"], errors="coerce") / gp
    df["_RPG"] = pd.to_numeric(df["REB"], errors="coerce") / gp if "REB" in df.columns else 0.0
    df["_APG"] = pd.to_numeric(df["AST"], errors="coerce") / gp if "AST" in df.columns else 0.0
    out = {}
    for tid, grp in df.groupby("TEAM_ID"):
        tid = int(tid)
        top_pts = grp.nlargest(3, "_PPG")
        top_reb = grp.nlargest(3, "_RPG")
        top_ast = grp.nlargest(3, "_APG")
        def _row(r, name_col, val_key, val):
            d = {"player_name": r[name_col] if pd.notna(r[name_col]) else "Unknown", val_key: round(float(val), 1)}
            if pid_col and pd.notna(r.get(pid_col)):
                try:
                    d["player_id"] = int(r[pid_col])
                except (ValueError, TypeError):
                    pass
            return d
        out[tid] = {
            "top_3_scorers": [_row(row, name_col, "ppg", row["_PPG"]) for _, row in top_pts.iterrows()],
            "top_3_rebounders": [_row(row, name_col, "rpg", row["_RPG"]) for _, row in top_reb.iterrows()],
            "top_3_assisters": [_row(row, name_col, "apg", row["_APG"]) for _, row in top_ast.iterrows()],
        }
    return out


def get_players_last_10(player_ids, stat="pts"):
    """
    For each player_id, fetch last 10 games and return list of stat values (most recent first).
    stat: "pts" | "reb" | "ast"
    Returns: { "player_id": [val1, val2, ...], ... } (up to 10 values per player).
    """
    if not player_ids:
        return {}
    player_ids = [int(pid) for pid in player_ids if pid is not None][:20]
    if not player_ids:
        return {}
    col = {"pts": "PTS", "reb": "REB", "ast": "AST"}.get(stat.lower(), "PTS")
    out = {}
    for pid in player_ids:
        try:
            time.sleep(NBA_DELAY)
            pgl = PlayerGameLog(player_id=pid, season=SEASON, timeout=30, headers=NBA_HEADERS)
            df = pgl.get_data_frames()[0]
        except Exception as e:
            print("[players-last-10] PlayerGameLog failed for %s: %s" % (pid, e))
            out[str(pid)] = []
            continue
        if df is None or df.empty:
            out[str(pid)] = []
            continue
        df = _normalize_cols(df)
        date_col = "GAME_DATE" if "GAME_DATE" in df.columns else "GAME_DATE_EST" if "GAME_DATE_EST" in df.columns else None
        if date_col and col in df.columns:
            df["_dt"] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.dropna(subset=["_dt"]).sort_values("_dt", ascending=False).head(10)
            vals = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int).tolist()
        else:
            vals = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int).head(10).tolist()
        out[str(pid)] = vals
    return out


_player_list_cache = None
_player_list_cache_time = 0


def get_player_list():
    """Return list of players for the current season: [{ "id": str, "full_name": str }]. Cached 5 min."""
    global _player_list_cache, _player_list_cache_time
    now = time.time()
    if _player_list_cache is not None and (now - _player_list_cache_time) < CACHE_SECONDS:
        return _player_list_cache
    try:
        time.sleep(NBA_DELAY)
        ld = LeagueDashPlayerStats(season=SEASON, timeout=60, headers=NBA_HEADERS)
        df = ld.get_data_frames()[0]
    except Exception as e:
        print("[player-list] LeagueDashPlayerStats failed:", e)
        return _player_list_cache if _player_list_cache is not None else []
    if df is None or df.empty:
        return _player_list_cache if _player_list_cache is not None else []
    df = _normalize_cols(df)
    name_col = next((c for c in df.columns if "PLAYER" in str(c) and "NAME" in str(c)), None)
    if not name_col:
        first_col = next((c for c in df.columns if "FIRST" in str(c)), None)
        last_col = next((c for c in df.columns if "LAST" in str(c) or "FAMILY" in str(c)), None)
        if first_col and last_col:
            df["_NAME"] = (df[first_col].astype(str) + " " + df[last_col].astype(str)).str.strip()
            name_col = "_NAME"
    pid_col = next((c for c in df.columns if "PLAYER" in str(c) and "ID" in str(c)), None)
    if not name_col or not pid_col:
        return _player_list_cache if _player_list_cache is not None else []
    out = []
    seen = set()
    for _, row in df.iterrows():
        pid = row.get(pid_col)
        if pd.isna(pid):
            continue
        try:
            pid_str = str(int(pid))
        except (ValueError, TypeError):
            continue
        if pid_str in seen:
            continue
        seen.add(pid_str)
        name = row.get(name_col)
        if pd.isna(name) or not str(name).strip():
            continue
        out.append({"id": pid_str, "full_name": str(name).strip()})
    out.sort(key=lambda x: x["full_name"].lower())
    _player_list_cache = out
    _player_list_cache_time = now
    return out


def get_player_last_10_full(player_id: str):
    """
    For a single player, return last 20 games with PTS, REB, AST, MIN.
    Returns: { player_id, player_name, team_abbreviation, summary, games }.
    """
    try:
        pid = int(player_id)
    except (ValueError, TypeError):
        return None
    players = get_player_list()
    player_name = next((p["full_name"] for p in players if p["id"] == player_id), None)
    if not player_name:
        player_name = "Unknown"
    try:
        time.sleep(NBA_DELAY)
        pgl = PlayerGameLog(player_id=pid, season=SEASON, timeout=30, headers=NBA_HEADERS)
        df = pgl.get_data_frames()[0]
    except Exception as e:
        print("[player-last-20-full] PlayerGameLog failed for %s: %s" % (player_id, e))
        return {"player_id": player_id, "player_name": player_name, "team_abbreviation": None, "summary": {}, "games": [], "error": str(e)}
    if df is None or df.empty:
        return {"player_id": player_id, "player_name": player_name, "team_abbreviation": None, "summary": {}, "games": []}
    df = _normalize_cols(df)
    date_col = "GAME_DATE" if "GAME_DATE" in df.columns else "GAME_DATE_EST" if "GAME_DATE_EST" in df.columns else None
    if date_col:
        df["_dt"] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=["_dt"]).sort_values("_dt", ascending=False).head(20)
    else:
        df = df.head(20)
    team_abbreviation = None
    team_abbr_col = next((c for c in df.columns if "TEAM" in str(c) and "ABBREV" in str(c)), None)
    if team_abbr_col and not df.empty:
        val = df.iloc[0].get(team_abbr_col)
        if pd.notna(val) and str(val).strip():
            team_abbreviation = str(val).strip()
    if not team_abbreviation:
        team_id_col = next((c for c in df.columns if "TEAM" in str(c) and "ID" in str(c)), None)
        if team_id_col and not df.empty:
            first_team_id = df.iloc[0].get(team_id_col)
            if pd.notna(first_team_id):
                try:
                    tid = int(first_team_id)
                    team_list = teams.get_teams()
                    for t in team_list:
                        if t["id"] == tid:
                            team_abbreviation = t["abbreviation"]
                            break
                except (ValueError, TypeError):
                    pass
    if not team_abbreviation and not df.empty:
        matchup = str(df.iloc[0].get("MATCHUP", "") or "")
        if " vs. " in matchup:
            team_abbreviation = matchup.split(" vs. ")[0].strip()[:3]
        elif " @ " in matchup:
            team_abbreviation = matchup.split(" @ ")[0].strip()[:3]
    games_list = []
    pts_sum = reb_sum = ast_sum = min_sum = 0.0
    min_count = 0
    for _, row in df.iterrows():
        date_val = row.get(date_col) if date_col else row.get("GAME_DATE", "")
        if hasattr(date_val, "strftime"):
            date_str = date_val.strftime("%b %d, %Y")
        else:
            date_str = str(date_val) if date_val else ""
        matchup = str(row.get("MATCHUP", "") or "")
        pts = int(pd.to_numeric(row.get("PTS", 0), errors="coerce") or 0)
        reb = int(pd.to_numeric(row.get("REB", 0), errors="coerce") or 0)
        ast = int(pd.to_numeric(row.get("AST", 0), errors="coerce") or 0)
        min_raw = row.get("MIN")
        if pd.isna(min_raw) or min_raw is None or str(min_raw).strip() == "":
            min_val = None
        else:
            min_s = str(min_raw).strip()
            if ":" in min_s:
                parts = min_s.split(":")
                try:
                    min_val = int(parts[0]) + int(parts[1]) / 60.0 if len(parts) >= 2 else int(parts[0])
                except (ValueError, TypeError):
                    min_val = None
            else:
                try:
                    min_val = float(min_s)
                except (ValueError, TypeError):
                    min_val = None
        if min_val is not None:
            min_sum += min_val
            min_count += 1
        pts_sum += pts
        reb_sum += reb
        ast_sum += ast
        games_list.append({
            "date": date_str,
            "matchup": matchup,
            "pts": pts,
            "reb": reb,
            "ast": ast,
            "min": round(min_val, 1) if min_val is not None else None,
            "usg_pct": None,
        })
    n = len(games_list)
    summary = {}
    if n:
        summary = {
            "ppg_avg": round(pts_sum / n, 1),
            "rpg_avg": round(reb_sum / n, 1),
            "apg_avg": round(ast_sum / n, 1),
            "min_avg": round(min_sum / min_count, 1) if min_count else None,
        }
    return {
        "player_id": player_id,
        "player_name": player_name,
        "team_abbreviation": team_abbreviation,
        "summary": summary,
        "games": games_list,
    }


_league_defense_cache = None
_league_defense_cache_time = 0


def get_league_defense_last_10():
    """
    For all 30 teams, return last 10 games PPG/RPG/APG allowed and variance vs league avg.
    Uses LeagueGameLog only (one API call). Cached 5 min.
    """
    global _league_defense_cache, _league_defense_cache_time
    now = time.time()
    if _league_defense_cache is not None and (now - _league_defense_cache_time) < CACHE_SECONDS:
        return _league_defense_cache

    # League averages optional: if slow/fails we still try LeagueGameLog with default 0
    try:
        league_avg = get_league_averages()
    except Exception as e:
        print("[league-defense] get_league_averages failed:", e)
        league_avg = {}
    lg_ppg = league_avg.get("ppg") or 0
    lg_rpg = league_avg.get("rpg") or 0
    lg_apg = league_avg.get("apg") or 0

    df = None
    last_error = None
    # 75s per attempt; requires gunicorn --timeout 180 on Render (see RENDER.md)
    for attempt in range(2):
        try:
            time.sleep(NBA_DELAY)
            lgl = LeagueGameLog(season=SEASON, timeout=75, headers=NBA_HEADERS)
            df = lgl.get_data_frames()[0]
            if df is not None and not df.empty:
                break
        except Exception as e:
            last_error = e
            print("[league-defense] LeagueGameLog attempt %s failed: %s" % (attempt + 1, e))
        if attempt < 1:
            time.sleep(2)
    if df is None or df.empty:
        err_msg = str(last_error) if last_error else "No data returned"
        print("[league-defense] All attempts failed. Last error:", err_msg)
        return _league_defense_cache if _league_defense_cache else {
            "teams": [], "league_avg": league_avg, "error": "NBA API failed: " + err_msg
        }

    if df is None or df.empty:
        return _league_defense_cache if _league_defense_cache else {"teams": [], "league_avg": league_avg}

    df.columns = [str(c).upper() if isinstance(c, str) else c for c in df.columns]
    if "GAME_ID" not in df.columns or "TEAM_ID" not in df.columns or "PTS" not in df.columns:
        print("[league-defense] Missing required columns. Have:", list(df.columns)[:10])
        return {"teams": [], "league_avg": league_avg}

    date_col = "GAME_DATE" if "GAME_DATE" in df.columns else "GAME_DATE_EST" if "GAME_DATE_EST" in df.columns else None
    if date_col:
        df["_dt"] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=["_dt"])
    else:
        df["_dt"] = pd.NaT

    # Build game_id -> {team_id: {pts, reb, ast}}
    game_teams = {}
    for _, r in df.iterrows():
        gid = r.get("GAME_ID")
        if pd.isna(gid) or gid is None:
            continue
        try:
            gid_str = str(int(float(gid))).zfill(10)
        except (ValueError, TypeError):
            continue
        tid = int(r.get("TEAM_ID") or 0)
        pts = int(r.get("PTS") or 0)
        reb = int(r.get("REB") or 0)
        ast = int(r.get("AST") or 0)
        if gid_str not in game_teams:
            game_teams[gid_str] = {}
        game_teams[gid_str][tid] = {"pts": pts, "reb": reb, "ast": ast}

    # For each team, get last 10 games
    team_games = {}
    for _, r in df.iterrows():
        tid = int(r.get("TEAM_ID") or 0)
        gid = r.get("GAME_ID")
        if pd.isna(gid):
            continue
        try:
            gid_str = str(int(float(gid))).zfill(10)
        except (ValueError, TypeError):
            continue
        game_date = r.get("_dt")
        if tid not in team_games:
            team_games[tid] = []
        team_games[tid].append({"game_id": gid_str, "date": game_date})

    team_names = {t["id"]: {"name": t["full_name"], "abbr": t["abbreviation"]} for t in teams.get_teams()}

    result = []
    for tid, games in team_games.items():
        games_sorted = sorted(games, key=lambda x: x["date"], reverse=True)[:10]
        opp_pts_list = []
        opp_reb_list = []
        opp_ast_list = []
        for g in games_sorted:
            gid = g["game_id"]
            if gid not in game_teams or len(game_teams[gid]) != 2:
                continue
            rows = game_teams[gid]
            opp_tids = [t for t in rows if t != tid]
            if not opp_tids:
                continue
            other = rows[opp_tids[0]]
            opp_pts_list.append(other["pts"])
            opp_reb_list.append(other["reb"])
            opp_ast_list.append(other["ast"])

        n = len(opp_pts_list)
        if n == 0:
            continue
        ppg_a = round(sum(opp_pts_list) / n, 1)
        rpg_a = round(sum(opp_reb_list) / n, 1)
        apg_a = round(sum(opp_ast_list) / n, 1)

        def var_pct(team_val, league_val):
            if not league_val:
                return None
            return round((team_val - league_val) / league_val * 100, 1)

        info = team_names.get(tid, {"name": "Unknown", "abbr": "???"})
        result.append({
            "team_id": str(tid),
            "team_name": info["name"],
            "team_abbreviation": info["abbr"],
            "ppg_allowed": ppg_a,
            "rpg_allowed": rpg_a,
            "apg_allowed": apg_a,
            "ppg_vs_league_pct": var_pct(ppg_a, lg_ppg),
            "rpg_vs_league_pct": var_pct(rpg_a, lg_rpg),
            "apg_vs_league_pct": var_pct(apg_a, lg_apg),
        })

    # Enrich with next opponent and top scorers/rebounders/assisters per team
    next_opp = get_next_opponents()
    top_per_team = get_top_scorers_rebounders_assisters_per_team()
    for t in result:
        tid_int = int(t["team_id"])
        opp = next_opp.get(tid_int, {})
        t["next_opponent_abbr"] = opp.get("abbr")
        t["next_opponent_name"] = opp.get("name")
        data = top_per_team.get(tid_int, {})
        t["top_3_scorers"] = data.get("top_3_scorers", [])
        t["top_3_rebounders"] = data.get("top_3_rebounders", [])
        t["top_3_assisters"] = data.get("top_3_assisters", [])

    _league_defense_cache = {"teams": result, "league_avg": league_avg}
    _league_defense_cache_time = now
    print("[league-defense] Loaded %s teams" % len(result))
    return _league_defense_cache


@app.route("/")
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "index.html")


@app.route("/api/teams")
def api_teams():
    return jsonify(get_team_list())


@app.route("/api/players")
def api_players():
    try:
        return jsonify(get_player_list())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/player/<player_id>/last-10")
def api_player_last_10(player_id):
    try:
        data = get_player_last_10_full(player_id)
        if data is None:
            return jsonify({"error": "Player not found"}), 404
        return jsonify(data)
    except ConnectionResetError as e:
        print("[player-last-10] Connection reset:", e)
        return jsonify({"error": "Connection reset by NBA API. Wait a few seconds and try again."}), 503
    except (ConnectionError, OSError) as e:
        errno = getattr(e, "errno", None)
        if errno == 10054 or "10054" in str(e):
            print("[player-last-10] Connection forcibly closed:", e)
            return jsonify({"error": "Connection closed by remote host. Wait a few seconds and try again."}), 503
        print("[player-last-10] Connection error:", e)
        return jsonify({"error": "Network error. Try again in a moment."}), 503
    except Exception as e:
        print("[player-last-10] Error:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/league-defense-last-10")
def api_league_defense_last_10():
    try:
        return jsonify(get_league_defense_last_10())
    except Exception as e:
        return jsonify({"teams": [], "league_avg": {}, "error": str(e)}), 500


@app.route("/api/players-last-10")
def api_players_last_10():
    """GET ?ids=123,456,789&stat=pts|reb|ast. Returns { "123": [24,22,...], ... }."""
    from flask import request
    ids_str = request.args.get("ids", "")
    stat = request.args.get("stat", "pts")
    player_ids = [x.strip() for x in ids_str.split(",") if x.strip()]
    try:
        return jsonify(get_players_last_10(player_ids, stat))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/team/<team_id>/defense-last-10")
def api_defense_last_10(team_id):
    try:
        data = get_defense_last_10(team_id)
        if data is None:
            return jsonify({"error": "Team not found"}), 404
        if "error" in data and data.get("games") is None:
            print("[defense] Returning error to client:", data.get("error"))
            return jsonify(data), 500
        return jsonify(data)
    except Exception as e:
        print("[defense] Unhandled exception:", e)
        return jsonify({"error": "Server error: " + str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
