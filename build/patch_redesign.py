"""Redesign ("v2"): dark broadcast look + a Scoreboard tab (every game of a week as score cards; click = the full box score).
Pure presentation layer over the finished pages from make_github_pack.py; all stats, tabs and box-score logic are unchanged.
  - fonts Oswald/IBM Plex -> Barlow Condensed/Inter; forced dark palette via the page's own CSS tokens; wider layout
  - Scoreboard tab (default view): week chips, conference filter (CFB), team search, sort (A-Z, closest, highest scoring,
    biggest box-score luck); cards show team-colored badges, score, deserved (box-score) score and deserved win %
  - team colors (redesign_colors.json: CFBD team colors / NFL) on the team banner and the box-score header
  - CFB: period/drive-chart shards are fetched from SHARD_BASE (the live /cfb/ folder) so no second copy is needed
usage: patch_redesign.py cfb|nfl IN.html OUT.html [SHARD_BASE]"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
LG, SRC, DST = sys.argv[1:4]
BASE = sys.argv[4] if len(sys.argv) > 4 else ''
TAG = '<script id="dashboard-data" type="application/json">'
s = open(SRC).read()
a = s.index(TAG); b = s.index('</script>', a)
head, data, tail = s[:a], s[a:b], s[b:]
if 'id="v2theme"' in head + tail: sys.exit(f'{SRC}: already patched')
COL = json.load(open(os.path.join(HERE, 'redesign_colors.json')))[LG]

def rep(txt, old, new, n=1, where=''):
    c = txt.count(old)
    assert c == n, (where, old[:70], c)
    return txt.replace(old, new)

# ---------- fonts ----------
FONT_OLD = '<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">'
FONT_NEW = '<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
head = rep(head, FONT_OLD, FONT_NEW, where='font link')
for part in ('head', 'tail'):
    t = locals()[part].replace('font-family:"Oswald";', 'font-family:"Barlow Condensed","Arial Narrow",sans-serif;').replace('"Oswald"', '"Barlow Condensed"')
    t = t.replace('"IBM Plex Sans"', 'Inter').replace("'IBM Plex Sans'", 'Inter')
    if part == 'head': head = t
    else: tail = t

# ---------- theme ----------
CSS = r"""
<style id="v2theme">
  :root:not(#v2x), :root:not(#v2x)[data-theme="light"], :root:not(#v2x)[data-theme="dark"]{
    color-scheme: dark;
    --page:#0A0E16; --surface:#111724; --surface-2:#182131; --ink:#F3F5F9; --ink-2:#C9D1DE; --ink-muted:#94A0B4;
    --line:#222C3E; --line-strong:#33405A; --off:#4C9AFF; --off-wash:#12233A; --def:#FF7A3D; --def-wash:#2C1A10;
    --good:#2FBF71; --warning:#FFB020; --critical:#F0625A; --accent:#FFB020;
    --shadow: 0 1px 2px rgba(0,0,0,0.45), 0 1px 1px rgba(0,0,0,0.3);
  }
  html, body{ background:#0A0E16; }
  body{ font-family:Inter, system-ui, -apple-system, sans-serif; padding-inline:16px; }
  .wrap{ max-width:1320px; }
  h1,h2,h3{ font-family:"Barlow Condensed", system-ui, sans-serif; letter-spacing:0.02em; }
  h3{ text-transform:uppercase; letter-spacing:0.05em; }
  .eyebrow{ color:var(--accent); letter-spacing:0.14em; }

  /* broadcast header */
  .topbar{ background:#0D121C; border:1px solid var(--line); border-radius:18px; padding:18px 22px; align-items:center; }
  .titleblock h1{ font-size:40px; font-weight:700; text-transform:uppercase; line-height:1; }
  .v2-league{ display:flex; gap:4px; background:#111724; border:1px solid var(--line); border-radius:999px; padding:3px; width:fit-content; margin-bottom:10px; }
  .v2-league a{ min-height:32px; display:flex; align-items:center; padding:0 14px; border-radius:999px; font-weight:700; font-size:12px; letter-spacing:0.08em; color:#B7C0CF; text-decoration:none; }
  .v2-league a[aria-current="page"]{ background:var(--accent); color:#1A1300; }
  .tabs{ background:transparent; border:none; padding:0; gap:2px; flex-wrap:wrap; }
  .tabs[role="tablist"] .tab-btn{ text-transform:uppercase; letter-spacing:0.06em; font-size:13px; padding:10px 14px; border-radius:0; color:var(--ink-muted); box-shadow:none; min-height:44px; }
  .tabs[role="tablist"] .tab-btn:hover{ color:var(--ink); }
  .tabs[role="tablist"] .tab-btn.active{ background:transparent; color:var(--ink); box-shadow:inset 0 -3px 0 var(--accent); }
  .adj-toggle{ background:#111724; border:1px solid var(--line); border-radius:999px; padding:3px; }
  .adj-toggle .tab-btn{ border-radius:999px; }
  .adj-toggle .tab-btn.active{ background:var(--accent); color:#1A1300; }
  .control select, .control input{ background:#111724; border-color:var(--line-strong); border-radius:10px; min-height:40px; }
  .control select:focus-visible, .control input:focus-visible, .tab-btn:focus-visible{ outline:2px solid var(--accent); }

  /* team banner */
  .banner{ border-top:4px solid var(--team, var(--accent)); border-radius:16px; }
  .banner-id h2{ font-size:40px; text-transform:uppercase; display:flex; align-items:center; gap:14px; }
  .banner-id h2[data-abb]::before{ content:attr(data-abb); font-size:20px; letter-spacing:0.04em; padding:6px 10px; border-radius:8px;
    background:var(--team, #33405A); color:var(--team-fg, #fff); box-shadow:inset 0 0 0 1px rgba(255,255,255,0.16); }
  .meta-figure .v{ font-size:32px; }
  .tile .v{ font-size:26px; }
  .tile-grid, .compare, .gauge-card, .radar-card, .game-card, .lb-table-wrap, .mt-card{ border-radius:14px; }
  .dc-rslt.blue{ background:#2563EB; color:#fff; }
  .dc-rslt.red{ background:#F0625A; color:#1A0503; }
  .gc-result.W{ background:#2FBF71; color:#04140B; } .gc-result.L{ background:#F0625A; color:#1A0503; }
  .stackbar .seg{ color:#0A0E16; }
  table.lb th{ background:#141C2A; }
  table.lb tbody tr:hover{ background:#151D2B; }

  /* box score */
  .bs-overlay{ background:rgba(3,5,10,0.78); padding:20px 12px; }
  .bs-modal{ max-width:1240px; background:#0D121C; border:1px solid var(--line); border-radius:20px; padding:22px 24px 28px; }
  .bs-title h2{ font-size:28px; text-transform:uppercase; }
  .bs-close{ min-height:40px; border-radius:10px; }
  .bs-score{ background:#111A28; border:1px solid var(--line); border-radius:16px; padding:16px 18px; gap:12px 16px; align-items:center; }
  .bs-score .team{ font-size:24px; text-transform:uppercase; display:inline-flex; align-items:center; gap:10px; }
  .bs-score .pts{ font-size:52px; line-height:0.9; }
  .bs-score .xscore{ flex-basis:100%; margin-left:0; font-size:13px; opacity:1; color:var(--accent); }
  .v2-badge{ display:inline-flex; align-items:center; justify-content:center; min-width:46px; height:32px; padding:0 8px; border-radius:7px; font-family:"Barlow Condensed",sans-serif;
    font-weight:700; font-size:16px; letter-spacing:0.04em; box-shadow:inset 0 0 0 1px rgba(255,255,255,0.16); }
  .bs-period{ border-radius:14px; }
  .bs-period select{ min-height:38px; border-radius:9px; }
  .bs-caveat{ background:#111724; border:1px solid var(--line); }
  .bs-section{ padding:0 0 8px; border-radius:14px; overflow:visible; }
  .bs-section-title{ font-family:"Barlow Condensed",sans-serif; font-size:18px; letter-spacing:0.06em; color:var(--ink); background:#141C2A;
    padding:10px 14px; margin:0 0 4px; border-bottom:1px solid var(--line); border-radius:14px 14px 0 0; }
  table.bs-table{ font-size:12.5px; }
  table.bs-table th, table.bs-table td{ padding:5px 12px; }
  table.bs-table td{ font-family:"Barlow Condensed",sans-serif; font-size:16px; font-weight:600; }
  table.bs-table td:first-child{ font-family:Inter,sans-serif; font-size:12.5px; font-weight:400; }
  table.bs-table td.bs-heat{ font-weight:700; }
  span.bs-pct{ display:inline-block; margin:0 0 0 6px; padding:1px 5px; border-radius:4px; background:rgba(255,176,32,0.16); color:#FFCB66; font-family:Inter,sans-serif; font-size:9.5px; font-weight:700; vertical-align:middle; }
  .bs-section-note{ padding:4px 14px 0; margin-top:0; }
  .bs-subhead{ color:var(--accent); text-transform:uppercase; letter-spacing:0.08em; font-size:10.5px; margin:10px 12px 3px; }
  .bs-drivechart-title{ font-family:"Barlow Condensed",sans-serif; font-size:20px; color:var(--ink); }
  .dc-list{ border-radius:14px; }
  .dc-row{ font-size:11.5px; border-radius:6px; }
  span.bp-cnt{ display:inline-block; min-width:32px; padding:1px 8px; border-radius:6px; background:#1E2738; border:1px solid #33405A; border-bottom:1px solid #33405A; text-align:center; cursor:pointer; }
  span.bp-cnt:hover, span.bp-cnt:focus{ border-color:var(--accent); }
  span.bp-pop{ background:#0B1019; border-color:#33405A; font-family:Inter,sans-serif; font-size:11.5px; }
  .bp-h b{ color:#FFCB66; }

  /* scoreboard */
  .sb-head{ display:flex; flex-wrap:wrap; align-items:flex-end; justify-content:space-between; gap:14px 20px; }
  .sb-title{ display:flex; flex-direction:column; gap:4px; }
  .sb-title h2{ font-size:52px; line-height:0.95; text-transform:uppercase; font-weight:700; }
  .sb-sub{ font-size:13px; color:var(--ink-muted); }
  .sb-weeks{ display:flex; flex-wrap:wrap; gap:6px; }
  .sb-week{ min-width:44px; min-height:44px; padding:0 10px; border-radius:10px; border:1px solid var(--line); background:#111724; color:var(--ink-2);
    font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:18px; cursor:pointer; }
  .sb-week:hover{ border-color:var(--line-strong); color:var(--ink); }
  .sb-week[aria-pressed="true"]{ background:var(--accent); border-color:var(--accent); color:#1A1300; }
  .sb-week:focus-visible, .sb-card:focus-visible{ outline:2px solid var(--accent); outline-offset:2px; }
  .sb-grid{ display:grid; grid-template-columns:repeat(auto-fill, minmax(270px, 1fr)); gap:14px; }
  .sb-card{ text-align:left; padding:0; background:#111724; border:1px solid var(--line); border-radius:14px; color:inherit; cursor:pointer; display:flex;
    flex-direction:column; overflow:hidden; font:inherit; transition:transform .12s ease, border-color .12s ease, background-color .12s ease; }
  .sb-card:hover{ background:#161D2B; border-color:var(--line-strong); transform:translateY(-2px); }
  .sb-top{ display:flex; justify-content:space-between; align-items:center; gap:8px; padding:10px 14px 4px; font-size:11px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; color:var(--ink-muted); }
  .sb-flag{ color:var(--accent); letter-spacing:0.08em; }
  .sb-row{ display:flex; align-items:center; gap:10px; padding:6px 14px; }
  .sb-row:last-of-type{ padding-bottom:10px; }
  .sb-row .v2-badge{ min-width:44px; height:28px; font-size:14px; }
  .sb-name{ flex:1; min-width:0; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color:#AEB7C6; font-weight:500; }
  .sb-pts{ font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:30px; line-height:1; color:#7D879A; }
  .sb-row.win .sb-name, .sb-row.win .sb-pts{ color:var(--ink); }
  .sb-row.win .sb-name{ font-weight:700; }
  .sb-foot{ display:flex; justify-content:space-between; align-items:center; gap:8px; padding:9px 14px; background:#0D131E; border-top:1px solid var(--line); font-size:12px; color:var(--ink-muted); }
  .sb-foot b{ color:#D5DBE6; font-weight:600; }
  table.bs-table td:not(:first-child){ white-space:nowrap; }
  @media (max-width:640px){
    .tabs[role="tablist"]{ flex-wrap:nowrap; overflow-x:auto; max-width:100%; scrollbar-width:none; }
    .tabs[role="tablist"] .tab-btn{ flex:none; }
    .titleblock h1{ font-size:30px; } .sb-title h2{ font-size:40px; } .banner-id h2{ font-size:28px; }
    .bs-modal{ padding:16px 12px 22px; } .bs-score .pts{ font-size:40px; }
  }
  .sb-empty{ padding:36px; text-align:center; color:var(--ink-muted); background:#111724; border:1px solid var(--line); border-radius:14px; }
</style>
"""
head = rep(head, '<div class="wrap">', CSS + '<div class="wrap">', where='wrap')

# ---------- league switch + scoreboard tab/view ----------
LEAGUE = ('<nav class="v2-league" aria-label="League"><a href="../nfl/"' + (' aria-current="page"' if LG == 'nfl' else '') + '>NFL</a>'
          '<a href="../cfb/"' + (' aria-current="page"' if LG == 'cfb' else '') + '>CFB</a></nav>')
head = rep(head, '<div class="titleblock">', '<div class="titleblock">' + LEAGUE, where='titleblock')
head = rep(head, '<button class="tab-btn active" id="tabBtnTeam" data-target="team" role="tab" aria-selected="true">Team</button>',
           '<button class="tab-btn active" id="tabBtnScores" data-target="scores" role="tab" aria-selected="true">Scoreboard</button>'
           '<button class="tab-btn" id="tabBtnTeam" data-target="team" role="tab" aria-selected="false">Team</button>', where='tab btn')
CONF = ('<div class="control"><label for="sbConf">Conference</label><select id="sbConf"></select></div>' if LG == 'cfb' else '')
VIEW = ('<div data-view="scores" class="active">\n'
        '    <div class="sb-head"><div class="sb-title"><span class="eyebrow">Scoreboard</span><h2 id="sbWeekTitle">Week</h2>'
        '<span class="sb-sub" id="sbSub"></span></div>'
        '<div class="sb-weeks" role="group" aria-label="Week" id="sbWeeks"></div></div>\n'
        '    <div class="lb-controls">' + CONF +
        '<div class="control"><label for="sbSearch">Team</label><input id="sbSearch" placeholder="Filter by team…" autocomplete="off"></div>'
        '<div class="control"><label for="sbSort">Sort</label><select id="sbSort"><option value="az">A–Z (home team)</option>'
        '<option value="close">Closest finish</option><option value="points">Most points</option>'
        '<option value="luck">Biggest box-score luck</option></select></div></div>\n'
        '    <div class="sb-grid" id="sbGrid" aria-label="Games"></div>\n'
        '  </div>\n\n  <div data-view="team">')
head = rep(head, '<div data-view="team" class="active">', VIEW, where='team view')
head = rep(head, '</head>', '<script id="v2-colors" type="application/json">' + json.dumps(COL, separators=(',', ':')) + '</script>\n'
           + ('<script>window.V2_BASE=' + json.dumps(BASE) + ';</script>\n' if BASE else '') + '</head>', where='head end') \
    if '</head>' in head else head.replace('<style id="v2theme">', '<script id="v2-colors" type="application/json">' + json.dumps(COL, separators=(',', ':')) + '</script>\n'
           + ('<script>window.V2_BASE=' + json.dumps(BASE) + ';</script>\n' if BASE else '') + '<style id="v2theme">', 1)

# ---------- JS ----------
if LG == 'cfb':
    tail = rep(tail, 'window.fetch(path)', 'window.fetch((window.V2_BASE||"")+path)', where='shard fetch')
tail = rep(tail, "var tabBtns = [document.getElementById('tabBtnTeam'),", "var tabBtns = [document.getElementById('tabBtnScores'), document.getElementById('tabBtnTeam'),", where='tabBtns')
tail = rep(tail, "var views = { team: document.querySelector('[data-view=\"team\"]'),",
           "var views = { scores: document.querySelector('[data-view=\"scores\"]'), team: document.querySelector('[data-view=\"team\"]'),", where='views')
tail = rep(tail, "if(target==='leaderboard') renderLeaderboard();", "if(target==='scores') v2RenderScores(); if(target==='leaderboard') renderLeaderboard();", where='setTab')
JS = r"""
  // ---------- v2: scoreboard + team colors ----------
  var V2C = JSON.parse(document.getElementById('v2-colors').textContent);
  function v2col(t){ var c = V2C[t]; if(c) return c; var w = t.split(/\s+/); return [(w.length>1 ? w.map(function(x){return x[0];}).join('') : t.slice(0,4)).toUpperCase().slice(0,4), '#3A4356', '#FFFFFF']; }
  function v2badge(t){ var c = v2col(t); return '<span class="v2-badge" style="background:'+c[1]+';color:'+c[2]+'">'+c[0]+'</span>'; }
  function v2esc(x){ return String(x).replace(/[&<>"]/g, function(ch){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]; }); }
  var V2G = [];
  Object.keys(boxscores).forEach(function(gk){
    var rec = boxscores[gk], ts = Object.keys(rec).filter(function(k){ return k!=='driveChart'; });
    if(ts.length!==2 || !rec[ts[0]].meta || !rec[ts[1]].meta) return;
    var h = rec[ts[0]].meta.home ? ts[0] : (rec[ts[1]].meta.home ? ts[1] : ts[0]), a = h===ts[0] ? ts[1] : ts[0];
    var mh = rec[h].meta, ma = rec[a].meta;
    V2G.push({ gk:gk, week:mh.week, home:h, away:a, hs:mh.ts, as:ma.ts, hx:mh.xPts, ax:ma.xPts, hw:mh.xWin });
  });
  var V2W = V2G.map(function(g){ return g.week; }).filter(function(w, i, arr){ return arr.indexOf(w)===i; }).sort(function(x, y){ return x-y; });
  var v2Week = V2W[V2W.length-1];
  var sbConf = document.getElementById('sbConf'), sbSearch = document.getElementById('sbSearch'), sbSort = document.getElementById('sbSort');
  if(sbConf){
    var o0 = document.createElement('option'); o0.value='all'; o0.textContent='All games'; sbConf.appendChild(o0);
    Object.keys(teams).map(function(t){ return teams[t].conf; }).filter(function(c, i, arr){ return c && arr.indexOf(c)===i; }).sort().forEach(function(c){
      var o = document.createElement('option'); o.value=c; o.textContent=c; sbConf.appendChild(o); });
    sbConf.addEventListener('change', v2RenderScores);
  }
  sbSearch.addEventListener('input', v2RenderScores); sbSort.addEventListener('change', v2RenderScores);
  function v2RenderScores(){
    var wk = document.getElementById('sbWeeks');
    wk.innerHTML = V2W.map(function(w){ return '<button type="button" class="sb-week" data-w="'+w+'" aria-pressed="'+(w===v2Week)+'" aria-label="Week '+w+'">'+w+'</button>'; }).join('');
    Array.prototype.forEach.call(wk.querySelectorAll('.sb-week'), function(bt){ bt.addEventListener('click', function(){ v2Week = +bt.getAttribute('data-w'); v2RenderScores(); }); });
    var conf = sbConf ? sbConf.value : 'all', q = (sbSearch.value||'').trim().toLowerCase(), sort = sbSort.value;
    var all = V2G.filter(function(g){ return g.week===v2Week; });
    var list = all.filter(function(g){
      if(conf!=='all' && !((teams[g.home]||{}).conf===conf || (teams[g.away]||{}).conf===conf)) return false;
      if(q && g.home.toLowerCase().indexOf(q)<0 && g.away.toLowerCase().indexOf(q)<0) return false;
      return true; });
    function luck(g){ return (g.hx==null||g.ax==null) ? -1 : Math.abs((g.hs-g.as)-(g.hx-g.ax)); }
    list.sort(function(x, y){
      if(sort==='close') return Math.abs(x.hs-x.as)-Math.abs(y.hs-y.as);
      if(sort==='points') return (y.hs+y.as)-(x.hs+x.as);
      if(sort==='luck') return luck(y)-luck(x);
      return x.home<y.home ? -1 : (x.home>y.home ? 1 : 0); });
    document.getElementById('sbWeekTitle').textContent = 'Week '+v2Week;
    document.getElementById('sbSub').textContent = list.length+(list.length===all.length?'':' of '+all.length)+' games · click a game for the full box score';
    var grid = document.getElementById('sbGrid');
    if(!list.length){ grid.innerHTML = '<div class="sb-empty">No games match these filters.</div>'; return; }
    grid.innerHTML = list.map(function(g, i){
      var aw = g.as>g.hs, hw = g.hs>g.as, flag = '';
      if(g.hw!=null && ((hw && g.hw<50) || (aw && g.hw>50))) flag = 'Box-score upset';
      var dw = g.hw==null ? '' : (g.hw>=50 ? v2col(g.home)[0]+' '+g.hw.toFixed(0)+'%' : v2col(g.away)[0]+' '+(100-g.hw).toFixed(0)+'%');
      var xs = (g.ax==null||g.hx==null) ? '—' : v2col(g.away)[0]+' '+g.ax.toFixed(1)+' · '+v2col(g.home)[0]+' '+g.hx.toFixed(1);
      return '<button type="button" class="sb-card" data-i="'+i+'" aria-label="'+v2esc(g.away+' '+g.as+' at '+g.home+' '+g.hs+', open box score')+'">'
        + '<span class="sb-top"><span>Final</span><span class="sb-flag">'+flag+'</span></span>'
        + '<span class="sb-row'+(aw?' win':'')+'">'+v2badge(g.away)+'<span class="sb-name">'+v2esc(g.away)+'</span><span class="sb-pts">'+g.as+'</span></span>'
        + '<span class="sb-row'+(hw?' win':'')+'">'+v2badge(g.home)+'<span class="sb-name">'+v2esc(g.home)+'</span><span class="sb-pts">'+g.hs+'</span></span>'
        + '<span class="sb-foot"><span title="Box-score (deserved) score">Deserved <b>'+xs+'</b></span><span title="Deserved win %">'+dw+'</span></span></button>';
    }).join('');
    Array.prototype.forEach.call(grid.querySelectorAll('.sb-card'), function(c){
      c.addEventListener('click', function(){ var g = list[+c.getAttribute('data-i')]; openBoxScore(g.away, g.week, g.home); }); });
  }
  // team colors: box-score header badges + team banner
  (function(){
    var sc = document.getElementById('bsScore');
    new MutationObserver(function(){
      Array.prototype.forEach.call(sc.querySelectorAll('.team'), function(el){ if(!el.querySelector('.v2-badge')) el.insertAdjacentHTML('afterbegin', v2badge(el.textContent.trim())); });
    }).observe(sc, { childList:true });
    var tn = document.getElementById('teamName'), bn = tn.closest('.banner');
    function paint(){ var t = tn.textContent.trim(); if(!t || t==='—') return; var c = v2col(t); tn.setAttribute('data-abb', c[0]); bn.style.setProperty('--team', c[1]); bn.style.setProperty('--team-fg', c[2]); }
    new MutationObserver(paint).observe(tn, { childList:true, characterData:true, subtree:true }); paint();
  })();
  (function(){ var eb = document.querySelector('.titleblock .eyebrow'); if(eb && V2W.length) eb.textContent = eb.textContent.replace(/Weeks? [0-9–\-]+/, 'Weeks '+V2W[0]+'–'+V2W[V2W.length-1]); })();
  setTimeout(function(){ setTab('scores'); }, 0);
"""
anchor = "tabBtns.forEach(function(b){ b.addEventListener('click', function(){ setTab(b.getAttribute('data-target')); }); });"
tail = rep(tail, anchor, anchor + JS, where='tab listeners')
open(DST, 'w').write(head + data + tail)
print(f'{LG}: redesign -> {DST} ({len(head + data + tail) // 1024} KB)')
