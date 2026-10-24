<#
  Build local do Alfred no Windows (mesmos passos do GitHub Actions).

    powershell -ExecutionPolicy Bypass -File build_windows.ps1 -Edition full
    powershell -ExecutionPolicy Bypass -File build_windows.ps1 -Edition lite -SkipTests

  Requisitos: Windows 10/11 x64, Python 3.12 (python.org, com "py" launcher) e Inno Setup 6.
  A edição completa copia o LibreOffice instalado na máquina (ou instala via Chocolatey).
#>
param(
  [ValidateSet('full', 'lite')][string]$Edition = 'full',
  [switch]$SkipTests,
  [switch]$SkipInstaller
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Step($t) { Write-Host "`n=== $t" -ForegroundColor Yellow }

Step 'Ambiente virtual'
if (-not (Test-Path .venv\Scripts\python.exe)) { py -3.12 -m venv .venv }
$py = Resolve-Path .venv\Scripts\python.exe
& $py -m pip install --upgrade pip | Out-Null
& $py -m pip install -r requirements-build.txt -r requirements-dev.txt
if ($LASTEXITCODE) { throw 'pip install falhou' }

Step "Motores ($Edition)"
& $py tools\fetch_engines.py --edition $Edition --out vendor\engines
if ($LASTEXITCODE) { throw 'fetch_engines falhou' }

if (-not $SkipTests) {
  Step 'Testes'
  $env:ALFRED_ENGINES_DIR = (Resolve-Path vendor\engines).Path
  & $py -m pytest -q -ra
  if ($LASTEXITCODE) { throw 'testes falharam' }
  Remove-Item Env:\ALFRED_ENGINES_DIR
}

Step 'PyInstaller'
& $py tools\build.py --edition $Edition --engines vendor\engines
if ($LASTEXITCODE) { throw 'build falhou' }

Step 'Autoteste do executável'
$report = Join-Path $env:TEMP 'alfred-selftest.json'
$p = Start-Process dist\Alfred\Alfred.exe -ArgumentList @('--self-test', "`"$report`"") -Wait -PassThru
if ($p.ExitCode -ne 0) { Get-Content $report; throw 'autoteste falhou' }
Write-Host 'Autoteste OK' -ForegroundColor Green

if (-not $SkipInstaller) {
  Step 'Inno Setup'
  $iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
  foreach ($c in "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") {
    if (-not $iscc -and (Test-Path $c)) { $iscc = $c }
  }
  if (-not $iscc) { throw 'Inno Setup 6 não encontrado: https://jrsoftware.org/isdl.php' }
  $version = & $py -c "import sys; sys.path.insert(0,'src'); import alfred; print(alfred.__version__)"
  & $iscc "/DAppVersion=$version" "/DEdition=$Edition" packaging\installer\Alfred.iss
  if ($LASTEXITCODE) {
    Write-Warning 'ISCC falhou com compressão máxima; tentando com compressão rápida.'
    & $iscc "/DFastCompression=1" "/DAppVersion=$version" "/DEdition=$Edition" packaging\installer\Alfred.iss
    if ($LASTEXITCODE) { throw 'ISCC falhou' }
  }
  Get-ChildItem release\*.exe | Format-Table Name, Length
}
Write-Host "`nPronto." -ForegroundColor Green
