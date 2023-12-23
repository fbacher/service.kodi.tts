# -*- coding: utf-8 -*-
#
import sys

try:
    pass
    # import web_pdb;

    # web_pdb.set_trace()
except Exception as e:
    pass

if __name__ == '__main__':
    try:
        print('main')
        from test.gtts_driver import GttsTestDriver

        GttsTestDriver.run_test('en', 'You are a lovely person')
        GttsTestDriver.run_test('de', 'Du bist ein liebenswerter Mensch')
        GttsTestDriver.run_test('fr', 'Vous êtes une personne adorable')
        # Canadian French
        GttsTestDriver.run_test('fr', 'Vous êtes une personne charmante')
        GttsTestDriver.run_test('es', 'Eres una persona encantadora')
        GttsTestDriver.run_test('ar', 'أنت شخص جميل')
        GttsTestDriver.run_test('uk', 'Ви прекрасна людина')
        GttsTestDriver.run_test('tr', 'Çok sevimli bir insansın')

        print('from run_test')
        # xbmc.log('started service.startService thread', xbmc.LOGDEBUG)

    except Exception as e:
        print(f'Exception {e}')
    sys.exit()
