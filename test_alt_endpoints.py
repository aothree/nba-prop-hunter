"""
Test alternative NBA API endpoints for 2025-26 box score data.
"""
import time

GAME_ID = "0022500702"  # Boston vs Milwaukee, Feb 1 2026

print("=" * 60)
print(f"Testing alternative endpoints for game {GAME_ID}")
print("=" * 60)

# Test 1: BoxScoreTraditionalV3 (newer version)
print("\n1. BoxScoreTraditionalV3...")
try:
    from nba_api.stats.endpoints import BoxScoreTraditionalV3
    box = BoxScoreTraditionalV3(game_id=GAME_ID, timeout=30)
    dfs = box.get_data_frames()
    print(f"   Returned {len(dfs)} dataframes")
    for i, df in enumerate(dfs):
        if df is not None and not df.empty:
            print(f"   ✓ Dataframe {i}: {len(df)} rows, cols: {list(df.columns)[:5]}")
        else:
            print(f"   Dataframe {i}: EMPTY")
except Exception as e:
    print(f"   ✗ Failed: {e}")

time.sleep(0.6)

# Test 2: BoxScoreSummaryV2
print("\n2. BoxScoreSummaryV2...")
try:
    from nba_api.stats.endpoints import BoxScoreSummaryV2
    box = BoxScoreSummaryV2(game_id=GAME_ID, timeout=30)
    dfs = box.get_data_frames()
    print(f"   Returned {len(dfs)} dataframes")
    for i, df in enumerate(dfs):
        if df is not None and not df.empty:
            print(f"   ✓ Dataframe {i}: {len(df)} rows, cols: {list(df.columns)[:5]}")
        else:
            print(f"   Dataframe {i}: EMPTY")
except Exception as e:
    print(f"   ✗ Failed: {e}")

time.sleep(0.6)

# Test 3: PlayerGameLog for a specific player in that game (e.g., Jayson Tatum)
print("\n3. PlayerGameLog (Jayson Tatum, 2025-26)...")
try:
    from nba_api.stats.endpoints import PlayerGameLog
    TATUM_ID = 1628369
    pgl = PlayerGameLog(player_id=TATUM_ID, season="2025-26", timeout=30)
    df = pgl.get_data_frames()[0]
    print(f"   ✓ Returned {len(df)} games")
    if not df.empty:
        print(f"   Columns: {list(df.columns)}")
        print(f"   First row PTS: {df.iloc[0].get('PTS', 'N/A')}")
except Exception as e:
    print(f"   ✗ Failed: {e}")

time.sleep(0.6)

# Test 4: LeagueGameLog
print("\n4. LeagueGameLog (2025-26)...")
try:
    from nba_api.stats.endpoints import LeagueGameLog
    lgl = LeagueGameLog(season="2025-26", timeout=30)
    df = lgl.get_data_frames()[0]
    print(f"   ✓ Returned {len(df)} entries")
    if not df.empty:
        print(f"   Columns: {list(df.columns)[:8]}")
        # Find our game
        game_rows = df[df['GAME_ID'] == GAME_ID] if 'GAME_ID' in df.columns else df[df['Game_ID'] == GAME_ID] if 'Game_ID' in df.columns else None
        if game_rows is not None and not game_rows.empty:
            print(f"   ✓ Found {len(game_rows)} rows for game {GAME_ID}")
            print(f"   Sample: {game_rows.iloc[0].to_dict()}")
except Exception as e:
    print(f"   ✗ Failed: {e}")

time.sleep(0.6)

# Test 5: BoxScoreAdvancedV2
print("\n5. BoxScoreAdvancedV2...")
try:
    from nba_api.stats.endpoints import BoxScoreAdvancedV2
    box = BoxScoreAdvancedV2(game_id=GAME_ID, timeout=30)
    dfs = box.get_data_frames()
    print(f"   Returned {len(dfs)} dataframes")
    for i, df in enumerate(dfs):
        if df is not None and not df.empty:
            print(f"   ✓ Dataframe {i}: {len(df)} rows")
        else:
            print(f"   Dataframe {i}: EMPTY")
except Exception as e:
    print(f"   ✗ Failed: {e}")

time.sleep(0.6)

# Test 6: Direct JSON endpoint (bypass nba_api parsing)
print("\n6. Direct stats.nba.com JSON request...")
try:
    import requests
    url = f"https://stats.nba.com/stats/boxscoretraditionalv2?GameID={GAME_ID}&StartPeriod=0&EndPeriod=14&StartRange=0&EndRange=28800&RangeType=0"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://stats.nba.com/",
        "Accept": "application/json",
        "x-nba-stats-origin": "stats",
        "x-nba-stats-token": "true",
    }
    resp = requests.get(url, headers=headers, timeout=30)
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        result_sets = data.get("resultSets", [])
        print(f"   ✓ Returned {len(result_sets)} result sets")
        for rs in result_sets:
            name = rs.get("name", "unknown")
            rows = rs.get("rowSet", [])
            print(f"   {name}: {len(rows)} rows")
except Exception as e:
    print(f"   ✗ Failed: {e}")

print("\n" + "=" * 60)
print("SUMMARY: Use whichever endpoint returned data!")
print("=" * 60)
