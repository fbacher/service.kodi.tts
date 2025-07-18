# SAPI voice
# https://learn-powershell.net/2013/12/04/give-powershell-a-voice-using-the-speechsynthesizer-class/
Function GetSapiVoices {

  #  if (-not ([appdomain]::currentdomain.GetAssemblies() | Where-Object {$_.Location -eq 'C:\Windows\Microsoft.Net\assembly\GAC_MSIL\System.Speech\v4.0_4.0.0.0__31bf3856ad364e35\System.Speech.dll'})) {
  #          Add-Type -AssemblyName System.Speech
  #      }
  #  }

Add-Type -AssemblyName System.speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
# $speak | Get-Member  # Shows API calls
# $echo "SAPI Voices"
# $speak.GetInstalledVoices()
$sapi_voices = $speak.GetInstalledVoices().VoiceInfo | ConvertTo-Json
$sapi_voices 
$speak.Dispose()
}

# Just run it
GetSapiVoices