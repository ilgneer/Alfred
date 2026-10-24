# Componentes de terceiros

O Alfred é distribuído com os componentes abaixo. Os textos completos das licenças ficam em
`licenses/` (repositório e pasta de instalação). Cada motor em `engines/` traz também um `SOURCE.txt`
com a versão exata e onde obter o código-fonte; o workflow de release publica `third-party-sources.zip`
com os fontes dos componentes GPL.

## Motores (executáveis independentes em `engines/`)

| Componente | Uso no Alfred | Licença | Origem |
|---|---|---|---|
| FFmpeg 7.x | áudio e vídeo | GPL-3.0-or-later (build com `--enable-gpl --enable-version3`) | binário do pacote `imageio-ffmpeg` (PyPI) |
| Pandoc 3.x | documentos, Markdown, HTML, EPUB, RTF | GPL-2.0-or-later | binário do pacote `pypandoc_binary` (PyPI) |
| 7-Zip | extração de RAR e 7Z | GNU LGPL-2.1 + BSD-3 + restrição unRAR | instalação oficial (7-zip.org) |
| LibreOffice (só edição Completa) | DOC/DOCX/ODT/RTF, PPT/PPTX/ODP, XLS/XLSX/ODS ↔ PDF | MPL-2.0 (avisos em `engines/libreoffice/LICENSE.html`) | instalação oficial (libreoffice.org) |

A restrição unRAR do 7-Zip proíbe usar o código de descompressão RAR para recriar o compressor RAR — o
Alfred só extrai.

## Bibliotecas Python (dentro de `_internal/`)

| Pacote | Licença |
|---|---|
| Python 3.12 | PSF-2.0 |
| PySide6 / Qt 6 | LGPL-3.0 (bibliotecas Qt carregadas dinamicamente, substituíveis) |
| PyMuPDF / MuPDF | AGPL-3.0 |
| pdf2docx | MIT |
| OpenCV (headless) | Apache-2.0 |
| NumPy | BSD-3-Clause |
| Pillow | MIT-CMU (HPND) |
| pillow-heif (libheif LGPL-3.0, libde265 LGPL-3.0, x265 GPL-2.0) | BSD-3-Clause + bibliotecas citadas |
| python-docx, python-pptx, openpyxl | MIT |
| xlrd | BSD |
| lxml | BSD-3-Clause |
| fontTools | MIT |

O inventário exato de cada build (nome, versão, licença declarada e arquivos de licença copiados) é
gerado automaticamente em `licenses/python/INDEX.md` por `tools/collect_licenses.py`.

## Outros recursos

| Recurso | Licença |
|---|---|
| Fontes Inter e Lora | SIL Open Font License 1.1 |
| Arquivos `.rar` de teste em `tests/fixtures` | ISC (projeto rarfile) |
| Sons do Alfred | CC0 1.0 (originais) |
