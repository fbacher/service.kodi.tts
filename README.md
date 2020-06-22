service.xbmc.tts
================

Text to speech for Kodi (XBMC)
------------------------------
Adds speech to Kodi. It does this by using the available speech engines for the particular platform, and aims to
work 'out of the box' as much as possible.

Installation should be done through Kodi System::Settings::Add-ons::Get Add-Ons::All Add-Ons::Services::XBMC TTS

If you want to ensure you are using the latest version of the addon you can install my [repository .zip file](http://ruuks-repo.googlecode.com/files/ruuk.addon.repository-1.0.0.zip).

Installation of the repository should be done through Kodi System::Settings::Add-ons::Install from zip file

Support is available at: http://forum.xbmc.org/showthread.php?tid=196757

Ideas:
 * Enable F12 key by default at installation
 * Announce help startup: 'Kodi Text to Speech enabled.
  press Fxx to configure now. This message will be
  announced on starup until you configure it.'
  
  * Configuration includes:
    - Disable configuration announcement
    - Add optional startup help announcement
    - Change F12 key
    - Use system locale by default to configure TTS language
    - Present only TTS systems appropriate for O/S
    - Configuration should be voiced as it occurs using changing settings
    - Add help
   * Ideas: 
      - Auto-detect and use system TTS system
      - Review necessity of Pipe, mplayer and other options
      - Consider adding ability to call arbitrary script/command with fixed
        args and returned values/sound file