
## Install Addons

First, install the latest released version of Kodi.

Next, install the Kodi TTS addon as well as its dependents. Since this Alpha release 
is not available from the Kodi repository, you will have to manually download and 
install Kodi TTS and a dependent addon.

Download the two addons (you want the .zip file):

  * [script.module.langcodes](https://github.com/fbacher/script.module.langcodes/archive/refs/tags/v0.0.1-alpha.zip)
  * [service.kodi.tts](https://github.com/fbacher/service.kodi.tts/tags)

To install, in Kodi, go to **Settings -> Add-ons -> Add-on browser -> Install from zip file**. There will probably be a warning about installing from unofficial sites. Select to allow the installation. Install **script.module.langcodes** first. Choose the path where you downloaded each zip file above. After the installation of both is complete, exit Kodi.

## Install TTS Engines and Players
After installing the kodi addons, you may need to install one or more players and TTS engines.

### Linux
I suggest that you install **mpv** to play audio. It is frugal with resources, is of very good quality, is very responsive when used with caching and slave mode. **mplayer** is the predessor to mpv and is supported for those who want it.

Optionally install eSpeak-NG, which is typically available from your distribution.

Almost certainly mpv, eSpeak and mplayer are available from your normal Linux distribution channels. They should be easy to find and install.

### Windows

Windows TTS (Navigator) is fairly high quality, runs locally and is builtin. It does require a Powershell script to use, which must be configured.

Google TTS comes with Kodi TTS and requires no configuration. It does require mpv, however.

I suggest that you install **mpv** to play audio on Windows, it can play the audio produced by either Google TTS or Navigator. It supports cached audio as well as both mp3 and wave files. **mpv** is NOT required if you use Windows TTS (Navigator), but I prefer using the cache and mpv.

eSpeak is available for those who like it.

#### mpv

Install images for [**mpv** are here](https://github.com/shinchiro/mpv-winbuild-cmake/releases) (this link is from [the official mpv installation page](the https://mpv.io/installation)). MPV version 0.37.0 or newer should be fine.

Carefully choose the correct image for your platform. You want something that has "mpv-x86_64" in its name, like: https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20250623/**mpv-x86_64**-20250623-git-18defc8.7z. You DON'T want ffmpeg or a 'dev' build. If the build you install doesn't run (if it launches it should be ok), then try another build. Some are built with different compilers, others are for different cpus. Intel/amd should have "mpv-x86_64" in the name.

The following file operations will require Admin privilege.

  * Create the folder **C:\Program Files\mpv**
  * Unzip the downloaded files into the directory just created
  * As admin, run the script **C:\Program Files\mpv\installer\mpv-install.bat**

### Optionally install eSpeak-NG
Install eSpeak-NG through the Windows App installer.

### Configure paths and powershell scripts
The following does several things:
  * Adds Environment Variables for several players and engines that you may use. Note
    the paths assume the players and engines are located in C:\Program Files.
  * Gives permission to run a simple Powershell script which provides access to Navigator

Configure steps:
  1. Launch 'Command Prompt' with Administrator Privileges
  2. Enter the command: 
     "%APPDATA%"\Kodi\addons\service.kodi.tts\resources\scripts\config_script.bat

You should see several messages as the script runs and no obvious errors.

At this point you should be able to run Kodi. A few seconds after starting Kodi you
should hear a note, followed by speech. To see the configuration menu, you can
press ***Ctrl, F12*** on the keyboard. If there is no voice nor configuration 
menu, then something went wrong and you should collect a log and send it to me.

If you made any configuration changes that you want to keep, then select the **OK**
button at the bottom of the dialog, otherwise, to exit configuration, enter Escape, 
or select the Cancel button at the bottom of the dialog.

### Third-party software:

#### Players

MPV is a followon to MPlayer. MPV has added numerous improvements which make it well suited for Kodi-TTS. In particular it has a 'slave-mode' that is superior to Mplayer's. Slave-mode allows Kodi-TTS to dynamically control what is played, canceled, paused, volume or speed changed, etc.. This is much better than killing and relaunching mpv on every utterance.

#### TTS Engines

googleTTS My current favorite. It supports many languages and dialects. The naming is logical which should make it easy for users.

eSpeak-NG is an old standby that is fast, small and supports many languages. The voices sound distinctly computer generated. The universe of voices and the files required for them can be difficult to find and to get working. Finally, the metadata used to identify the voice (language, country, gender, etc.) is difficult to use programatically (or perhaps I haven't studied enough).

Espeak-NG Linux is in multiple distributions
Windows Version 1.52.0 can be downloaded from https://github.com/espeak-ng/espeak-ng/releases

#### Adding More Voices to Windows Narrator
Currently, Kodi TTS only supports David and Zira english voices. The ability to choose
between all installed voices will be ready soon.

## Keyboard mappings
Kodi provides a means to define and modify numerous shortcuts for keyboards, 
ir-remotes and other devices. Kodi TTS comes with a small set of shortcuts to 
help you get started. Suggestions for improving these assignments are welcome.

Keyboard (and other input device) mappings are configured in .xml files in Kodi’s
user_data/keymaps directory. The pre-configured one installed with Kodi is named 
“kodi.tts.keyboard.xml” It can be directly edited to change the key assignments. 
Currently, a keymap editor for this file is not available.

What follows are the default keyboard mapping definitions for all platforms:

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
        Voice hint toggles voicing hint text which is currently only embedded in  
        the kodi.tts configuration and help dialogs.

Function: REPEAT

        keyboard shortcut: shift, F12

        Repeat voicing the previous item, including complete context (Window name, 
        heading, etc. on down to the item itself).

Function EXTRA

        Increase verbosity (more context)  

        Shortcut not defined

Function ITEM_EXTRA

        Shortcut not defined

Function TOGGLE_ON_OFF

        keyboard shortcut: F12
        Starts/stops Kodi TTS

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
        This will launch Kodi’s document reader where you can get more information   
        about how to use Kodi TTS.


## Configuration

Kodi TTS does NOT USE Kodi’s addon configuration menus. Instead, it uses custom configuration dialog and code. The reasons for this include:

* Instant audio feedback for changes as they are made
* Ability to revert changes
* Dynamic UI that presents valid choices for the current configuration
* Able to voice items that Kodi’s built-in configuration menus can not
* Ability to voice hints, additional detail as well as help (not fully implemented)

### Configuration Dialog

The Configuration Dialog is accessed by pressing **Ctrl F12**. The Dialog is roughly 
organized in the logical order that changes are made. By pressing **Alt-h** 
Kodi TTS will voice some terse hint information as you navigate through your choices.
To disable the hints, press **Alt-h** again.

#### Choose Engine

The first thing to choose is the TTS Engine, which is the first dialog item. By pressing
'enter' (or equivalent) a Selection Dialog is displayed that lists all of the available
engines. By changing the focus you will hear each engine speak. Simply select the
engine you want by pressing 'enter' (or equivalent). Note that the change won't be made
permanent until you save it when leaving the Configuration Dialog.

#### Voice speed

By now you may have noticed that the voicing speed has slowed down after you changed
the engine. This is done to make sure the new engine is understandable. To fix the speed,
navigate to the **speed** item. Here you use the left or right cursor to change the
speed. It is recomended that the speed is changed after choosing the engine and 
language variant.

#### Language Variant (voice)

After engine selection, the next thing to choose is the 'Language Variant' or voice. 
Again, press enter to bring up the Selection Dialog where you can hear each choice.

#### Player

The default player depends on the engine. Generally mpv is preferred since it supports
mp3 (smaller than wave) and 'slave mode' which improves performance, especially when
used with a cache.

The other significant choice, for engines that support it, is built-in player. A
built-in player is part of the engine, so a separate player does not need to be
installed. The biggest downside is that it is much slower than using a cache.

#### Caching

Note that you can't configure to use a cache if the current engine or player does
not support it.

Since the process of voice generation is expensive, Caching can greatly speed up 
voicing. Currently, there are no limits on cache size, nor is there garbage collection.
For an engine that produces mp3 a cache for a typical library can grow to 1G or more.
Wave files are larger. If you have the space, then a cache is recommended. 

A different cache is used for each engine and voice (language variant). Therefore if
you have been using a cache for a few weeks and switched to a new voice, it may be
worth deleting the old cache.

Caches are located within the addon_data directory, by default is:

    * Windows: c:\Users\<user-id>\AppData\Roaming\Kodi\userdata\addon_data
    * Linux: /user/home/<user_id>/.kodi/userdata/addon_data

From there, the cache is located in:

    * Windows: service.kodi.tts\cache\<engine_id>\<language_id>\<country_id>\<voice_id>\
    * Linux: service.kodi.tts/cache/<engine_id>/<language_id>/<country_id>/<voice_id>

For example a cache for google, in english, united states, voice: en-us the cache is
in: /user/home/<user_id>/.kodi/userdata/addon_data/service.kodi.tts/cache/goo/en/us/en-us

For other engines the id's can be completely different.

#### Player Mode

The choice of player modes depends upon the engine and player.

    * SLAVE mode allows a player to run in slave-mode, which is best for caching,
      but should also improve performance in non-cache environments

    * FILE mode tells the player to get the audio from a file

    * PIPE mode is meant to improve performance by transmitting the audio via  
      in-memory 'pipes' instead of through a file. However, it is currently  
      implemented by going through a file anyway. The option remains because it   
      may be useful in the future.

    * ENGINE_SPEAK mode uses the engine's built-in player (if supported).

#### Speed

Speed is always measured as a scale factor. 1 is 'normal' speed. 2 is twice 'normal' 
and 0.5 is 1/2 normal speed. Whenever the engine changes the speed reverts to 1.
Whenever a player is used, the player implements the speed change (if supported),
otherwise the engine does it. Note that any player that supports caching must also
support speed change (without a change in pitch).

#### Volume

Volume is always measured in decibels, with 0.0dB being 'normal' volume. An attempt
is made to have a volume of 0.0dB about the same across the different engines,
however, not a great deal of effort has been put into this.
