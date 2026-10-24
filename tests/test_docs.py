"""Repository consistency: generated docs, links, icons, packaging files."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_compatibility_matrix_is_up_to_date(tmp_path):
    doc = ROOT / "docs" / "COMPATIBILIDADE.md"
    before = doc.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "tools" / "gen_matrix.py")], check=True, capture_output=True)
    after = doc.read_text(encoding="utf-8")
    assert before == after, "rode: python tools/gen_matrix.py"


def test_markdown_relative_links_exist():
    for md in [ROOT / "README.md", *ROOT.glob("*.md"), *(ROOT / "docs").glob("*.md")]:
        text = md.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", text) + re.findall(r'src="([^"]+)"', text):
            if target.startswith(("http", "mailto:", "../../")):
                continue
            assert (md.parent / target).exists(), f"{md.name}: link quebrado {target}"


def test_every_target_icon_exists():
    from alfred.core import routes
    from alfred.ui import icons

    names = set(icons.names())
    for t in routes.T.values():
        assert t.icon in names, t.key


def test_packaging_files_reference_existing_assets():
    iss = (ROOT / "packaging" / "installer" / "Alfred.iss").read_text(encoding="utf-8-sig")
    for rel in re.findall(r"\{#Root\}\\([^,\s\"]+)", iss):
        if rel != "release":
            assert (ROOT / rel.replace("\\", "/")).exists(), rel
    assert (ROOT / "packaging" / "installer" / "LICENCA_INSTALADOR.txt").read_bytes().startswith(b"\xef\xbb\xbf")
    spec = (ROOT / "packaging" / "alfred.spec").read_text(encoding="utf-8")
    for rel in re.findall(r'ROOT / "assets" / "([^"]+)"', spec):
        assert (ROOT / "assets" / rel).exists(), rel


def test_version_is_consistent():
    from alfred import __version__

    assert re.match(r"^\d+\.\d+\.\d+", __version__)
    assert f"[{__version__}]" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_alternative_art_not_shipped():
    spec = (ROOT / "packaging" / "alfred.spec").read_text(encoding="utf-8")
    assert "alfred_alternative" not in spec and "extras" not in spec
