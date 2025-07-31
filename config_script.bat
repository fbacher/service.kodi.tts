@ECHO OFF
CLS

:: ============================================================================
:: Check for Administrative Privileges and self-elevate if not present
:: ============================================================================
NET FILE >NUL 2>NUL
IF '%ERRORLEVEL%' NEQ '0' (
    ECHO Requesting administrative privileges...
    ECHO(
    powershell.exe -Command "Start-Process '%~f0' -Verb RunAs"
    EXIT /B
)

:: ============================================================================
:: Your Administrative Code Starts Here (This section only runs if elevated)
:: ============================================================================
@ECHO OFF
cd "%APPDATA%\Kodi\addons\service.kodi.tts\resources\scripts"
powershell -command ^
"Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force; ^
Unblock-File -Path config_env.ps1; ^
. .\config_env.ps1; ^
Config_Kodi_Env"

IF '%ERRORLEVEL%' EQU '0' (
    ECHO Successfully Configured KODI TTS.
    exit /b 0
) ELSE (
    ECHO FAILED to Configure Kodi TTS.
    exit /b 1
)

GOTO :EOF
