Welcome to the **Alpha1 **release of Kodi Text To Speech which provides basic TTS functionality to Kodi. It is based upon XBMC TTS which is no longer supported. This version of Kodi TTS is maintained by a different team and is a major release.

The goals of this early release are to provide basic functionality, iron out installation and configuration issues as well as get feedback. Functionality is limited: 

For Linux:

   * TTS engines: **eSpeak-ng** and **Google TTS**
   * Audio players: **MPV**, **Mplayer** and Kodi's built-in player (**XFS**)


For Windows:

   * TTS engines: **Navigator**, **eSpeak-ng** and **Google TTS**
   * Audio players: **MPV**, **Navigator** and **XFS**

#Installation

Since this Alpha release is not available from the Kodi repository, you will have to manually download and install Kodi TTS and dependent addons.

Download and install two addons which are NOT available from the repository.

  * script.module.langcodes from https://github.com/fbacher/script.module.langcodes/archive/refs/tags/v0.0.1-alpha.zip
  * service.kodi.tts from https://github.com/fbacher/service.kodi.tts/archive/refs/tags/v.0.0.2-alpha.zip

In Kodi, go to **Settings -> Add-ons -> Add-on browser -> Install from zip file**. There will probably be a warning about installing from unofficial sites. Select to allow the installation (only if you want to). **Install script.module.langcodes** first. Choose the path where you downloaded each zip file above. After installation is complete, exit Kodi.

##Install optional TTS engines and Players
After installing the kodi addons, you may need to install one or more players and TTS engines.

###Linux
I suggest that you install **mpv** to play audio. It is frugal with resources, has very good quality and when using caching and slave mode, is very responsive.

Optionally install eSpeak-NG, which is typically available from your distribution

Almost certainly mpv, eSpeak and mplayer are available from your normal Linux distribution channels. Should be easy to find and install.

###Windows
I suggest that you install **mpv** to play audio on Windows, it can play the audio produced by either Google TTS or Navigator. It supports cached audio as well as both mp3 and wave files. **mpv** is NOT required if you use Windows TTS (Navigator), but I prefer using the cache and mpv.

####Optionally install mpv

Install images can be found at https://github.com/shinchiro/mpv-winbuild-cmake/releases (this link is on the https://mpv.io/installation page). MPV version 0.37.0 or newer should be fine.

Carefully choose the correct image for your platform. You want something like: https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20250621/**mpv-aarch64-**20250621-git-18defc8.7z. You DON'T want ffmpeg or a 'dev' build.

The following file operations will require Admin privelege. I my case I was prompted to get Admin privelege.

Create the folder **C:\Program Files\mpv**
Unzip the downloaded files into the directory just created
As admin, run the script **C:\Program Files\mpv\installer\mpv-install.bat**

####Optionally install eSpeak-NG
Install eSpeak-NG through the Windows App installer.

###Configure paths and powershell scripts
Here you have to launch PowerShell and enter several commands.


REQUIRES that user MANUALLY set PowerShell's ExecutionPolicy on this file before running:

From the 'search' menu on bottom of desktop enter 'powershell'
    powershell
    select 'Run as Administrator'
Run the command
     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

When prompted, enter 'A' for 'all'
Enter your userid in place of <user_name>, below

While still in powershell, run the commands:
cd "c:\Users\<user_name>\AppData\Roaming\Kodi\addons\service.kodi.tts\resources\scripts"

Unblock-File -Path  .\config_env.ps1

Finally, run the script 
 . config_env       # Loads the script into powershell
  Config_Kodi_Env   # Runs the function defined in the script


At this point you should be able to run Kodi. A few seconds after starting Kodi you should hear a note, followed by speech. To see the configuration menu, you can press ***F12*** on the keyboard. If there is no voice or no configuration menu, then something went wrong and you should collect a log and send it to me.

###Third-party software:

####Players
MPV is followon to MPlayer. MPV has added numerous improvements which make it well suited for Kodi-TTS. In particular it has a 'slave-mode' that is superior to Mplayer's. Slave-mode allows Kodi-TTS to dynamically control what is played, canceled, paused, volume or speed changed, etc.. This is much better than killing and relaunching mpv on every utterance change.

####TTS Engines
googleTTS- My current favorite. It supports many languages and dialects. The naming is logical which should make it easy for users.

eSpeak-NG is an old standby that is fast, small and supports many languages. The voices sound distinctly computer generated. The universe of voices and the files required for them can be difficult to find and to get working. Finally, the metadata used to identify the voice (language, country, gender, etc.) is difficult to use programatically (or perhaps I haven't studied enough).
####Adding More Voices to eSpeak


Espeak-NG Linux is in multiple distributions
Windows Version 1.52.0 can be downloaded from https://github.com/espeak-ng/espeak-ng/releases


####Adding More Voices to Windows Narrator
This will require some research to find out what voices/languages are supported. Hopefully this can be determined dynamically

##Keyboard mappings
Kodi provides a means to define and modify numerous shortcuts for keyboards, ir-remotes and other devices. Kodi TTS comes with a small set of shortcuts to help you get started. Suggestions for improving these assignments are welcome.

Keyboard (and other input device) mappings are configured in .xml files in Kodi’s user_data/keymaps directory. The pre-configured one installed with Kodi is named “kodi.tts.keyboard.xml” It can be directly edited to change the key assignments. It can also be configured within Kodi.

What follows are the current definitions for all platforms:

keyboard shortcut F11
Function: Advanced to next logging mode
Cycles through Severe, error, warning, debug and info

keyboard shortcut ctrl F11
Function: dumps every python thread to the log

Function: Open Settings
Launches the Kodi TTS configuration settings dialog
keyboard shortcut: Ctrl-F12

Function: STOP
Causes currently voiced text to be skipped
keyboard shortcut: STOP

Function: VOICE_HINT
Voice hint toggles voicing hint text which is currently only embedded in the kodi.tts dialogs.
keyboard shortcut: Alt-h


Function: REPEAT
Repeat voicing the previous item, including complete context (Window name, heading, etc. on down to the item itself).
keyboard shortcut: shift-F12

Function EXTRA
Increase verbosity (more context)

Function ITEM_EXTRA

Function TOGGLE_ON_OFF
Starts/stops Kodi TTS
keyboard shortcut: f12

Changes the volume of the voiced text (not general volume)

Function VOL_UP
keyboard shortcut: ctrl + (control plus) TTS volume UP

Function VOL_DOWN
keyboard shortcut: ctrl - (control minus) TTS volume Down

Changes the speed of Voiced Text

Function: SPEED_UP / SLOW_DOWN
keyboard shortcut: alt +

Function: SLOW_DOWN
keyboard shortcut: alt -
Changes how fast text is read

Function: Display Help Dialog
This will launch Kodi’s document reader where you can get more information about how to use Kodi TTS.
keyboard shortcut: ctrl F1


###Configuration

Kodi TTS does NOT USE Kodi’s addon configuration menus. Instead, it uses custom configuration dialog and code. The reasons for this include:


* Instant audio feedback for changes as they are made
* Ability to revert changes
* Dynamic UI that presents valid choices for the current configuration
* Able to voice items that Kodi’s built-in configuration menus can not
* Ability to voice hints, additional detail as well as help (not fully implemented)