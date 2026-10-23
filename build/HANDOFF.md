# CFB & NFL Team Dashboards — build handoff

Everything needed to keep building Jake's CFB (FBS) and NFL team dashboards, moved out of the original
Claude chat so a chat with GitHub access can build **and push** each update.

- Repo: `jakesirkus/CFB-NFL-Dashboards` (public, GitHub Pages from `main` / root)
- Live site: https://jakesirkus.github.io/CFB-NFL-Dashboards/  (`/cfb/` and `/nfl/`)
- Also published as claude.ai artifacts: CFB "FBS Team Dashboard", NFL "NFL Team Dashboard" (optional to keep updating)
- Offline single-file copies go to the user's Downloads: `CFB_Dashboard_Weeks_1-N.html` (zipped), `NFL_Dashboard_Weeks_1-N.html`

State at handoff (Oct 23, 2026): **CFB Weeks 1–7 complete (all FBS-involved games). NFL Weeks 1–6 complete**;
Week 7 TNF (NE @ CHI, Bears 30–24) was not yet in nflverse play-by-play.

## Layout (run scripts from inside `cfb_full/` or `nfl_full/`)

```
cfb_full/   CFB pipeline (Python). out5/ = current published CFB site (index.html + periods/ + drivecharts/ shards)
            out4/ = Weeks 1-6 base used by rebuild_w1_7.sh. combined_raw_w1_7.pkl = all CFB play-by-play so far.
nfl_full/   NFL pipeline. nfl_v31.html = current NFL page. live_v23.html = page template, live_data.json = team list/order.
nfl_rebuild/cfb_team_list.json  FBS team list
add_ppo.py, make_github_pack.py, verify_*.js (jsdom page tests; `npm install jsdom` first)
```

## CFB weekly update
Source: the user's CollegeFootballData play-by-play CSV export for the week (`download_NN.csv`).
1. Append the new week's rows to `combined_raw_w1_7.pkl` (same 28 columns; cast dtypes to match; replace any game
   that was partial in an earlier export). Keep only FBS-involved games on the site.
2. **Verify every final** before building: tally of scoring plays = max score = last score in the feed
   (see `w7_finals.py`), cross-check anything odd against an official box score, then add to `official_finals.json`.
   Finals always come from `official_finals.json`, never the feed's score columns.
3. `python3 -I make_tables.py combined_raw_w1_7.pkl` (applies review-text stripping, nullified-TD fix, FG-typed-as-kickoff
   retyping, turnover flags, yardage fixes, `yard_overrides.json`, `flag_overrides.json`).
4. `full_pipeline.py` → `winloss_and_radar.py` → `finalize_radar.py` (season table → final_teams.json)
5. `build_week.py WEEK gids.txt out5 out6` (new week's boxes, splits, drive charts, game logs; asserts chart final = official final)
6. `sync_scores.py out6/index.html out6/index.html`, `python3 -I ../add_ppo.py out6/index.html out6/index.html`
7. Checks — must be clean before publishing: `check_week.py out6 WEEK` (and earlier weeks), `scan_chart_scores.py out6`,
   `node ../verify_w6.js out6/index.html`, `node ../verify_ppo.js out6/index.html "Ohio State"`.
   Known/accepted flags: 5_401866434 Kent State–Ohio (feed is missing a Kent possession) and ~21 FCS-vs-FCS feed gaps.
8. Data fixes that touch earlier weeks: see `rebuild_w1_7.sh` (patch_turnovers, regen_boxes, improve_week, fix_week_opps,
   polish_charts, chart_overrides.py). Hand-verified fixes live in `flag_overrides.json`, `yard_overrides.json`, `chart_overrides.py`.
9. Offline file: `build_offline.py out6 offline_template.html OUT.html` then `../add_ppo.py OUT.html OUT.html --js-only`.

## NFL update
1. Download `https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.csv.gz`, `read_csv` → `to_pickle pbp_newN.pkl`.
   Schedule/finals: `https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv`.
2. `FULLWEEK=<games in the latest week> python3 -I assemble_nfl.py pbp_newN.pkl live_data.json live_v23.html nfl_vNN.html nfl_vNN.json 1 2 ... W`
   (takes ~12 min — run in the background). It runs add_ppo automatically.
3. Checks: `check_nfl_scores.py nfl_vNN.json pbp_newN.pkl` (0 problems), `check_nfl_charts.py nfl_vNN.json` (no issues),
   `node ../verify_nfl5.js nfl_vNN.html`, and confirm earlier weeks' drive charts are unchanged vs the previous build.

## Publish to GitHub
`python3 -I make_github_pack.py cfb_full/<out> nfl_full/<nfl_vNN.html> <repo checkout>` writes `index.html`, `nfl/index.html`,
`cfb/index.html` and the CFB shards merged into ~20+20 packs (`cfb/periods/pack_XX.json`, `cfb/drivecharts/pack_XX.json`).
Copy into the repo checkout, commit, push. (It also writes a "(3 steps)" copy for manual browser uploads — not needed with git.)

## Conventions / lessons (don't regress these)
- Reviewed plays: only the final ruling counts (text before "The previous play is under review…").
- "TOUCHDOWN nullified by penalty" is not a TD. Own fumble recovered in the end zone = offense TD, not a turnover.
- Double turnovers count a giveaway for each side. Penalty-play yardage: incomplete pass = 0; trust text when feed is 15+ off.
- Missed/blocked FGs the feed types as "Kickoff" are retyped; a missed-FG return TD shows as "Missed FG (Return TD)".
- NFL drive builder: order rows by game clock, score = running max in the unit, punt-return fumbles get a "Fumbled Punt" entry.
- Points per opportunity = points on drives with a play inside the opponent 30, summed from box scores.
- The user wants it correct first, and fast — reuse these scripts, don't rebuild from scratch; keep messages short.
