"""v9 step 6: zip the print package (README, print/, assembled/, docs/). Run from spoiler/:  python3 v9/src/p6_package.py"""
import sys, os, json, zipfile; sys.path.insert(0, 'v9/src')
from layout import OUT, ASM, PRN, DOC, IDS, STEM
ROOT = 'Polo_spoiler_v9'; ZIP = 'v9/Polo_spoiler_v9_print_package.zip'
n_pins = json.load(open(f'{OUT}/joints.json'))['n_pins']
items = [('v9/README.md', 'README.md')]
items += [(f'{PRN}/{f}', f'print/{f}') for f in sorted(os.listdir(PRN)) if f.endswith('.stl')]
items += [(f'{ASM}/{STEM[k]}.stl', f'assembled/{STEM[k]}_assembled.stl') for k in IDS]
items += [(f'{ASM}/v9_CENTRE_SPLINE.stl', 'assembled/v9_CENTRE_SPLINE_assembled.stl')]
items += [(f'{ASM}/v9_PIN_{i:02d}.stl', f'assembled/v9_PIN_{i:02d}_assembled.stl') for i in range(1, n_pins + 1)]
items += [(f'{DOC}/{f}', f'docs/{f}') for f in sorted(os.listdir(DOC)) if f.endswith('.png')]
with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for src, dst in items: z.write(src, f'{ROOT}/{dst}')
print(ZIP, '%d files, %.1f MB' % (len(items), os.path.getsize(ZIP) / 1e6))
