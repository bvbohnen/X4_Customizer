'''
This small module sets up the path to the X4 Customizer home
directory, consistently for both original source and the compiled
version.  Split off from other modules for easier imports.
'''


# Set the directory where the package resides, which is one
#  level up from here.
# Note: pyinstaller can change directories around, and needs special
#  handling.
# See https://stackoverflow.com/questions/404744/determining-application-path-in-a-python-exe-generated-by-pyinstaller
# In short, a 'frozen' attribute is added to sys by pyinstaller,
#  which can be checked to know if this is running in post-installer mode,
#  in which case _MEIPASS will hold the app base folder.
# TODO: check if this is still needed in the latest pyinstaller.
import sys
from pathlib import Path
if getattr(sys, 'frozen', False):
    # This appears to be the folder with Main, so go up 1 level.
    home_path = Path(sys._MEIPASS).parent
else:
    home_path = Path(__file__).resolve().parents[2]