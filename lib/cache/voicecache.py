import datetime
import hashlib
import io
import os
import time
import zlib
from lib import util

import xbmc


class VoiceCache:

    @staticmethod
    def is_cache_sound_files():
        return util.getSetting('cache_voice_files', False)

    @staticmethod
    def get_sound_file(text_to_voice, suffix):
        if not VoiceCache.is_cache_sound_files():
            return None

        path = VoiceCache.get_path_to_voice_file(text_to_voice, suffix)
        exception_occurred = False
        voiced_text = None
        try:
            if not os.path.exists(path):
                return None

            if not os.access(path, os.R_OK):
                util.VERBOSE_LOG(
                    'VoiceCache.get_sound_file- Can not read cache file: {}'.format(path))
                return None

            expiration_time = time.time() - \
                datetime.timedelta(util.getSetting(
                    'cache_expiration_days', 30)).total_seconds()

            if os.stat(path).st_mtime < expiration_time:
                util.VERBOSE_LOG(
                    'VoiceCache.get_sound_file- Expired sound file: {}'.format(path))
                return None

            with io.open(path, mode='rb') as cache_file:
                voiced_text = cache_file.read()
        except IOError as e:
            util.ERROR('IOError reading voice file: {}'.format(path))
            util.ERROR(str(e))
            exception_occurred = True
        except Exception as e:
            util.ERROR('Exception reading voice file: {}'.format(path))
            util.ERROR(str(e))
            exception_occurred = True

        try:
            # Blow away bad cache file
            if exception_occurred and path is not None:
                os.remove(path)
        except Exception as e:
            util.ERROR('Trying to delete bad cache file.')
        return voiced_text

    @staticmethod
    def get_path_to_voice_file(text_to_voice, suffix):
        file_name = VoiceCache.get_hash(text_to_voice) + suffix
        cache_directory = util.getSetting('cache_path')
        cache_directory = xbmc.translatePath(cache_directory)
        path = os.path.join(cache_directory, file_name)
        return path

    @staticmethod
    def get_hash(text_to_voice):
        hash_value = hashlib.md5(text_to_voice.encode('UTF-8')).hexdigest()
        # if len(text_to_voice) > 5:
        #    hash_value = text_to_voice[:4]
        #    hash_value = hash_value + '_' + \
        #        hashlib.md5(text_to_voice.encode('UTF-8')).hexdigest()
        #
        # else:
        #     hash_value = text_to_voice

        return hash_value

    @staticmethod
    def save_sound_file(text_to_voice,  # type: str
                        suffix,  # type: str
                        voiced_text  # type: bytes
                        ):
        # type: (str, str, bytes) -> None
        """
            Write the given voiced text to the cache
        """
        path = VoiceCache.get_path_to_voice_file(text_to_voice, suffix)
        cache_directory = util.getSetting('cache_path',
                                          xbmc.translatePath('special://userdata/{}/cache'.format(util.ADDON_ID)))
        try:
            if not os.path.exists(cache_directory):
                try:
                    os.makedirs(cache_directory)
                except Exception as e:
                    util.ERROR(
                        'Can not create cache directory: {}'.format(cache_directory))

            if os.path.exists(path) and not os.access(path, os.W_OK):
                util.ERROR('Can not write cache file: {}'.format(path))
            with io.open(path, mode='wb') as cacheFile:
                cacheFile.write(voiced_text)
                cacheFile.flush()
        except Exception as e:
            util.ERROR('Can not write cache file: {}'.format(path))

    @staticmethod
    def clean_cache(purge=False):
        dummy_cached_file = VoiceCache.get_path_to_voice_file('', '')
        cache_directory, _ = os.path.split(dummy_cached_file)
        expiration_time = time.time() - \
            util.getSetting(
                'cache_expiration_days', 30) * 86400
        for root, dirs, files in os.walk(cache_directory, topdown=False):
            for file in files:
                try:
                    path = os.path.join(root, file)
                    if purge or os.stat(path).st_mtime < expiration_time:
                        util.VERBOSE_LOG('Deleting: {}'.format(path))
                        os.remove(path)
                except Exception as e:
                    pass
