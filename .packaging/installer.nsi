; Installation de Flow-EDT pour Windows (NSIS 3, Unicode).
;
; Compilé depuis Linux par .packaging/build.py, d'où les chemins en « / » :
; makensis les convertit lui-même. Les variables APP_VERSION, APP_SOURCE,
; OUT_FILE, ICON_FILE et LICENSE_FILE sont fournies par le script de build.

Unicode true

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

!define APP_NAME "Flow-EDT"
!define APP_PUBLISHER "B.Dupont"
!define APP_URL "https://github.com/GitKernelDesign/FlowEDT"
!define APP_EXE "Flow-EDT.exe"
!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\FlowEDT"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "${OUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\${APP_NAME}"
InstallDirRegKey HKCU "Software\${APP_NAME}" "InstallDir"

; Installation par utilisateur : aucun droit administrateur demandé.
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetCompressorDictSize 64
CRCCheck on
XPStyle on
BrandingText "${APP_NAME} ${APP_VERSION}"

VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=1036 "ProductName" "${APP_NAME}"
VIAddVersionKey /LANG=1036 "ProductVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1036 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1036 "FileDescription" "${APP_NAME} — générateur d'emplois du temps"
VIAddVersionKey /LANG=1036 "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey /LANG=1036 "LegalCopyright" "GPL-3.0 — ${APP_PUBLISHER}"
VIAddVersionKey /LANG=1036 "LegalTrademarks" "Logiciel libre sous licence GPL-3.0"

; --------------------------------------------------------------------------
; Interface

!define MUI_ICON "${ICON_FILE}"
!define MUI_UNICON "${ICON_FILE}"
!define MUI_ABORTWARNING
!define MUI_ABORTWARNING_TEXT "Voulez-vous vraiment interrompre l'installation de ${APP_NAME} ?"
!define MUI_WELCOMEPAGE_TITLE "Installation de ${APP_NAME} ${APP_VERSION}"
!define MUI_WELCOMEPAGE_TEXT "Cet assistant va installer ${APP_NAME}, le générateur d'emplois du temps pour établissement scolaire.$\r$\n$\r$\nAucune donnée n'est envoyée sur Internet : tout reste sur cet ordinateur.$\r$\n$\r$\nCliquez sur Suivant pour continuer."
!define MUI_FINISHPAGE_TITLE "${APP_NAME} est installé"
!define MUI_FINISHPAGE_TEXT "${APP_NAME} ${APP_VERSION} est prêt à être utilisé.$\r$\n$\r$\nLes raccourcis ont été créés sur le Bureau et dans le menu Démarrer.$\r$\n$\r$\nLicence GPL-3.0 — logiciel libre, sans garantie."
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Lancer ${APP_NAME} maintenant"
!define MUI_FINISHPAGE_LINK "Code source sur GitHub"
!define MUI_FINISHPAGE_LINK_LOCATION "${APP_URL}"
!define MUI_DIRECTORYPAGE_TEXT_TOP "Choisissez le dossier d'installation de ${APP_NAME}. L'installation se fait pour l'utilisateur courant, sans droits administrateur."
!define MUI_UNCONFIRMPAGE_TEXT_TOP "La désinstallation supprime le programme. Les emplois du temps enregistrés (dossier de données utilisateur) sont conservés."
!define MUI_UNFINISHPAGE_NOAUTOCLOSE

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${LICENSE_FILE}"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "French"

; --------------------------------------------------------------------------
; Installation

Section "Programme" SecMain
    SectionIn RO
    SetShellVarContext current

    ; Fermer une éventuelle instance en cours pour pouvoir remplacer les fichiers.
    nsExec::Exec 'taskkill /F /IM "${APP_EXE}"'
    Pop $0
    Sleep 400

    SetOutPath "$INSTDIR"
    File /r "${APP_SOURCE}/*"

    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\Désinstaller ${APP_NAME}.lnk" "$INSTDIR\Uninstall.exe"
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

    WriteUninstaller "$INSTDIR\Uninstall.exe"

    WriteRegStr HKCU "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\${APP_NAME}" "Version" "${APP_VERSION}"

    WriteRegStr HKCU "${UNINST_KEY}" "DisplayName" "${APP_NAME} — générateur d'emplois du temps"
    WriteRegStr HKCU "${UNINST_KEY}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "${UNINST_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
    WriteRegStr HKCU "${UNINST_KEY}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKCU "${UNINST_KEY}" "URLInfoAbout" "${APP_URL}"
    WriteRegStr HKCU "${UNINST_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKCU "${UNINST_KEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
    WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
    WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1
    WriteRegDWORD HKCU "${UNINST_KEY}" "EstimatedSize" ${APP_SIZE_KB}

    ; Réassociation de l'icône du dossier et du cache du Bureau.
    System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, i 0, i 0)'
SectionEnd

; --------------------------------------------------------------------------
; Désinstallation

Section "Uninstall"
    SetShellVarContext current

    nsExec::Exec 'taskkill /F /IM "${APP_EXE}"'
    Pop $0
    Sleep 400

    Delete "$DESKTOP\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Désinstaller ${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"

    ; Les données utilisateur (%APPDATA%\Flow-EDT) ne sont jamais supprimées.
    DeleteRegKey HKCU "${UNINST_KEY}"
    DeleteRegKey HKCU "Software\${APP_NAME}"

    RMDir /r "$INSTDIR"
SectionEnd

Function .onInit
    ; Installation silencieuse possible : /S
    ${If} ${FileExists} "$INSTDIR\${APP_EXE}"
        ; Mise à jour : on propose le même dossier par défaut.
    ${EndIf}
FunctionEnd
