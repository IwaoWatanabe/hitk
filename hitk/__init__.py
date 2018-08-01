# coding: utf-8

import sys
import concurrent.futures
import functools
from traceback import format_exc

if sys.version_info < (3, 0):
  import Tkinter as tk, ttk
  from Queue import Queue, Empty
  import tkMessageBox as messagebox, tkSimpleDialog as simpledialog, \
      tkFileDialog as filedialog, tkFont as tkfont, Tkdnd as tkdnd
  import tkColorChooser as colorchooser

  from Tkinter import TclError, TOP, BOTTOM, LEFT, RIGHT, BOTH, \
    INSERT, END, SEL, SEL_FIRST, SEL_LAST, NORMAL, DISABLED, \
    Menu, Listbox, Text, Canvas, PhotoImage, PanedWindow, \
    StringVar, IntVar, DoubleVar, BooleanVar

  from ttk import Label, Button, Entry, Checkbutton, Radiobutton, \
    Scrollbar, Notebook, Combobox, Frame, OptionMenu, LabelFrame, Treeview, \
    Progressbar, Panedwindow, Menubutton

else:
  import tkinter as tk
  from tkinter import ttk
  from queue import Queue, Empty
  from tkinter import messagebox, simpledialog, filedialog, \
    font as tkfont, dnd as tkdnd, colorchooser

  from tkinter import TclError, TOP, BOTTOM, LEFT, RIGHT, BOTH, \
    INSERT, END, SEL, SEL_FIRST, SEL_LAST, NORMAL, ACTIVE, DISABLED, \
    Menu, Listbox, Text, Canvas, PhotoImage, PanedWindow, \
    StringVar, IntVar, DoubleVar, BooleanVar

  from tkinter.ttk import Label, Button, Entry, Checkbutton, Radiobutton, \
    Scrollbar, Notebook, Combobox, OptionMenu, Frame, LabelFrame, Treeview, \
    Progressbar, Panedwindow, Menubutton
  
ui = __import__(__name__)

def trace_text(e):
  """スタック・トレースのテキストを入手する"""
  msg = "%s\n\n%s\n%s\n\n%s" % (e, "-" * 20, e.__class__, format_exc())
  title = "%s - Internal Error" % e.__class__.__name__
  return msg, title


def _return_self(func):
  "カスケード呼び出しができるように自身を返すメソッドにするデコレータ"
  @functools.wraps(func)
  def wrap(self, *args, **kwargs):
    func(self, *args, **kwargs)
    return self
  return wrap

def _return_config_self(func):
  @functools.wraps(func)
  def wrap(self, cnf=None, **kw):
    res = func(self, cnf=cnf, **kw)
    return res if cnf else self
  return wrap

tk.Pack.pack = _return_self(tk.Pack.pack)
tk.Grid.grid = _return_self(tk.Grid.grid)
tk.Place.place = _return_self(tk.Place.place)
tk.Misc.config = _return_config_self(tk.Misc.config)
Combobox.set = _return_self(Combobox.set)


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

  def execute(cmd, *closure, **kwargs):
    '別スレッドで処理を行う'
    pass

  def invoke_lator(cmd, *closure):
    'GUIスレッドで処理を行う'
    pass

  def invoke_and_wait(cmd, *closure):
    'GUIスレッドで処理を行い、その完了を待つ'
    pass


# アプリケーション全体制御用のウィジェット

root = tk.Tk()

def show_error(prompt, title="error", **options):
  """ エラーダイアログ表示 
表示内容はクリップボードに設定される
"""
  if isinstance(prompt, Exception):
      prompt, title = trace_text(prompt)
  root.clipboard_clear()
  root.clipboard_append(prompt)
  messagebox.showerror(title, prompt, **options)

  
# 別スレッドからGUI処理を受け取る間隔(ms)
_polling_interval = 200

_polling_timer = None

# スレッドプールの最大平行処理数
_max_workers = 20

# スレッドプール
_executor = None

# 非同期処理をGUIスレッドに引き渡すためのキュー
_app_queue = Queue()


def _polling_queues():
  #非同期にGUI処理を行うための仕掛け
  global _polling_timer

  # キューから処理対象の手続きを取り出して、Tkが暇なときに動作するキューに詰め込み直す
  while True:
    # trace("_polling_queues ..")
    try:
      task = _app_queue.get(block=False)
    except Empty:
      break
    else:
      root.after_idle(task)

  _polling_timer = root.after(_polling_interval, _polling_queues)


class _AsyncTask:
  """非同期呼び出しをサポートするためのクラス
    別スレッドに呼び出しパラメータを引き渡すのと、
そのスレッドで生じた例外をキャッチしてエラー情報をGUIスレッドに渡す
"""
    
  def __init__(self, cmd, proc, closure, kwds):
    self.cmd = cmd
    self.proc = proc
    self.closure = closure
    self.kwds = kwds
    self.flag = False
    self.error = None
    self.msg = None

  def call(self):
    # このメソッドはGUIとは別のスレッドで動作する
    try:
      self.proc(self.cmd, *self.closure, **self.kwds)
      self.flag = True
    except Exception as e:
      trace("proc%s" % self.proc, file=sys.stderr)
      # show_error(msg)　# そのまま表示しようとすると固まった
      msg, title = trace_text(e)
      self.error = e
      self.msg = msg
      _app_queue.put(self.notify)
      
  def notify(self):
    """ EDTでダイアログを表示する"""
    show_error(self.msg, "%s - Internal Error" % self.error.__class__.__name__)

    
class _TkAppContext(_AppContext):
    
  def execute(cmd, *closure, **kwargs):
    """タスクをスレッド・プール経由で動作させる """
    global _executor, _polling_timer
    if not _executor: _executor = concurrent.futures.ThreadPoolExecutor(max_workers=_max_workers)
    if not _polling_timer: _polling_timer = root.after(_polling_interval, _polling_queues)
    proc = kwargs.get('proc', self.apps[-1].execute_task)
    task = _AsyncTask(cmd, proc, closure, kwargs)
    task.app = self
    _executor.submit(self._run_task, task)

  def _run_task(self, task):
    # 別スレッドで動作する
    th = threading.currentThread()
    th.task = task
    task.call()

  def invoke_lator(self, cmd, *closure, **kwds):
    """GUIの処理キューに処理を登録する"""
    th = threading.currentThread()
    task = _AsyncTask(cmd, th.task.proc, closure, kwds)
    task.app = self
    _app_queue.put(task.call)
    # trace("#invoke_lator ", cmd, task.proc, closure)

  def invoke_and_wait(self, cmd, *closure, **kwds):
    """GUIに処理を依頼して完了するまで待つ"""
    th = threading.currentThread()
    th.task.flag = False
    task = _AsyncTask(cmd, th.task.proc, closure, kwds)
    task.app = self
    _app_queue.put(task.call)
    while not task.flag: sleep(0.2)


class App():
  'GUIアプリケーションのユーザコードが継承するクラス'

  def create_widgets(self, base):
    '''このタイミングでユーザコードはGUIを組み立てる
  baseにはGUIパーツを組み立てる場所が渡されてくる。（通常はフレーム）'''
    pass

  def create_menu_bar(self):
    '''アプリケーションが固有メニューを提供する場合、このタイミングで作成する'''
    pass

  def execute_task(self, cmd, *closure, **option):
    '''別スレッドで動作する処理'''
    pass

  title = None # このプロパティからタイトルを入手する
  cc = None # このプロパティに共通機能を提供するインスタンスを差し込む

  @classmethod
  def run(Cls, argv=()):
    app = Cls()
    cc = _TkAppContext()
    cc.apps = [app]
    top = root
    cc.top = top
    app.cc = cc  # ここで共通機能を提供するインスタンスを差し込む
    app.create_widgets(top)
    bar = app.create_menu_bar()
    if bar: top.configure(menu=bar) # メニューバーがあれば設定する
    top.mainloop() # イベントループに入る

