# coding: utf-8

import platform, sys

from hitk import Frame, Scrollbar, Text, \
    INSERT, END, SEL, SEL_FIRST, SEL_LAST, ui, dialogs, tk, trace

class MemoApp01(ui.App):
  def create_widgets(self, base, rows=15, column=60):
    tk.Text(base, width=column, height=rows,
            undo=1,maxundo=1000).pack(fill='both', expand=1)

class TimerApp01(ui.App):

  def create_widgets(self, base, rows=15, column=60):
    var = ui.StringVar()
    ui.Entry(base, textvariable=var).pack(fill='both', expand=1)
    self.timer = var
    self.cc.timer('timer', interval=0.5).start()

  def perform(self, cmd, *args):
    if 'timer' == cmd:
      self.timer.set(ui.strftime("%Y-%m-%d %H:%M:%S"))
    
    
text_menu_items = [
  [ 'file;ファイル(&F)',
    'new;新規メモ(&N);ctrl-N',
    'open;メモを開く(&O) ..;ctrl-O',
    'dir-select;基準フォルダの選択(&B) ..;;idlelib/Icons/folder.gif',
    '-',
    'close;メモを閉じる(&C);ctrl-W',
  ],
  [ 'edit;編集(&E)',
    'copy;選択したテキストをクリップボードに複製(&C);ctrl-C',
    'select-all;全て選択(&A);ctrl-A',
    '-',
    'find;テキストを検索(&F) ..;ctrl-F',
    'goto-line;指定する行にカレットを移動(&G)..;ctrl-L',
  ],
  [ 'view;表示(&V)',
    '+wrap;行を折り返す(&W)',
    '-',
    'font;フォントの選択(&F)..',
    'big;大きく(&+);ctrl-+',
    'small;小さく(&-);ctrl--',
  ],
  [ 'help;ヘルプ(&H)',
    'about;このアプリについて(&A);;idlelib/Icons/python.gif',
  ],
  [ 'text-shortcut;',
    'copy;選択したテキストをクリップボードに複製(&C);ctrl-C',
    'select-all;全て選択(&A);ctrl-A',
    '-',
    'find; 検索(&F) ..;ctrl-F',
    'goto-line;指定する行にカレットを移動(&G)..;ctrl-L',
    '-',
    'open;メモを開く(&O) ..;ctrl-O',
    'close;メモを閉じる(&C);ctrl-W',
  ]
]

text_file_types = [
  ('Plain Text', '*.txt'),
  ('All Files', '*'),
]

from hitk.cli import localfiles as lf

class MemoApp02(ui.App, dialogs.TextFind):
  menu_items = text_menu_items
  menu_bar = 'file:edit:view:help'

  def create_widgets(self, base, rows=15, column=60):
    buf = tk.Text(base, width=column, height=rows, undo=1,maxundo=1000).pack(fill='both', expand=1)
    #buf = ui.scrolled_widget(base, tk.Text, width=column, height=rows, undo=1, maxundo=1000)
    self.buf = buf
    shortcut = self.find_menu('text-shortcut')
    ui.register_shortcut(buf, shortcut)

    cc = self.cc
    cc.bind('<MouseWheel>', self._adjust_font_size, '+')
    cc.bind('<Button-4>', self._adjust_font_size, '+')
    cc.bind('<Button-5>', self._adjust_font_size, '+')
    
  initialdir = None
  
  def perform(self, cmd, *args):
    ''' メニュー選択により動作する機能 '''
    trace(cmd, args)
    cc = self.cc
    buf = self.buf

    if 'copy' == cmd:
      if _text_select_present(buf):
        text = buf.get(SEL_FIRST, SEL_LAST)
        cc.set_clipboard_text(text)
      return 'break'

    elif 'select-all' == cmd:
      buf.tag_remove(SEL, '1.0', END)
      buf.tag_add(SEL, '1.0', END)
      buf.mark_set(INSERT, '1.0')
      buf.see(INSERT)
      return 'break'

    elif 'goto-line' == cmd:
      ln = int(buf.index(END).split('.')[0])
      msg = 'Input Line Number 1..%d' % ln
      msg = '移動行を入力ください (範囲 1..%d)' % ln
      tt = cc.input_text(msg, 'line-number')
      if not tt: return
      idx = '%d.0' % int(tt)
      buf.mark_set(INSERT, idx)
      buf.see(idx)
      buf.focus_set()
      return

    elif 'dir-select' == cmd:
      td = cc.ask_folder(initialdir=self.initialdir)
      if not td: return
      self.initialdir = td
      
    elif 'open' == cmd:
      tf = cc.ask_open_file(filetypes=text_file_types, \
                            initialdir=self.initialdir)
      if not tf: return
      trace(tf)
      buf['cursor'] = 'watch'
      cc.execute('load-text', tf)

    elif 'close' == cmd:
      self.close()
      
    elif 'new' == cmd:
      self.start()

    elif 'about' == cmd:
      cc.show_info('Python version: %s\nTK version: %s\n' % (
          sys.version, tk.TkVersion), 'about')

    elif 'font' == cmd:
      fd = cc.find_dialog('font', dialogs.FontDialog)
      fd.open(self)
      return 'break'
    
    elif 'big' == cmd:
      return dialogs.adjust_font_size(self, dir=1)

    elif 'small' == cmd:
      return dialogs.adjust_font_size(self, dir=-1)

    elif 'find' == cmd:
      try: text = buf.get(SEL_FIRST, SEL_LAST)
      except tk.TclError: text = ''
      fd = cc.find_dialog('find', dialogs.FindDialog)
      fd.open(text, self)
      return 'break'
      
  fm = lf.LocalFolder()
    
  def execute_task(self, cmd, *closure):
    # 別スレッドで処理される内容を定義
    cc = self.cc
    buf = self.buf
    
    if 'load-text' == cmd:
      try:
        target_file = closure[0]
        task = 'replace-text'
        for text in self.fm.readlines(target_file, step=1000):
          cc.invoke_lator(task, text)
          task = 'append-text'
      finally: cc.invoke_lator('done')
      
    elif 'replace-text' == cmd:
      text = closure[0]
      buf.edit_reset()
      buf.delete('1.0', END)
      buf.insert('1.0', text)
      buf.edit_modified(False)
      
    elif 'append-text' == cmd:
      text = closure[0]
      buf.insert(END, text)
      buf.edit_modified(False)
      
    elif 'done' == cmd:
      buf['cursor'] = ''
      buf.mark_set(INSERT, '1.0')
      buf.focus_set()
      
        
  @property
  def font(self):
    buf = self.buf
    fn = buf.cget('font')
    font = ui.find_font(fn)
    return font
  
  @font.setter
  def font(self, font):
    buf = self.buf
    if type(font) == str: font = ui.find_font(font)
    buf.config(font=font)
    
  def _adjust_font_size(self, ev):
    # マウスホイールでフォントサイズの調整
    return dialogs.adjust_font_size(self, event=ev)




def _text_select_present(buf):
  """バッファの範囲指定がされているか判定する"""
  pf = buf.index(SEL_FIRST)
  pl = buf.index(SEL_LAST)
  return not pl == pf


class TextViewApp(ui.App):

  menu_bar = 'file:edit:view:help'
  
  menu_items = [
    [ 'file;ファイル(&F)',
      'new;新規にウィンドウを開く(&N);ctrl-N',
      'open;ファイルを開く(&O) ..;ctrl-O',
      '-',
      [
        'encoding;日本語文字コード(&E)',
        '*enc.iso-2022-jp;JIS (ISO-2022-JP)',
        '*enc.sjis;Shift JIS',
        '*enc.euc_jp;EUC',
        '*enc.utf-8;UTF-8',
      ],
      '-',
      'close;閉じる(&C);ctrl-W',
    ],
    [ 'edit;編集(&E)',
      'copy;選択した範囲のテキストをクリップボードに複製(&C);ctrl-C',
      'select-all;全て選択する(&A);ctrl-A',
      '-',
      'goto-line;指定する行にカレットを移動(&G)..;ctrl-L',
      'find;テキストを検索(&F) ..;ctrl-F',
    ],
    [ 'view;表示(&V)',
      '+wrap;行を折り返す(&W)',
      '-',
      'font;フォントの選択(&F)..',
      'big;大きく(&+);ctrl-+',
      'small;小さく(&-);ctrl--',
    ],
    [ 'help;ヘルプ(&H)',
      'about;このアプリについて(&A);;idlelib/Icons/python.gif',
    ],
    [ 'text-shortcut;',
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
  ]

  def perform(self, cmd, *args):
    ''' メニュー選択により動作する機能 '''
    trace(cmd, args)
    cc = self.cc
    buf = self.buf

    if 'copy' == cmd:
      if _text_select_present(buf):
        text = buf.get(SEL_FIRST, SEL_LAST)
        cc.set_clipboard_text(text)
      return 'break'

    elif 'select-all' == cmd:
      buf.tag_remove(SEL, '1.0', END)
      buf.tag_add(SEL, '1.0', END)
      buf.mark_set(INSERT, '1.0')
      buf.see(INSERT)
      return 'break'

    elif 'goto-line' == cmd:
      ln = int(buf.index(END).split('.')[0])
      msg = 'Input Line Number 1..%d' % ln
      msg = '移動行を入力ください (範囲 1..%d)' % ln
      tt = cc.input_text(msg, 'line-number')
      if not tt: return
      idx = '%d.0' % int(tt)
      buf.mark_set(INSERT, idx)
      buf.see(idx)
      buf.focus_set()
      return
    
    elif 'open' == cmd:
      tf = cc.ask_open_file(filetypes=text_file_types)
      if not tf: return
      trace(tf)
      cc.execute('load-text', tf, self.encoding)
      
    elif 'find' == cmd:
      try: text = buf.get(SEL_FIRST, SEL_LAST)
      except tk.TclError: text = ''
      fd = cc.find_dialog('find', dialogs.FindDialog)
      fd.open(text, self)

    elif 'font' == cmd:
      fd = cc.find_dialog('font', dialogs.FontDialog)
      fd.open(self)
      return 'break'
    
    elif 'big' == cmd:
      return dialogs.adjust_font_size(self, dir=1)

    elif 'small' == cmd:
      return dialogs.adjust_font_size(self, dir=-1)

    elif 'wrap' == cmd:
      flag = self.wrap.get()
      wrap = 'word' if flag == 1 else 'none'
      buf.config(wrap=wrap)
      return
    
    elif 'close' == cmd:
      self.close()
      
    elif 'new' == cmd:
      self.__class__.start()

    elif 'about' == cmd:
      cc.show_info('Python version: %s\nTK version: %s\n' % (
          sys.version, tk.TkVersion), 'about')

  encoding = None
  
  @property
  def font(self):
    buf = self.buf
    fn = buf.cget('font')
    font = ui.find_font(fn)
    return font
  
  @font.setter
  def font(self, font):
    if type(font) == str: font = ui.find_font(font)
    buf = self.buf
    buf.config(font=font)
    
  def _adjust_font_size(self, ev):
    # マウスホイールでフォントサイズの調整
    return dialogs.adjust_font_size(self, event=ev)
  
  def create_widgets(self, base, columns=30, rows=5):
    cc = self.cc
    buf = tk.ScrolledText(base, width=columns, height=rows,
                  undo=1,maxundo=1000).pack(fill='both', expand=1)
    self.buf = buf
    buf.insert(END, 'メニューの機能試験')
    cc.find_status_bar()

    shortcut = self.find_menu('text-shortcut')
    ui.register_shortcut(buf, shortcut)

    # メニューに登録されているアクセラレータを登録
    for cond, cmd in (
      ('<Control-n>', 'new'),
      ('<Control-a>', 'select-all'),
      ('<Control-c>', 'copy'),
      ('<Control-o>', 'open'),
      ('<Control-l>', 'goto-line'),
      ('<Control-+>', 'big'),
      ('<Control-w>', 'close'),
      ): cc.bind(cond, self.bind_proc(cmd))

    cc.bind('<MouseWheel>', self._adjust_font_size, '+')
    cc.bind('<Button-4>', self._adjust_font_size, '+')
    cc.bind('<Button-5>', self._adjust_font_size, '+')


class EventViewApp(ui.App):
  """発生したキーやボタン・イベントを表示する"""
  
  def create_widgets(self, base, rows=15, column=60):
    cc = self.cc
    fr = Frame(base)
    fr.pack(side='top', fill='both', expand=1)
    sbar = Scrollbar(fr)
    self.buf = buf = tk.Text(fr, width=column, height=rows, padx=5)
    sbar.config(command=buf.yview)
    sbar.pack(side='right', fill='y')
    buf.config(yscrollcommand=sbar.set)
    buf.pack(side='left', fill='both', expand=1)

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

    shortcut = self.find_menu('eventview-shortcut')
    ui.register_shortcut(buf, shortcut)
    #if ui.need_unpost: shortcut.bind('<FocusOut>', lambda ev, wi=shortcut: wi.unpost())
    buf.insert(INSERT, 'platform: %s: %s\n' % (platform.system(), sys.platform))
  
  def _append_event_text(self, ev):
    #print type(ev.keysym), type(ev.keycode)

    def _cv(tt): return str(tt)
    
    et = ' '.join(map(_cv, (
          ev.serial, ev.type, ev.num, ev.char, ev.keysym, 'kcd', ev.keycode,
          'st', ev.state, ev.width, ev.height, ev.x, ev.y, ev.x_root, ev.y_root, ev.delta)))
    buf = self.buf
    buf.insert(END, '%s\n' % (et, ))
    buf.see(END)
    return 'break'
  
  menu_items = [
    [ 'eventview-shortcut;',
      'new;新規に作成する(&N) ..;ctrl-N',
      'clear;ログ削除;',
      '-',
      'close;閉じる(&C);ctrl-W',
    ],
  ]
  
  def perform(self, cmd, *args):
    buf = self.buf
    buf.insert(INSERT, 'perfrom %s %s\n' % (cmd, args))
    if 'close' == cmd or 'exit' == cmd: self.dispose()
    elif 'new' == cmd: self.__class__.start()
    elif 'clear' == cmd: buf.delete('1.0', END)
    

if __name__ == '__main__': MemoApp01.run()
