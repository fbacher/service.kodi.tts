cd "%APPDATA%\Kodi\addons\service.kodi.tts\resources\scripts"
powershell -command ^
"Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force; ^
Unblock-File -Path config_env.ps1; ^
. .\config_env.ps1; ^
Config_Kodi_Env"
