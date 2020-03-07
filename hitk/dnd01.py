# -*- coding: utf-8 -*-
# このスクリプトは OSのDDLを利用しているため、Windowsでのみ動作します。

# Python+TkでD&DAdd より
# http://d.hatena.ne.jp/MasaHero/20111201/p1
# https://sites.google.com/site/pythoncasestudy/home/tkinterdedrag-drop-ctypes-shi-yong

import ctypes, sys
from ctypes import c_long, c_void_p, WINFUNCTYPE
from ctypes.wintypes import HWND, UINT, WPARAM, LPARAM
from hitk import ui

WM_DROPFILES = 0x0233
GWL_WNDPROC = -4
FS_ENCODING = sys.getfilesystemencoding()

DragAcceptFiles = ctypes.windll.shell32.DragAcceptFiles

DragQueryFile = ctypes.windll.shell32.DragQueryFile
DragQueryFile.argtypes = [c_void_p, UINT, c_void_p, UINT]

DragFinish = ctypes.windll.shell32.DragFinish
DragFinish.argtypes = [c_void_p]

CallWindowProc = ctypes.windll.user32.CallWindowProcW
CallWindowProc.argtypes = [c_void_p, HWND, UINT, WPARAM, LPARAM]

try:
  SetWindowLong = ctypes.windll.user32.SetWindowLongPtrW
except AttributeError:
  SetWindowLong = ctypes.windll.user32.SetWindowLongW


class _WinDnD:
  dnd_interval = 600

  def dnd_setup(self, win, dnd_notify):
    """Windowsのイベント処理のフックを定義する"""

    self.drop_names = []

  def drop_check():
    if self.drop_names:
      fns = self.drop_names
      self.drop_names = []
      dnd_notify(fns, win)
    win.after(self.dnd_interval, drop_check)

  @WINFUNCTYPE(c_long, HWND, UINT, WPARAM, LPARAM)
  def replace_win_proc(hwnd, msg, wp, lp):
    """D&D用のコールバック
      ファイルのドラッグアンドドロップイベント(WM_DROPFILES)を検出して、
      ドロップされたファイル名を保持する。
      ここでウィンドウ(tk)を使用するとハングアップするのでデータ保存だけ行う。
      """
    if msg == WM_DROPFILES:
      nf = DragQueryFile(wp, -1, None, 0)
      buf = ctypes.c_buffer(260)
      fns = [buf.value.decode(FS_ENCODING) for nn in range(nf) \
             if DragQueryFile(wp, nn, buf, ctypes.sizeof(buf))]
      DragFinish(wp)
      self.drop_names.extend(fns)
      if ui.verbose: ui.trace("%s dnd_notify: %s" % (self, hwnd), file=sys.stderr)
        
      return CallWindowProc(self.org_proc, hwnd, msg, wp, lp)

    hwnd = win.winfo_id()
    DragAcceptFiles(hwnd, True)
    self.win_proc = replace_win_proc
    self.org_proc = SetWindowLong(hwnd, GWL_WNDPROC, self.win_proc)
    win.after_idle(drop_check)
    if ui.verbose: ui.trace("%s dnd_setup: %s,%s" % (self, hwnd, self.org_proc))


def register_dnd_notify(win, dnd_notify):
    """DnD呼び出しを登録する"""
    dnd = _WinDnD()
    win.dnd = dnd
    win.after_idle(lambda: dnd.dnd_setup(win, dnd_notify))


if __name__ == "__main__":

  class DnDApp(ui.App):
    """DnDの振る舞いを確認する簡易アプリ"""
        
    def create_widgets(self, base):
      tw = tkui.Text(base, width=80, height=16)
      tw.pack(fill='both', expand=1)
      register_dnd_notify(tw, self.dnd_notify)
            
    def dnd_notify(self, filenames, wi):
      for nn in filenames:
        wi.insert('end', "%s\n" % nn)

  DnDApp.run()
  
