"""Build the GitHub Pages copy of both dashboards (repo jakesirkus/CFB-NFL-Dashboards).
GitHub's web uploader takes at most 100 files per drag and 25 MB per file, so the CFB page's
180+180 small shard files are merged into 20+20 larger packs and the index maps are rewritten.
usage: make_github_pack.py CFB_OUT_DIR NFL_HTML DEST_DIR"""
import sys, os, json, glob, shutil
CFB, NFL, DEST = sys.argv[1:4]
N_PACKS = 20
shutil.rmtree(DEST, ignore_errors=True)
os.makedirs(DEST + '/cfb/periods'); os.makedirs(DEST + '/cfb/drivecharts'); os.makedirs(DEST + '/nfl')
s = open(CFB + '/index.html').read()
def blk(tag):
    o = f'<script id="{tag}" type="application/json">'; a = s.index(o) + len(o); return a, s.index('</script>', a)
for tag, sub in (('period-index-data', 'periods'), ('drivechart-index-data', 'drivecharts')):
    a, b = blk(tag); idx = json.loads(s[a:b])
    shards = sorted(set(idx.values()))
    per = -(-len(shards) // N_PACKS)
    remap = {sh: f'{sub}/pack_{i // per:02d}.json' for i, sh in enumerate(shards)}
    packs = {}
    for sh in shards: packs.setdefault(remap[sh], {}).update(json.load(open(CFB + '/' + sh)))
    for p, d in packs.items():
        json.dump(d, open(DEST + '/cfb/' + p, 'w'), separators=(',', ':'))
        assert os.path.getsize(DEST + '/cfb/' + p) < 24e6
    new = {gk: remap[v] for gk, v in idx.items()}
    s = s[:a] + json.dumps(new, separators=(',', ':')) + s[b:]
open(DEST + '/cfb/index.html', 'w').write(s)
shutil.copy(NFL, DEST + '/nfl/index.html')
open(DEST + '/index.html', 'w').write("""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>CFB &amp; NFL Dashboards</title>
<style>
:root{--bg:#f4f2ec;--card:#fff;--ink:#1b1b19;--muted:#66635a;--line:#dcd6c3;--accent:#2d4a8a}
@media (prefers-color-scheme:dark){:root{--bg:#14161a;--card:#1c1f26;--ink:#e9e9ea;--muted:#9a9da5;--line:#2f333d;--accent:#7fa0ea}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,sans-serif;padding:40px 16px}
.wrap{max-width:640px;margin:0 auto}h1{font-size:28px;margin:0 0 6px}p{color:var(--muted);margin:0 0 24px}
a.card{display:block;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin-bottom:14px;color:inherit;text-decoration:none}
a.card:hover{border-color:var(--accent)}a.card b{display:block;font-size:19px;color:var(--accent)}
</style></head><body><div class="wrap"><h1>Team Dashboards</h1><p>Season-to-date team stats built from play-by-play.</p>
<a class="card" href="cfb/"><b>College Football &rarr;</b>Every FBS team: percentiles, leaderboards, box scores, drive charts</a>
<a class="card" href="nfl/"><b>NFL &rarr;</b>All 32 teams: percentiles, leaderboards, box scores, drive charts</a>
</div></body></html>""")
files = [os.path.relpath(f, DEST) for f in glob.glob(DEST + '/**/*', recursive=True) if os.path.isfile(f)]
print('files', len(files), '| largest MB', round(max(os.path.getsize(DEST + '/' + f) for f in files) / 1e6, 1),
      '| total MB', round(sum(os.path.getsize(DEST + '/' + f) for f in files) / 1e6, 1))
# GitHub's web uploader chokes on one ~70 MB drag: also lay the same files out as three smaller drag-in steps
ST = DEST + ' (3 steps)'
shutil.rmtree(ST, ignore_errors=True)
for step, items in (('Step 1', ['index.html', 'nfl/index.html']),
                    ('Step 2', ['cfb/index.html'] + ['cfb/periods/' + os.path.basename(f) for f in glob.glob(DEST + '/cfb/periods/*.json')]),
                    ('Step 3', ['cfb/drivecharts/' + os.path.basename(f) for f in glob.glob(DEST + '/cfb/drivecharts/*.json')])):
    for it in items:
        os.makedirs(os.path.dirname(f'{ST}/{step}/{it}'), exist_ok=True); shutil.copy(f'{DEST}/{it}', f'{ST}/{step}/{it}')
print('3-step upload folders written to', ST)
