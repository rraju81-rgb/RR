"""v15 step 6: zip the print package: the six parts and the one pin model (print/), plus the README and its figures.
No other models. Run from spoiler/:  python3 v15/src/p6_package.py"""
import sys, os, zipfile; sys.path.insert(0, 'v15/src')
from layout import PRN, DOC, IDS, STEM
ROOT = 'Polo_spoiler_v15'; ZIP = 'v15/Polo_spoiler_v15_print_package.zip'
models = [f'{STEM[k]}.stl' for k in IDS] + ['v15_PIN_3x18.stl']
assert sorted(os.listdir(PRN)) == sorted(models), f'print/ should hold exactly the six parts and the pin: {sorted(os.listdir(PRN))}'
items = [('v15/README.md', 'README.md')] + [(f'{PRN}/{f}', f) for f in models]
items += [(f'{DOC}/{f}', f'docs/{f}') for f in sorted(os.listdir(DOC)) if f.endswith(('.png', '.jpg'))]
if os.path.exists(ZIP): os.remove(ZIP)
with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for src, dst in items: z.write(src, f'{ROOT}/{dst}')
print(ZIP, '%d files (%d models: %s), %.1f MB' % (len(items), len(models), ', '.join(models), os.path.getsize(ZIP) / 1e6))
