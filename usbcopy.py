#!/usr/bin/env python3
 
"""
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
"""

import re
import string
from queue import Queue
from threading import Thread, RLock, current_thread
from shutil import copy, copytree
from subprocess import run, check_output, CalledProcessError
from time import sleep
from os import devnull, listdir
from os.path import join, isdir, basename
from platform import system
from appJar import gui
import tkinter
from tkinter import filedialog, simpledialog
 
IS_WIN = system() == "Windows"
if IS_WIN:
    from ctypes import windll
else:
    windll = None
 
NUM_THREADS = 10  # number of parallel worker threads that process connected USB sticks
if IS_WIN:
    FORMAT_CMD = "FORMAT {0} /FS:exFAT /V:{1} /Q /Y"
    UMOUNT_CMD = "RemoveDrive.exe {} -L"
else:
    FORMAT_CMD = "diskutil eraseDisk exFat {1} {0}"
    UMOUNT_CMD = "diskutil unmountDisk {}"
UNIX_MOUNT_ROOT = "/Volumes"  # the root of mounted volumes, typically /media on Linux and /Volumes on MacOS
UNIX_MNT2DEV_CMD = "mount | grep -E \"{} \([0-9a-z, ]*\)\""  # command providing device info for given mount point ONLY
UNIX_MNT2DEV_RE = re.compile("(^.+?[0-9]+)")  # regex to filter device from output of prev. command
 
DEVNULL = open(devnull, 'w')
devices_ready = Queue()
drive_mount_points = dict()
out_lock = RLock()
 
 
def initializeGUI():
    global app
    app = gui()
    for count in range(1, NUM_THREADS + 1):
        name = 'Thread ' + str(count)
        app.addLabel(name, name)
        app.setLabelBg(name, 'green')
        app.setLabelHeight(name, 3)
        app.setLabelWidth(name, 30)
        app.setLabelRelief(name, 'groove')
    return app
 
 
def mnt2dev(mount_point):
    if IS_WIN:
        return mount_point
    else:
        try:
            groups = UNIX_MNT2DEV_RE.search(check_output(UNIX_MNT2DEV_CMD.format(re.escape(mount_point)), shell=True)
                                            .decode('ascii'))
            return groups.group(1) if groups else None
        except CalledProcessError:
            return None
 
 
def print_safe(obj):
    with out_lock:
        print(obj)
 
 
def get_mounted_devices():
    drives = []
    if IS_WIN:
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(letter + ":")
            bitmask >>= 1
    else:
        roots = listdir(UNIX_MOUNT_ROOT)
        for r in roots:
            drives.append(join(UNIX_MOUNT_ROOT, r))
    return drives
 
 
def copy_file(source_paths, label):
    name = current_thread().getName()
    print_safe(name + ": Started")
    while True:
        device = devices_ready.get()
        app.setLabelBg(name, 'yellow')
 
        try:
            format_cmd = FORMAT_CMD.format(device, label)
            print_safe(name + ": Format \"" + device + "\": " + format_cmd)
            run(format_cmd, stdout=DEVNULL, shell=True)
 
            app.setLabelBg(name, 'blue')
            # this operation is safe, as the information accessed here won't change until this key is set to "False"
            mount = drive_mount_points[device]
            print_safe(name + ": Copy contents to " + mount)
            for sp in source_paths:
                if isdir(sp):
                    copytree(sp, join(mount, basename(sp)))
                else:
                    copy(sp, mount)
 
            app.setLabelBg(name, 'red')
            umount_cmd = UMOUNT_CMD.format(device)
            print_safe(name + ": Eject \"" + device + "\": " + umount_cmd)
            run(umount_cmd, stdout=DEVNULL, shell=True)
        except Exception as e:
            print_safe(name + ": Copy failed " + device)
            print(e)
 
        # this step "releases" the device for being queued again with a new mount point
        drive_mount_points[device] = False
 
        app.setLabelBg(name, 'green')
 
 
def mount_watch():
    ignore_mounts = set(get_mounted_devices())
    print("Ignoriere folgende Mountpoints: " + str(ignore_mounts))
    while True:
        new_mounts = set(get_mounted_devices()).difference(ignore_mounts)
        for nm in new_mounts:
            ndev = mnt2dev(nm)
            # ensure that ndev is not "None" (no device found) and available
            if ndev and not drive_mount_points.get(ndev, False):
                # this 2 lines "offer" a device to the worker threads and bind it to the found mount point until release
                drive_mount_points[ndev] = nm
                devices_ready.put(ndev)
        sleep(1)  # sleep one second
 
 
def process_sticks(label, source_paths):
    thread = Thread(target=mount_watch, name="Mount_Watcher")
    thread.setDaemon(True)
    thread.start()
    for i in range(1, NUM_THREADS + 1):
        thread = Thread(target=copy_file, args=[source_paths, label], name="Thread " + str(i))
        thread.setDaemon(True)
        thread.start()
 
 
if __name__ == '__main__':
    label_dialog_params = ["Laufwerksbezeichnung", "Laufwerksbezeichnung eingeben:"]
    dir_dialog_title = "Ordner mit Inhalt für Sticks auswählen"
    app = initializeGUI()
    if IS_WIN:
        root = tkinter.Tk()
        root.withdraw()
        label = simpledialog.askstring(*label_dialog_params)
        directory = filedialog.askdirectory(parent=root, title=dir_dialog_title)
    else:
        label = app.textBox(*label_dialog_params)
        directory = app.directoryBox(title=dir_dialog_title)
    source_paths = [join(directory, f) for f in listdir(directory)]
    process_sticks(label, source_paths)
    print(directory)
    for i in listdir(directory):
        print(" |- " + i)
    app.go()
 
 
__author__ = "Michael Lux"
__copyright__ = "Copyright 2017"
__credits__ = ["Dennis Eisen"]
__license__ = "CC BY-NC 4.0"
__version__ = "1.0.1"
__maintainer__ = "Michael Lux"
__email__ = "michi.lux@gmail.com"
__status__ = "Development"
