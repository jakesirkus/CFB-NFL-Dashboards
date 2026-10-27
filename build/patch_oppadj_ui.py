"""Add the Raw / Opponent-adjusted toggle to a dashboard page (CFB or NFL). Needs DATA.teamsAdj (opp_adjust.py);
the toggle hides itself when that is missing. Switches the season numbers, ranks, radar and leaderboard; box scores,
game logs and counting stats (yards, TDs, sacks, turnovers) stay raw. Raw is the default. Idempotent.
usage: patch_oppadj_ui.py PAGE.html [PAGE.html ...]"""
import sys, re
TOGGLE = ('\n    <div class="tabs adj-toggle" role="group" aria-label="Season numbers" id="adjToggle">'
          '<button class="tab-btn active" id="modeRaw" type="button">Raw</button>'
          '<button class="tab-btn" id="modeAdj" type="button" title="Season numbers adjusted for opponent strength">Opponent-adjusted</button></div>')
NOTE = '\n      <div class="scope-note" id="adjNote" hidden></div>'
JS = """
  // ---------- Raw / Opponent-adjusted toggle ----------
  var adjMode = false;
  function setMode(adj){
    adjMode = !!adj && !!DATA.teamsAdj;
    teams = adjMode ? DATA.teamsAdj : DATA.teams;
    document.getElementById('modeRaw').classList.toggle('active', !adjMode);
    document.getElementById('modeAdj').classList.toggle('active', adjMode);
    var note = document.getElementById('adjNote');
    note.hidden = !adjMode;
    if(adjMode){ var o = (DATA.meta && DATA.meta.oppAdj) || {};
      note.textContent = 'Opponent-adjusted: ' + (o.note || '') + ' Ratings through Week ' + (o.ratingsThroughWeek || '?') +
        '. Rates, ranks and the radar are adjusted; counting stats (yards, TDs, sacks, turnovers), game logs and box scores stay raw.'; }
    var v = teamInput.value; if(teams[v]) renderTeam(v);
    if(views.leaderboard.classList.contains('active')) renderLeaderboard();
  }
  if(!DATA.teamsAdj){ document.getElementById('adjToggle').style.display = 'none'; }
  document.getElementById('modeRaw').addEventListener('click', function(){ setMode(false); });
  document.getElementById('modeAdj').addEventListener('click', function(){ setMode(true); });
"""
for p in sys.argv[1:]:
    s = open(p).read()
    if 'id="adjToggle"' in s: print(p, 'already patched'); continue
    m = re.search(r'id="tabBtnLeaderboard"[^>]*>Leaderboard</button>\s*</div>', s); assert m, (p, 'tabs anchor')
    s = s[:m.end()] + TOGGLE + s[m.end():]
    m = re.search(r'<div class="scope-note" id="scopeNote">.*?</div>', s, re.S); assert m, (p, 'scope note anchor')
    s = s[:m.end()] + NOTE + s[m.end():]
    anchor = "\n  confFilter.value = 'all';"
    assert s.count(anchor) == 1, (p, 'init anchor', s.count(anchor))
    s = s.replace(anchor, JS + anchor)
    open(p, 'w').write(s); print(p, 'patched')
