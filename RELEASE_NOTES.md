Release Notes
=============
Welcome to the **Alpha 5** release of Kodi Text To Speech which provides basic TTS 
functionality to Kodi. It is based upon XBMC TTS (by Rick Phillips (ruuk) and pvagner),
which is no longer supported. This version of Kodi TTS is maintained by a 
different team and has major changes. Kodi TTS is installable on Kodi 20 and 21.

The goals of this early release are to provide basic functionality, iron out
installation and configuration issues as well as get feedback. Functionality
is limited to just several platforms, TTS engines and players:

For Linux:

   * TTS engines: **eSpeak-ng** and **Google TTS**
   * Audio players: **MPV**, **Mplayer** and Kodi's built-in player (**SFX**)

For Windows:

   * TTS engines: **Navigator**, **eSpeak-ng** and **Google TTS**
   * Audio players: **MPV**, **Navigator** and **SFX**

### Limitations

    * Windows and Linux only. Just several TTS engines and players supported.

    * English only. The main limitations are testing and message translation.

    * Windows TTS, only the SAPI voices (names end in 'Desktop') are are available  
      at this time. The One-Core voices (higher quality, names do not end in 'Desktop')
      voices will come before release.

    * To reduce latency in voicing, use of a cache is strongly encouraged.  
      Currently Windows TTS voice files are stored as wave files, which are much  
      larger than mp3 files. Before release a mp3 transcoder will be available.

    * Also to reduce latency in voicing, the mpv player with slave_mode is used,  
      however, this is not yet enabled on Windows. (Caching is still worth using,  
      despite these limitations.)

    * The help system has some navigation and voicing issues that need to be fixed.
      The content for the help system is preliminary.

    * A keymap editor to edit TTS keyboard/remote shortcut has not been tested and 
      not yet made directly available. Also, the keymappings have been changed to 
      my preference (a mistake). The key mappings will change to be in line with the earler 
      mappings.

### Kodi Voicing Limitations

Kodi itself has a number of limitations that impact TTS:

    * Throughout the UI, Buttons are used where a different control should be. 
      Buttons have an enabled/disabled state, which is always announced, even  
      when it is not relevant. The proper fix is to have Kodi change which control
      is used, or to add some additional information to the button so that TTS can
      can determine when the enabled state applies.

    * Except for the custom config dialogs, sliders are not voiced. The label for
      a slider is not included as part of the slider and there is no association 
      between the slider and its label. Further, there is no notification when 
      the slider value changes, requiring polling to determine any value change.
      The custom config dialogs have had metadata added to give extra information 
      to enable better screen-scraping.

    * There is no information from Kodi about the relationship between controls,
      other than the static structure from the .xml files. There are hard-coded
      rules in the original .xml parser. A new parser, currently only used for the TTS  
      configuration dialogs, uses additional custom-xml elements to add information  
      to the windows and dialogs. This covers a tiny portion of the UI and is  
      experimental.

    * Fader labels can not be voiced, kodi does not provide a means to get the 
      text value of such a label. If, however, the label's contents can be found
      by some other means, then it can be voiced using custom code for each 
      occurance.

### Issues

See [bug tracking](https://github.com/fbacher/service.kodi.tts/issues) for a formal 
list of defects and to report problems. The 
[Kodi TTS forum](https://forum.kodi.tv/showthread.php?tid=357602) is a good place to
discuss anything about this addon.

Items of particular interest:

    * A recent fix has been put in to address stopping /cancelling playing phrases
      or switching players, engines or player modes. Symptoms are high cpu usage, 
      extra player processes running, no audio or long delays in playing audio. If 
      this reoccurs, please add a note in github issue 16 
      (https://github.com/fbacher/service.kodi.tts/issues/16) OR on the forum, listed
      elsewhere.

    * Exiting TTS (or Kodi) can cause Kodi to get a Segmentation Violation on 
      Linux (it may also on Windows). A fix has been implemented. If you notice
      a segmentation violation (or a crash notice from Kodi) then add a note 
      to the forum, or to issue 17).

### Dependencies

Kodi TTS depends upon several libraries which are incorporated with TTS:
[gTTS][2] as well as [num2words][1] 

  * gTTS is found in the 'resources/lib/gtts' module. Please note the LICENSE and   
    README.md files.
  * num2words library is found in resources/lib/num2words. Please note the COPYING,  
    README.md and README.rst files. The GNU Lesser General Public License can be  
    found in COPYING.

### Installation

See SETUP.md for installation and configuration.

  [1]: https://github.com/savoirfairelinux/num2words
  [2]: https://github.com/pndurette/gTTs
