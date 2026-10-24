; Instalador do Alfred (Inno Setup 6.3+)
; Compilar:  ISCC.exe /DAppVersion=2.0.0 /DEdition=full packaging\installer\Alfred.iss
; Edition: full (com LibreOffice) | lite (sem LibreOffice)

#ifndef AppVersion
  #define AppVersion "2.0.0"
#endif
#ifndef Edition
  #define Edition "full"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\dist\Alfred"
#endif
#if Edition == "full"
  #define EditionLabel "Completa"
#else
  #define EditionLabel "Leve"
#endif
#define AppName "Alfred"
#define AppExe "Alfred.exe"
#define AppPublisher "@ilgn3r"
#define AppURL "https://www.youtube.com/@ilgn3r"
#define Root "..\.."

[Setup]
; Mesmo AppId da versão 1.x: o instalador atualiza a instalação antiga.
AppId={{3B741ED6-1A2B-48B8-BC4D-FC2B0243EC95}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion} (edição {#EditionLabel})
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppComments=Algumas tarefas é melhor deixar para o Alfred.
AppCopyright=Código AGPL-3.0-or-later · Arte © {#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
OutputDir={#Root}\release
OutputBaseFilename=Alfred_Setup_{#AppVersion}_{#EditionLabel}_x64
SetupIconFile={#Root}\assets\alfred.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
WizardResizable=no
WizardImageFile={#Root}\assets\installer\wizard_100.bmp,{#Root}\assets\installer\wizard_125.bmp,{#Root}\assets\installer\wizard_150.bmp,{#Root}\assets\installer\wizard_175.bmp,{#Root}\assets\installer\wizard_200.bmp,{#Root}\assets\installer\wizard_250.bmp
WizardSmallImageFile={#Root}\assets\installer\small_100.bmp,{#Root}\assets\installer\small_125.bmp,{#Root}\assets\installer\small_150.bmp,{#Root}\assets\installer\small_175.bmp,{#Root}\assets\installer\small_200.bmp,{#Root}\assets\installer\small_250.bmp
LicenseFile=LICENCA_INSTALADOR.txt
; O compilador do Inno Setup é 32 bits: "ultra64" com várias threads estoura a memória
; ("Out of memory"). A compressão roda num processo separado (64 bits quando disponível).
#ifdef FastCompression
Compression=lzma2/fast
#else
Compression=lzma2/max
#endif
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=1
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
UsedUserAreasWarning=no
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Instalador do {#AppName}
VersionInfoProductName={#AppName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
brazilianportuguese.GroupShortcuts=Atalhos:
brazilianportuguese.GroupIntegration=Integração com o Windows:
brazilianportuguese.TaskDesktop=Criar atalho na área de trabalho
brazilianportuguese.TaskStartup=Iniciar o Alfred com o Windows (recomendado para o gesto Shift + arrastar)
brazilianportuguese.TaskGesture=Ativar a roda de conversão com Shift + arrastar no Explorador de Arquivos
brazilianportuguese.TaskContext=Adicionar “Converter com Alfred” ao clique direito
brazilianportuguese.TaskSendTo=Adicionar o Alfred ao menu “Enviar para”
brazilianportuguese.Launch=Abrir o Alfred agora
brazilianportuguese.RemoveData=Deseja apagar também as configurações e o histórico do Alfred?
english.GroupShortcuts=Shortcuts:
english.GroupIntegration=Windows integration:
english.TaskDesktop=Create a desktop shortcut
english.TaskStartup=Start Alfred with Windows (recommended for the Shift + drag gesture)
english.TaskGesture=Enable the conversion wheel with Shift + drag in File Explorer
english.TaskContext=Add “Converter com Alfred” to the right-click menu
english.TaskSendTo=Add Alfred to the “Send to” menu
english.Launch=Open Alfred now
english.RemoveData=Also delete Alfred's settings and history?

[Tasks]
Name: "desktopicon"; Description: "{cm:TaskDesktop}"; GroupDescription: "{cm:GroupShortcuts}"; Flags: unchecked
Name: "startup"; Description: "{cm:TaskStartup}"; GroupDescription: "{cm:GroupIntegration}"
Name: "gesture"; Description: "{cm:TaskGesture}"; GroupDescription: "{cm:GroupIntegration}"
Name: "contextmenu"; Description: "{cm:TaskContext}"; GroupDescription: "{cm:GroupIntegration}"
Name: "sendto"; Description: "{cm:TaskSendTo}"; GroupDescription: "{cm:GroupIntegration}"

[InstallDelete]
; Atualização limpa: remove o runtime e motores da versão anterior (inclui a pasta LibreOffice da v1).
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\engines"
Type: filesandordirs; Name: "{app}\licenses"
Type: filesandordirs; Name: "{app}\LibreOffice"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "ilgn3r.Alfred"; Comment: "Algumas tarefas é melhor deixar para o Alfred."
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "ilgn3r.Alfred"; Tasks: desktopicon
Name: "{usersendto}\{#AppName}"; Filename: "{app}\{#AppExe}"; Parameters: "--open"; Tasks: sendto

[Registry]
; Inicialização com o Windows (em segundo plano, só a bandeja)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Alfred"; ValueData: """{app}\{#AppExe}"" --background"; Tasks: startup; Flags: uninsdeletevalue
; Menu de contexto (arquivos e pastas)
Root: HKCU; Subkey: "Software\Classes\*\shell\Alfred"; ValueType: string; ValueName: ""; ValueData: "Converter com Alfred"; Tasks: contextmenu; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\Alfred"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#AppExe},0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\Alfred"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\Alfred\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" --open ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\shell\Alfred"; ValueType: string; ValueName: ""; ValueData: "Converter com Alfred"; Tasks: contextmenu; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Directory\shell\Alfred"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#AppExe},0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\shell\Alfred\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" --open ""%1"""; Tasks: contextmenu
; Escolhas do assistente, aplicadas pelo Alfred na próxima inicialização
Root: HKCU; Subkey: "Software\Alfred\InstallerDefaults"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Alfred\InstallerDefaults"; ValueType: dword; ValueName: "Pending"; ValueData: 1
Root: HKCU; Subkey: "Software\Alfred\InstallerDefaults"; ValueType: dword; ValueName: "ExplorerGesture"; ValueData: 1; Tasks: gesture
Root: HKCU; Subkey: "Software\Alfred\InstallerDefaults"; ValueType: dword; ValueName: "ExplorerGesture"; ValueData: 0; Tasks: not gesture
Root: HKCU; Subkey: "Software\Alfred\InstallerDefaults"; ValueType: dword; ValueName: "ContextMenu"; ValueData: 1; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Alfred\InstallerDefaults"; ValueType: dword; ValueName: "ContextMenu"; ValueData: 0; Tasks: not contextmenu
Root: HKCU; Subkey: "Software\Alfred\InstallerDefaults"; ValueType: dword; ValueName: "StartWithWindows"; ValueData: 1; Tasks: startup
Root: HKCU; Subkey: "Software\Alfred\InstallerDefaults"; ValueType: dword; ValueName: "StartWithWindows"; ValueData: 0; Tasks: not startup

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:Launch}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; 1) pede para a instância em execução encerrar; 2) garante o encerramento; 3) remove integrações criadas pelo app
Filename: "{app}\{#AppExe}"; Parameters: "--quit"; Flags: runhidden waituntilterminated; RunOnceId: "QuitAlfred"
Filename: "{sys}\taskkill.exe"; Parameters: "/F /T /IM {#AppExe}"; Flags: runhidden waituntilterminated; RunOnceId: "KillAlfred"
Filename: "{app}\{#AppExe}"; Parameters: "--unregister"; Flags: runhidden waituntilterminated; RunOnceId: "UnregisterAlfred"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function KillRunningAlfred(): Boolean;
var
  ResultCode: Integer;
begin
  { O Alfred roda na bandeja: encerra antes de copiar arquivos (instalação/atualização). }
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM {#AppExe}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  KillRunningAlfred();
  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Purge: Boolean;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    { Remoção de dados do usuário: pergunta no modo interativo; /PURGE=1 no modo silencioso. }
    Purge := ExpandConstant('{param:PURGE|0}') = '1';
    if (not UninstallSilent) and (not Purge) then
      Purge := MsgBox(CustomMessage('RemoveData'), mbConfirmation, MB_YESNO) = IDYES;
    if Purge then
    begin
      DelTree(ExpandConstant('{userappdata}\Alfred'), True, True, True);
      DelTree(ExpandConstant('{localappdata}\Alfred'), True, True, True);
    end;
  end;
end;
