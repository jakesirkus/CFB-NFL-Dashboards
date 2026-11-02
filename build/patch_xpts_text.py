"""Expected-score tooltip text: turnovers are no longer part of the model (Nov 2, 2026) and the NFL model has no explosive term.
Idempotent. usage: patch_xpts_text.py cfb|nfl PAGE.html [PAGE.html ...]"""
import sys
LG = sys.argv[1]
OLD = "what each offense should have scored from drives, share of available yards gained, success rate, explosive plays and interceptions + half of fumbles. Field position, return/defensive TDs and red-zone finishing are left out on purpose."
NEW = ("what each offense should have scored from drives, share of available yards gained, success rate" + (" and explosive plays" if LG == 'cfb' else "")
       + ". Turnovers are not counted against the offense (treated as luck). Field position, return/defensive TDs and red-zone finishing are left out on purpose.")
for p in sys.argv[2:]:
    s = open(p).read(); n = s.count(OLD)
    if not n: print(p, 'already patched' if 'not counted against the offense' in s else 'TEXT NOT FOUND'); continue
    open(p, 'w').write(s.replace(OLD, NEW)); print(p, 'patched', n)
