Function New-TextToSpeechMessage {
<#
.SYNOPSIS
    This will use Powershell to have a message read out loud through your computer speakers.

.NOTES
    Name: New-TextToSpeechMessage
    Author: theSysadminChannel
    Version: 1.0
    DateCreated: 2021-Feb-28

    From: https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.speechsynthesizer?view=netframework-4.8

    SetOutputToAudioStream, SetOutputToDefaultAudioDevice, SetOutputToNull, and
    SetOutputToWaveFile methods.

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

        [ValidateSet('David', 'Zira')]
        [string]    $Voice = 'Zira',

        [Parameter(
            Position = 2,
            Mandatory = $false
        )]
        [string]    $AudioPath
    )

    BEGIN {
        if (-not ([appdomain]::currentdomain.GetAssemblies() | Where-Object {$_.Location -eq 'C:\Windows\Microsoft.Net\assembly\GAC_MSIL\System.Speech\v4.0_4.0.0.0__31bf3856ad364e35\System.Speech.dll'})) {
            Add-Type -AssemblyName System.Speech
        }
    }

    PROCESS {
        try {
            $NewMessage = New-Object System.Speech.Synthesis.SpeechSynthesizer

            if ($Voice -eq 'Zira') {
                $NewMessage.SelectVoice("Microsoft Zira Desktop")
            } else {
                $NewMessage.SelectVoice("Microsoft David Desktop")
            }
            if ($AudioPath -ne '') {
                $NewMessage.SetOutputToWaveFile($AudioPath)
            }

            $NewMessage.Speak($Message)

        } catch {
            Write-Error $_.Exception.Message
        }
    }

    END {}
}
