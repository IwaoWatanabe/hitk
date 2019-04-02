# coding: utf-8

import platform, sys
from hitk import Frame, Scrollbar, Text, \
    INSERT, END, SEL, SEL_FIRST, SEL_LAST, ui, tk, trace

class MemoApp(ui.App):
  def create_widgets(self, base, rows=15, column=60):
    tk.Text(base, width=column, height=rows,
            undo=1,maxundo=1000).pack(fill='both', expand=1)


def _select_present(buf):
  """バッファの範囲指定がされているか判定する"""
  pf = buf.index(SEL_FIRST)
  pl = buf.index(SEL_LAST)
  return not pl == pf


class MemoApp01(ui.App):
  
  menubar_items = [
    'menubar;',
    [ 'file;ファイル(&F)',
      'new;新規にウィンドウを開く(&N);ctrl-N',
      'open;ファイルを開く(&O) ..;ctrl-O',
      "save;ファイルに保存する(&S);ctrl-S",
      '-',
      'close;閉じる(&C);ctrl-W',
      ],
    [ 'help;ヘルプ(&H)',
      'about;このアプリについて(&A);;idlelib/Icons/python.gif',
      ],
    ]

  shortcut_items = [
    'text-shortcut;',
    'copy;選択した範囲のテキストをクリップボードに複製(&C);ctrl-C',
    'select-all;全て選択する(&A);ctrl-A',
    '-',
    'goto-line;指定する行にカレットを移動(&G)..;ctrl-L',
    'find; 検索(&F) ..;ctrl-F',
    '-',
    'open;ファイルを開く(&O) ..;ctrl-O',
    '-',
    'close;閉じる(&C);ctrl-W',
  ]
  
  text_file_types = [
    ('Plain Text', '*.txt'),
    ('All Files', '*'),
    ]


  def perform(self, cmd, *args):
    ''' メニュー選択により動作する機能 '''
    trace(cmd, args)
    cc = self.cc
    buf = self.buf

    if 'copy' == cmd:
      if _select_present(buf):
        text = buf.get(SEL_FIRST, SEL_LAST)
        cc.set_clipboard_text(text)
      return 'break'

    elif "select-all" == cmd:
      buf.tag_remove(SEL, '1.0', END)
      buf.tag_add(SEL, '1.0', END)
      buf.mark_set(INSERT, '1.0')
      buf.see(INSERT)
      return 'break'

    elif 'open' == cmd:
      tf = cc.ask_open_file(filetypes=self.text_file_types)
      if not tf: return
      trace(tf)
      
    elif 'save' == cmd:
      tf = cc.ask_save_file(filetypes=self.text_file_types, defaultextension='.txt')
      trace(tf)
      
    elif 'close' == cmd:
      self.close()
      
    elif 'new' == cmd:
      self.__class__.start()

    elif 'about' == cmd:
      cc.show_info('Python version: %s\nTK version: %s\n' % (
          sys.version, tk.TkVersion), 'about')

  def create_widgets(self, base, columns=30, rows=5):
    cc = self.cc

    buf = tk.Text(base, width=columns, height=rows,
                  undo=1,maxundo=1000).pack(fill='both', expand=1)
    self.buf = buf
    buf.insert(END, 'メニューの機能試験')
    ui.setup_theme(buf)
    cc.find_status_bar()

    shortcut = self.find_menu(self.shortcut_items, buf)
    ui.register_shortcut(buf, shortcut)

    # メニューに登録されているアクセラレータを登録
    for cond, cmd in (
      ('<Control-n>', 'new'),
      ('<Control-a>', 'select-all'),
      ('<Control-c>', 'copy'),
      ('<Control-o>', 'open'),
      ('<Control-s>', 'save'),
      ('<Control-w>', 'close'),
      ): cc.bind(cond, self.bind_proc(cmd))



class EventViewApp(ui.App):
  """発生したキーやボタン・イベントを表示する"""
  
  def create_widgets(self, base, rows=15, column=60):
    cc = self.cc
    fr = Frame(base)
    fr.pack(side='top', fill='both', expand=1)
    sbar = Scrollbar(fr)
    self.buf = buf = Text(fr, width=column, height=rows, padx=5)
    sbar.config(command=buf.yview)
    sbar.pack(side='right', fill='y')
    buf.config(yscrollcommand=sbar.set)
    buf.pack(side='left', fill='both', expand=1)
    ui.setup_theme(buf)

    for cond, proc in (
      #('<Button>', self._append_event_text),
      ('<ButtonPress>', self._append_event_text),
      ('<ButtonRelease>', self._append_event_text),
      ('<KeyPress>', self._append_event_text),
      ('<KeyRelease>', self._append_event_text),
      #('<Key>', self._append_event_text),
      ('<Control-w>', lambda e, ac=cc: ac.close()),
      ('<Enter>', lambda e, wi=buf: wi.focus_set()),
      ('<MouseWheel>', self._append_event_text),
      ('<Configure>', self._append_event_text),
      ): buf.bind(cond, proc)

    shortcut = cc.find_menu(self.shortcut_items, buf, self.perform)
    ui.register_shortcut(buf, shortcut)
    #if ui.need_unpost: shortcut.bind('<FocusOut>', lambda ev, wi=shortcut: wi.unpost())
    buf.insert(INSERT, "platform: %s: %s\n" % (platform.system(), sys.platform))
  
  def _append_event_text(self, ev):
    #print type(ev.keysym), type(ev.keycode)

    e = ' '.join(map(str, (
          ev.serial, ev.type, ev.num, ev.char, ev.keysym, ev.keycode,
          ev.state, ev.width, ev.height, ev.x, ev.y, ev.x_root, ev.y_root, ev.delta)))
    buf = self.buf
    buf.insert(END, '%s\n' % (e, ))
    buf.see(END)
    return 'break'
  
  shortcut_items = [
    'eventview-shortcut;',
    'new;新規に作成する(&N) ..;ctrl-N',
    'clear;ログ削除;',
    '-',
    'close;閉じる(&C);ctrl-W',
    ]

  def perform(self, cmd, *args):
    buf = self.buf
    buf.insert(INSERT, 'perfrom %s %s\n' % (cmd, args))
    if 'close' == cmd or 'exit' == cmd: self.dispose()
    elif 'new' == cmd: self.__class__.start()
    elif 'clear' == cmd: buf.delete('1.0', END)
    

if __name__ == '__main__': MemoApp.run()
