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
CHIP_HTML = '\n        <span class="chip" id="adjRankChip" hidden></span>'
CHIP_JS = """
    var arc = document.getElementById('adjRankChip');
    if(arc){ if(t.adjRank){ arc.hidden = false;
        arc.textContent = 'Adj. Offense #'+t.adjRank.off+' \u00b7 Adj. Defense #'+t.adjRank.def+(t.sos?' \u00b7 Schedule #'+t.sos.rank:'')+' (of '+total+')';
        arc.title = 'Opponent-adjusted composite: EPA/play 30%, early-down EPA/play 15%, success rate 15%, EPA/drive 20%, points per opportunity 10%, explosive rate 10%'+(t.sos?'. Schedule #'+t.sos.rank+' = average opponent power rating '+t.sos.avgOppRating.toFixed(1)+' (1 = hardest)':'');
      } else { arc.hidden = true; } }"""
UPGRADES = [("""arc.textContent = 'Adj. Offense #'+t.adjRank.off+' \u00b7 Adj. Defense #'+t.adjRank.def+' (of '+total+')';""",
              """arc.textContent = 'Adj. Offense #'+t.adjRank.off+' \u00b7 Adj. Defense #'+t.adjRank.def+(t.sos?' \u00b7 Schedule #'+t.sos.rank:'')+' (of '+total+')';"""),
            ("points per opportunity 10%, explosive rate 10%';",
             "points per opportunity 10%, explosive rate 10%'+(t.sos?'. Schedule #'+t.sos.rank+' = average opponent power rating '+t.sos.avgOppRating.toFixed(1)+' (1 = hardest)':'');")]
UNIT_HTML = '\n        <span class="chip" id="adjUnitChip" hidden></span>'
UNIT_JS = """
    var auc = document.getElementById('adjUnitChip');
    if(auc){ if(t.adjRank && t.adjRank.rushOff){ auc.hidden = false;
        auc.textContent = 'Rush O #'+t.adjRank.rushOff+' \u00b7 Pass O #'+t.adjRank.passOff+' \u00b7 Rush D #'+t.adjRank.rushDef+' \u00b7 Pass D #'+t.adjRank.passDef;
        auc.title = 'Opponent-adjusted. Rush: EPA/rush 35%, rush success rate 20%, opportunity rate 15%, explosive run rate 10%, line yards 10%, stuff rate 10%. Pass: EPA/dropback 35%, pass success rate 20%, early-down pass success rate 15%, explosive pass rate 15%, yards/dropback 15%';
      } else { auc.hidden = true; } }"""
def unit_chip(s, p):                  # rush/pass offense/defense ranks, second header chip (Oct 27)
    if 'id="adjUnitChip"' in s: return s
    a = '<span class="chip" id="adjRankChip" hidden></span>'
    assert s.count(a) == 1, (p, 'rank chip html anchor')
    s = s.replace(a, a + UNIT_HTML)
    j = "      } else { arc.hidden = true; } }"
    assert s.count(j) == 1, (p, 'rank chip js anchor')
    return s.replace(j, j + UNIT_JS)
def chip(s, p):                       # composite adjusted off/def rank chip in the team header (Oct 27)
    if 'id="adjRankChip"' in s: return s
    a = '<span class="chip" id="teamGp">\u2014</span>' if '<span class="chip" id="teamGp">\u2014</span>' in s else '<span class="chip" id="teamGp">—</span>'
    assert s.count(a) == 1, (p, 'gp chip anchor')
    s = s.replace(a, a + CHIP_HTML)
    j = "document.getElementById('teamGp').textContent = t.gp + (t.gp===1?' game':' games');"
    assert s.count(j) == 1, (p, 'gp js anchor')
    return s.replace(j, j + CHIP_JS)
for p in sys.argv[1:]:
    s = open(p).read()
    if 'id="adjToggle"' in s:
        s2 = chip(s, p)
        for o, n in UPGRADES: s2 = s2.replace(o, n)
        s2 = unit_chip(s2, p)
        if s2 != s: open(p, 'w').write(s2); print(p, 'rank chip added')
        else: print(p, 'already patched')
        continue
    m = re.search(r'id="tabBtnLeaderboard"[^>]*>Leaderboard</button>\s*</div>', s); assert m, (p, 'tabs anchor')
    s = s[:m.end()] + TOGGLE + s[m.end():]
    m = re.search(r'<div class="scope-note" id="scopeNote">.*?</div>', s, re.S); assert m, (p, 'scope note anchor')
    s = s[:m.end()] + NOTE + s[m.end():]
    anchor = "\n  confFilter.value = 'all';"
    assert s.count(anchor) == 1, (p, 'init anchor', s.count(anchor))
    s = s.replace(anchor, JS + anchor)
    s = chip(s, p)
    for o, n in UPGRADES: s = s.replace(o, n)
    s = unit_chip(s, p)
    open(p, 'w').write(s); print(p, 'patched')
