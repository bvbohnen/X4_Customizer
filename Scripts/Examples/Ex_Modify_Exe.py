'''
Run the exe modifications.

This requires the name of the base exe be specified if not the default X4.exe.
The modified exe name will look like "X4.mod.exe" or similar.

Generally needs to be rerun each time the X4 exe version changes.

For steam, the original X4.exe needs to be renamed, and the modified exe
put in its place, since steam will always relaunch from X4.exe.
'''
from Plugins import *

Settings(
    #X4_exe_name = 'X4_nonsteam.exe',
    X4_exe_name = 'X4.vanilla.exe',
    )

# Remove sig error log spam.
Remove_Sig_Errors()
# Remove the modified flag check (in some cases).
Remove_Modified()
    
# Write out only modified binary files.
Write_Modified_Binaries()
