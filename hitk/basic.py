# -*- coding: utf-8 -*-

""" hitkの一連の基本機能を使ったサンプルコード
"""

from hitk import Button, Checkbutton, Combobox, Entry, Frame,\
    Label, LabelFrame, Listbox, Notebook, Scrollbar, Text, Treeview, \
    StringRef, BooleanRef

from hitk import tk, ui, trace, END, set_tool_tip, item_caption, find_image, \
    entry_focus, entry_store, dialogs

class BasicWidgetApp(ui.App):
  """ウィジェットの基本機能の確認"""
  menu_bar = 'file:view:help'

  menu_items = [
    [ 'file;ファイル(&F)',
      'new;新規作成(&N);ctrl-n',
      'open;ファイルを開く(&O) ..;ctrl-o',
      'opens;複数のファイルを選択して開く(&O) ..',
      'save;ファイルに保存する(&S);ctrl-s',
      'saveAs;名前を指定してファイルに保存する(&A) ..',
      'dir;ディレクトリを選択する(&D) ..;;idlelib/Icons/folder.gif',
      '-',
      'close;閉じる(&C);ctrl-w',
      'exit;アプリを終了する(&E);ctrl-q',
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
      text = self.input
      self.prompt = text

    elif 'combo' == cmd:
      text = self.combo
      self.prompt = '%s selected.' % text
      entry_store(self.combo_ent, text)

    elif 'theme' == cmd:
      if event.widget.current(): # value #0 is not a theme
        newtheme = event.widget.get()
        # change to the new theme and refresh all the widgets
        ui.style.theme_use(newtheme)

    elif 'open' == cmd:
      flag = self.multi
      tf = cc.ask_open_file(multiple=flag, filetypes=self.textFileTypes)
      if not tf: return
      trace(tf)

    elif 'save' == cmd:
      tf = cc.ask_save_file(filetypes=self.textFileTypes, defaultextension='.txt')

    elif 'dir' == cmd:
      tf = cc.ask_folder()
      if not tf: return
      trace(tf)
      self.dirinput = tf

    elif 'close' == cmd:
      cc.close()

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
      fd.open(cc.ref('datepickup'))

    elif 'fg_select' == cmd:
      cn = self.foreground
      ct = cc.ask_color(cn)
      if not ct or not ct[1]: return
      self._set_fg_input(ct[1])

    elif 'fg_color' == cmd:
      cn = self.foreground
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
    self.foreground = cname
    self.fg_sample.configure(background=cname if cname else 'systemWindowText')

  def release(self):
    self.cc.log('release called. %s', self)

  prompt = StringRef()
  input = StringRef()
  passwd = StringRef()
  combo = StringRef()
  
  def _create_basic_tab(self, tab):
    """Basicタブを作成 """
    fr = Frame(tab).pack(side='top')

    self.prompt = 'メッセージ表示(変更できます)'
    lab = Label(tab, name='prompt').pack(side='top', fill='x')
# -- entry
    fr = Frame(tab).pack(side='top')

    cap = 'I&nput'
    pos, label = item_caption(cap)
    lab = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    self.input = 'aaa'
    ent = Entry(fr, width=25, name='input').pack(side='left', padx=3, pady=3)
    ent.bind('<Return>', self.bind_proc('input'))
    ent.label = lab
    entry_focus(ent)

# -- passwod entry
    fr = Frame(tab).pack(side='top')
    cap = '&Password'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    self.passwd = 'bbb'
    ent = Entry(fr, show='*', width=25, name='passwd').pack(side='left', padx=3, pady=3)

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
    lab = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    ent = Combobox(fr, width=30, name='combo').pack(side='left', padx=3, pady=3)
    ent['values'] = ( 'AA', 'BB', 'CC' )
    ent.current(1)
    self.combo_ent = ent

    ent.bind('<<ComboboxSelected>>', self.bind_proc('combo'))
    ent.bind('<Return>', self.bind_proc('combo'))
    ent.bind('<Control-j>', self.bind_proc('combo'))

# -- combobox(Readonly)
    fr = Frame(tab).pack(side='top')
    cap = 'Theme &Select'
    pos, label = item_caption(cap)
    lab = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    themes = list(ui.style.theme_names())
    themes.insert(0, 'Pick a theme')
    cmb = Combobox(fr, values=themes, state='readonly', height=8)
    cmb.set(themes[0])
    cmb.pack(side='left', padx=3, pady=3)
    cmb.bind('<<ComboboxSelected>>', self.bind_proc('theme'))
    cmb.label = lab
    
# -- Text
    fr = Frame(tab).pack(side='top')
    cap = '&Text'
    pos, label = item_caption(cap)
    lab = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    buf = Text(fr, undo=1, maxundo=50, width=25, height=3).pack(side='left', padx=3, pady=3)
    self.buf = buf
    lab.label_for = buf
    
  def _create_list_tab(self, tab):
    """Listタブを作成 """
    sl = _SelectList()
    sl.create_widgets(tab)
    self.list = sl

  multi = BooleanRef()
  dirinput = StringRef()
  datepickup = StringRef()
  foreground = StringRef()
  
  def _create_dialog_tab(self, tab):
    """ダイアログ・タブシートの作成 """
    blist = []
    tab.blist = blist

    fr = Frame(tab).pack(side='top', fill='x', expand=0, padx=5, pady=5)

    cap = '&Open'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self.menu_proc('open')).pack(side='left', padx=3, pady=3)

    self.multi = 1
    cb = Checkbutton(fr, text='multiple', name='multi').pack(side='left', padx=3, pady=3)

    cap = '&Save'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self.menu_proc('save')).pack(side='left', padx=3, pady=3)

 # -- ディレクトリ選択

    fr = Frame(tab).pack(side='top', fill='x', expand=0, padx=5, pady=5)
    cap = '&Directory'
    pos, label = item_caption(cap)
    lab = Label(fr, text=label, underline=pos).pack(side='left', padx=3)
    ent = Entry(fr, width=25, name='dirinput').pack(side='left', padx=3, pady=3)
    ent.label = lab
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
        btn.pack(side='left', padx=3, pady=3)

# -- カレンダ選択

    fr = Frame(tab).pack(side='top', fill='x', expand=0, padx=5, pady=5)

    cap = '&Calendar'
    pos, label = item_caption(cap)
    lab = Label(fr, text=label, underline=pos).pack(side='left', padx=3)
    ent = Entry(fr, width=15, name='datepickup').pack(side='left', padx=3, pady=3)
    ent.label = lab
    btn = tk.Button(fr, text='..', command=self.menu_proc('calendar-popup')).pack(side='left', padx=3, pady=3)

 # -- 色選択

    fr = Frame(tab).pack(side='top', fill='x', expand=0, padx=5, pady=5)
    cap = '&Foreground'
    pos, label = item_caption(cap)
    lab = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    self.fg_sample = tk.Label(fr, text='   ').pack(side='left', padx=3)

    ent = Entry(fr, width=25, name='foreground').pack(side='left', padx=3, pady=3)
    ent.bind('<Return>', self.bind_proc('fg_color'))
    ent.label = lab
    
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
    ui.register_dnd_notify(comp.buf, self.dnd_notify)

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



class _EmptyTreeData:
  """ツリーデータを入手する"""

  def __init__(self, rows=1000, cols=10, **opts):
    self.rows = rows


    
class TreeDemo(ui.App):
  """Treeview の振る舞いの確認"""
    
  menu_items = [
    [ 'tree-shortcut;',
      'add-child;子ノードを追加(&A)',
      'insert-node;兄弟ノードを追加(&I)',
      'rename;ノード名称変更(&R);F2',
      'delete-node;ノードの削除(&D);delete',
      '-',
      'expand-all;ノードの展開(&E);ctrl-Right',
      'collapse-all;ノードの折り畳み(&L);ctrl-Left',
      '-',
      'copy;クリップボードにテキストを取り込む(&P);ctrl-c',
      'paste;クリップボードのテキストを取り込む(&P);ctrl-v',
      'select-all;全て選択(&S)',
      'clear-selection;選択解除(&N)',
      '-',
      [
        'select-mode;&Selection Mode;',
        '*sm.browse;&Browse',
        '*sm.extended;&Extended',
        '*sm.none;&None',
      ],
      [
        'view;表示(&V);',
        'show-selected-item; 選択したアイテムを表示(&I);',
        'show-all-item; 全て表示(&A)',
      ],
      '-',
      'close;閉じる(&C);ctrl-w',
    ]
  ]
  
  def perform(self, cmd, *args):
    """メニュー選択により動作する機能"""
    tree = self.tree
    cc = self.cc

    if cmd.startswith('sm.'):
      sm = cmd[3:]
      tree['selectmode'] = sm
      cc.set_status('change selection mode: %s', sm)
      return

    elif 'add-child' == cmd:
      # 子ノードを追加
      msg = '追加する子ノード名を入力ください '
      tt = cc.input_text(msg, 'add-child')
      if not tt: return
      parent = tree.focus()
      iid = tree.insert(parent, END, text=tt)
      tree.item(parent, open=1)
      if not parent: tree.focus(iid)
      return

    elif 'insert-node' == cmd:
      # 兄弟ノードを挿入
      msg = '挿入するノード名を入力ください '
      tt = cc.input_text(msg, 'insert-node')
      if not tt: return
      iid = tree.focus()
      if not iid:
        # ルートに追加
        iid = tree.insert('', END, text=tt)
        tree.focus(iid)
        return
      pos = tree.index(iid)
      parent = tree.parent(iid)
      tree.insert(parent, pos, text=tt)
      return

    elif 'rename' == cmd:
      # ノード名称変更
      iid = tree.focus()
      if not iid: self.cc.show_warnig('ノードが選択されていません'); return
      msg = '変更後のテキストを入力ください '
      tt = cc.input_text(msg, 'rename-node')
      if not tt: return
      tree.item(iid,text=tt)

    elif 'delete-node' == cmd:
      # 選択したノードを削除
      iid = tree.focus()
      by = tree.bbox(iid)[1]+1 if iid else 0
      items = reversed(tree.selection())
      if items: tree.delete(*items)
      iid = tree.identify_row(by)
      if iid: tree.focus(iid)
            
    elif 'copy' == cmd:
      # 選択されたノードのテキストをクリップボードに複製
      selc = tree.selection()
      sels = set(selc)
      idc = self.indent_char

      def _has_selected_node(items):
        # 選択されたノードが子孫に存在するか診断する
        if not items: return False
        for iid in items:
          if iid in sels: return True
          children = tree.get_children(iid)
          if _has_selected_node(children): return True
        return False

      def _has_selected_child(children):
        # 選択されたノードが子に存在するか診断する
        if not children: return False
        for iid in children:
          if iid in sels: return True
        return False

      def _node_text(iid, buf, ind=0):
        # 選択されたノードだけをピックアップする
        text = tree.item(iid, 'text')
        buf.append('%s%s' % (idc * ind, text) if ind else text)
        children = tree.get_children(iid)
        if not children: return 
        ind += 1
        if _has_selected_node(children):
          # 選択されている子ノードだけ複製
          for ciid in children:
            if ciid in sels:
              _node_text(ciid,buf,ind)
              sels.remove(ciid)
        else:
          # 子ノード全部を複製
          for ciid in children:
            _node_text(ciid,buf,ind)
            
      def _node_text_all(iid,buf,ind=0):
        # 指定するノードとその子孫をピックアップする
        text = tree.item(iid,'text')
        buf.append('%s%s' % (idc * ind, text) if ind else text)
        children = tree.get_children(iid)
        if not children: return 
        ind += 1
        for ciid in children:
          _node_text_all(ciid,buf,ind)

      # --- ここからテキストの収集
      buf = []
      for iid in selc:
        if not iid in sels: continue
        children = tree.get_children(iid)
        if _has_selected_node(children):
          _node_text(iid, buf)
        else:
          _node_text_all(iid, buf)

      text = '\n'.join(buf)
      buf = None
      if text:
        tree.clipboard_clear()
        tree.clipboard_append(text)
        trace(text)

    elif 'paste' == cmd:
      text = tree.selection_get(selection='CLIPBOARD')
      iid = tree.focus()
      idx = tree.index(iid) if iid else END
      parent = tree.parent(iid) if iid else ''
      trace(text)
      idc = self.indent_char

      def _paste_node(parent,idx,textlist,ind=0):
        children = tree.get_children(parent)
        iid = children[-1] if idx == END else children[idx]
                
        while textlist:
          tt = textlist[0]
          if tt[ind] == idc:
            cind = ind + 1
            if tt[cind] == idc:
              # 孫ノードがいる
              _paste_node(iid,END,textlist,cind)
              if not textlist: return
            # 子ノードを追加
            tt = textlist.pop(0)
            tree.insert(iid, END, text = tt[cind:])
            continue
        
          # 兄弟を追加
          tt = textlist.pop(0)
          iid = tree.insert(parent, idx, text = tt[ind:])
          if idx != END: idx += 1

      _paste_node(parent, idx, text.split('\n'))

    elif 'select-all' == cmd:
      # 全てのアイテムを選択する
      def select_items(items):
        if not items: return
        tree.selection_add(items)
        for iid in items:
          children = tree.get_children(iid)
          select_items(children)

      children = tree.get_children()
      select_items(children)

    elif 'clear-selection' == cmd:
      # 選択アイテムを解除する
      items = tree.selection()
      tree.selection_remove(items)
      trace(items)
      
    elif 'show-selected-item' == cmd:
      # 選択アイテムを表示する
      items = tree.selection()
      for it in items:
        ti = tree.item(it)
        trace(ti, type(ti))
        ti = tree.item(it,'text')
        trace(ti, type(ti))

    elif 'show-all-item' == cmd:
      def _show_items(items,indent=0):
        if not items: return
        pre = ' ' * indent
        for iid in items:
          ti = tree.item(iid,'text')
          trace(pre, ti)
          children = tree.get_children(iid)
          show_items(children, indent + 1)

      root_items = tree.get_children()
      _show_items(root_items)

    elif 'expand-all' == cmd:
      #選択アイテムを展開する
      def _expand_items(items):
        if not items: return
        for iid in items:
          tree.item(iid,open=1)
          children = tree.get_children(iid)
          _expand_items(children)

      items = tree.selection()
      _expand_items(items)
      return 'break'
        
    elif 'collapse-all' == cmd:
      #選択アイテムを折り畳む
      def _collapse_items(items):
        if not items: return
        for iid in items:
          tree.item(iid,open=0)
          children = tree.get_children(iid)
          _collapse_items(children)

      items = tree.selection()
      _collapse_items(items)
      return 'break'

    elif 'close' == cmd:
      cc.close()
            
  def __init__(self):
    self.indent_char = '\t'

  def __test_data(self, tree):
    tree.insert('' , 0, text='Line 1')
 
    id2 = tree.insert('', 1, 'dir2', text='Dir 2', open=True)
    tree.insert(id2, 'end', 'dir 2', text='sub dir 1')
    tree.insert(id2, 'end', 'dir 2a', text='sub dir 2')
    id3 = tree.insert(id2, 'end', 'dir 2b', text='sub dir 3')
    tree.insert(id2, 'end', 'dir 2c', text='sub dir 4')

    for n in xrange(0,3):
      tree.insert(id3, END, text='%d sub dir' % n)

    ##alternatively:    
    tree.insert('', 3, 'dir3', text='Dir 3', open=True)
    for n in xrange(0,7):
      tree.insert('dir3', 3, text='%d sub dir' % n)

    tree.focus_set()
    tree.focus(id3)

  def create_widgets(self, base):
    cc = self.cc
    cc.find_status_bar()

    if False:
      fr = Frame(base)
      fr.pack(side='top', fill='x')
            
      cap = '&Tree Editor'
      cap = 'ツリーエディタ(&T)'
      pos, label = item_caption(cap)
      cap = Label(fr, text=label, underline=pos).pack(side='left')
        
    fr = Frame(base).pack(side='top', fill='both', expand=1)

    tree = Treeview(fr, show='tree', takefocus=True, height=10,
                    selectmode='extended')
    self.tree = tree
    ysb = Scrollbar(fr, orient='vertical', command=tree.yview)
    ysb.pack(side='right', fill='y')
    tree.configure(yscroll=ysb.set)
    tree.pack(side='top', fill='both', expand=1)
    tree.heading('#0', text='Path', anchor='w')

    shortcut = self.find_menu('tree-shortcut')
    ui.register_shortcut(tree, shortcut)

    tree.timer = None
    delay_msec = 600
        
    def _delay_proc(event):
      # 遅延表示
      if tree.timer: tree.after_cancel(tree.timer)
      tiid = tree.focus()
      if tiid:
        tree.timer = tree.after(delay_msec, lambda wi=tree, iid=tiid:
                                trace(wi.index(iid), wi.item(iid, 'text'), iid))
            
    tree.bind('<<TreeviewSelect>>', _delay_proc)
    tree.bind('<<TreeviewOpen>>', _delay_proc)
    tree.bind('<<TreeviewClose>>', _delay_proc)
    
    sm = cc.menu['select-mode']
    sm.set('sm.extended')
    self.selection_mode = sm

    self.__test_data(tree)

    for ev, cmd in (
        ('<\Control-Insert>', 'copy'),
        ('<Shift-Insert>', 'paste'),
        ('<Delete>', 'delete-node'),
        ('<F2>', 'rename'),
        ('<\Control-Right>', 'expand-all'),
        ('<\Control-Left>', 'collapse-all'),
    ): tree.bind(ev, self.bind_proc(cmd))


if __name__ == '__main__':
    #_SelectList.start()
    BasicWidgetApp.run()
