<#
  Testa o instalador do Alfred de ponta a ponta em uma máquina Windows (usado no GitHub Actions).

    pwsh tools/test_installer.ps1 -Installer release\Alfred_Setup_2.0.0_Completa_x64.exe -Edition full

  Verifica: instalação silenciosa, arquivos, atalhos, registro, autoteste do app instalado,
  instância única, encerramento pelo desinstalador, remoção de arquivos/registro e ausência
  de processos residentes.
#>
param(
  [Parameter(Mandatory = $true)][string]$Installer,
  [ValidateSet('full', 'lite')][string]$Edition = 'full'
)
$ErrorActionPreference = 'Stop'
$failures = New-Object System.Collections.Generic.List[string]
function Check($cond, $msg) {
  if ($cond) { Write-Host "  [ok]  $msg" -ForegroundColor Green }
  else { Write-Host "  [FALHA] $msg" -ForegroundColor Red; $failures.Add($msg) }
}

$dir = Join-Path $env:LOCALAPPDATA 'Programs\AlfredCI'
$log = Join-Path $env:RUNNER_TEMP 'alfred-install.log'
if (-not $env:RUNNER_TEMP) { $log = Join-Path $env:TEMP 'alfred-install.log' }

Write-Host "== Instalação silenciosa em $dir"
$p = Start-Process -FilePath $Installer -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
    "/DIR=`"$dir`"", '/TASKS="startup,gesture,contextmenu,sendto"', "/LOG=`"$log`"") -Wait -PassThru
Check ($p.ExitCode -eq 0) "instalador terminou com código 0 (obtido $($p.ExitCode))"
Check (Test-Path "$dir\Alfred.exe") 'Alfred.exe instalado'
Check (Test-Path "$dir\unins000.exe") 'desinstalador presente'
Check (Test-Path "$dir\engines\ffmpeg\ffmpeg.exe") 'FFmpeg incluído'
Check (Test-Path "$dir\engines\pandoc\pandoc.exe") 'Pandoc incluído'
Check (Test-Path "$dir\engines\7zip\7z.exe") '7-Zip incluído'
if ($Edition -eq 'full') { Check (Test-Path "$dir\engines\libreoffice\program\soffice.exe") 'LibreOffice incluído (edição completa)' }
Check (Test-Path "$dir\licenses\AGPL-3.0.txt") 'licenças instaladas'
$startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Alfred.lnk'
Check (Test-Path $startMenu) 'atalho no menu Iniciar'
Check (Test-Path (Join-Path $env:APPDATA 'Microsoft\Windows\SendTo\Alfred.lnk')) 'atalho em Enviar para'
$run = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name Alfred -ErrorAction SilentlyContinue
Check ($run -and $run.Alfred -like '*--background*') 'inicialização com o Windows registrada'
Check (Test-Path 'HKCU:\Software\Classes\*\shell\Alfred\command') 'menu de contexto registrado'

Write-Host '== Autoteste do aplicativo instalado (sem console)'
$report = Join-Path $env:TEMP 'alfred-installed-selftest.json'
$st = Start-Process -FilePath "$dir\Alfred.exe" -ArgumentList @('--self-test', "`"$report`"") -Wait -PassThru
Check ($st.ExitCode -eq 0) "autoteste do app instalado (código $($st.ExitCode))"
if (Test-Path $report) { Get-Content $report -Raw | Write-Host }

Write-Host '== Execução residente + instância única'
$main = Start-Process -FilePath "$dir\Alfred.exe" -ArgumentList '--background' -PassThru
Start-Sleep -Seconds 8
Check (-not $main.HasExited) 'Alfred continua em execução em segundo plano'
$second = Start-Process -FilePath "$dir\Alfred.exe" -ArgumentList '--background' -PassThru
$second.WaitForExit(20000) | Out-Null
Check ($second.HasExited) 'segunda instância encerra e entrega o pedido à primeira'
$count = @(Get-Process -Name Alfred -ErrorAction SilentlyContinue).Count
Check ($count -eq 1) "apenas uma instância residente (encontradas: $count)"

Write-Host '== Desinstalação silenciosa (com o Alfred aberto)'
$u = Start-Process -FilePath "$dir\unins000.exe" -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/PURGE=1') -Wait -PassThru
Check ($u.ExitCode -eq 0) "desinstalador terminou com código 0 (obtido $($u.ExitCode))"
Start-Sleep -Seconds 5
$left = @(Get-Process -Name Alfred, soffice, soffice.bin, ffmpeg, pandoc -ErrorAction SilentlyContinue)
Check ($left.Count -eq 0) "nenhum processo residente após desinstalar (restantes: $($left.Name -join ', '))"
Check (-not (Test-Path "$dir\Alfred.exe")) 'arquivos removidos'
Check (-not (Test-Path $startMenu)) 'atalho do menu Iniciar removido'
Check (-not (Test-Path (Join-Path $env:APPDATA 'Microsoft\Windows\SendTo\Alfred.lnk'))) 'atalho Enviar para removido'
$run = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name Alfred -ErrorAction SilentlyContinue
Check (-not $run) 'entrada de inicialização removida'
Check (-not (Test-Path 'HKCU:\Software\Classes\*\shell\Alfred')) 'menu de contexto removido'
Check (-not (Test-Path 'HKCU:\Software\Alfred')) 'chave HKCU\Software\Alfred removida'
Check (-not (Test-Path (Join-Path $env:APPDATA 'Alfred'))) 'configurações removidas (/PURGE=1)'

if ($failures.Count -gt 0) {
  Write-Host "`n$($failures.Count) verificação(ões) falharam:" -ForegroundColor Red
  $failures | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
  exit 1
}
Write-Host "`nInstalador aprovado em todas as verificações." -ForegroundColor Green
