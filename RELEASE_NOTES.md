Release Notes
=============
Welcome to the **Alpha** release of Kodi Text To Speech which provides basic TTS 
functionality to Kodi. It is based upon XBMC TTS (by Rick Phillips (ruuk) and pvagner),
which is no longer supported. This version of Kodi TTS is maintained by a 
different team and is a major release.

For right or wrong this release is nearly a rewrite of the original. Much technical 
debt remains and cleanup is a high priority and will be ongoing. The plan is to 
do cleanup in chunks with each release. 

The goals of this early release are to provide basic functionality, iron out
installation and configuration issues as well as get feedback. Functionality
is limited to just several TTS engines and players:

For Linux:

   * TTS engines: **eSpeak-ng** and **Google TTS**
   * Audio players: **MPV**, **Mplayer** and Kodi's built-in player (**XFS**)

For Windows:

   * TTS engines: **Navigator**, **eSpeak-ng** and **Google TTS**
   * Audio players: **MPV**, **Navigator** and **XFS**

### Limitations

    * Windows and Linux only. Just several TTS engines and players supported.

    * English only. The main limitations are testing, message translation and  
      getting the list of languages and voices for Windows TTS.

    * Windows TTS only the voices David and Zira are available at this time.

    * To reduce latency in voicing, use of a cache is strongly encouraged.  
      Currently Windows TTS voice files are stored as wave files, which are much  
      larger than mp3 files.

    * Also to reduce latency in voicing, the mpv player with slave_mode is used,  
      however, this is not yet enabled on Windows. (Caching is still worth using,  
      despite these limitations.)

    * The help system has some navigation and voicing issues that need to be fixed.
      The content for the help system is preliminary.

### Voicing Limitations

    * Throughout the UI Buttons are used where a different control should be. 
      Buttons have an enabled/disabled state, which is always announced, even  
      though it is not relevant. The proper fix is to have Kodi change which control
      is used, or to add some additional information to the button so that TTS can
      can determine when the enabled state is relevant.

    * Sliders are not voiced. The label for a slider is not included as part of the 
      slider and there is no association between the slider and its label. Further,
      there is no notification when the slider value changes, requiring polling 
      to determine any value change.

    * There is no information from Kodi about the relationship between controls,
      other than the static structure from the .xml files. There are hard-coded
      rules in the original .xml parser. A new parser, used for the configuration
      dialogs, uses additional custom-xml elements to add information to the windows
      and dialogs. This covers a tiny portion of the UI and is experimental.

    * This list is incomplete, more to be added here as they are discovered.

### Issues

See [bug tracking](https://github.com/fbacher/service.kodi.tts/issues) for a formal
list of defects and to report problems. The 
[Kodi TTS forum](https://forum.kodi.tv/showthread.php?tid=357602) is a good place to
discuss anything about this addon.

Items of particular interest:

    * It is possible to cause high CPU usage while configuring TTS. The cause is
      yet unknown, but is related to changing player configuration. The solution
      is to restart Kodi, or TTS. 

    * Exiting TTS (or Kodi) can cause Kodi to get a Segmentation Violation on 
      Linux (it may also on Windows). I have seen this before. Probably related
      to shut-down code for TTS, or improper file handling. Requires investigation.

### Dependencies

Kodi TTS depends upon other libraries:

[gTTS][2] as well as [num2words][1] 

  * gTTS is found in the 'resources/lib/gtts' module. The MIT LICENSE, README.md files  
    are also found there.
  * num2words library is contained in resources/lib/num2words, which also includes  
    the GNU Lesser General Public License Version 2.1 in COPYING as well as 
    README.md and README.rst

  [1]: https://github.com/savoirfairelinux/num2words
  [2]: https://github.com/pndurette/gTTs
