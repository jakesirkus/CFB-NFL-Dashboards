#!/bin/bash
# Week 8 build: Weeks 1-7 (out5b = the Oct 25 expected-score version: regenerated Wk1-6 boxes + xPts) + Week 8 (56 FBS-involved games) -> out6.
# Raw data: combined_raw_w1_8.pkl = combined_raw_w1_7.pkl + CFBD API /plays week 8 (completed games),
# converted to the CSV-export layout. Verified finals: official_finals.json; scoring fixes: score_overrides.json.
set -e
cd "$(dirname "$0")"
python3 -I make_tables.py combined_raw_w1_8.pkl
python3 -I full_pipeline.py >/dev/null && python3 -I winloss_and_radar.py >/dev/null && python3 -I finalize_radar.py >/dev/null
python3 -I build_week.py 8 w8_gids.txt out5b out6 | tail -1
python3 -I ../patch_early_sr_ui.py out6/index.html   # early-down success rate rows in the box score (Oct 26)
# earlier-week finals corrected after the CFBD audit (Oct 25): MTSU-Nevada wk3 27-20, Air Force-Nevada wk4 36-33
python3 -I fix_published_finals.py out6 3_401864443,4_401864509
python3 -I regen_boxes.py out6 401864443,401864509,401856667,401856787,401858212 | tail -1   # + lost fumbles the feed typed as own recoveries (Oct 25)
python3 -I polish_charts.py out6 8 | tail -1
python3 -I chart_overrides.py out6
python3 -I sync_scores.py out6/index.html out6/index.html | tail -1
python3 -I ../add_ppo.py out6/index.html out6/index.html | tail -1
python3 -I ../add_early_sr.py cfb out6
# box-score expected score: new games + the two games whose box scores were regenerated above
python3 -I ../add_xpts.py cfb out6/index.html out6/index.html --recompute 3_401864443,4_401864509,1_401856667,2_401856787,1_401858212
# opponent adjustments (user's power ratings, blend 0.25 (25% at-the-time / 75% current); Oct 27) - Raw/Adjusted toggle
python3 -I ../patch_oppadj_ui.py out6/index.html
python3 -I ../opp_adjust.py cfb out6/index.html out6/index.html --blend 0.25
