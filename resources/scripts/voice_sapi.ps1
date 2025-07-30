Function Voice-Sapi {
<#
.SYNOPSIS
    This will use Powershell to have a message read out loud through your computer speakers.

.NOTES
    Name: New-TextToSpeechMessage
    Author: theSysadminChannel
    Version: 1.0
    DateCreated: 2021-Feb-28

    From: https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.speechsynthesizer?view=netframework-4.8

    See the following output methods. Note that to close the OutputToaudioStream, you have to set it to
    something else, like SetOutputToNull, otherwise it won't close (except probably exiting powershell)

    SetOutputToAudioStream(Stream, SpeechAudioFormatInfo)
    SetOutputToDefaultAudioDevice()
    SetOutputToNull()
    SetOutputToWaveStream(Stream)


    To generate speech, use the Speak, SpeakAsync, SpeakSsml, or SpeakSsmlAsync method.
    The SpeechSynthesizer can produce speech from text, a Prompt or PromptBuilder
    object, or from Speech Synthesis Markup Language (SSML) Version 1.0.

    To pause and resume speech synthesis, use the Pause and Resume methods.

    To add or remove lexicons, use the AddLexicon and RemoveLexicon methods. The
    SpeechSynthesizer can use one or more lexicons to guide its pronunciation of words.

    To modify the delivery of speech output, use the Rate and Volume properties.
.LINK
    https://thesysadminchannel.com/powershell-text-to-speech-how-to-guide -

.EXAMPLE
    New-TextToSpeechMessage 'This is the text I want to have read out loud' -Voice Zira
    or powershell.exe  "& { . '.\voice.ps1'; New-TextToSpeechMessage 'This is the text I want to have read out loud' Zira './foo.wav' }"
#>
    [CmdletBinding()]
    param(
        [Parameter(
            Position = 0,
            Mandatory = $true
        )]

        [string]    $Message,


        [Parameter(
            Position = 1,
            Mandatory = $false
        )]

        [string]    $Voice = 'Microsoft Zira Desktop',

        [Parameter(
            Position = 2,
            Mandatory = $false
        )]
        [string]    $AudioPath
    )

    BEGIN {
        [System.console]::InputEncoding = [System.console]::OutputEncoding = [System.Text.Encoding]::UTF8
        if (-not ([appdomain]::currentdomain.GetAssemblies() | Where-Object {$_.Location -eq 'C:\Windows\Microsoft.Net\assembly\GAC_MSIL\System.Speech\v4.0_4.0.0.0__31bf3856ad364e35\System.Speech.dll'})) {
            Add-Type -AssemblyName System.Speech
        }
    }

    PROCESS {
        try {
            $NewMessage = New-Object System.Speech.Synthesis.SpeechSynthesizer
            $NewMessage.SelectVoice($Voice)

            if ($AudioPath -ne '') {
                $NewMessage.SetOutputToWaveFile($AudioPath)
            }

            $NewMessage.Speak($Message)
            if ($AudioPath -ne '') {
                $NewMessage.SetOutputToNull()
            }

        } catch {
            Write-Error $_.Exception.Message
        }
    }

    END {}
}
