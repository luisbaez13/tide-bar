#!/bin/bash
python3 -m pip install py2app datetime rumps datetime
python3 setup.py py2app -A
mv ./dist/tides.app /Applications/tides.app
open /Applications/tides.app
rmdir dist
rm -r build
