Unicode true
!include "MUI2.nsh"
!include "x64.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"
!ifndef VERSION
  !define VERSION "0.4.0"
!endif
Name "GCP Yt Rebalance"
OutFile "..\dist\GCP-Yt-Rebalance-${VERSION}-Windows-x64-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\GCP Yt Rebalance"
InstallDirRegKey HKCU "Software\GestaoCulturalPro\GCPYtRebalance" "InstallDir"
RequestExecutionLevel user
ManifestDPIAware true
SetCompressor lzma
VIProductVersion "${VERSION}.0"
VIAddVersionKey /LANG=1046 "ProductName" "GCP Yt Rebalance"
VIAddVersionKey /LANG=1046 "CompanyName" "Bruno Albertini"
VIAddVersionKey /LANG=1046 "FileDescription" "Instalador do GCP Yt Rebalance"
VIAddVersionKey /LANG=1046 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=1046 "ProductVersion" "${VERSION}"
VIAddVersionKey /LANG=1046 "LegalCopyright" "Bruno Albertini — Gestão Cultural Pro"
!define MUI_ICON "..\assets\branding\taskbar.ico"
!define MUI_UNICON "..\assets\branding\taskbar.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "GCP Yt Rebalance"
!define MUI_WELCOMEPAGE_TEXT "Áudio, vídeo e karaokê no seu computador.$\r$\n$\r$\nTudo incluído: motor de separação, modelo, FFmpeg/ffprobe, downloader e runtime. Nada para baixar por fora.$\r$\n$\r$\nDesenvolvido por Bruno Albertini$\r$\nGestão Cultural Pro"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\GCP Yt Rebalance.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Abrir GCP Yt Rebalance"
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "PortugueseBR"
Var TestMode

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "Esta versão requer Windows de 64 bits."
    Abort
  ${EndIf}
  SetRegView 64
  ${GetParameters} $0
  ClearErrors
  ${GetOptions} $0 "/TESTMODE" $TestMode
  ${If} ${Errors}
    StrCpy $TestMode "0"
  ${Else}
    StrCpy $TestMode "1"
  ${EndIf}
FunctionEnd

Section "GCP Yt Rebalance (completo)" Core
  SectionIn RO
  SetOutPath "$INSTDIR"
  ClearErrors
  ; Atualização: aguarda o aplicativo anterior fechar (até 10 s).
  StrCpy $2 0
  wait_app:
  ClearErrors
  Delete "$INSTDIR\GCP Yt Rebalance.exe"
  ${If} ${Errors}
    IntOp $2 $2 + 1
    ${If} $2 < 20
      Sleep 500
      Goto wait_app
    ${EndIf}
  ${EndIf}
  ; Atualização: remove o payload anterior antes de copiar a nova versão.
  RMDir /r "$INSTDIR\_internal"
  File /r "..\dist\windows\GCP Yt Rebalance\*.*"
  ${If} ${Errors}
    MessageBox MB_ICONSTOP "Não foi possível copiar todos os componentes. Verifique espaço livre e permissões."
    Abort
  ${EndIf}
  FileOpen $0 "$INSTDIR\gcp-install.marker" w
  FileWrite $0 "GCP Yt Rebalance"
  FileClose $0
  WriteUninstaller "$INSTDIR\Desinstalar.exe"
  ${If} $TestMode == "0"
    WriteRegStr HKCU "Software\GestaoCulturalPro\GCPYtRebalance" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GCPYtRebalance" "DisplayName" "GCP Yt Rebalance"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GCPYtRebalance" "DisplayVersion" "${VERSION}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GCPYtRebalance" "Publisher" "Bruno Albertini"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GCPYtRebalance" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GCPYtRebalance" "DisplayIcon" "$INSTDIR\GCP Yt Rebalance.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GCPYtRebalance" "UninstallString" '$\"$INSTDIR\Desinstalar.exe$\"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GCPYtRebalance" "URLInfoAbout" "https://gestaoculturalpro.com.br"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GCPYtRebalance" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GCPYtRebalance" "NoRepair" 1
    ; Remover somente o atalho legado cujo nome foi gravado com codificação incorreta.
    Delete "$SMPROGRAMS\GestÃ£o Cultural Pro\GCP Yt Rebalance.lnk"
    RMDir "$SMPROGRAMS\GestÃ£o Cultural Pro"
    CreateDirectory "$SMPROGRAMS\Gestão Cultural Pro"
    CreateShortCut "$SMPROGRAMS\Gestão Cultural Pro\GCP Yt Rebalance.lnk" "$INSTDIR\GCP Yt Rebalance.exe"
  ${EndIf}
SectionEnd

Section "Atalho na área de trabalho" Desktop
  ${If} $TestMode == "0"
    CreateShortCut "$DESKTOP\GCP Yt Rebalance.lnk" "$INSTDIR\GCP Yt Rebalance.exe"
  ${EndIf}
SectionEnd

Function un.onInit
  SetRegView 64
  ${GetParameters} $0
  ClearErrors
  ${GetOptions} $0 "/TESTMODE" $TestMode
  ${If} ${Errors}
    StrCpy $TestMode "0"
  ${Else}
    StrCpy $TestMode "1"
  ${EndIf}
FunctionEnd

Section "Uninstall"
  IfFileExists "$INSTDIR\gcp-install.marker" +3 0
    MessageBox MB_ICONSTOP "Identificação da instalação ausente. Nenhum arquivo foi removido."
    Abort
  FileOpen $0 "$INSTDIR\gcp-install.marker" r
  FileRead $0 $1
  FileClose $0
  StrCpy $1 $1 16
  ${If} $1 != "GCP Yt Rebalance"
    Abort
  ${EndIf}
  ; Remover somente componentes próprios; saídas, histórico e preferências ficam fora desta pasta.
  RMDir /r "$INSTDIR\_internal"
  Delete "$INSTDIR\GCP Yt Rebalance.exe"
  Delete "$INSTDIR\gcp-install.marker"
  Delete "$INSTDIR\Desinstalar.exe"
  RMDir "$INSTDIR"
  ${If} $TestMode == "0"
    Delete "$DESKTOP\GCP Yt Rebalance.lnk"
    Delete "$SMPROGRAMS\Gestão Cultural Pro\GCP Yt Rebalance.lnk"
    RMDir "$SMPROGRAMS\Gestão Cultural Pro"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GCPYtRebalance"
    DeleteRegKey HKCU "Software\GestaoCulturalPro\GCPYtRebalance"
  ${EndIf}
SectionEnd
