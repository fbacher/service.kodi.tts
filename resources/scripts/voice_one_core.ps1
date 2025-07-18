<#
Handles OneCore Voices


SAPI voices, OneCore voices, and the new natural voices for Narrator, belong to three different speech systems.

The assembly System.Speech only provides access to SAPI voices. On Windows 10/11, built-in SAPI voices have names ending in "Desktop", such as Microsoft Zira Desktop. (Don't have Desktop Suffix from this script

The voices shown in System Settings > Time & language > Speech > Voices are OneCore voices, which are the voices in Speech_OneCore registry key. Built-in OneCore voices don't have "Desktop" in their names, and there are some voices that are OneCore-exclusive, such as Microsoft Mark, which do not have corresponding SAPI versions. You can use OneCore voices in Powershell, but OneCore voices require using WinRT APIs, which requires a little bit more work.
#>
Function Voice-Sapi {
{
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

        [string]    $Voice = 'Microsoft Sean',

        [Parameter(
            Position = 2,
            Mandatory = $false
        )]
        [string]    $AudioPath
    )
     BEGIN {
         Add-Type -AssemblyName System.Runtime.WindowsRuntime

         # Load the required WinRT classes by using them once here
         [Windows.Foundation.IAsyncOperation`1, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
         [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime] | Out-Null
         [Windows.Media.SpeechSynthesis.SpeechSynthesisStream, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime] | Out-Null
     }

     PROCESS {
         # Some code to convert WinRT tasks to .NET tasks and wait on it
         $_taskMethods = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
             $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1
         }

         $asTaskGeneric = ($_taskMethods | Where-Object {
             $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
         })[0];
         Function Await($WinRtTask, $ResultType)
         {
             $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
             $netTask = $asTask.Invoke($null, @($WinRtTask))
             $netTask.Wait(-1) | Out-Null
             $netTask.Result
         }

         # List all OneCore voices
         $voices = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices

         $speak = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
         # Select a voice
         $speak.Voice = $voices | Where-Object {
             $_.DisplayName -eq $Voice
         } | Select-Object -First 1

         # Generate speech output and put it into a stream.
         # It provides no method to output the audio directly through speakers, so we will have to do this ourselves
         $winrtStream = Await ($speak.SynthesizeTextToStreamAsync($Message)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
         # Convert WinRT stream to .NET stream
         if ($AudioPath -ne '') {

             $winrtStream.
         }
         $stream = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($winrtStream)

         # Play the synthesized voice in the stream
         $player = New-Object System.Media.SoundPlayer $stream
         $player.PlaySync() # Play and wait
     }
     END {
    # Dispose resources
    $player.Dispose()
    $stream.Dispose()
    $winrtStream.Dispose()
    $speak.Dispose()
    }
}
