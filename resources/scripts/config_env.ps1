Function Config_Kodi_Env {
<#
.SYNOPSIS
    Configure serveral environment variables, permissions, etc. for Kodi TTS on Windows.

    REQUIRES that user MANUALLY set PowerShell's ExecutionPolicy on this file before
    running:

	From the 'search' menu on bottom of screen enter 'powershell'
        powershell
        select 'Run as Administrator'
            Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
        When prompted, enter 'A' for 'all'
        Enter your userid in place of <user_name>, below
            Unblock-File -Path "c:\Users\<user_name>\AppData\Roaming\Kodi\addons\service.kodi.tts\resources\scripts\config_env.ps1"
        Finally, run the script (while still in powershell):
        cd c:\Users\<user_name>\AppData\Roaming\Kodi\addons\service.kodi.tts\resources\scripts
        . config_env
        Config_Kodi_Env


.NOTES
    Name: New-Config_Kodi_Env
    Author: Frank Feuerbacher
    Version: 1.0
    DateCreated: April 29, 2025

.EXAMPLE
#>

    [CmdletBinding()]
    param(
        [Parameter(
            Position = 0,
            Mandatory = $false
            )]

        [string]    $KodiPath = 'C:\Program Files\Kodi21',

        [Parameter(
            Position = 1,
            Mandatory = $false
            )]

        [string]  $TTSScriptPath = ("$env:USERPROFILE\" +
            "\AppData\Roaming\Kodi\addons\service.kodi.tts\resources\scripts"),
        [string]  $MPVScriptPath = ("$env:USERPROFILE\" +
            "\AppData\Roaming\Kodi\addons\service.kodi.tts\resources\scripts"),

        [Parameter(
            Position = 2,
            Mandatory = $false
        )]

        [string]    $MpvPath = $null,  # 'C:\Program Files\mpv',

        [Parameter(
            Position = 3,
            Mandatory = $false
        )]

        [string]    $MplayerPath = $null,  # 'C:\Program Files\Mplayer',

        [Parameter(
            Position = 4,
            Mandatory = $false
        )]
        [string]    $eSpeakPath = $null,  # 'C:\Program Files\eSpeak NG',

          [Parameter(
            Position = 5,
            Mandatory = $false
        )]
        [string]    $eSpeakDataPath = $null  # 'C:\Program Files\eSpeak NG\espeak-ng-data'
    )
    BEGIN {
    }

    PROCESS {
        try {
        if ( -not $KodiPath -or -not (Test-Path $KodiPath))
            {
                Write-Host "$KodiPath does not exist"
                $KodiPath = $null
            }

        if ( -not $TTSScriptPath -or -not (Test-Path $TTSScriptPath))
           {
                WRITE-HOST "$TTSScriptPath"
                $USER_HOME = "$env:USERPROFILE"
                $SUFFIX = "\AppData\Roaming\Kodi\addons\service.kodi.tts\resources\scripts"
                $TSScriptPath = "$USER_HOME$SUFFIX"
           }

        if ( $eSpeakPath -and -not (Test-Path $eSpeakPath))
            {
                Write-Host "$eSpeakPath does not exist"
                $eSpeakPath = $null
            }

        if ( $eSpeakDataPath -and -not (Test-Path $eSpeakDataPath))
            {
                Write-Host "$eSpeakDataPath does not exist"
                $eSpeakDataPath = $null
            }

        if ( $MpvPath -and -not (Test-Path $MpvPath))
            {
                Write-Host "$MpvPath does not exist: $MpvPath"
                $MpvPath = $null
            }
        if ( $MplayerPath -and -not (Test-Path $MplayerPath))
            {
                Write-Host "$MplayerPath does not exist"
                $MplayerPath = $null
            }

        if ($KodiPath)
        {
            [System.Environment]::SetEnvironmentVariable("KODI_PATH", $KodiPath,
                [System.EnvironmentVariableTarget]::User)
            Write-Host "Defined KODI_PATH environment variable as ${KodiPath}"
        }

        if ($TTSScriptPath)
        {
            Write-Host "$TTSScriptPath\voice.ps1"
            Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
            Unblock-File -Path "$TTSScriptPath\voice.ps1"
        }

        # if ($MPVScriptPath)
        # {
        #     Write-Host "$MPVScriptPath\mpv_socket.ps1"
        #     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
        #     Unblock-File -Path "$MPVScriptPath\mpv_socket.ps1"
        # }

         if ($eSpeakPath)
        {
            [System.Environment]::SetEnvironmentVariable("ESPEAK_PATH", $eSpeakPath,
                [System.EnvironmentVariableTarget]::User)
            Write-Host "Defined ESPEAK_PATH environment variable as $eSpeakPath"
        }

         if ($eSpeakDataPath)
        {
            [System.Environment]::SetEnvironmentVariable("ESPEAK_DATA_PATH",
                    $eSpeakDataPath,
                [System.EnvironmentVariableTarget]::User)
            Write-Host "Defined ESPEAK_DATA_PATH environment variable as $eSpeakDataPath"
        }

        if ($MpvPath)
        {
            [System.Environment]::SetEnvironmentVariable("MPV_PATH", $MpvPath,
                [System.EnvironmentVariableTarget]::User)
            Write-Host "Defined MPV_PATH environment variable as $MpvPath"
        }

        if ($MplayerPath)
        {
            [System.Environment]::SetEnvironmentVariable("MPLAYER_PATH", $MplayerPath,
                [System.EnvironmentVariableTarget]::User)
            Write-Host "Defined MPLAYER_PATH environment variable as $MplayerPath"
        }

        } catch {
            Write-Error $_.Exception.Message
        }

    }

    END { }
}
