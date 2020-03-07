# -*- coding: utf-8 -*-
# このスクリプトは OSのDDLを利用しているため、Windowsでのみ動作します。

import os, sys
from win32com.shell import shell, shellcon
import win32api, win32con, win32ui, win32gui
from PIL import Image, ImageTk

# pip install --user pillow pywin32

def get_icon(PATH, size='small', hold_image=False):
    # Windowsプラットフォームでファイルのアイコン画像を入手する
    # https://stackoverflow.com/questions/21070423/python-saving-accessing-file-extension-icons-and-using-them-in-a-tkinter-progra
    SHGFI_ICON = 0x000000100
    SHGFI_ICONLOCATION = 0x000001000
    if size == 'small':
        SHIL_SIZE = 0x00001
    elif size == 'large':
        SHIL_SIZE = 0x00002
    else:
        raise TypeError("Invalid argument for 'size'. Must be equal to 'small' or 'large'")

    ret, info = shell.SHGetFileInfo(PATH, 0, SHGFI_ICONLOCATION | SHGFI_ICON | SHIL_SIZE)
    hIcon, iIcon, dwAttr, name, typeName = info
    if not hIcon: return None
    ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
    hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
    hbmp = win32ui.CreateBitmap()
    hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_x)
    hdc = hdc.CreateCompatibleDC()
    hdc.SelectObject(hbmp)
    hdc.DrawIcon((0, 0), hIcon)
    win32gui.DestroyIcon(hIcon)

    bmpinfo = hbmp.GetInfo()
    bmpstr = hbmp.GetBitmapBits(True)
    img = Image.frombuffer(
        'RGBA',
        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
        bmpstr, 'raw', 'BGRA', 0, 1
    )

    if size == 'small':
        img = img.resize((16, 16), Image.ANTIALIAS)
    ph = ImageTk.PhotoImage(img)
    ph.image = img if hold_image else None
    return ph

