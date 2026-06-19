; QSL73 Inno-Setup-Skript (Beta-Variante) -- Copyright (C) 2026 DF1DS
; AppId-GUID: {A3F5C8D2-7E4B-4A91-B5C6-2D8E9F3A1B07} -- NIEMALS ÄNDERN (Update/Deinstall)
; Stabile Variante: installer/qsl73.iss (eigene GUID, eigener Pfad -- parallel installierbar)

#ifndef APP_VERSION
  #define APP_VERSION "0.1.0"
#endif

[Setup]
AppId={{A3F5C8D2-7E4B-4A91-B5C6-2D8E9F3A1B07}
AppName=QSL73 Beta
AppVersion={#APP_VERSION}
AppPublisher=DF1DS – Stephan Dahmen
AppPublisherURL=https://github.com/DF1DS/qsl73
AppSupportURL=https://github.com/DF1DS/qsl73/issues
DefaultDirName={autopf}\QSL73 Beta
DefaultGroupName=QSL73 Beta
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=QSL73-Beta-Setup
SetupIconFile=..\assets\qsl73.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
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
Name: "{group}\QSL73 Beta";                Filename: "{app}\QSL73.exe"; IconFilename: "{app}\QSL73.exe"
Name: "{group}\QSL73 Beta – Liesmich";    Filename: "{app}\LIESMICH.html"
Name: "{group}\QSL73 Beta – Änderungen";  Filename: "{app}\AENDERUNGEN.html"
Name: "{commondesktop}\QSL73 Beta";        Filename: "{app}\QSL73.exe"; Tasks: desktopicon; IconFilename: "{app}\QSL73.exe"
Name: "{group}\QSL73 Beta deinstallieren"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\QSL73.exe";           Description: "{cm:LaunchProgram,QSL73 Beta}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\LIESMICH.html";       Description: "Liesmich anzeigen";    Flags: postinstall unchecked skipifsilent shellexec
Filename: "{app}\AENDERUNGEN.html";    Description: "Änderungen anzeigen";  Flags: postinstall unchecked skipifsilent shellexec

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataPath: String;
  Antwort: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDataPath := ExpandConstant('{userappdata}\QSL73-Beta');
    if DirExists(AppDataPath) then
    begin
      Antwort := MsgBox(
        'Möchten Sie auch die persönlichen Daten und Einstellungen von QSL73 Beta entfernen?' + #13#10 +
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
