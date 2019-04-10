# -*- coding: utf-8 -*-

""" tkuiの一連の基本機能を使ったサンプルコード
"""

from hitk import Button, Checkbutton, Combobox, Entry, Frame,\
    Label, LabelFrame, Listbox, Notebook, Scrollbar, Text, StringVar, BooleanVar

from hitk import tk, ui, trace, END, set_tool_tip, item_caption, find_image, \
    entry_focus, entry_store, dialogs

class BasicWidgetApp(ui.App):
  """ウィジェットの基本機能の確認"""

  menubar_items = [
    'basic_menubar;',
    [ 'file;ファイル(&F)',
      'new;新規作成(&N);ctrl-N',
      'open;ファイルを開く(&O) ..;ctrl-O',
      'opens;複数のファイルを選択して開く(&O) ..',
      'save;ファイルに保存する(&S);ctrl-S',
      'saveAs;名前を指定してファイルに保存する(&A) ..',
      'dir;ディレクトリを選択する(&D) ..;;idlelib/Icons/folder.gif',
      '-',
      'close;閉じる(&C);ctrl-W',
      'exit;アプリを終了する(&E);ctrl-Q',
      ],
    [ 'view;表示(&V)',
      '*aa;&AA',
      '*bb;&BB',
      '*cc;&CC',
      '',
      '+xx;&XX',
      '+yy;&YY',
      '+zz;&ZZ',
      ],
    [ 'help;ヘルプ(&H)',
      'about;このアプリについて(&A);;idlelib/Icons/python.gif',
      ],
    ]
  
  # ダイアログで利用するファイルのサフィックス情報。
  textFileTypes = [
    ('Plain Text', '*.txt'),
    ('Python Source File', '*.py;*.pyw'),
    ('Comma/Tab Separated Value', '*.csv;*.tsv'),
    ('XML', '*.xml'),
    ('HTML', '*.html;*.htm'),
    ('All Files', '*'),
    ]

  def perform(self, cmd, *args):
    """ メニュー選択により動作する機能"""
    if ui.verbose: trace(cmd, args)
    if args: event = args[0]
    cc = self.cc

    if 'clock' == cmd:
      self.buf.bell()

    elif 'input' == cmd:
      text = self.input.get()
      self.prompt.set(text)

    elif 'combo' == cmd:
      text = self.sel.get()
      self.prompt.set('%s selected.' % text)
      entry_store(self.combo, text)

    elif 'theme' == cmd:
      if event.widget.current(): # value #0 is not a theme
        newtheme = event.widget.get()
        # change to the new theme and refresh all the widgets
        ui.style.theme_use(newtheme)

    elif 'open' == cmd:
      flag = self.multi.get()
      tf = cc.ask_open_file(multiple=flag, filetypes=self.textFileTypes)
      if not tf: return
      trace(tf)

    elif 'save' == cmd:
      tf = cc.ask_save_file(filetypes=self.textFileTypes, defaultextension='.txt')

    elif 'dir' == cmd:
      tf = cc.ask_folder()
      if not tf: return
      trace(tf)
      self.dirinput.set(tf)

    elif 'close' == cmd:
      self.close()

    elif 'info-msg' == cmd:
      cc.show_info('情報メッセージ表示')

    elif 'warn-msg' == cmd:
      cc.show_warnig('警告メッセージ表示')

    elif 'error-msg' == cmd:
      cc.show_error('エラー・メッセージ表示')

    elif 'yes-no' == cmd:
      rc = cc.ask_yes_no('処理を継続しますか？')
      cc.set_status('%s selected.' % rc)

    elif 'retry-cancel' == cmd:
      rc = cc.ask_retry_cacnel('処理が継続できません')
      cc.set_status('%s selected.' % rc)

    elif 'abort-retry-ignore' == cmd:
      rc = cc.ask_abort_retry_ignore('処理が継続できません')
      cc.set_status('%s selected.' % rc)

    elif 'input-text' == cmd:
      text = cc.input_text('テキストを入力ください')
      cc.set_status('input text: %s' % text)

    elif 'calendar-popup' == cmd:
      parent = args[0].widget if args else self.cc.top
      fd = cc.find_dialog('calendar', dialogs.CalendarDialog, parent)
      fd.open(self.datepickup)

    elif 'fg_select' == cmd:
      cn = self.fg_name.get()
      ct = cc.ask_color(cn)
      if not ct or not ct[1]: return
      self._set_fg_input(ct[1])

    elif 'fg_color' == cmd:
      cn = self.fg_name.get()
      self._set_fg_input(cn)

    elif 'new' == cmd:
      self.__class__.start()

    elif 'exit' == cmd:
      cc.exit()

    elif 'about' == cmd:
      cc.show_info('Python version: %s\nTK version: %s\n' %
                   (ui.sys.version, tk.TkVersion) , 'about')

  def _set_fg_input(self, cname):
    """色を設定する"""
  # http://wiki.tcl.tk/37701
    self.fg_name.set(cname)
    self.fg_sample.configure(background=cname if cname else 'systemWindowText')

  def create_menu_bar(self):
    """メニュー定義テキストよりメニュー・インスタンスを作成する"""
    bar = self.find_menu(self.menubar_items)
    return bar

  def release(self):
    self.cc.log('release called. %s', self)

  def _create_basic_tab(self,tab):
    """Basicタブを作成 """
    fr = Frame(tab).pack(side='top')
    blist = []
    tab.blist = blist

    var = StringVar()
    self.prompt = var
    prompt = 'メッセージ表示(変更できます)'
    var.set(prompt)
    cap = Label(tab, textvariable=var).pack(side='top', fill='x')
# -- entry
    fr = Frame(tab).pack(side='top')

    cap = 'I&nput'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    var = StringVar()
    self.input = var
    var.set('aaa')
    ent = Entry(fr, width=25, textvariable=var).pack(side='left', padx=3, pady=3)
    ent.bind('<Return>', self.bind_proc('input'))
    ui.register_entry_popup(ent)
    blist.append(('<Alt-n>', lambda event, wi=ent: entry_focus(wi)))
    entry_focus(ent)

# -- passwod entry
    fr = Frame(tab).pack(side='top')

    cap = '&Password'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    var = StringVar()
    var.set('bbb')
    self.passwd = var
    ent = Entry(fr, show='*', width=25, textvariable=var).pack(side='left', padx=3, pady=3)
    ui.register_entry_popup(ent)
    blist.append(('<Alt-p>', lambda event, wi=ent: entry_focus(wi)))

# -- button

    fr = Frame(tab).pack(side='top')

    CLOCK = 'ref/meza-bl-2.gif'
    img = find_image(CLOCK)

    cap = 'Change'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos,
                 image=img, compound='top',
                 command=self.menu_proc('input')).pack(side='left', padx=3, pady=3)
    ui.set_tool_tip(btn, 'メッセージを入力値に置き換えます。')

# -- combobox(Edit)
    fr = Frame(tab).pack(side='top')

    cap = 'Co&mbobox'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    var = StringVar()
    self.sel = var
    ent = Combobox(fr, width=30, textvariable=var)
    ent['values'] = ( 'AA', 'BB', 'CC' )
    ent.current(1)
    ent.pack(side='left', padx=3, pady=3)
    self.combo = ent

    ent.bind('<<ComboboxSelected>>', self.bind_proc('combo'))
    ent.bind('<Return>', self.bind_proc('combo'))
    ent.bind('<Control-j>', self.bind_proc('combo'))
    ui.register_entry_popup(ent)
    blist.append(('<Alt-m>', lambda event, wi=ent: entry_focus(wi)))

# -- combobox(Readonly)
    fr = Frame(tab).pack(side='top')
    cap = 'Theme &Select'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    themes = list(ui.style.theme_names())
    themes.insert(0, 'Pick a theme')
    cmb = Combobox(fr, values=themes, state='readonly', height=8)
    cmb.set(themes[0])
    cmb.pack(side='left', padx=3, pady=3)
    cmb.bind('<<ComboboxSelected>>', self.bind_proc('theme'))
    blist.append(('<Alt-s>', lambda event, wi=ent: wi.focus_set()))

# -- Text
    fr = Frame(tab).pack(side='top')
    cap = '&Text'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='left', padx=3)
    buf = Text(fr, undo=1, maxundo=50, width=25, height=3).pack(side='left', padx=3, pady=3)
    self.buf = buf
    ui.register_text_popup(buf)
    blist.append(('<Alt-t>', lambda event, wi=buf: wi.focus_set()))

  def _create_list_tab(self, tab):
    """Listタブを作成 """
    sl = _SelectList()
    sl.create_widgets(tab)
    self.list = sl

  def _create_dialog_tab(self, tab):
    """ダイアログ・タブシートの作成 """
    blist = []
    tab.blist = blist

    fr = Frame(tab).pack(side='top', fill='x', expand=0, padx=5, pady=5)

    def invoke(btn): btn.focus(); btn.invoke()

    cap = '&Open'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self.menu_proc('open')).pack(side='left', padx=3, pady=3)
    blist.append(('<Alt-%s>' % cap[pos+1].lower(), lambda event, wi=btn: invoke(wi)))

    var = BooleanVar()
    var.set(1)
    self.multi = var
    cb = Checkbutton(fr, text='multiple', variable=var).pack(side='left', padx=3, pady=3)

    cap = '&Save'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self.menu_proc('save')).pack(side='left', padx=3, pady=3)
    blist.append(('<Alt-%s>' % cap[pos+1].lower(), lambda event, wi=btn: invoke(wi)))

 # -- ディレクトリ選択

    fr = Frame(tab).pack(side='top', fill='x', expand=0, padx=5, pady=5)
    cap = '&Directory'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    var = StringVar()
    self.dirinput = var
    ent = Entry(fr, width=25, textvariable=var).pack(side='left', padx=3, pady=3)
    ui.register_entry_popup(ent)
    blist.append(('<Alt-d>', lambda event, wi=ent: entry_focus(wi)))

    btn = tk.Button(fr, text='..', command=self.menu_proc('dir')).pack(side='left', padx=3, pady=3)

# ポップアップ
    fr = LabelFrame(tab, text='message dialog').pack(side='top', fill='x', expand=0, padx=5, pady=5)

    for cap, cmd in (
      ('&Information', 'info-msg'),
      ('&Warning', 'warn-msg'),
      ('&Error', 'error-msg'),
      ):
        pos, label = item_caption(cap)
        btn = Button(fr, text=label, underline=pos, command=self.menu_proc(cmd))

        blist.append(('<Alt-%s>' % cap[pos+1].lower(), lambda event, wi=btn: invoke(wi)))
        btn.pack(side='left', padx=3, pady=3)

    fr = LabelFrame(tab, text='confirm dialog').pack(side='top', fill='x', expand=0, padx=5, pady=5)
    for cap, cmd in (
        ('&Yes No', 'yes-no'),
        ('&Retry Cancel', 'retry-cancel'),
        ('&Abort Retry Ignore', 'abort-retry-ignore'),
        ('Input &Text', 'input-text'),
        ):
        pos, label = item_caption(cap)
        btn = Button(fr, text=label, underline=pos, command=self.menu_proc(cmd))

        if ui.platform != 'darwin':
            blist.append(('<Alt-%s>' % cap[pos+1].lower(), lambda event, wi=btn: invoke(wi)))
        btn.pack(side='left', padx=3, pady=3)

# -- カレンダ選択

    fr = Frame(tab).pack(side='top', fill='x', expand=0, padx=5, pady=5)

    cap = '&Calendar'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    var = StringVar()
    self.datepickup = var
    ent = Entry(fr, width=15, textvariable=var).pack(side='left', padx=3, pady=3)
    ui.register_entry_popup(ent)
    blist.append(('<Alt-c>', lambda event, wi=ent: entry_focus(wi)))

    btn = tk.Button(fr, text='..',
                    command=self.menu_proc('calendar-popup')).pack(side='left', padx=3, pady=3)

 # -- 色選択

    fr = Frame(tab).pack(side='top', fill='x', expand=0, padx=5, pady=5)
    cap = '&Foreground'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    cap = tk.Label(fr, text='   ').pack(side='left', padx=3)
    self.fg_sample = cap

    var = StringVar()
    self.fg_name = var
    ent = Entry(fr, width=25, textvariable=var).pack(side='left', padx=3, pady=3)
    ui.register_entry_popup(ent)
    blist.append(('<Alt-f>', lambda event, wi=ent: entry_focus(wi)))
    ent.bind('<Return>', self.bind_proc('fg_color'))

    btn = tk.Button(fr, text='..', command=self.menu_proc('fg_select')).pack(side='left', padx=3, pady=3)
    cn = 'black'
    self._set_fg_input(cn)

# ------------------------ テーブル操作関連の記述　ここから

  def _create_table_tab(self, tab):
    """テーブル・タブシートの作成"""
    from assistant.tkui.tsv_editor import TsvEditor
    self.tsv_editor = comp = TsvEditor()
    comp.client_context = self.cc
    comp.create_widgets(tab)

# ------------------------ テキスト操作関連の記述　ここから

  def _create_text_tab(self, tab):
    """テーブル・タブシートの作成"""
    from assistant.tkui.edit02 import Memo
    self.tsv_editor = comp = Memo()
    comp.client_context = self.cc
    comp.create_widgets(tab)
    tkui.register_dnd_notify(comp.buf, self.dnd_notify)

  def dnd_notify(self, filenames, wi):
    for nn in filenames:
        wi.insert(END, '%s\n' % nn)

  def create_widgets(self, base):
    """構成コンポーネントの作成"""

    fr = self.cc.find_status_bar()
    nb = Notebook(base).pack(expand=1, fill='both', padx=5, pady=5)
    nb.enable_traversal()
    nb.tno = None
    tno = 0
    tab_bind = { }
        
    def _tab_changed(event):
      """タブの切り替えで、まとめてバインド"""
      if nb.tno in tab_bind:
          for bk, proc in tab_bind[nb.tno]: self.cc.unbind(bk)
      nb.tno = nb.index('current')
      if nb.tno in tab_bind:
        for bk, proc in tab_bind[nb.tno]: self.cc.bind(bk, proc)

    # タブの切り替えで呼び出される仮想イベント
    nb.bind('<<NotebookTabChanged>>', _tab_changed)

    # -- 基本コンポーネントシート

    tab = Frame(nb).pack(expand=1, fill='both', padx=5, pady=5)
    cap = '&Basic'
    pos, label = item_caption(cap)
    nb.add(tab, text=label, underline=pos)

    self._create_basic_tab(tab)
    if hasattr(tab, 'blist'): tab_bind[tno] = tab.blist
    tno += 1

    # -- ダイアログ呼び出し
    tab = Frame(nb).pack(expand=1, fill='both', padx=5, pady=5)
    cap = '&Dialog'
    pos, label = item_caption(cap)
    nb.add(tab, text=label, underline=pos)

    self._create_dialog_tab(tab)
    if hasattr(tab, 'blist'): tab_bind[tno] = tab.blist
    tno += 1
        
    # -- リスト・コンポーネントシート
    if 1:
        tab = Frame(nb).pack(expand=1, fill='both', padx=5, pady=5)
        cap = '&List'
        pos, label = item_caption(cap)
        nb.add(tab, text=label, underline=pos)
        self._create_list_tab(tab)
        tno += 1

    # -- テーブル表示のサンプル
    if 0:
        tab = Frame(nb).pack(expand=1, fill='both', padx=5, pady=5)
        cap = '&Table'
        pos, label = item_caption(cap)
        nb.add(tab, text=label, underline=pos)
        self._create_table_tab(tab)
        tno += 1

    # -- テキスト表示のサンプル
    if 0:
        tab = Frame(nb).pack(expand=1, fill='both', padx=5, pady=5)
        cap = 'Te&xt'
        pos, label = item_caption(cap)
        nb.add(tab, text=label, underline=pos)
        self._create_text_tab(tab)
        tno += 1

    # -- 下部のボタン配置
    if 1:
        fr = Frame(base).pack(expand=0, side='bottom')
        cap = '&Close'
        pos, label = item_caption(cap)
        btn = Button(fr, text=label, underline=pos, command=self.dispose).pack(side='left', padx=3, pady=3)
        self.cc.bind('<Alt-%s>' % cap[pos + 1].lower(), lambda event, wi=btn: wi.invoke())

    # -- キーバインドの設定
    if 1:
        for ev, cmd in (
            ('<Control-a>', 'select-all'),
            ('<Control-o>', 'open'),
            ('<Control-s>', 'save'),
            ('<Control-q>', 'exit'),
            ('<Control-w>', 'close'),
            ('<F5>', 'datetime'),
            ): self.cc.bind(ev, self.bind_proc(cmd))


class _SelectList(ui.App):
  """リストを使った選択ダイアログ"""

  def create_widgets(self, tab):
    rows = 8
# -- left list
    fr = Frame(tab).pack(side='left', fill='both', expand=1)

    cap = "Source"
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='top', padx=3)

    lb = Listbox(fr, height=rows, selectmode=tk.EXTENDED).pack(side='left', fill='both', expand=1)
    lb.bind('<Double-1>', self._left_selected)
    lb.bind('<Return>', self._left_selected)
    ui.setup_theme(lb)

    sb = Scrollbar(fr).pack(side='left', fill='y', expand=0)
    sb.config(command=lb.yview)
    lb.config(yscrollcommand=sb.set)
    for nn in dir(self): lb.insert(END, nn)
    self.leftList = lb
    fr = Frame(tab).pack(side='left', fill='y')

# -- button
    fr = Frame(tab).pack(side='left', fill='y', pady=10, padx=3)
    btn = Button(fr, text='>>', command=self._left_move_all).pack(side='top', pady=3)
    btn = Button(fr, text='<<', command=self._right_move_all).pack(side='top', pady=3)
    btn = Button(fr, text='>', command=self._left_selected).pack(side='top', pady=3)
    btn = Button(fr, text='<', command=self._right_selected).pack(side='top', pady=3)
    
# -- right list
    fr = Frame(tab).pack(side='left', fill='both', expand=1)
    cap = "Selected"
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='top', padx=3)

    lb = Listbox(fr, height=rows, selectmode=tk.EXTENDED).pack(side='left', fill='both', expand=1)
    lb.bind('<Double-1>', self._right_selected)
    lb.bind('<Return>', self._right_selected)
    ui.setup_theme(lb)
    
    sb = Scrollbar(fr).pack(side='left', fill='y', expand=0)
    sb.config(command=lb.yview)
    lb.config(yscrollcommand=sb.set)

    self.rightList = lb

  def _left_selected(self, *event):
    self._move_list_item(self.leftList, self.rightList)

  def _right_selected(self, *event):
    self._move_list_item(self.rightList, self.leftList)

  def _move_list_item(self, src, dst):
    indexes = sorted(src.curselection(),reverse=True)
    items = []
    for idx in indexes:
      label = src.get(idx)
      src.delete(idx)
      items.append(label)
        
    items.reverse()
    for label in items:
      dst.insert(END, label)

  def _left_move_all(self, *event):
    self._move_list_item_all(self.leftList, self.rightList)

  def _right_move_all(self, *event):
    self._move_list_item_all(self.rightList, self.leftList)

  def _move_list_item_all(self, src, dst):
    items = sorted(src.get(0, END))
    src.delete(0, END)
    for label in items: dst.insert(END, label)



if __name__ == '__main__':
    #_SelectList.start()
    BasicWidgetApp.run()
