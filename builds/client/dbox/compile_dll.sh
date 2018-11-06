#!/bin/bash
i686-w64-mingw32-gcc -shared c2file_dll.c -o c2file.dll

#python -m PyInstaller -F -r c2file.dll dbox_client.py
