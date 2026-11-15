#!/bin/bash
# Week 11 build: Weeks 1-10 (out8 = published Week 10 site) + Week 11 FBS-involved games (completed ones) -> out9.
# Raw data: combined_raw_w1_11.pkl = combined_raw_w1_10.pkl + CFBD API /plays week 11 (completed games only; /home/claude/data/cfbd/w11), converted to the
# CSV-export layout. Verified finals: official_finals.json (CFBD game scores, tally = max checked by w10_finals.py);
# scoring fixes: score_overrides.json (7 Week 10 entries: review-text PATs, Iowa KR TD, MTSU final-play TD). make_tables also retypes 'Field Goal Good' plays whose text says NO GOOD.
# PFF line data: run ../pff_fetch.py cfb 2026 10 first.
set -e -o pipefail
cd "$(dirname "$0")"
python3 -I make_tables.py combined_raw_w1_11.pkl
python3 -I full_pipeline.py >/dev/null && python3 -I winloss_and_radar.py >/dev/null && python3 -I finalize_radar.py >/dev/null
rm -rf out9
python3 -I build_week.py 11 w11_gids.txt out8 out9 | tail -1
for p in patch_offsched_ui patch_early_sr_ui patch_oppadj_ui patch_rankings_ui patch_schedule_ui patch_matchup_ui patch_lines_ui patch_bigplays_ui patch_pace_ui patch_fourth_ui; do
  python3 -I ../$p.py out9/index.html >/dev/null; done           # idempotent (out8 already has them)
python3 -I polish_charts.py out9 11 | tail -1
python3 -I chart_overrides.py out9
python3 -I sync_scores.py out9/index.html out9/index.html | tail -1
python3 -I ../add_ppo.py out9/index.html out9/index.html | tail -1
python3 -I ../add_early_sr.py cfb out9
python3 -I ../add_offsched.py cfb out9 prepped_to.pkl
python3 -I ../add_bigplays.py cfb out9 prepped_to.pkl     # box-score big plays 20+/30+/40+ with hover lists (Nov 1)
python3 -I ../add_pace.py cfb out9 prepped_to.pkl         # pace stats (Nov 2)
python3 -I ../add_xpts.py cfb out9/index.html out9/index.html --all   # every game (deserved score v3 / option 4, Nov 3; reads prepped_to.pkl)
python3 -I ../patch_xpts_text.py cfb out9/index.html
python3 -I ../add_totals.py cfb out9/index.html out9/index.html   # projected score / total for the Matchup tab (Nov 2)
python3 -I ../add_line_stats.py cfb out9/index.html out9/index.html
python3 -I ../opp_adjust.py cfb out9/index.html out9/index.html --blend 0.25
# Predictions tab (Nov 8 2026; opener + line-move columns Nov 9): user's power ratings vs the market for the UPCOMING week (public, user's call). Refresh the inputs first:
#   CFBD /games?year=2026&week=$PW -> /home/claude/data/cfbd/games_w$PW.json, /lines?year=2026&week=$PW -> lines_w$PW.json
PW=${PRED_WEEK:-12}
python3 -I ../patch_predictions_ui.py out9/index.html
python3 -I ../add_predictions.py out9/index.html $PW /home/claude/data/cfbd/games_w$PW.json /home/claude/data/cfbd/lines_w$PW.json /home/claude/data/cfbd/lines_w${PW}_open.json   # opener = Sunday snapshot
