<#
Handles OneCore Voices


SAPI voices, OneCore voices, and the new natural voices for Narrator, belong to three different speech systems.

The assembly System.Speech only provides access to SAPI voices. On Windows 10/11, built-in SAPI voices have names ending in "Desktop", such as Microsoft Zira Desktop. (Don't have Desktop Suffix from this script

The voices shown in System Settings > Time & language > Speech > Voices are OneCore voices, which are the voices in Speech_OneCore registry key. Built-in OneCore voices don't have "Desktop" in their names, and there are some voices that are OneCore-exclusive, such as Microsoft Mark, which do not have corresponding SAPI versions. You can use OneCore voices in Powershell, but OneCore voices require using WinRT APIs, which requires a little bit more work.
#>
     Add-Type -AssemblyName System.Runtime.WindowsRuntime

     # Load the required WinRT classes by using them once here
     # [Windows.Foundation.IAsyncOperation`1, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
     [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime] | Out-Null
     # [Windows.Media.SpeechSynthesis.SpeechSynthesisStream, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime] | Out-Null

     # Some code to convert WinRT tasks to .NET tasks and wait on it
     $_taskMethods = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
         $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1
     }

     # List all OneCore voices

     $voices_json = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | ConvertTo-Json
     $voices_json

# Dispose resources
# $player.Dispose()
#  $stream.Dispose()
# $winrtStream.Dispose()
#  $speak.Dispose()
