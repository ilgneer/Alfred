# Matriz de compatibilidade

> Gerada automaticamente a partir de `src/alfred/core/routes.py` por `tools/gen_matrix.py`.
> Cada linha é executada com um arquivo real por `tests/test_routes_all.py` (o workflow de release roda
> esses testes no Windows com os motores que vão dentro do instalador) e o arquivo gerado é validado.

**Legenda** — ✅ estável · 🧪 experimental (funciona, mas a fidelidade depende do conteúdo) · Completa* = exige LibreOffice (incluído na edição Completa; na edição Leve funciona se o LibreOffice estiver instalado no Windows). Quando há duas formas, o Alfred usa a primeira disponível.

## Imagens

| Origem | Destino | Status | Motor | Edição | Observação |
|---|---|---|---|---|---|
| AVIF, BMP, HEIC, HEIF, PNG, SVG, TIF, TIFF, WEBP | JPG | ✅ | Pillow | Leve e Completa |  |
| AVIF, BMP, HEIC, HEIF, JFIF, JPE, JPEG, JPG, SVG, TIF, TIFF, WEBP | PNG | ✅ | Pillow | Leve e Completa |  |
| AVIF, BMP, HEIC, HEIF, JFIF, JPE, JPEG, JPG, PNG, SVG, TIF, TIFF | WEBP | ✅ | Pillow | Leve e Completa |  |
| BMP, HEIC, HEIF, JFIF, JPE, JPEG, JPG, PNG, SVG, TIF, TIFF, WEBP | AVIF | ✅ | Pillow + Pillow AVIF | Leve e Completa |  |
| AVIF, BMP, JFIF, JPE, JPEG, JPG, PNG, SVG, TIF, TIFF, WEBP | HEIC | ✅ | Pillow + pillow-heif (x265) | Leve e Completa |  |
| AVIF, BMP, HEIC, HEIF, JFIF, JPE, JPEG, JPG, PNG, SVG, WEBP | TIFF | ✅ | Pillow | Leve e Completa |  |
| AVIF, HEIC, HEIF, JFIF, JPE, JPEG, JPG, PNG, SVG, TIF, TIFF, WEBP | BMP | ✅ | Pillow | Leve e Completa |  |
| AVIF, BMP, HEIC, HEIF, JFIF, JPE, JPEG, JPG, PNG, TIF, TIFF, WEBP | PDF | ✅ | Pillow | Leve e Completa |  |
| SVG | PDF | ✅ | QtSvg + Qt PDF | Leve e Completa | PDF vetorial (SVG Tiny 1.2) |
| AVIF, BMP, HEIC, HEIF, JFIF, JPE, JPEG, JPG, PNG, SVG, TIF, TIFF, WEBP | PDF único | ✅ | Pillow | Leve e Completa |  |

## Áudio

| Origem | Destino | Status | Motor | Edição | Observação |
|---|---|---|---|---|---|
| AAC, AIF, AIFF, FLAC, M4A, OGA, OGG, OPUS, WAV, WMA | MP3 | ✅ | FFmpeg | Leve e Completa |  |
| AAC, AIF, AIFF, FLAC, MP3, OGA, OGG, OPUS, WAV, WMA | M4A | ✅ | FFmpeg | Leve e Completa |  |
| AAC, AIF, AIFF, FLAC, M4A, MP3, OGA, OGG, OPUS, WMA | WAV | ✅ | FFmpeg | Leve e Completa |  |
| AAC, AIF, AIFF, M4A, MP3, OGA, OGG, OPUS, WAV, WMA | FLAC | ✅ | FFmpeg | Leve e Completa |  |
| AAC, AIF, AIFF, FLAC, M4A, MP3, OPUS, WAV, WMA | OGG | ✅ | FFmpeg | Leve e Completa |  |
|  |  | 🧪 | ↳ alternativa: FFmpeg | Leve e Completa | codificador Vorbis nativo |
| AAC, AIF, AIFF, FLAC, M4A, MP3, OGA, OGG, WAV, WMA | OPUS | ✅ | FFmpeg | Leve e Completa |  |
|  |  | 🧪 | ↳ alternativa: FFmpeg | Leve e Completa | codificador Opus nativo |
| AAC, FLAC, M4A, MP3, OGA, OGG, OPUS, WAV, WMA | AIFF | ✅ | FFmpeg | Leve e Completa |  |
| AAC, AIF, AIFF, FLAC, M4A, MP3, OGA, OGG, OPUS, WAV | WMA | ✅ | FFmpeg | Leve e Completa |  |

## Vídeo

| Origem | Destino | Status | Motor | Edição | Observação |
|---|---|---|---|---|---|
| AVI, GIF, MKV, MOV, WEBM, WMV | MP4 | ✅ | FFmpeg | Leve e Completa | H.264 + AAC; cópia sem perdas quando possível |
| AVI, GIF, M4V, MKV, MP4, WEBM, WMV | MOV | ✅ | FFmpeg | Leve e Completa | H.264 + AAC |
| AVI, GIF, M4V, MOV, MP4, WEBM, WMV | MKV | ✅ | FFmpeg | Leve e Completa | remux sem perdas quando possível |
| AVI, GIF, M4V, MKV, MOV, MP4, WMV | WEBM | ✅ | FFmpeg | Leve e Completa | VP9 + Opus |
|  |  | ✅ | ↳ alternativa: FFmpeg | Leve e Completa | VP9 + Vorbis |
| GIF, M4V, MKV, MOV, MP4, WEBM, WMV | AVI | ✅ | FFmpeg | Leve e Completa | MPEG-4 Part 2 + MP3 |
| AVI, GIF, M4V, MKV, MOV, MP4, WEBM | WMV | ✅ | FFmpeg | Leve e Completa | WMV8 + WMA |
| AVI, M4V, MKV, MOV, MP4, WEBM, WMV | GIF | ✅ | FFmpeg | Leve e Completa | paleta otimizada, 12 fps, até 720 px |
| AVI, M4V, MKV, MOV, MP4, WEBM, WMV | MP3 só áudio | ✅ | FFmpeg | Leve e Completa |  |

## PDF

| Origem | Destino | Status | Motor | Edição | Observação |
|---|---|---|---|---|---|
| PDF | DOCX | ✅ | pdf2docx + PyMuPDF | Leve e Completa | layouts complexos podem variar |
| PDF | PPTX | ✅ | PyMuPDF + python-pptx | Leve e Completa | cada página vira um slide (imagem) com o texto nas notas |
| PDF | XLSX | 🧪 | PyMuPDF + openpyxl | Leve e Completa | detecção automática de tabelas |
| PDF | PNG páginas | ✅ | PyMuPDF | Leve e Completa | todas as páginas, 300 DPI |
| PDF | JPG páginas | ✅ | PyMuPDF | Leve e Completa | todas as páginas, 300 DPI |
| PDF | EPUB | 🧪 | PyMuPDF + Pandoc | Leve e Completa | texto, títulos e imagens; sem layout fixo |
| PDF | TXT | ✅ | PyMuPDF | Leve e Completa |  |
| PDF | MD Markdown | 🧪 | PyMuPDF | Leve e Completa | títulos detectados pelo tamanho da fonte |

## Documentos

| Origem | Destino | Status | Motor | Edição | Observação |
|---|---|---|---|---|---|
| DOC | PDF | ✅ | LibreOffice | Completa* |  |
| DOCX, ODT, RTF | PDF | ✅ | LibreOffice | Completa* |  |
|  |  | 🧪 | ↳ alternativa: Pandoc + Qt PDF | Leve e Completa | sem LibreOffice: layout simplificado |
| EPUB | PDF | 🧪 | Pandoc + Qt PDF | Leve e Completa | sem paginação original |
| HTM, HTML | PDF | ✅ | LibreOffice | Completa* |  |
|  |  | 🧪 | ↳ alternativa: Qt PDF | Leve e Completa | HTML/CSS básico |
| MARKDOWN, MD | PDF | ✅ | Pandoc + Qt PDF | Leve e Completa |  |
| TXT | PDF | ✅ | Qt PDF | Leve e Completa |  |
| DOC | DOCX | ✅ | LibreOffice | Completa* |  |
| ODT, RTF | DOCX | ✅ | LibreOffice | Completa* |  |
|  |  | ✅ | ↳ alternativa: Pandoc | Leve e Completa |  |
| EPUB, HTM, HTML, MARKDOWN, MD, TXT | DOCX | ✅ | Pandoc | Leve e Completa |  |
| DOCX, HTM, HTML, ODT, RTF, TXT | DOC | ✅ | LibreOffice | Completa* |  |
| EPUB, MARKDOWN, MD | DOC | ✅ | Pandoc + LibreOffice | Completa* |  |
| DOC | ODT | ✅ | LibreOffice | Completa* |  |
| DOCX, RTF | ODT | ✅ | LibreOffice | Completa* |  |
|  |  | ✅ | ↳ alternativa: Pandoc | Leve e Completa |  |
| EPUB, HTM, HTML, MARKDOWN, MD, TXT | ODT | ✅ | Pandoc | Leve e Completa |  |
| DOC | RTF | ✅ | LibreOffice | Completa* |  |
| DOCX, ODT | RTF | ✅ | LibreOffice | Completa* |  |
|  |  | ✅ | ↳ alternativa: Pandoc | Leve e Completa |  |
| EPUB, HTM, HTML, MARKDOWN, MD, TXT | RTF | ✅ | Pandoc | Leve e Completa |  |
| DOC | TXT | ✅ | LibreOffice + Pandoc | Completa* |  |
| DOCX, EPUB, HTM, HTML, MARKDOWN, MD, ODT, RTF | TXT | ✅ | Pandoc | Leve e Completa |  |
| DOC | MD Markdown | ✅ | LibreOffice + Pandoc | Completa* |  |
| DOCX, EPUB, HTM, HTML, ODT, RTF, TXT | MD Markdown | ✅ | Pandoc | Leve e Completa |  |
| DOC | HTML | ✅ | LibreOffice + Pandoc | Completa* |  |
| DOCX, EPUB, MARKDOWN, MD, ODT, RTF, TXT | HTML | ✅ | Pandoc | Leve e Completa |  |
| DOC | EPUB | ✅ | LibreOffice + Pandoc | Completa* |  |
| DOCX, HTM, HTML, MARKDOWN, MD, ODT, RTF, TXT | EPUB | ✅ | Pandoc | Leve e Completa |  |

## Apresentações

| Origem | Destino | Status | Motor | Edição | Observação |
|---|---|---|---|---|---|
| ODP, PPT, PPTX | PDF | ✅ | LibreOffice | Completa* |  |
| ODP, PPT | PPTX | ✅ | LibreOffice | Completa* |  |
| ODP, PPTX | PPT | ✅ | LibreOffice | Completa* |  |
| PPT, PPTX | ODP | ✅ | LibreOffice | Completa* |  |
| ODP, PPT, PPTX | PNG páginas | ✅ | LibreOffice + PyMuPDF | Completa* | um arquivo por slide |
| ODP, PPT, PPTX | JPG páginas | ✅ | LibreOffice + PyMuPDF | Completa* | um arquivo por slide |

## Planilhas

| Origem | Destino | Status | Motor | Edição | Observação |
|---|---|---|---|---|---|
| CSV, TSV | XLSX | ✅ | openpyxl | Leve e Completa |  |
|  |  | ✅ | ↳ alternativa: LibreOffice | Completa* |  |
| ODS | XLSX | ✅ | LibreOffice | Completa* |  |
| XLS | XLSX | ✅ | LibreOffice | Completa* |  |
|  |  | 🧪 | ↳ alternativa: xlrd + openpyxl | Leve e Completa | somente valores, sem formatação |
| CSV, ODS, TSV, XLSM, XLSX | XLS | ✅ | LibreOffice | Completa* |  |
| CSV, TSV, XLS, XLSM, XLSX | ODS | ✅ | LibreOffice | Completa* |  |
| TSV | CSV | ✅ | Python | Leve e Completa |  |
| ODS | CSV | ✅ | LibreOffice | Completa* |  |
| XLS | CSV | ✅ | xlrd | Leve e Completa | uma saída por aba |
|  |  | ✅ | ↳ alternativa: LibreOffice | Completa* |  |
| XLSM, XLSX | CSV | ✅ | openpyxl | Leve e Completa | uma saída por aba |
|  |  | ✅ | ↳ alternativa: LibreOffice | Completa* |  |
| CSV | TSV | ✅ | Python | Leve e Completa |  |
| ODS | TSV | ✅ | LibreOffice | Completa* |  |
| XLS | TSV | ✅ | xlrd | Leve e Completa | uma saída por aba |
|  |  | ✅ | ↳ alternativa: LibreOffice | Completa* |  |
| XLSM, XLSX | TSV | ✅ | openpyxl | Leve e Completa | uma saída por aba |
|  |  | ✅ | ↳ alternativa: LibreOffice | Completa* |  |
| CSV, ODS, TSV, XLS, XLSM, XLSX | PDF | ✅ | LibreOffice | Completa* |  |

## Legendas

| Origem | Destino | Status | Motor | Edição | Observação |
|---|---|---|---|---|---|
| VTT | SRT | ✅ | Python | Leve e Completa |  |
| SRT | VTT | ✅ | Python | Leve e Completa |  |
| SRT, VTT | TXT | ✅ | Python | Leve e Completa |  |

## Compactados

| Origem | Destino | Status | Motor | Edição | Observação |
|---|---|---|---|---|---|
| 7Z | Extrair aqui | ✅ | 7-Zip | Leve e Completa |  |
| BZ2, GZ, TAR, TAR.BZ2, TAR.GZ, TAR.XZ, TBZ2, TGZ, TXZ, XZ, ZIP | Extrair aqui | ✅ | Python | Leve e Completa |  |
| RAR | Extrair aqui | ✅ | 7-Zip (RAR) | Leve e Completa |  |
| 7Z | ZIP converter | ✅ | 7-Zip | Leve e Completa |  |
| RAR | ZIP converter | ✅ | 7-Zip (RAR) | Leve e Completa |  |
| TAR, TAR.BZ2, TAR.GZ, TAR.XZ, TBZ2, TGZ, TXZ | ZIP converter | ✅ | Python | Leve e Completa |  |

## Ações universais

| Seleção | Ação | Status | Motor |
|---|---|---|---|
| Qualquer arquivo ou pasta (um ou vários) | ZIP — compactar | ✅ | Python |
| Duas ou mais imagens | PDF único (todas as imagens em um PDF) | ✅ | Pillow |

## Não disponível (de propósito)

| Conversão | Motivo |
|---|---|
| Qualquer → Apple Pages (.pages) | Não existe conversor local confiável no Windows. Use DOCX, que o Pages abre. |
| Pages / RTFD / textClipping (macOS) → qualquer | Formatos exclusivos do macOS, sem leitor livre confiável. |
| Qualquer → RAR | A compressão RAR é proprietária (WinRAR). O Alfred extrai RAR e converte RAR → ZIP. |
| PDF → PPTX com texto editável | O PDF não guarda a estrutura de slides; as páginas viram imagens nítidas e o texto vai para as anotações. |
| Imagem → SVG (vetorização) | Exige traçado automático (vetorização), fora do escopo de uma conversão fiel. |
| Áudio → vídeo | Não há imagem de origem; seria uma conversão artificial. |
| Documentos/planilhas/apresentações → PDF sem LibreOffice | Na edição Leve, só TXT/MD/HTML (e DOCX/ODT/RTF/EPUB de forma experimental) viram PDF. |

Total de combinações origem → destino testadas: **443**.
