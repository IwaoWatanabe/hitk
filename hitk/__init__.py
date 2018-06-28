# coding: utf-8

import sys

if sys.version_info < (3, 0):
    import Tkinter as tk, ttk
    from Queue import Queue, Empty
else:
    import tkinter as tk
    from tkinter import ttk
    from queue import Queue, Empty


ui = __import__(__name__)

class _AppContext():
  ''' アプリケーションが利用する共通機能を提供するインスタンス '''
  def show_info(msg, title=None):
    '情報メッセージをポップアップダイアログで出現させる'
    pass

  def show_error(msg, title=None):
    'エラーメッセージをポップアップダイアログで出現させる'
    pass

  def input_text(msg, title=None):
    '１行テキスト入力を促すダイアログを出現させる'
    pass

  def execute(cmd, proc=None, *closure):
    '別スレッドで処理を行う'
    pass

  def invoke_lator(cmd, *closure):
    'GUIスレッドで処理を行う'
    pass

  def invoke_and_wait(cmd, *closure):
    'GUIスレッドで処理を行い、その完了を待つ'
    pass


class App():
  'GUIアプリケーションのユーザコードが継承するクラス'

  def create_widgets(self, base):
    '''このタイミングでユーザコードはGUIを組み立てる
  baseにはGUIパーツを組み立てる場所が渡されてくる。（通常はフレーム）'''
    pass

  def create_menu_bar(self):
    '''アプリケーションが固有メニューを提供する場合、このタイミングで作成する'''
    pass

  title = None # このプロパティからタイトルを入手する
  cc = None # このプロパティに共通機能を提供するインスタンスを差し込む

  @classmethod
  def run(Cls, argv=()):
    app = Cls()
    cc = _AppContext()
    cc.apps = [app]
    top = tk.Tk()
    cc.top = top
    app.cc = cc  # ここで共通機能を提供するインスタンスを差し込む
    app.create_widgets(top)
    bar = app.create_menu_bar()
    if bar: base.configure(menu=bar) # メニューバーがあれば設定する
    top.mainloop() # イベントループに入る

