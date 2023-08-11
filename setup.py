from setuptools import setup

APP = ['./tides.py']
DATA_FILES = ['./icons/waves.png', './icons/tides.db']
OPTIONS = {
    'argv_emulation': True,
    'qt_plugins' : "sqldrivers",
    'iconfile':'./icons/waves.icns',
     'plist': {
         'LSUIElement': False,
     },
    'packages': ['rumps', 'datetime', 'requests', 'time', 'sqlite3'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)