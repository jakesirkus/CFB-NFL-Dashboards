#!/bin/bash
# Week 9 build: Weeks 1-8 (out6 = published Week 8 site, all earlier fixes already applied) + Week 9 FBS-involved games -> out7.
# Raw data: combined_raw_w1_9.pkl = combined_raw_w1_8.pkl + CFBD API /plays week 9 (completed games only), converted to the
# CSV-export layout. Verified finals: official_finals.json (CFBD game scores, tally = max checked by w9_finals.py);
# scoring fixes: score_overrides.json (4 Week 9 entries). make_tables also retypes 'Field Goal Good' plays whose text says NO GOOD.
# PFF line data: run ../pff_fetch.py cfb 2026 8 9 10 first.
set -e -o pipefail
cd "$(dirname "$0")"
python3 -I make_tables.py combined_raw_w1_9.pkl
python3 -I full_pipeline.py >/dev/null && python3 -I winloss_and_radar.py >/dev/null && python3 -I finalize_radar.py >/dev/null
rm -rf out7
python3 -I build_week.py 9 w9_gids.txt out6 out7 | tail -1
for p in patch_offsched_ui patch_early_sr_ui patch_oppadj_ui patch_rankings_ui patch_schedule_ui patch_matchup_ui patch_lines_ui patch_bigplays_ui patch_pace_ui; do
  python3 -I ../$p.py out7/index.html >/dev/null; done           # idempotent (out6 already has them)
python3 -I regen_boxes.py out7 $(cat w9_regen_gids.txt) | tail -1     # Wk1-8 games whose yardage changed in the Nov 1 audit (fumble / penalty-play / duplicate-row fixes)
python3 -I polish_charts.py out7 9 | tail -1
python3 -I chart_overrides.py out7
python3 -I sync_scores.py out7/index.html out7/index.html | tail -1
python3 -I ../add_ppo.py out7/index.html out7/index.html | tail -1
python3 -I ../add_early_sr.py cfb out7
python3 -I ../add_offsched.py cfb out7 prepped_to.pkl
python3 -I ../add_bigplays.py cfb out7 prepped_to.pkl     # box-score big plays 20+/30+/40+ with hover lists (Nov 1)
python3 -I ../add_pace.py cfb out7 prepped_to.pkl         # pace stats (Nov 2)
python3 -I ../add_xpts.py cfb out7/index.html out7/index.html --all   # every game (model refitted without turnovers, Nov 2)
python3 -I ../patch_xpts_text.py cfb out7/index.html
python3 -I ../add_totals.py cfb out7/index.html out7/index.html   # projected score / total for the Matchup tab (Nov 2)
python3 -I ../add_line_stats.py cfb out7/index.html out7/index.html
python3 -I ../opp_adjust.py cfb out7/index.html out7/index.html --blend 0.25
