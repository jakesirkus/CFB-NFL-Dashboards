"""Add a 'Schedule' tab: each team's strength of schedule overall (average opponent power rating) and by unit faced
(opponent offenses, defenses, rush/pass offenses, rush/pass defenses), as ranks 1 = hardest; hover a cell for the
opponents' average rank. Reads DATA.teamsAdj (opp_adjust.py); hides itself if missing. Run after patch_rankings_ui.py.
Idempotent. usage: patch_schedule_ui.py PAGE.html [PAGE.html ...]"""
import sys, re
BTN = '<button class="tab-btn" id="tabBtnSchedule" data-target="schedule" role="tab" aria-selected="false">Schedule</button>'
VIEW = '''<div data-view="schedule">
    <div class="lb-controls">
      <div class="control">
        <label for="scConfFilter">Conference</label>
        <select id="scConfFilter"></select>
      </div>
      <div class="control">
        <label for="scSearch">Search</label>
        <input id="scSearch" placeholder="Filter by team name…" autocomplete="off">
      </div>
    </div>
    <div class="scope-note" id="scNote" style="max-width:none"></div>
    <div class="lb-table-wrap">
      <table class="lb" id="scTable">
        <thead><tr id="scHead"></tr></thead>
        <tbody id="scBody"></tbody>
      </table>
    </div>
  </div>

  '''
JS = """
  // ---------- Schedule tab (strength of schedule overall and by unit faced) ----------
  var SC_COLS = [
    { key:'pos', label:'#', type:'pos' }, { key:'team', label:'Team', type:'text' }, { key:'conf', label:'Conf', type:'text' },
    { key:'record', label:'W-L', type:'text' }, { key:'games', label:'Games', type:'int' },
    { key:'overall', label:'Overall', type:'rank', tip:'Average opponent power rating, 1 = hardest' },
    { key:'oppRating', label:'Avg Opp Rating', type:'num1', tip:'Average opponent power rating (points vs average)' },
    { key:'oppOff', label:'Opp Offenses', type:'rank', tip:'Quality of offenses faced (matters for your defense)' },
    { key:'oppDef', label:'Opp Defenses', type:'rank', tip:'Quality of defenses faced (matters for your offense)' },
    { key:'oppRushOff', label:'Opp Rush O', type:'rank', tip:'Rushing offenses faced (matters for your run defense)' },
    { key:'oppPassOff', label:'Opp Pass O', type:'rank', tip:'Passing offenses faced (matters for your pass defense)' },
    { key:'oppRushDef', label:'Opp Rush D', type:'rank', tip:'Run defenses faced (matters for your rushing offense)' },
    { key:'oppPassDef', label:'Opp Pass D', type:'rank', tip:'Pass defenses faced (matters for your passing offense)' }
  ];
  var scSort = { key:'overall', dir:1 };
  var scConf = document.getElementById('scConfFilter'), scSearch = document.getElementById('scSearch');
  (function(){ var o=document.createElement('option'); o.value='all'; o.textContent='All conferences'; scConf.appendChild(o);
    confs.forEach(function(c){ var x=document.createElement('option'); x.value=c; x.textContent=c; scConf.appendChild(x); }); scConf.value='all'; })();
  function renderSchedule(){
    var A = DATA.teamsAdj; if(!A) return;
    var o = (DATA.meta && DATA.meta.oppAdj) || {};
    document.getElementById('scNote').textContent = 'Strength of schedule so far, 1 = hardest. Overall uses opponents\\u2019 power ratings; the unit columns use opponents\\u2019 opponent-adjusted composite scores (same as the Rankings tab). Hover a cell for the opponents\\u2019 average rank.' + (o.note && o.note.indexOf('FBS-vs-FBS')>-1 ? ' FBS-vs-FBS games only.' : '');
    var tr = document.getElementById('scHead'); tr.innerHTML='';
    SC_COLS.forEach(function(col){
      var th=document.createElement('th'); th.textContent=col.label; if(col.tip) th.title=col.tip;
      if(col.key===scSort.key){ th.classList.add('sorted'); var ar=document.createElement('span'); ar.className='arrow'; ar.textContent=scSort.dir===1?'\\u25B2':'\\u25BC'; th.appendChild(ar); }
      if(col.type==='rank' || col.type==='num1' || col.type==='int'){ th.addEventListener('click', function(){
        if(scSort.key===col.key) scSort.dir*=-1; else { scSort.key=col.key; scSort.dir = col.type==='rank' ? 1 : -1; }
        renderSchedule(); }); }
      tr.appendChild(th);
    });
    var q=(scSearch.value||'').toLowerCase(), cf=scConf.value;
    var rows = teamKeys.filter(function(k){ return A[k] && A[k].sosUnits && (cf==='all' || DATA.teams[k].confLabel===cf) && (!q || k.toLowerCase().indexOf(q)>-1); })
      .map(function(k){ var u=A[k].sosUnits, t=DATA.teams[k], row={ team:k, conf:t.confLabel, record:t.wins+'-'+t.losses, games:u.games,
          overall:A[k].sos?A[k].sos.rank:null, oppRating:A[k].sos?A[k].sos.avgOppRating:null, _avg:{} };
        ['oppOff','oppDef','oppRushOff','oppPassOff','oppRushDef','oppPassDef'].forEach(function(c){ row[c]=u[c]?u[c].rank:null; row._avg[c]=u[c]?u[c].avgOppRank:null; });
        return row; });
    rows.sort(function(a,b){ var av=a[scSort.key], bv=b[scSort.key];
      av=(av===null||av===undefined)?Infinity*scSort.dir:av; bv=(bv===null||bv===undefined)?Infinity*scSort.dir:bv; return scSort.dir*(av-bv); });
    var body=document.getElementById('scBody'); body.innerHTML='';
    rows.forEach(function(row,i){ var r=document.createElement('tr');
      SC_COLS.forEach(function(col){ var td=document.createElement('td'), v=row[col.key];
        if(col.type==='pos'){ td.className='rk'; td.textContent=i+1; }
        else if(col.type==='text'){ td.textContent=v; }
        else if(col.type==='num1'){ td.className='num'; td.textContent=v===null?'\\u2014':v.toFixed(1); }
        else { td.className='num'; td.textContent=(v===null||v===undefined)?'\\u2014':v;
          if(row._avg[col.key]!=null) td.title='Opponents\\u2019 average '+col.label.replace('Opp ','')+' rank: '+row._avg[col.key].toFixed(1); }
        r.appendChild(td); });
      body.appendChild(r); });
  }
  scConf.addEventListener('change', renderSchedule);
  scSearch.addEventListener('input', renderSchedule);
  if(!DATA.teamsAdj){ document.getElementById('tabBtnSchedule').style.display='none'; }
"""
for p in sys.argv[1:]:
    s = open(p).read()
    if 'id="tabBtnSchedule"' in s: print(p, 'already patched'); continue
    assert 'id="tabBtnRankings"' in s, (p, 'run patch_rankings_ui.py first')
    m = re.search(r'(<button class="tab-btn" id="tabBtnRankings"[^>]*>Rankings</button>)', s); assert m, (p, 'tab anchor')
    s = s[:m.end()] + '\n      ' + BTN + s[m.end():]
    a = '<div data-view="leaderboard">'; assert s.count(a) == 1, (p, 'view anchor')
    s = s.replace(a, VIEW + a)
    a = "document.getElementById('tabBtnRankings')];"
    assert s.count(a) == 1, (p, 'tabBtns anchor')
    s = s.replace(a, "document.getElementById('tabBtnRankings'), document.getElementById('tabBtnSchedule')];")
    a = "rankings: document.querySelector('[data-view=\"rankings\"]') };"
    assert s.count(a) == 1, (p, 'views anchor')
    s = s.replace(a, "rankings: document.querySelector('[data-view=\"rankings\"]'), schedule: document.querySelector('[data-view=\"schedule\"]') };")
    a = "if(target==='rankings') renderRankings();"
    assert s.count(a) == 1, (p, 'setTab anchor')
    s = s.replace(a, a + " if(target==='schedule') renderSchedule();")
    a = "\n  confFilter.value = 'all';"
    assert s.count(a) == 1, (p, 'init anchor')
    s = s.replace(a, JS + a)
    open(p, 'w').write(s); print(p, 'patched')
