# CFB & NFL Team Dashboards — build handoff

Everything needed to keep building Jake's CFB (FBS) and NFL team dashboards, moved out of the original
Claude chat so a chat with GitHub access can build **and push** each update.

- Repo: `jakesirkus/CFB-NFL-Dashboards` (public, GitHub Pages from `main` / root)
- Live site: https://jakesirkus.github.io/CFB-NFL-Dashboards/  (`/cfb/` and `/nfl/`)
- Also published as claude.ai artifacts: CFB "FBS Team Dashboard", NFL "NFL Team Dashboard" (optional to keep updating)
- Offline single-file copies go to the user's Downloads: `CFB_Dashboard_Weeks_1-N.html` (zipped), `NFL_Dashboard_Weeks_1-N.html`

State (Nov 8, 2026): **CFB Weeks 1-10 — `out8`** (all 63 Week 10 FBS-involved games). **NFL Weeks 1-8 complete** (nfl_v40.html).

## Layout (run scripts from inside `cfb_full/` or `nfl_full/`)

```
cfb_full/   CFB pipeline (Python). out6/ = current published CFB site (out5b = Weeks 1-7 base with regenerated Wk1-6 boxes + xPts; out5 = older Weeks 1-7) (index.html + periods/ + drivecharts/ shards)
            out4/ = Weeks 1-6 base used by rebuild_w1_7.sh. combined_raw_w1_7.pkl = all CFB play-by-play so far.
nfl_full/   NFL pipeline. nfl_v36.html = current NFL page. live_v24.html = page template (has the expected-score display), live_data.json = team list/order.
nfl_rebuild/cfb_team_list.json  FBS team list
add_ppo.py, make_github_pack.py, verify_*.js (jsdom page tests; `npm install jsdom` first)
```

## CFB weekly update
Latest recipe: `cfb_full/rebuild_w10.sh` (out7 -> out8; to add late games: append their plays to combined_raw_w1_10.pkl, add ids to w10_gids.txt + official_finals.json, rerun) (builds the new week on top of the previous published out dir; all UI patches are idempotent).
Week 9 new rules: make_tables retypes 'Field Goal Good' plays whose text says NO GOOD (missed-FG return TD); week-9 entries in
score_overrides.json / flag_overrides.json / chart_overrides.py.
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
**Nov 2: refitted WITHOUT a turnover term (user: turnovers are variance, don't penalize offenses).** Old coefficients kept in
xpts_model.json `_previous_oct25`. CFB rebuild runs add_xpts --all; patch_xpts_text.py updates the tooltip wording.
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
Matchup tab (patch_matchup_ui.py, after schedule): two teams, adjusted unit ranks face off + every radar stat O-vs-D both ways;
edge = percentile gap (20+ edge, 40+ big edge); stats follow the Raw/Adjusted switch. Test: node verify_matchup.js PAGE A B.
Schedule tab (patch_schedule_ui.py, after rankings): SOS overall (avg opp power rating) + by unit faced (opponents' composite
scores: offenses, defenses, rush/pass O, rush/pass D), rank 1 = hardest, tooltip = opponents' average rank (sosUnits in opp_adjust.py).
Rankings tab (patch_rankings_ui.py): sortable table of all adjusted composite ranks + schedule rank/avg opp rating.
Header chip also shows Schedule #N = average blended opponent rating (games used by the adjustment), 1 = hardest.
Weekly: when the user sends updated workbooks, re-run read_ratings.py before the build. Test: `node verify_adj.js PAGE "Team"`.

## OL / DL line stats (Oct 27) — Lines tab, header chip 'OL # · DL #', Rankings OL/DL columns, Matchup trenches
Two halves, both opponent-adjusted with the same ridge model (opp_metrics.py / LINE in opp_adjust.py):
- Team play-by-play: sack rate (sacks allowed / generated per dropback), line yards, stuff rate, opportunity rate, power success.
- PFF player composite: `pff_fetch.py nfl|cfb 2026 WEEK...` caches weekly league-wide facets (pass_blocking, run_blocking,
  pass_rush, run D + games) in build/pff/raw/ (git-ignored; key in /home/claude/.secrets/pff_key, `Authorization: Bearer`, never commit).
  `add_line_stats.py LG IN OUT` matches PFF games to ours (teams + final score, week +-1), maps franchises, and writes box[team]['line']:
  OL (T/G/C) snap-weighted pass/run-block grades, PBE, pressure rate; DL (DI/ED) pass-rush grade, win rate, pressure rate, run-D grade, stop rate.
- Ranks: olStats/olPff/dlStats/dlPff, passPro/runBlock/passRush/runDef, overall ol/dl = 50/50 team stats + PFF. teamsAdj[t].lineVals = raw + adjusted values.
Weekly: run pff_fetch.py for the new week BEFORE the build (rebuild_wN.sh / assemble_nfl.py run add_line_stats + patch_lines_ui).
User OK'd publishing PFF-derived numbers on the public site (Oct 27). Test: `node verify_lines.js PAGE "Team A" "Team B"`.

## Off-schedule run rate (Oct 28)
FantasyPoints definition: run held under 4 yds on 1st down / under 3 on 2nd-4th, unless it converts or scores (lost fumble never converts;
kneels and 2-pt tries excluded). `add_offsched.py cfb OUT_DIR prepped_to.pkl` / `add_offsched.py nfl IN OUT PBP.pkl` adds rushing.offSchedAtt/Runs/Rate
to every box + split (asserts run count == rushAtt) and teams.offSchedPct / offSchedPctAllowed; opponent-adjusted via SEASON in opp_metrics.py.
`patch_offsched_ui.py` adds the box-score row (Rushing section) and two Leaderboard columns. Stuff % (yds<=0) is unchanged and stays in the line ranks.
Note: Rush SR / success rate on the site is EPA-based (EPA > 0), not a yards-to-go rule. Test: `node verify_offsched.js PAGE "Team"`.

## Yardage audit vs official box scores (Nov 1)
Team-game total yards checked against CFBD /games/teams (data/cfbd/teamstats_wN.json): 20+ yd misses 78 -> 27, 40+ 35 -> 6.
Fixes: yardfix.py m7 (fumble rows: offense gets its run/catch/sack yards before 'fumble', only when the feed is 15+ off and not 0),
m7b (name-format 'NN Yd Fumble Return' on the offense row -> 0), m8 (punt/kick-return fumble rows -> 0); prep.py credits the play's yards
on penalty-typed rows where the play stands; drop_plays.json (make_tables drops feed duplicates: OSU-CSU wk5 4th quarter logged twice).
regen_boxes.py no longer skips Week 7. Known leftover: OSU-CSU wk5 Oregon State still ~+129 vs official (feed broken).
Yards/Play: user wants to KEEP the inside-the-5 exclusion (asked Nov 1).

## Box-score Big Plays (Nov 1)
`add_bigplays.py cfb OUT_DIR prepped_to.pkl` / `add_bigplays.py nfl IN OUT PBP.pkl` stores every 20+ yd rush/pass (NFL: incl. scrambles) per box and
split as explosiveness.bigPlays [{q,c,y,k,td,t}] (asserts the 10+/15+ subsets reproduce explRush/explPass). `patch_bigplays_ui.py` adds
20+/30+/40+ rows (40+ split pass/rush) with hover/tap lists in the Explosiveness section. Test: `node verify_bigplays.js PAGE "Team"`.
Yardage: plays whose text credits 'gain (0)' (holding behind the run) but the feed has a big number go in yard_overrides.json (4 added Nov 1).

## Pace + totals model (CFB only, Nov 2 - user said NOT for NFL)
pace_lib.py (running-clock snap-to-snap tempo, situation-adjusted regression), add_pace.py (box/split pace + season fields, before opp_adjust),
totals_model.py (ridge: game possessions = pace_A + pace_B; expected points/drive = off_A + def_B + home; w=0 = deserved points chosen by
walk-forward backtest; `python3 -I totals_model.py cfb` re-runs it; FCS-opponent terms + walk-forward bias correction `calib`; FCS games weighted 5% and FCS rated the worst possible opponent; anchored to the user power ratings via totals_model.fit_rated, Nov 2), add_totals.py (DATA.meta.totals; CFB home edge from FBS-vs-FBS games),
patch_pace_ui.py (box rows, team tiles, leaderboard columns, Matchup 'Projected score & pace' card + Site picker). Vegas totals for the backtest:
/home/claude/data/cfbd/lines_wN.json (CFBD /lines). Test: node verify_pace.js PAGE A B TEAM.

## Publish to GitHub
`python3 -I make_github_pack.py cfb_full/<out> nfl_full/<nfl_vNN.html> <repo checkout>` writes `index.html`, `nfl/index.html`,
`cfb/index.html` and the CFB shards merged into ~20+20 packs (`cfb/periods/pack_XX.json`, `cfb/drivecharts/pack_XX.json`).
Copy `index.html`, `cfb/`, `nfl/` into the repo, commit, push. (`cfb.html` / `nfl.html` at the repo root are just redirects to the folders — never upload page copies there.)
**WARNING: make_github_pack.py deletes DEST first (`shutil.rmtree`). Never pass the repo checkout as DEST** — build into a
scratch folder, then copy `index.html`, `nfl/`, `cfb/` into the repo (that would otherwise wipe `.git` and `build/`). (It also writes a "(3 steps)" copy for manual browser uploads — not needed with git.)

### NEXT (user asked to do this Nov 4): early-down vs late-down success rate in the deserved score
Split success rate into early-down (1st/2nd) and late-down (3rd/4th) terms with separate weights; test on the 10 NFL seasons
(add early/late success + garbage shifts to nfl_hist_features.py, rerun ~35 min, extend nfl_xpts_grid.py) and on CFB 2026; adopt only if
forward prediction improves; same structure for both leagues. Also pending: CFB Week 10 update (Ohio-Akron was Tue Nov 3).

### Deserved score VERSION 3 — the user's "option 4" (Nov 3 2026, CURRENT; supersedes the two notes below)
User's philosophy: down-to-down success is the core; reward explosives but treat long TDs as partly variance; turnovers are variance
(neutral: no penalty, no bonus). Implementation: xpts_v3.py + add_xpts.py (rewritten) + xpts_model.json version 3:
  xPts = b0 + b1*drives + drives*(b2*avail + b3*success + b4*explosive)
  avail = mean over drives of min(capped yards / yards-to-goal, 1), each play's gain capped at 20 yds; a turnover drive counts what it gained
  (like a punt); garbage time faded (NFL win prob 90->98%; CFB margin 43/37/27/22 +/-7), small-sample blend (40 plays / 6 drives).
  Box field xptsInputs {av, sr, ex}. NFL: add_xpts needs --pbp (assemble_nfl.py passes it); CFB reads cfb_full/prepped_to.pkl.
NFL weights fitted on 2016-2025 nflverse pbp (nfl_hist_features.py / nfl_capped_yards.py -> /home/claude/data/nflhist; grid test
nfl_xpts_grid.py, leave-one-season-out, forward next-game MAE 10.344 vs 10.458 old). Turnover-as-average-drive versions tested WORSE and
were rejected by the user (they'd reward turning it over vs punting). CFB weights fitted on 2026 wks 1-9 (predict MAE 15.87 vs 15.96).
Finding: NFL actual point margin predicts next games about as well as any deserved score; 50/50 mix best (10.21).

### Deserved score: turnover-neutral drives (Nov 3 2026)
xpts_model.json 'availInput' = 'availYardsPctNoTO': add_xpts.py fills box drives.availYardsPctNoTO from the drive charts — a drive that
ENDS in an interception / lost fumble counts as the better of its own available-yards share and the team's average share on its other
drives (a turnover can't hurt the offense; yards gained before it still count). Displayed Available Yards % is unchanged. Refitted
CFB+NFL; prediction of other games' margins unchanged (fit_xpts.py compares variants A-F). add_totals re-run on the new values.
CFB needs out7/drivecharts/*.json next to the page when add_xpts runs (it is, inside rebuild_wN.sh).
CFB GARBAGE TIME (Nov 3 2026, xpts_model cfb 'garbage'): success rate, explosive rate and available-yards share for the deserved score
come from competitive plays/drives (score margin faded out around 43/37/27/22 pts in Q1-Q4, +/-7 fade; competitive rates blended toward
full-game rates with 40 plays / 6 drives of weight). build/garbage_time.py; add_xpts stores box xptsGarbageAdj and needs
cfb_full/prepped_to.pkl. Tested: CFB prediction slightly better (~80% confidence); NFL showed no gain -> NFL not applied (revisit with a
multi-season NFL refit).

### Redesign (`/new/`, Nov 3 2026) — run on EVERY publish after copying the pages into the repo
The dark broadcast redesign + Scoreboard tab (games by week -> full box score) lives at `new/` beside the original site until
the user approves switching. It is a presentation-only patch over the finished pages (stats/logic unchanged):
`python3 -I build/patch_redesign.py nfl nfl/index.html new/nfl/index.html`
`python3 -I build/patch_redesign.py cfb cfb/index.html new/cfb/index.html ../../cfb/`   (CFB shards are read from the live /cfb/ folder)
Team colors/abbreviations: build/redesign_colors.json (CFBD /teams colors + NFL list). `new/index.html` = dark landing page.
Run the jsdom tests against `new/*/index.html` too. To switch over later: point the root links at new/ (or copy new/* up), keep the old pages for rollback.

## Conventions / lessons (don't regress these)
- Reviewed plays: only the final ruling counts (text before "The previous play is under review…").
- "TOUCHDOWN nullified by penalty" is not a TD. Own fumble recovered in the end zone = offense TD, not a turnover.
- Double turnovers count a giveaway for each side. Penalty-play yardage: incomplete pass = 0; trust text when feed is 15+ off.
- Missed/blocked FGs the feed types as "Kickoff" are retyped; a missed-FG return TD shows as "Missed FG (Return TD)".
- NFL drive builder: order rows by game clock, score = running max in the unit, punt-return fumbles get a "Fumbled Punt" entry.
- Points per opportunity = points on drives with a play inside the opponent 30, summed from box scores.
- The user wants it correct first, and fast — reuse these scripts, don't rebuild from scratch; keep messages short.
