"""
Quick test to verify NBA API is returning data for recent games.
Run this to see if the issue is with nba_api or our code.
"""
from nba_api.stats.endpoints import BoxScoreTraditionalV2, TeamGameLog
from nba_api.stats.static import teams
import time

# Boston Celtics
TEAM_ID = 1610612738
SEASON = "2025-26"

print("=" * 60)
print("Testing NBA API directly...")
print("=" * 60)

# Test 1: Get game log
print("\n1. Testing TeamGameLog for Boston Celtics (2025-26)...")
try:
    tgl = TeamGameLog(team_id=TEAM_ID, season=SEASON, timeout=30)
    gl_df = tgl.get_data_frames()[0]
    print(f"   ✓ Game log returned {len(gl_df)} games")
    if not gl_df.empty:
        print(f"   First game ID: {gl_df.iloc[0]['Game_ID']}")
        print(f"   First game date: {gl_df.iloc[0]['GAME_DATE']}")
        first_game_id = str(int(float(gl_df.iloc[0]['Game_ID']))).zfill(10)
        print(f"   Formatted game ID: {first_game_id}")
    else:
        print("   ✗ Game log is empty!")
        first_game_id = None
except Exception as e:
    print(f"   ✗ TeamGameLog failed: {e}")
    first_game_id = None

# Test 2: Try a specific game's box score
if first_game_id:
    print(f"\n2. Testing BoxScoreTraditionalV2 for game {first_game_id}...")
    time.sleep(0.6)
    try:
        box = BoxScoreTraditionalV2(game_id=first_game_id, timeout=30)
        dfs = box.get_data_frames()
        print(f"   ✓ Box score returned {len(dfs)} dataframes")
        for i, df in enumerate(dfs):
            if df is not None and not df.empty:
                print(f"   Dataframe {i}: {len(df)} rows, columns: {list(df.columns)[:5]}...")
            else:
                print(f"   Dataframe {i}: EMPTY or None")
    except Exception as e:
        print(f"   ✗ BoxScoreTraditionalV2 failed: {e}")

# Test 3: Try with 2024-25 season (last completed season)
print("\n3. Testing with 2024-25 season (fallback)...")
try:
    tgl_old = TeamGameLog(team_id=TEAM_ID, season="2024-25", timeout=30)
    gl_df_old = tgl_old.get_data_frames()[0]
    print(f"   ✓ 2024-25 game log returned {len(gl_df_old)} games")
    if not gl_df_old.empty:
        old_game_id = str(int(float(gl_df_old.iloc[0]['Game_ID']))).zfill(10)
        print(f"   First game ID: {old_game_id}")
        time.sleep(0.6)
        box_old = BoxScoreTraditionalV2(game_id=old_game_id, timeout=30)
        dfs_old = box_old.get_data_frames()
        print(f"   ✓ 2024-25 box score returned {len(dfs_old)} dataframes")
        for i, df in enumerate(dfs_old):
            if df is not None and not df.empty:
                print(f"   Dataframe {i}: {len(df)} rows")
            else:
                print(f"   Dataframe {i}: EMPTY")
except Exception as e:
    print(f"   ✗ 2024-25 test failed: {e}")

print("\n" + "=" * 60)
print("DIAGNOSIS:")
print("=" * 60)
print("If 2025-26 returns empty box scores but 2024-25 works,")
print("the NBA API hasn't finalized 2025-26 data yet.")
print("We'll need to use 2024-25 season or wait for NBA to update.")
print("=" * 60)
