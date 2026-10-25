#!/bin/bash
# Week 8 build: published Weeks 1-7 (out5) + Week 8 (54 FBS-involved games) -> out6.
# Raw data: combined_raw_w1_8.pkl = combined_raw_w1_7.pkl + CFBD API /plays week 8 (completed games),
# converted to the CSV-export layout. Verified finals: official_finals.json; scoring fixes: score_overrides.json.
set -e
cd "$(dirname "$0")"
python3 -I make_tables.py combined_raw_w1_8.pkl
python3 -I full_pipeline.py >/dev/null && python3 -I winloss_and_radar.py >/dev/null && python3 -I finalize_radar.py >/dev/null
python3 -I build_week.py 8 w8_gids.txt out5 out6 | tail -1
# earlier-week finals corrected after the CFBD audit (Oct 25): MTSU-Nevada wk3 27-20, Air Force-Nevada wk4 36-33
python3 -I fix_published_finals.py out6 3_401864443,4_401864509
python3 -I regen_boxes.py out6 401864443,401864509 | tail -1
python3 -I polish_charts.py out6 8 | tail -1
python3 -I chart_overrides.py out6
python3 -I sync_scores.py out6/index.html out6/index.html | tail -1
python3 -I ../add_ppo.py out6/index.html out6/index.html | tail -1
