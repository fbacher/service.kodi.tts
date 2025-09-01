---
layout: home
---
<meta http-equiv='Content-Type' content='text/html; charset=utf-8' />
# How to install on Windows running Kodi

## Requirements

    * Kodi 20 (Nexus) or Kodi 21 (Omega) 
    * Windows-11. Not tested on other versions of Windows
    * For installing on Linux systems see: [INSTALL_LINUX](.INSTALL_LINUX.md)

## Windows Quick Start

### Optionally install mpv

**Recommended, but optional**: install mpv player prior to Kodi TTS addon so that GooglTTS and
Navigator voices will be available on first use of Kodi.

The [official mpv development site](https://mpv.io/installation) does not provide any install
images, but rather refers to some other sites that provide regular builds. One such site is
[nightly.link](https://nightly.link/mpv-player/mpv/workflows/build/master). No login required.
MPV version 0.37.0 or newer should be fine.

Carefully choose the correct image for your windows. You want something that has
"mpv-x86_64" in its name, such as: **mpv-x86_64-pc-windows-msvc. **

The following file operations will require Admin privilege.

  * Create the folder **C:\Program Files\mpv**
  * Unzip the downloaded files into the directory just created
  * As admin, run the script **C:\Program Files\mpv\installer\mpv-install.bat**

### Optionally install eSpeak-NG
Install eSpeak-NG through the Windows App installer.

### Download and install Kodi addons

**Note:** The first time that Kodi TTS runs on Windows, a Dialog will request Administator
privilege to set several permissions:

  1. Permission to enable two simple powershell scripts to call the Voicing API.
     Only the current user will have the permission.
  2. Permission to add variables to the User's environment.

Since this Alpha release is not available from the Kodi repository, you will get it from
my private repository.

Download the repository .zip file.
[private repository](https://feuerbacher.us/kodi_repo).


To install, in Kodi, go to **Settings -> Add-ons -> Add-on browser -> Install from zip file**.
There will probably be a warning about installing from unofficial sites. Select to
allow the installation. Install **script.module.langcodes** first. Choose the path
where you downloaded each zip file above. After the installation of both is complete,
Kodi TTS will start and basic configuration will begin:

### Kodi TTS First Run

When Kodi TTS runs for the first time it performs several setup tasks:

  * On Windows, several scripts are run to give permission for scripts to run and to update
    environment variables. A (non-voiced) dialog will prompt the user to allow Admin
    privilege for a powershell script.
  * Next, several windows will quickly flash by an dissapear
  * Kodi should begin voicing its progress. A notification will be read before each step, each
    taking about five seconds to read. The installation/modification of a basic keymap named
    service.kodi.tts.keyboard.xml will be announced.
  * Next, it will be announced that Hint Text is enabled.
  * Finally, TTS announces that the Configuration Dialog will be displayed.

### Configuration Dialog

The Configuration Dialog is a custom Dialog where you can change TTS settings and hear the
changes as they are made. You don't have to change anything. You can press Escape and it
will exit. However there is one setting in particular that you probably want to change is
the speed of the voice.

You will probably notice that the configuration Dialog is very chatty and helpful. This is
because the first time you run it extra verbosity is enabled. Normally this is enabled/disabled
by pressing a particular key on the keyboard, as determined by the keymap.

### To Change Speed

Move the down cursor until you are on the 5th Line. The label will be "Speed 1.2" (or similar).
Use the right cursor (arrow) to increase the speed, or left to reduce the speed.

### Save Settings

In order to save the settings you have chosen, move the cursor down until it reaches the
OK button. Selecting OK will save the settings and dismiss the dialog, returning you to
where you were in Kodi.

### To Make Other Changes

Move the cursor to the line of your choice, such as **Engine** If you click on or press Enter
a Selection Dialog will appear and you will be able to navigate up and down to learn and
hear about the various options. If you press Escape, then no changes will be made to your
Settings. If you select (click on or press Enter) something, then that choice will be
remembered in the Settings Dialog. You can undo your action by going back to the Selection
Dialog and making another choice. Or you can discard all of your changes by pressing Escape
or the Cancel button to the right of the OK button.


### Linux Quick Start

Linux, requires either espeak-NG or mpv player to be installed before
anything is voiced. Since most people agree that the Google TTS (which requires mpv) is
superior to eSpeak, installing mpv is a very good idea. By installing it before Kodi TTS is
installed voicing will begin immediately on first-use.

Mpv, espeak and mplayer are likely available from the 'normal' place for your Linux
distribution. Kodi expects them to be installed in /usr/bin.

After installing any players or engines, install the Kodi TTS addon as well as its
dependents. Since this Alpha release is not available from the Kodi repository,
you will have to manually download and install Kodi TTS and a dependent addon.

Download the two addons (you will need the .zip file):

  * [script.module.langcodes](URL_LANGCODES_ZIP_REPLACE)
  * [service.kodi.tts](URL_TTS_ZIP_REPLACE)


To install, in Kodi, go to **Settings -> Add-ons -> Add-on browser -> Install from zip file**.
There will probably be a warning about installing from unofficial sites. Select to
allow the installation. Install **script.module.langcodes** first. Choose the path
where you downloaded each zip file above. After the installation of both is complete,
Kodi TTS will start and basic configuration will begin.

### Kodi TTS First Run

When Kodi TTS runs for the first time it performs several setup tasks:

  * On Windows, several scripts are run to give permission for scripts to run and to update
    environment variables. A (non-voiced) dialog will prompt the user to allow Admin
    privilege for a powershell script.
  * Next, on Windows, several windows will quickly flash by an dissapear
  * On Linux, no special scripts or permissions are needed.
  * Kodi should begin voicing its progress. A notification will be read before each step, each
    taking about five seconds to read. The installation/modification of a basic keymap named
    service.kodi.tts.keyboard.xml will be announced.
  * Next, it will be announced that Hint Text is enabled.
  * Finally, TTS announces that the Configuration Dialog will be displayed.

### [Link to Configuration Dialog](configuration-dialog 'Configuration Dialog')

## What follows is additional information and not part of the Quick-Start

### Keyboard mappings
Kodi provides a means to define and modify numerous shortcuts for keyboards,
ir-remotes and other devices. Kodi TTS comes with a small set of shortcuts to
help you get started.

I made the mistake of ignoring the previous keymap assignments. This will be corrected
before Beta is released. Suggestions for improving these assignments are welcome.

Keyboard (and other input device) mappings are configured in .xml files in Kodi’s
user_data/keymaps directory. The pre-configured one installed with Kodi is named
“kodi.tts.keyboard.xml” It can be directly edited to change the key assignments.
Currently, a keymap editor for this file is not available. (but will be before beta).

What follows are the **current** default keyboard mapping definitions for all platforms:

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


### Configuration

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

Another choice, for engines that support it, is built-in player. A
built-in player is part of the engine, so a separate player does not need to be
installed. The biggest downside is that it is much slower than using a cache.

Similar to using a built-in player is the SFX player. SFX uses Kodi to play the audio.
The advantage being that SFX is always there. However, there are limitations:
  * You can not change speed or volume (without changing Kodi volume)
  * It only works with wave files, requiring a transcoder (slowing things down)
  * Wave files are larger than mpg

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

#### Volume

Volume is always measured in decibels, with 0.0dB being 'normal' volume. An attempt
is made to have a volume of 0.0dB about the same across the different engines and players,
however, not a great deal of effort has been put into this, so far.
