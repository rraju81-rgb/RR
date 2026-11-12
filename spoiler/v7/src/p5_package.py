"""v7 step 5: zip the print package (README, print/, assembled/, docs/). Run from spoiler/:  python3 v7/src/p5_package.py"""
import sys, os, zipfile; sys.path.insert(0, 'v7/src')
from layout import ASM, PRN, DOC, IDS, STEM, N_KEYS
ROOT = 'Polo_spoiler_v7'; ZIP = 'v7/Polo_spoiler_v7_print_package.zip'
items = [('v7/README.md', 'README.md')]
items += [(f'{PRN}/{f}', f'print/{f}') for f in sorted(os.listdir(PRN)) if f.endswith('.stl')]
items += [(f'{ASM}/{k}.stl', f'assembled/{STEM[k]}_assembled.stl') for k in IDS]
items += [(f'{ASM}/KEY_{i}.stl', f'assembled/v7_KEY_{i}_assembled.stl') for i in range(1, N_KEYS + 1)]
items += [(f'{DOC}/{f}', f'docs/{f}') for f in sorted(os.listdir(DOC)) if f.endswith('.png')]
with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for src, dst in items: z.write(src, f'{ROOT}/{dst}')
print(ZIP, '%d files, %.1f MB' % (len(items), os.path.getsize(ZIP) / 1e6))
