# CFB & NFL Team Dashboards — build handoff

Everything needed to keep building Jake's CFB (FBS) and NFL team dashboards, moved out of the original
Claude chat so a chat with GitHub access can build **and push** each update.

- Repo: `jakesirkus/CFB-NFL-Dashboards` (public, GitHub Pages from `main` / root)
- Live site: https://jakesirkus.github.io/CFB-NFL-Dashboards/  (`/cfb/` and `/nfl/`)
- Also published as claude.ai artifacts: CFB "FBS Team Dashboard", NFL "NFL Team Dashboard" (optional to keep updating)
- Offline single-file copies go to the user's Downloads: `CFB_Dashboard_Weeks_1-N.html` (zipped), `NFL_Dashboard_Weeks_1-N.html`

State (Oct 25, 2026): **CFB Weeks 1–8 complete (all 56 Week 8 FBS-involved games) — `out6`. NFL Weeks 1–7 complete** (nfl_v36.html).

## Layout (run scripts from inside `cfb_full/` or `nfl_full/`)

```
cfb_full/   CFB pipeline (Python). out6/ = current published CFB site (out5b = Weeks 1-7 base with regenerated Wk1-6 boxes + xPts; out5 = older Weeks 1-7) (index.html + periods/ + drivecharts/ shards)
            out4/ = Weeks 1-6 base used by rebuild_w1_7.sh. combined_raw_w1_7.pkl = all CFB play-by-play so far.
nfl_full/   NFL pipeline. nfl_v36.html = current NFL page. live_v24.html = page template (has the expected-score display), live_data.json = team list/order.
nfl_rebuild/cfb_team_list.json  FBS team list
add_ppo.py, make_github_pack.py, verify_*.js (jsdom page tests; `npm install jsdom` first)
```

## CFB weekly update
Source: the CollegeFootballData API (`/plays?year=2026&week=N`, key from the user — never commit it) converted to the (`cfbd_to_csvfmt.py ref.pkl plays.json out.pkl`)
28-column CSV-export layout (same data as the website's CSV export; Week 7 cross-checked Oct 25), or the user's CSV export.
Only add games the API marks `completed`. Week 8 example: `rebuild_w8.sh`.
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
   Also `check_fumble_text.py wN_gids.txt` (feed sometimes types a LOST fumble as 'Fumble Recovery (Own)': fix hits in flag_overrides.json).
   Known/accepted flags: 5_401866434 Kent State–Ohio (feed is missing a Kent possession) and ~21 FCS-vs-FCS feed gaps.
8. Data fixes that touch earlier weeks: see `rebuild_w1_7.sh` (patch_turnovers, regen_boxes, improve_week, fix_week_opps,
   polish_charts, chart_overrides.py). Hand-verified fixes live in `flag_overrides.json`, `yard_overrides.json`, `chart_overrides.py`.
9. Offline file: `build_offline.py out6 offline_template.html OUT.html` then `../add_ppo.py OUT.html OUT.html --js-only`.

**Scoring fixes:** `score_overrides.json` (play Id -> hand-verified scoring events, each with a `why`) for plays the feed gets wrong or
is missing (missing final FG, missing kickoff-return TD, name-format scoop-and-score…). `fix_published_finals.py OUT wk_gid,...` corrects an
already-published game's final after adding it to official_finals.json (refuses unless only chart scores change).
**Oct 25 audit:** every FBS-involved Wk 1-7 game re-pulled from the API: 508/510 site finals = CFBD official; the other two
(MTSU-Nevada wk3 27-20, Air Force-Nevada wk4 36-33) were corrected. Five Wk 7 games have since gained a few feed plays (no score change).

## NFL update
1. Download `https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.csv.gz`, `read_csv` → `to_pickle pbp_newN.pkl`.
   Schedule/finals: `https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv`.
2. `FULLWEEK=<games in the latest week> python3 -I assemble_nfl.py pbp_newN.pkl live_data.json live_v23.html nfl_vNN.html nfl_vNN.json 1 2 ... W`
   (takes ~12 min — run in the background). It runs add_ppo automatically.
3. Checks: `check_nfl_scores.py nfl_vNN.json pbp_newN.pkl` (0 problems), `check_nfl_charts.py nfl_vNN.json` (no issues),
   `node ../verify_nfl5.js nfl_vNN.html`, and confirm earlier weeks' drive charts are unchanged vs the previous build.

## Box-score expected score (xPts / deserved win %)
Model: `xpts_model.json` (fixed coefficients fitted Oct 25 on Weeks 1-7; formula in its `_doc`). `add_xpts.py cfb|nfl IN OUT`
fills games that have none (plus `--recompute gk,...` for games whose box was regenerated). NFL: assemble_nfl.py runs it with
`--all`; set `PREV=<previous nfl_vNN.html>` so unchanged games keep their values. CFB: last step of `rebuild_wN.sh`.

## Early-down success rate (Oct 26)
Box score: Overall 'Early Down Success Rate' (under Success Rate, with percentile) + 'Success Rate' in the Early Downs section,
for the full game and every quarter/half split. `add_early_sr.py` derives it from the stored early pass/rush counts and rates
(exact); `patch_early_sr_ui.py` adds the rows to a page template. Both run inside rebuild_wN.sh (CFB) and assemble_nfl.py (NFL).
Render check: `node verify_box_esr.js PAGE.html "Team"`.

## Opponent adjustments (Oct 27) — Raw / Opponent-adjusted toggle
Uses the USER'S weekly power ratings (private: build/ratings/{nfl,cfb}.json are git-ignored; after a workspace reset ask
for the model workbooks, then `read_ratings.py nfl|cfb WORKBOOK.xlsx`). Model per stat (opp_metrics.py): game-level weighted ridge,
y = mu + bOff*R_off + bDef*R_def + home + shrunk unit residuals; R = 0.25*(rating going into that week) + 0.75*(current)  (user's choice, Oct 27).
CFB uses FBS-vs-FBS games only. `opp_adjust.py LG IN OUT --blend 0.25` adds DATA.teamsAdj (rates, ranks, radar);
`opp_adjust.py LG IN /dev/null --cv` re-runs the cross-validation (lambdas in ratings/*_cv.json). `patch_oppadj_ui.py` adds the toggle.
Both run in rebuild_wN.sh / assemble_nfl.py; with no ratings file the step is skipped and the toggle hidden.
Composite adjusted Offense/Defense rank (team header chip, adjusted mode only): z-scored adjusted EPA/play 30%, early-down EPA/play 15%,
success rate 15%, EPA/drive 20%, points per opportunity 10%, explosive rate 10% (COMP in opp_adjust.py).
Second header chip: Rush O/Pass O/Rush D/Pass D ranks (RUSH: EPA/rush 35%, rush SR 20%, opportunity rate 15%, explosive runs 10%,
line yards 10%, stuff rate 10%; PASS: EPA/dropback 35%, pass SR 20%, early-down pass SR 15%, explosive passes 15%, yds/dropback 15%; RUSH/PASS in opp_adjust.py).
Schedule tab (patch_schedule_ui.py, after rankings): SOS overall (avg opp power rating) + by unit faced (opponents' composite
scores: offenses, defenses, rush/pass O, rush/pass D), rank 1 = hardest, tooltip = opponents' average rank (sosUnits in opp_adjust.py).
Rankings tab (patch_rankings_ui.py): sortable table of all adjusted composite ranks + schedule rank/avg opp rating.
Header chip also shows Schedule #N = average blended opponent rating (games used by the adjustment), 1 = hardest.
Weekly: when the user sends updated workbooks, re-run read_ratings.py before the build. Test: `node verify_adj.js PAGE "Team"`.

## Publish to GitHub
`python3 -I make_github_pack.py cfb_full/<out> nfl_full/<nfl_vNN.html> <repo checkout>` writes `index.html`, `nfl/index.html`,
`cfb/index.html` and the CFB shards merged into ~20+20 packs (`cfb/periods/pack_XX.json`, `cfb/drivecharts/pack_XX.json`).
Copy `index.html`, `cfb/`, `nfl/` into the repo, commit, push. (`cfb.html` / `nfl.html` at the repo root are just redirects to the folders — never upload page copies there.)
**WARNING: make_github_pack.py deletes DEST first (`shutil.rmtree`). Never pass the repo checkout as DEST** — build into a
scratch folder, then copy `index.html`, `nfl/`, `cfb/` into the repo (that would otherwise wipe `.git` and `build/`). (It also writes a "(3 steps)" copy for manual browser uploads — not needed with git.)

## Conventions / lessons (don't regress these)
- Reviewed plays: only the final ruling counts (text before "The previous play is under review…").
- "TOUCHDOWN nullified by penalty" is not a TD. Own fumble recovered in the end zone = offense TD, not a turnover.
- Double turnovers count a giveaway for each side. Penalty-play yardage: incomplete pass = 0; trust text when feed is 15+ off.
- Missed/blocked FGs the feed types as "Kickoff" are retyped; a missed-FG return TD shows as "Missed FG (Return TD)".
- NFL drive builder: order rows by game clock, score = running max in the unit, punt-return fumbles get a "Fumbled Punt" entry.
- Points per opportunity = points on drives with a play inside the opponent 30, summed from box scores.
- The user wants it correct first, and fast — reuse these scripts, don't rebuild from scratch; keep messages short.
