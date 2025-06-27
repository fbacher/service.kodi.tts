Welcome to the **Alpha2 **release of Kodi Text To Speech which provides basic TTS functionality to Kodi. It is based upon XBMC TTS which is no longer supported. This version of Kodi TTS is maintained by a different team and is a major release.

The goals of this early release are to provide basic functionality, iron out installation and configuration issues as well as get feedback. Functionality is limited to just several TTS engines and players:

For Linux:

   * TTS engines: **eSpeak-ng** and **Google TTS**
   * Audio players: **MPV**, **Mplayer** and Kodi's built-in player (**XFS**)


For Windows:

   * TTS engines: **Navigator**, **eSpeak-ng** and **Google TTS**
   * Audio players: **MPV**, **Navigator** and **XFS**

#Installation

First, install the latest released version of Kodi.

Next, install the Kodi TTS addon as well as its dependents. Since this Alpha release is not available from the Kodi repository, you will have to manually download and install Kodi TTS and a dependent addon.

Download the two addons:

  * [script.module.langcodes](https://github.com/fbacher/script.module.langcodes/archive/refs/tags/v0.0.1-alpha.zip)
  * [service.kodi.tts](https://github.com/fbacher/service.kodi.tts/archive/refs/tags/v.0.0.2-alpha.zip)

To install, in Kodi, go to **Settings -> Add-ons -> Add-on browser -> Install from zip file**. There will probably be a warning about installing from unofficial sites. Select to allow the installation. Install **script.module.langcodes** first. Choose the path where you downloaded each zip file above. After the installation of both is complete, exit Kodi.

##Install optional TTS engines and Players
After installing the kodi addons, you may need to install one or more players and TTS engines.

###Linux
I suggest that you install **mpv** to play audio. It is frugal with resources, is of very good quality, is very responsive when used with caching and slave mode. **mplayer** is the predessor to mpv and is supported for those who want it.

Optionally install eSpeak-NG, which is typically available from your distribution.

Almost certainly mpv, eSpeak and mplayer are available from your normal Linux distribution channels. They should be easy to find and install.

###Windows
Windows TTS (Navigator) is fairly high quality, runs locally and is builtin. It does require a Powershell script to use, which must be configured.

Google TTS comes with Kodi TTS and requires no configuration. It does require mpv, however.

I suggest that you install **mpv** to play audio on Windows, it can play the audio produced by either Google TTS or Navigator. It supports cached audio as well as both mp3 and wave files. **mpv** is NOT required if you use Windows TTS (Navigator), but I prefer using the cache and mpv.

eSpeak is available for those who like it.

####mpv

Install images for [**mpv** are here](https://github.com/shinchiro/mpv-winbuild-cmake/releases) (this link is from [the official mpv installation page](the https://mpv.io/installation)). MPV version 0.37.0 or newer should be fine.

Carefully choose the correct image for your platform. You want something that has "mpv-x86_64" in its name, like: https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20250623/**mpv-x86_64**-20250623-git-18defc8.7z. You DON'T want ffmpeg or a 'dev' build. If the build you install doesn't run (if it launches it should be ok), then try another build. Some are built with different compilers, others are for different cpus. Intel/amd should have "mpv-x86_64" in the name.

The following file operations will require Admin privilege.

  * Create the folder **C:\Program Files\mpv**
  * Unzip the downloaded files into the directory just created
  * As admin, run the script **C:\Program Files\mpv\installer\mpv-install.bat**

##
####Optionally install eSpeak-NG
Install eSpeak-NG through the Windows App installer.

###Configure paths and powershell scripts
Here you have to launch PowerShell and enter several commands.


REQUIRES that user MANUALLY set PowerShell's ExecutionPolicy on this file before running:

From the 'search' menu on bottom of desktop enter 'powershell'

    * **powershell** should display as a choice to run
    * select 'Run as Administrator'


From Powershell, run the command

        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

        When prompted, enter 'A' for 'all'

        Enter your userid in place of <user_name>, below

While still in powershell, run the commands:

        cd "c:\Users\<user_name>\AppData\Roaming\Kodi\addons\service.kodi.tts\resources\scripts"

        Unblock-File -Path  .\config_env.ps1

Finally, run the script: 

        . .\config_env.ps1   # Loads the script into powershell
        Config_Kodi_Env      # Runs the function defined in the script


At this point you should be able to run Kodi. A few seconds after starting Kodi you should hear a note, followed by speech. To see the configuration menu, you can press ***Ctrl, F12*** on the keyboard. If there is no voice or no configuration menu, then something went wrong and you should collect a log and send it to me.

To exit configuration, enter Escape, or select the Cancel button at the bottom of the page.

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

Function: Advance to next logging mode

        keyboard shortcut F11
        Cycles through severe, error, warning, debug and info

Function: dumps every python thread to the log

        keyboard shortcut ctrl F11
        Useful for debugging

Function: Open Settings

        keyboard shortcut: Ctrl, F12
        Launches the Kodi TTS configuration settings dialog

Function: STOP
        keyboard shortcut: STOP
        Causes currently voiced text to be skipped

Function: VOICE_HINT

        keyboard shortcut: Alt-h
        Voice hint toggles voicing hint text which is currently only embedded in the kodi.tts configuration and help dialogs.


Function: REPEAT

        keyboard shortcut: shift, F12

        Repeat voicing the previous item, including complete context (Window name, heading, etc. on down to the item itself).

Function EXTRA
        Increase verbosity (more context)
        Shortcut not defined

Function ITEM_EXTRA
        Shortcut not defined

Function TOGGLE_ON_OFF

        keyboard shortcut: F12
        Starts/stops Kodi TTS

         <!-- At least on Linux, when you press "alt, shift, +"
             it gets interpreted as "Meta, +"
             BUT, when you press "shift, alt, +" it gets interpreted as "shift, meta, 160",
             which I don't think you can get to work here. Requires more study.-->
         <plus mod="meta,shift">NotifyAll(service.kodi.tts,SPEED_UP)</plus>
         <minus mod="alt">NotifyAll(service.kodi.tts,SLOW_DOWN)</minus>

Function VOL_UP

        keyboard shortcut: ctrl, shift + (control, shift, plus)
        Changes the volume of the voiced text (not general volume)

Function VOL_DOWN

        keyboard shortcut: ctrl - (control minus)
        Changes the speed of Voiced Text

Function: SPEED_UP

        keyboard shortcut: alt, shift + 
        Increases how fast the text is spoken
        Note: At least on the Linux distribution and keyboard that I am 
        using, pressing (in order) "alt, shift, +" gets interpreted as 
        "meta +", however, pressing "shift, alt, +" is interpreted as 
        "shift, meta, 160". More study is required to find better shortcut.

Function: SLOW_DOWN

        keyboard shortcut: alt -
        Reduces how fast text is read

Function: Display Help Dialog

        keyboard shortcut: ctrl F1
        This will launch Kodi’s document reader where you can get more information about how to use Kodi TTS.


###Configuration

Kodi TTS does NOT USE Kodi’s addon configuration menus. Instead, it uses custom configuration dialog and code. The reasons for this include:

* Instant audio feedback for changes as they are made
* Ability to revert changes
* Dynamic UI that presents valid choices for the current configuration
* Able to voice items that Kodi’s built-in configuration menus can not
* Ability to voice hints, additional detail as well as help (not fully implemented)