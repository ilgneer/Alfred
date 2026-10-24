"""Generates docs/COMPATIBILIDADE.md from the route registry (single source of truth).

    python tools/gen_matrix.py
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alfred.core import formats as F  # noqa: E402
from alfred.core import routes as R  # noqa: E402

ENGINE_NAMES = {
    "pillow": "Pillow", "heif_enc": "pillow-heif (x265)", "avif_enc": "Pillow AVIF", "qtsvg": "QtSvg",
    "qtpdf": "Qt PDF", "builtin": "Python", "pymupdf": "PyMuPDF", "pdf2docx": "pdf2docx", "pptx": "python-pptx",
    "openpyxl": "openpyxl", "xlrd": "xlrd", "pandoc": "Pandoc", "libreoffice": "LibreOffice", "sevenzip": "7-Zip",
    "sevenzip:rar": "7-Zip (RAR)",
}
CATEGORY_TITLES = [
    (F.IMAGE, "Imagens"), (F.AUDIO, "Áudio"), (F.VIDEO, "Vídeo"), (F.PDF, "PDF"), (F.DOCUMENT, "Documentos"),
    (F.PRESENTATION, "Apresentações"), (F.SPREADSHEET, "Planilhas"), (F.SUBTITLE, "Legendas"),
    (F.ARCHIVE, "Compactados"),
]
NOT_AVAILABLE = [
    ("Qualquer → Apple Pages (.pages)", "Não existe conversor local confiável no Windows. Use DOCX, que o Pages abre."),
    ("Pages / RTFD / textClipping (macOS) → qualquer", "Formatos exclusivos do macOS, sem leitor livre confiável."),
    ("Qualquer → RAR", "A compressão RAR é proprietária (WinRAR). O Alfred extrai RAR e converte RAR → ZIP."),
    ("PDF → PPTX com texto editável", "O PDF não guarda a estrutura de slides; as páginas viram imagens nítidas e o "
                                      "texto vai para as anotações."),
    ("Imagem → SVG (vetorização)", "Exige traçado automático (vetorização), fora do escopo de uma conversão fiel."),
    ("Áudio → vídeo", "Não há imagem de origem; seria uma conversão artificial."),
    ("Documentos/planilhas/apresentações → PDF sem LibreOffice", "Na edição Leve, só TXT/MD/HTML (e DOCX/ODT/RTF/EPUB"
                                                                  " de forma experimental) viram PDF."),
]


def edition_of(plan: R.Plan) -> str:
    if "libreoffice" in plan.requires:
        return "Completa*"
    return "Leve e Completa"


def engines_of(plan: R.Plan) -> str:
    names = []
    for r in plan.requires:
        if r.startswith("ffmpeg:"):
            if "FFmpeg" not in names:
                names.append("FFmpeg")
            continue
        names.append(ENGINE_NAMES.get(r, r))
    return " + ".join(dict.fromkeys(names))


def main() -> None:
    lines = [
        "# Matriz de compatibilidade",
        "",
        "> Gerada automaticamente a partir de `src/alfred/core/routes.py` por `tools/gen_matrix.py`.",
        "> Cada linha é executada com um arquivo real por `tests/test_routes_all.py` (o workflow de release roda",
        "> esses testes no Windows com os motores que vão dentro do instalador) e o arquivo gerado é validado.",
        "",
        "**Legenda** — ✅ estável · 🧪 experimental (funciona, mas a fidelidade depende do conteúdo) · "
        "Completa* = exige LibreOffice (incluído na edição Completa; na edição Leve funciona se o LibreOffice "
        "estiver instalado no Windows). Quando há duas formas, o Alfred usa a primeira disponível.",
        "",
    ]
    by_cat: dict[str, list[R.Route]] = defaultdict(list)
    for route in R.ROUTES:
        by_cat[route.category].append(route)
    total = 0
    for cat, title in CATEGORY_TITLES:
        lines += [f"## {title}", "", "| Origem | Destino | Status | Motor | Edição | Observação |",
                  "|---|---|---|---|---|---|"]
        order = R.ORDER.get(cat, [])
        routes = sorted(by_cat[cat], key=lambda r: (order.index(r.target) if r.target in order else 99,
                                                     sorted(r.sources)))
        for route in routes:
            t = R.T[route.target]
            dest = f"{t.label} {t.sublabel}".strip()
            fmt = R.TARGET_FORMAT.get(route.target, "")
            shown = sorted(s.upper() for s in route.sources if not fmt or F.canonical(s) != fmt)
            if not shown:
                continue
            src = ", ".join(shown)
            for i, plan in enumerate(route.plans):
                status = "✅" if plan.status == R.STABLE else "🧪"
                prefix = "" if i == 0 else "↳ alternativa: "
                lines.append(f"| {src if i == 0 else ''} | {dest if i == 0 else ''} | {status} | {prefix}"
                             f"{engines_of(plan)} | {edition_of(plan)} | {plan.note} |")
                total += len(shown)
        lines.append("")
    lines += ["## Ações universais", "", "| Seleção | Ação | Status | Motor |", "|---|---|---|---|",
              "| Qualquer arquivo ou pasta (um ou vários) | ZIP — compactar | ✅ | Python |",
              "| Duas ou mais imagens | PDF único (todas as imagens em um PDF) | ✅ | Pillow |", "",
              "## Não disponível (de propósito)", "", "| Conversão | Motivo |", "|---|---|"]
    lines += [f"| {a} | {b} |" for a, b in NOT_AVAILABLE]
    lines += ["", f"Total de combinações origem → destino testadas: **{total}**.", ""]
    out = ROOT / "docs" / "COMPATIBILIDADE.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"{out} ({total} combinações)")


if __name__ == "__main__":
    main()
