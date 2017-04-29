# pardepo
Pardepo - Parallel Device Puplicator

A tool for automatically copying the content of a directory to multiple USB sticks

ATTENTION: EVERY WRITABLE DEVICE ATTACHED TO THIS MACHINE WHILE THE MAIN WINDOW IS ACTIVE WILL BE ERASED!!!
The author/contributors are not liable in any way for any damage caused by wrong use of this tool!

This tool queries a new volume name and a directory first.
Every USB Stick attached after the overview window showed up will be
a) formatted, using the command FORMAT_CMD as specified below, with the given label being inserted using format()
b) filled with all the contents of the selected directory
c) ejected using the command UMOUNT_CMD as specified below, with the device name being inserted using format()

Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)
https://creativecommons.org/licenses/by-nc/4.0/legalcode
