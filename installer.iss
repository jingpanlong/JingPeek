#ifndef StageDir
  #define StageDir "dist\JingPeek"
#endif
#ifndef OutputDirPath
  #define OutputDirPath "dist"
#endif
[Setup]
AppId={{07E41524-8B10-4DD4-A44A-72027D183E54}
AppName=景速览 JingPeek
AppVersion=1.6.0
AppPublisher=景同学
DefaultDirName={localappdata}\Programs\JingPeek
DefaultGroupName=JingPeek
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDirPath}
OutputBaseFilename=JingPeek-Setup-1.6.0-x64
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\JingPeek.exe
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
WizardImageFile=installer-large.bmp
WizardSmallImageFile=installer-small.bmp
WizardImageStretch=yes
CloseApplications=yes
RestartApplications=no
LicenseFile=LICENSE.txt
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"


[CustomMessages]
english.DesktopIcon=Create a desktop shortcut
chinesesimp.DesktopIcon=创建桌面快捷方式
english.Startup=Start JingPeek with Windows
chinesesimp.Startup=登录 Windows 后启动景速览
english.ContextTask=Add file context menu: Preview with JingPeek
chinesesimp.ContextTask=添加文件右键菜单：使用景速览预览
english.ContextLabel=Preview with JingPeek
chinesesimp.ContextLabel=使用景速览预览
english.Launch=Launch JingPeek
chinesesimp.Launch=启动景速览

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; Flags: unchecked
Name: "startup"; Description: "{cm:Startup}"; Flags: unchecked
Name: "contextmenu"; Description: "{cm:ContextTask}"; Flags: unchecked

[Files]
Source: "{#StageDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\JingPeek"; Filename: "{app}\JingPeek.exe"
Name: "{group}\Uninstall JingPeek"; Filename: "{uninstallexe}"
Name: "{autodesktop}\JingPeek"; Filename: "{app}\JingPeek.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\JingTongXue\JingPeek"; ValueType: string; ValueName: "language"; ValueData: "{code:InitialLanguage}"; Flags: createvalueifdoesntexist
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "JingPeek"; ValueData: """{app}\JingPeek.exe"" --background"; Tasks: startup; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\*\shell\JingPeek"; ValueType: string; ValueData: "{cm:ContextLabel}"; Tasks: contextmenu; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\JingPeek\command"; ValueType: string; ValueData: """{app}\JingPeek.exe"" ""%1"""; Tasks: contextmenu

[Run]
Filename: "{app}\JingPeek.exe"; Description: "{cm:Launch}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\JingPeek.exe"; Parameters: "--quit"; Flags: runhidden waituntilterminated; RunOnceId: "QuitJingPeek"

[Code]
function InitialLanguage(Param: String): String;
begin
  if ActiveLanguage = 'english' then Result := 'en_US' else Result := 'zh_CN';
end;
