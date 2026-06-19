; QSL73 Inno-Setup-Skript (Stable-Variante) -- Copyright (C) 2026 DF1DS
; AppId-GUID: {4FB91B69-CF4A-4DC9-B59D-2EA92B857D0B} -- NIEMALS ÄNDERN (Update/Deinstall)
; Für die Beta-Variante: AppId, AppName, DefaultDirName, AppDataPath-Pfad anpassen

[Setup]
AppId={{4FB91B69-CF4A-4DC9-B59D-2EA92B857D0B}
AppName=QSL73
AppVersion=0.1.0
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
Source: "..\dist\QSL73\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\QSL73"; Filename: "{app}\QSL73.exe"; IconFilename: "{app}\QSL73.exe"
Name: "{commondesktop}\QSL73"; Filename: "{app}\QSL73.exe"; Tasks: desktopicon; IconFilename: "{app}\QSL73.exe"
Name: "{group}\QSL73 deinstallieren"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\QSL73.exe"; Description: "{cm:LaunchProgram,QSL73}"; Flags: nowait postinstall skipifsilent

[Code]
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
