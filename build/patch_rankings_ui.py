"""Add a 'Rankings' tab: every team's opponent-adjusted Offense/Defense, Rush/Pass O/D ranks and schedule
(rank + average opponent rating), sortable, with conference filter + search. Reads DATA.teamsAdj, so it shows the
same numbers whichever Raw/Adjusted mode is on; the tab hides itself if there are no adjustments. Idempotent.
usage: patch_rankings_ui.py PAGE.html [PAGE.html ...]"""
import sys, re
BTN = '<button class="tab-btn" id="tabBtnRankings" data-target="rankings" role="tab" aria-selected="false">Rankings</button>'
VIEW = '''<div data-view="rankings">
    <div class="lb-controls">
      <div class="control">
        <label for="rkConfFilter">Conference</label>
        <select id="rkConfFilter"></select>
      </div>
      <div class="control">
        <label for="rkSearch">Search</label>
        <input id="rkSearch" placeholder="Filter by team name…" autocomplete="off">
      </div>
    </div>
    <div class="scope-note" id="rkNote" style="max-width:none"></div>
    <div class="lb-table-wrap">
      <table class="lb" id="rkTable">
        <thead><tr id="rkHead"></tr></thead>
        <tbody id="rkBody"></tbody>
      </table>
    </div>
  </div>

  '''
JS = """
  // ---------- Rankings tab (opponent-adjusted composite ranks + schedule) ----------
  var RK_COLS = [
    { key:'pos', label:'#', type:'pos' },
    { key:'team', label:'Team', type:'text' },
    { key:'conf', label:'Conf', type:'text' },
    { key:'record', label:'W-L', type:'text' },
    { key:'off', label:'Adj Offense', type:'rank' }, { key:'def', label:'Adj Defense', type:'rank' },
    { key:'rushOff', label:'Rush O', type:'rank' }, { key:'passOff', label:'Pass O', type:'rank' },
    { key:'rushDef', label:'Rush D', type:'rank' }, { key:'passDef', label:'Pass D', type:'rank' },
    { key:'sos', label:'Schedule', type:'rank' }, { key:'opp', label:'Avg Opp Rating', type:'num1' }
  ];
  var rkSort = { key:'off', dir:1 };
  var rkConf = document.getElementById('rkConfFilter'), rkSearch = document.getElementById('rkSearch');
  (function(){ var o=document.createElement('option'); o.value='all'; o.textContent='All conferences'; rkConf.appendChild(o);
    confs.forEach(function(c){ var x=document.createElement('option'); x.value=c; x.textContent=c; rkConf.appendChild(x); }); rkConf.value='all'; })();
  function renderRankings(){
    var A = DATA.teamsAdj; if(!A) return;
    var o = (DATA.meta && DATA.meta.oppAdj) || {};
    document.getElementById('rkNote').textContent = 'Opponent-adjusted composite ranks (1 = best; hover a column for its recipe). Schedule: 1 = hardest, by average opponent power rating. Ratings through Week '+(o.ratingsThroughWeek||'?')+'.';
    var tr = document.getElementById('rkHead'); tr.innerHTML='';
    var TIPS = { off:'EPA/play 30%, early-down EPA/play 15%, success rate 15%, EPA/drive 20%, points per opportunity 10%, explosive rate 10%',
      def:'Same recipe, allowed', rushOff:'EPA/rush 35%, rush SR 20%, opportunity rate 15%, explosive runs 10%, line yards 10%, stuff rate 10%',
      passOff:'EPA/dropback 35%, pass SR 20%, early-down pass SR 15%, explosive passes 15%, yards/dropback 15%', rushDef:'Rush recipe, allowed', passDef:'Pass recipe, allowed',
      sos:'Average opponent power rating over the games used, 1 = hardest', opp:'Average opponent power rating (points vs average)' };
    RK_COLS.forEach(function(col){
      var th=document.createElement('th'); th.textContent=col.label; if(TIPS[col.key]) th.title=TIPS[col.key];
      if(col.key===rkSort.key){ th.classList.add('sorted'); var ar=document.createElement('span'); ar.className='arrow'; ar.textContent=rkSort.dir===1?'\\u25B2':'\\u25BC'; th.appendChild(ar); }
      if(col.type==='rank' || col.type==='num1'){ th.addEventListener('click', function(){
        if(rkSort.key===col.key) rkSort.dir*=-1; else { rkSort.key=col.key; rkSort.dir = col.type==='num1' ? -1 : 1; }
        renderRankings(); }); }
      tr.appendChild(th);
    });
    var q=(rkSearch.value||'').toLowerCase(), cf=rkConf.value;
    var rows = teamKeys.filter(function(k){ return A[k] && A[k].adjRank && (cf==='all' || DATA.teams[k].confLabel===cf) && (!q || k.toLowerCase().indexOf(q)>-1); })
      .map(function(k){ var r=A[k].adjRank, t=DATA.teams[k];
        return { team:k, conf:t.confLabel, record:t.wins+'-'+t.losses, off:r.off, def:r.def, rushOff:r.rushOff, passOff:r.passOff,
                 rushDef:r.rushDef, passDef:r.passDef, sos:A[k].sos?A[k].sos.rank:null, opp:A[k].sos?A[k].sos.avgOppRating:null }; });
    rows.sort(function(a,b){ var av=a[rkSort.key], bv=b[rkSort.key];
      av=(av===null||av===undefined)?Infinity*rkSort.dir:av; bv=(bv===null||bv===undefined)?Infinity*rkSort.dir:bv; return rkSort.dir*(av-bv); });
    var body=document.getElementById('rkBody'); body.innerHTML='';
    rows.forEach(function(row,i){ var r=document.createElement('tr');
      RK_COLS.forEach(function(col){ var td=document.createElement('td');
        if(col.type==='pos'){ td.className='rk'; td.textContent=i+1; }
        else if(col.type==='text'){ td.textContent=row[col.key]; }
        else if(col.type==='num1'){ td.className='num'; td.textContent=row[col.key]===null?'\\u2014':row[col.key].toFixed(1); }
        else { td.className='num'; td.textContent=row[col.key]===null||row[col.key]===undefined?'\\u2014':row[col.key]; }
        r.appendChild(td); });
      body.appendChild(r); });
  }
  rkConf.addEventListener('change', renderRankings);
  rkSearch.addEventListener('input', renderRankings);
  if(!DATA.teamsAdj){ document.getElementById('tabBtnRankings').style.display='none'; }
"""
for p in sys.argv[1:]:
    s = open(p).read()
    if 'id="tabBtnRankings"' in s: print(p, 'already patched'); continue
    m = re.search(r'(<button class="tab-btn" id="tabBtnLeaderboard"[^>]*>Leaderboard</button>)', s); assert m, (p, 'tab anchor')
    s = s[:m.end()] + '\n      ' + BTN + s[m.end():]
    a = '<div data-view="leaderboard">'; assert s.count(a) == 1, (p, 'view anchor')
    s = s.replace(a, VIEW + a)
    a = "var tabBtns = [document.getElementById('tabBtnTeam'), document.getElementById('tabBtnLeaderboard')];"
    assert s.count(a) == 1, (p, 'tabBtns anchor')
    s = s.replace(a, "var tabBtns = [document.getElementById('tabBtnTeam'), document.getElementById('tabBtnLeaderboard'), document.getElementById('tabBtnRankings')];")
    a = "leaderboard: document.querySelector('[data-view=\"leaderboard\"]') };"
    assert s.count(a) == 1, (p, 'views anchor')
    s = s.replace(a, "leaderboard: document.querySelector('[data-view=\"leaderboard\"]'), rankings: document.querySelector('[data-view=\"rankings\"]') };")
    a = "if(target==='leaderboard') renderLeaderboard();"
    assert s.count(a) == 1, (p, 'setTab anchor')
    s = s.replace(a, a + " if(target==='rankings') renderRankings();")
    a = "\n  confFilter.value = 'all';"
    assert s.count(a) == 1, (p, 'init anchor')
    s = s.replace(a, JS + a)
    open(p, 'w').write(s); print(p, 'patched')
