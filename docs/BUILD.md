# Como compilar o Alfred

Há dois caminhos. Os dois produzem o mesmo resultado: `dist\Alfred\Alfred.exe` (sem console) e o
instalador `release\Alfred_Setup_<versão>_<Edição>_x64.exe`.

## 1. Pelo GitHub (recomendado — não precisa de Windows próprio)

O workflow [`.github/workflows/release.yml`](../.github/workflows/release.yml) roda num runner
Windows e faz tudo:

1. instala as dependências fixadas em `requirements-build.txt`;
2. prepara os motores com `tools/fetch_engines.py` (FFmpeg, Pandoc, 7-Zip e, na edição completa,
   LibreOffice);
3. roda **toda a suíte de testes com os motores que vão dentro do instalador** (inclusive o LibreOffice);
4. gera o executável com PyInstaller (`tools/build.py` + `packaging/alfred.spec`);
5. executa `Alfred.exe --self-test` no executável gerado;
6. compila o instalador com Inno Setup;
7. **instala o Alfred em silêncio, verifica arquivos, atalhos e registro, roda o autoteste do app
   instalado, testa a instância única, desinstala com o app aberto e confirma que não sobrou processo,
   arquivo nem chave de registro** (`tools/test_installer.ps1`);
8. publica os instaladores como artefatos (e, em tags `v*`, num rascunho de Release).

Passo a passo para iniciantes: [RELEASE.md](RELEASE.md).

## 2. No seu Windows

Requisitos:

- Windows 10/11 x64;
- [Python 3.12](https://www.python.org/downloads/windows/) (marque “Add python.exe to PATH” ou use o `py`);
- [Inno Setup 6](https://jrsoftware.org/isdl.php) (para gerar o instalador);
- edição completa: LibreOffice instalado (ou Chocolatey, que o script usa para instalá-lo).

```bat
build_windows.bat -Edition full
build_windows.bat -Edition lite -SkipTests
```

O script cria `.venv`, instala dependências, prepara `vendor\engines`, roda os testes, gera
`dist\Alfred` e o instalador em `release\`.

### Comandos individuais

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements-build.txt -r requirements-dev.txt
.venv\Scripts\python tools\fetch_engines.py --edition full
$env:ALFRED_ENGINES_DIR = "$PWD\vendor\engines"; .venv\Scripts\python -m pytest -q; Remove-Item Env:\ALFRED_ENGINES_DIR
.venv\Scripts\python tools\build.py --edition full
dist\Alfred\Alfred.exe --self-test "$env:TEMP\alfred.json"
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=2.0.0 /DEdition=full packaging\installer\Alfred.iss
```

## Edições

| | Leve | Completa |
|---|---|---|
| FFmpeg, Pandoc, 7-Zip, PyMuPDF, pdf2docx, Pillow/HEIC/AVIF | ✅ | ✅ |
| LibreOffice (DOC/PPT/XLS/ODF ↔ Office, Office → PDF) | usa o LibreOffice do sistema, se existir | ✅ incluído |
| Tamanho aproximado do instalador* | ~150–200 MB | ~350–450 MB |

\* Estimativa: os tamanhos reais aparecem no log do workflow. O LibreOffice, sozinho, ocupa cerca de
500 MB instalado.

## Variáveis úteis

| Variável | Efeito |
|---|---|
| `ALFRED_ENGINES_DIR` | pasta de motores alternativa (testes/CI) |
| `ALFRED_FFMPEG`, `ALFRED_PANDOC`, `ALFRED_SOFFICE`, `ALFRED_7Z` | caminho de um motor específico |
| `ALFRED_DISABLE_SYSTEM_LIBREOFFICE=1` | ignora o LibreOffice instalado no sistema |
| `ALFRED_CONFIG_DIR`, `ALFRED_DATA_DIR` | pastas de configurações/dados (testes) |
| `ALFRED_TEST_REGISTRY=1` | habilita os testes que alteram o registro do usuário |
| `ALFRED_QT_SOUND=1` | sons via QtMultimedia fora do Windows (desenvolvimento) |

## Recriar arte, sons e documentação gerada

```bash
python tools/gen_sounds.py       # assets/sounds/*.wav (sons originais sintetizados)
python tools/gen_art.py          # ícone .ico, ícone da bandeja, imagens do instalador, banner
python tools/gen_matrix.py       # docs/COMPATIBILIDADE.md (a partir do registro de rotas)
python tools/screenshots.py      # docs/screenshots/*.png (interface real renderizada off-screen)
```
