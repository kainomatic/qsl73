; QSL73 Inno-Setup-Skript (Stable-Variante) -- Copyright (C) 2026 DF1DS
; AppId-GUID: {4FB91B69-CF4A-4DC9-B59D-2EA92B857D0B} -- NIEMALS ÄNDERN (Update/Deinstall)
; Beta-Variante: installer/qsl73-beta.iss (eigene GUID, parallel installierbar)

; APP_VERSION wird vom Release-Workflow per /DAPP_VERSION=x.y.z injiziert.
; Lokaler Build ohne /D-Flag verwendet den hardkodierten Fallback.
#ifndef APP_VERSION
  #define APP_VERSION "0.1.0"
#endif

[Setup]
AppId={{4FB91B69-CF4A-4DC9-B59D-2EA92B857D0B}
AppName=QSL73
AppVersion={#APP_VERSION}
AppPublisher=DF1DS – Stephan Dahmen
AppPublisherURL=https://github.com/DF1DS/qsl73
AppSupportURL=https://github.com/DF1DS/qsl73/issues
DefaultDirName={autopf}\QSL73
DefaultGroupName=QSL73
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=QSL73-Setup
SetupIconFile=..\assets\qsl73.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
CloseApplications=yes
RestartApplications=no
AppMutex=QSL73-Stable
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
UninstallDisplayIcon={app}\QSL73.exe
LicenseFile=..\LICENSE
MinVersion=10.0
DisableProgramGroupPage=yes

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\QSL73\*";       DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; HTML-Infodateien (erzeugt vor dem ISCC-Lauf durch tools/make_docs_html.py)
Source: "docs\LIESMICH.html";    DestDir: "{app}"; Flags: ignoreversion
Source: "docs\AENDERUNGEN.html"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\QSL73";                Filename: "{app}\QSL73.exe"; IconFilename: "{app}\QSL73.exe"
Name: "{commondesktop}\QSL73";        Filename: "{app}\QSL73.exe"; Tasks: desktopicon; IconFilename: "{app}\QSL73.exe"
Name: "{group}\QSL73 deinstallieren"; Filename: "{uninstallexe}"

[Run]
; runascurrentuser: QSL73 startet als normaler Nutzer, nicht mit Admin-Rechten des Installers.
; Interaktive Installation: Abschluss-Checkbox (skipifsilent → bei /SILENT übersprungen).
Filename: "{app}\QSL73.exe";           Description: "{cm:LaunchProgram,QSL73}"; Flags: nowait postinstall runascurrentuser skipifsilent
; Self-Update (/SILENT /RESTARTQSL73): automatischer Neustart — ShouldRestartApp prüft den Flag.
Filename: "{app}\QSL73.exe";           Flags: nowait runascurrentuser; Check: ShouldRestartApp
Filename: "{app}\LIESMICH.html";       Description: "Liesmich anzeigen";    Flags: postinstall unchecked skipifsilent shellexec
Filename: "{app}\AENDERUNGEN.html";    Description: "Änderungen anzeigen";  Flags: postinstall unchecked skipifsilent shellexec

[Code]
{ Self-Update-Neustart: QSL73 startet neu, wenn der Installer mit /RESTARTQSL73 aufgerufen wurde. }
function ShouldRestartApp: Boolean;
begin
  Result := WizardSilent() and (Pos('/RESTARTQSL73', UpperCase(GetCmdTail)) > 0);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataPath: String;
  Antwort: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDataPath := ExpandConstant('{userappdata}\QSL73');
    if DirExists(AppDataPath) then
    begin
      Antwort := MsgBox(
        'Möchten Sie auch die persönlichen Daten und Einstellungen von QSL73 entfernen?' + #13#10 +
        '(Konfiguration, Logs, Sicherungen in ' + AppDataPath + ')' + #13#10 + #13#10 +
        'Empfehlung: NEIN – Einstellungen bleiben für eine spätere Neuinstallation erhalten.',
        mbConfirmation,
        MB_YESNO or MB_DEFBUTTON2
      );
      if Antwort = IDYES then
      begin
        DelTree(AppDataPath, True, True, True);
      end;
    end;
  end;
end;
