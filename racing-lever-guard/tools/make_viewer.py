"""Inline scene.json into the viewer template.

    python make_viewer.py scene.json ../docs/viewer.html [--fragment out.html]

The docs copy gets a full HTML skeleton; --fragment also writes the bare page body that
the claude.ai artifact publisher wraps itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    scene_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    fragment_path = Path(sys.argv[sys.argv.index("--fragment") + 1]) if "--fragment" in sys.argv else None
    page = (HERE / "viewer_template.html").read_text()
    page = page.replace("__SCENE_JSON__", scene_path.read_text().replace("</", "<\\/"))
    if fragment_path:
        fragment_path.write_text(page)
    head, body = page.split('<script type="importmap">', 1)
    full = (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        "<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
        "body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n"
        f'{head}<script type="importmap">{body.split("</script>", 1)[0]}</script>\n</head>\n<body>\n'
        f'{body.split("</script>", 1)[1]}\n</body>\n</html>\n'
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(full)
    print(f"wrote {out_path} ({out_path.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
