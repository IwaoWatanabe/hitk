# -*- coding: utf-8 -*-

"""　パッケージで提供するカスタム・ダイアログを定義
"""

import calendar
from datetime import datetime as _dt
from hitk import ui, Button, Checkbutton, Combobox, Entry, Frame, Label, LabelFrame, Listbox, \
  Radiobutton, Scrollbar, Treeview, BooleanVar, IntVar, StringVar, tkfont, \
  entry_store, item_caption, END, ui, trace


class FindDelegate():
  """検索ダイアログから呼び出されるメソッドを定義する"""

  def search_forward(self, term, nocase=None, regexp=None):
    """順方向に検索する"""
    pass

  def search_backward(self, term, nocase=None, regexp=None):
    """逆方向に検索する"""
    pass

  def replace_term(self, term):
    """テキストを置き換える"""
    pass

  def end_search(self):
    """検索操作を終了する"""
    pass

  def hilight(self, term, nocase=True, tag='hilight'):
    """検索対象をハイライト表示する"""
    pass


calendar.setfirstweekday(calendar.SUNDAY)

class _Calendar(Frame):
  """カレンダーを表示するコンポーネント"""
    
  def __init__(self, master=None, mon=None, year=None):
    Frame.__init__(self, master)
    self.cell = None
    self.base = None
    now = _dt.now()
    if not mon: mon = now.month
    if not year: year = now.year
    
    var = StringVar()
    self.caption = var
    var.set('%s-%s' % (year, mon))
    cap = Label(self, textvariable=var).pack(side='top')
    tbl = self.table = Treeview(self, takefocus=1, height=6, show='headings', selectmode='none')
    tbl.pack(side='top')

    week = ('Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa')
    tbl['columns'] = week
    
    for wn in week:
      tbl.heading(wn, text=wn)
      tbl.column(wn, width=30, anchor='center')
        
    var = StringVar()
    cell = ui.tk.Label(tbl, textvariable=var, anchor='center', bg='orange')
    cell.var = var
    cell.timer = None
    cell.info = None
    self.cell = cell
    self.reset_days(mon, year)
    
    for cond, proc in (
        ('<Button-1>', self._select_day),
        ('<FocusIn>', lambda ev: self._update_cell()),
        ('<FocusOut>', lambda ev: self.cell.place_forget()),
        ('<Configure>', self._resize_notify),
        ('<Double-1>', self.pickup_day),
        ('<Up>', lambda ev, key='up': self._key_action(ev, key)),
        ('<Down>', lambda ev, key='down': self._key_action(ev, key)),
        ('<Left>', lambda ev, key='left': self._key_action(ev, key)),
        ('<Right>', lambda ev, key='right': self._key_action(ev, key)),
        ('<End>', lambda ev, key='end': self._key_action(ev, key)),
        ('<Home>', lambda ev, key='home': self._key_action(ev, key)),
        ('<Control-f>', lambda ev, key='right': self._key_action(ev, key)),
        ('<Control-b>', lambda ev, key='left': self._key_action(ev, key)),
        ('<Control-p>', lambda ev, key='up': self._key_action(ev, key)),
        ('<Control-n>', lambda ev, key='down': self._key_action(ev, key)),
        ('<Control-a>', lambda ev, key='home': self._key_action(ev, key)),
        ('<Control-e>', lambda ev, key='end': self._key_action(ev, key)),
        ('<Return>', self.pickup_day),
        ): tbl.bind(cond, proc)
    cell.bind('<Double-1>', self.pickup_day)
    self.ent = None

  def _key_action(self, ev, cmd):
    tbl = ev.widget
    cell = self.cell
    iid, column = cell.info if cell.info else (tbl.get_children()[0], '#1')
    columns = len(tbl['columns'])
    # trace(ev, cmd, iid, column, columns)
    
    if 'down' == cmd:
      niid = tbl.next(iid)
      if niid: cell.info = (niid, column); self._update_cell(True)
      return
    elif 'up' == cmd:
      niid = tbl.prev(iid)
      if niid: cell.info = (niid, column); self._update_cell(True)
      return
    elif 'right' == cmd:
      cn = int(column[1:])
      if cn < columns:
        cell.info = (iid, '#%d' % (cn+1)); self._update_cell(True)
      else:
        niid = tbl.next(iid)
        if niid: cell.info = (niid, '#1'); self._update_cell(True)
        return
    elif 'left' == cmd:
      cn = int(column[1:])
      if cn > 1:
        cell.info = (iid, '#%d' % (cn-1)); self._update_cell(True)
      else:
        niid = tbl.prev(iid)
        if niid: cell.info = (niid, '#%d' % columns); self._update_cell(True)
        return
    elif 'home' == cmd:
      cell.info = (iid, '#1'); self._update_cell(True)
      return
    elif 'end' == cmd:
      cell.info = (iid, '#%d' % columns); self._update_cell(True)
      return

  def get_cell_info(self, ev):
    tbl = self.table
    item = tbl.identify('item', ev.x, ev.y)
    column = tbl.identify('column', ev.x, ev.y)
    return item, column

  def pickup_day(self, ev=None):
    """セル位置の日付の入手"""
    item, column = self.cell.info
    day = self.table.set(item, column)
    if not day: return None
    value = '%s-%s-%s' % (self.year, self.month, day)
    if self.ent:
      self.ent.set(value)
      if hasattr(self.ent, 'action'): self.ent.action()
    return value

  def _select_day(self, ev):
    """セル位置の選択"""
    self.cell.info = self.get_cell_info(ev)
    self._update_cell(with_value=True)

  def _resize_notify(self, ev):
    """大きさ変更に追随してセルの大きさの変更"""
    cell = self.cell
    delay = 100
    if cell.timer: cell.after_cancel(cell.timer)
    cell.timer = cell.after(delay, self._update_cell)
    
  def _update_cell(self, with_value=False):
    """選択されたセル位置を調整する"""
    if self.base: self.base.cal = self
    cell = self.cell
    if not cell: return
    cell.place_forget()
    if not cell.info: return
    try:
      item, column = cell.info[:2]
      bbox = self.table.bbox(item, column)
      if not bbox: return
      x, y, width, height = bbox
      cell.place(x=x, y=y, width=width, height=height)
      if with_value:
        # trace("(",item,column,")")
        value = self.table.set(item, column)
        cell.var.set(value)
    except: pass

  def reset_days(self, mon, year):
    """年月を指定して、日付を再設定する"""
    self.caption.set("%s-%s" % (year, mon))
    tbl = self.table
    items = tbl.get_children()
    tbl.delete(*items)
    if self.cell: self.cell.place_forget()
    
    td = _dt.today()
    if td.year != year or td.month != mon: td = None
    # print 'td:', td
    
    ca = calendar.monthcalendar(year, mon)
    ci = 0
    for days in ca:
      try:
        if td: ci = days.index(td.day) + 1
      # カラム位置を入手
      except: pass

      #  表示用に文字列に変換する
      dt = []
      for nn in days:
        if nn == 0: nn = ''
        dt.append(str(nn))

      iid = tbl.insert('', 'end', values=dt)
    # trace('iid', iid, 'ci:', ci)

      if ci and self.cell:
        self.cell.info = ( iid, '#%d' % ci)
        self.cell.var.set(td.day)
        tbl.after_idle(self._update_cell)
        # trace('cell:', self.cell.info)
        ci = 0

      self.year = year
      self.month = mon

  def next_month(self):
    month = self.month + 1
    year = self.year
    if month > 12:
      month = 1
      year += 1
    return month, year

  def previous_month(self):
    month = self.month
    year = self.year
    if month == 1:
      month = 12
      year -= 1
    else:
      month -= 1
    return month, year


class CalendarDialog(ui.App):
  """ カレンダ選択のためのダイアログを定義"""

  def __init__(self):
    self.table = None
    self.cal = None

  def _this_month(self, *args):
    now = _dt.now()
    (mon, year) = (now.month, now.year)
    self.cal1.reset_days(mon, year)
    (mon, year) = self.cal1.next_month()
    self.cal2.reset_days(mon, year)
    self.cal1.table.focus_set()

  def _next_month(self, *args):
    (mon, year) = self.cal1.next_month()
    self.cal1.reset_days(mon, year)
    (mon, year) = self.cal1.next_month()
    self.cal2.reset_days(mon, year)

  def _previous_month(self, *args):
    (mon, year) = self.cal1.previous_month()
    self.cal1.reset_days(mon, year)
    (mon, year) = self.cal1.next_month()
    self.cal2.reset_days(mon, year)

  def _pickup_date(self, *args):
      cal = self.cal
      if not cal or not cal.cell or not cal.cell.info: return # not selected
      date = cal.pickup_day()
      trace(date)

  def close(self, *args):
    self.cc.hide()

  def create_widgets(self, base):
    """ コンポーネントを作成する """
    cc = self.cc
    fr = Frame(base).pack(side='top')
    cal = _Calendar(fr).pack(side='left')
    cal.base = self
    self.cal1 = cal1 = cal
    
    (month, year) = cal.next_month()
    cal = _Calendar(fr, month, year).pack(side='left')
    cal.base = self
    self.cal2 = cal
    
    fr = Frame(base).pack(side='bottom')

    cap = '&Select'
    cap = '選択(&S)'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self._pickup_date)
    btn.pack(side='left', padx=3, pady=3)   
        
    cap = '&Today'
    cap = '今日(&T)'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self._this_month)
    btn.pack(side='left', padx=3, pady=3)

    cap = '&Previous'
    cap = '先月(&P)'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self._previous_month)
    btn.pack(side='left', padx=3, pady=3)

    cap = '&Next'
    cap = '来月(&N)'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self._next_month)
    btn.pack(side='left', padx=3)

    var = StringVar()
    self.today = var
    now = _dt.now()

    tf = u'today: %s-%s-%s'
    tf = u'今日: %s-%s-%s'
    
    var.set(tf % (now.year, now.month, now.day))
    cap = Label(fr, textvariable=var).pack(side='left', padx=3)

    cc.bind('<Alt-p>', self._previous_month)
    cc.bind('<Alt-n>', self._next_month)
    cc.bind('<Alt-m>', self._this_month)
    cc.bind('<Alt-t>', self._this_month)
    cc.bind('<Control-w>', self.close)
    cc.bind('<Escape>', self.close)
    cal1.table.focus_set()
        
  def open(self, entry=None):
    if entry:
        entry.action = self.close
        self.cal1.ent = entry
        self.cal2.ent = entry


searchWords = []
replaceWords = []


class FindDialog(ui.App):
  """ 検索ダイアログ
実際の処理は呼び出し元で定義する
"""

  def __init__(self, with_hilight=False):
    self.fkey = None # 検索キーを保持する StringVar
    self.rkey = None # 置換テキストを保持する StringVar
    self.fdir = None # 検索方向を保持する IntVar
    self.with_hilight = with_hilight # ハイライト表示を行うかどうか
    self.delegate = FindDelegate() # 実際に検索処理を行うオブジェクト

  def perform(self, cmd, *args):
    """ メニュー選択により動作する機能"""
    if ui.verbose: trace(cmd, args)
    
    if 'search' == cmd:
      self._do_find()

    elif 'replace' == cmd:
      self._do_replace()

    elif 'hilight' == cmd:
      self._do_hilight()
            
    elif 'ignore' == cmd:
      # フラグの変更
      flag = self.ignoreCase.get()
      flag = 0 if flag else 1
      self.ignoreCase.set(flag)

    elif 'reg' == cmd:
      # フラグの変更
      flag = self.regularExp.get()
      flag = 0 if flag else 1
      self.regularExp.set(flag)

    elif 'close' == cmd:
      self.delegate.end_search()
      global searchWords, replaceWords
      searchWords = self.fkey.ent['values']
      if self.rkey:
        replaceWords = self.rkey.ent['values']
        self.cc.hide()

  def _do_hilight(self):
    """検索した対象をハイライト表示"""
    searchword = self.fkey.get()
    ignoreCase = self.ignoreCase.get()
    self.delegate.hilight(searchword, ignoreCase)

  def set_status(self, msg, *args):
    self.delegate.set_status(msg, *args)

  def _do_find(self):
    """テキスト検索"""
    fdir = self.fdir.get()
    isForward = fdir == 'forward'
    searchTerm = self.fkey.get()
    ignoreCase = self.ignoreCase.get()
    regularExp = self.regularExp.get()
    if ui.verbose:
      trace(searchTerm, fdir, ignoreCase, regularExp, isForward)

    if isForward:
      self.delegate.search_forward(searchTerm, ignoreCase, regularExp)
    else:
      self.delegate.search_backward(searchTerm, ignoreCase, regularExp)

    entry_store(self.fkey.ent, searchTerm)

  def _do_replace(self):
    """置換と次検索"""
    fdir = self.fdir.get()
    isForward = fdir == 'forward'
    searchTerm = self.fkey.get()
    replaceTerm  = self.rkey.get()
    ignoreCase = self.ignoreCase.get()
    regularExp = self.regularExp.get()
    if ui.verbose:
      trace(searchTerm, replaceTerm, fdir)

    self.delegate.replace_term(replaceTerm)
    if isForward:
      self.delegate.search_forward(searchTerm, ignoreCase, regularExp)
    else:
      self.delegate.search_backward(searchTerm, ignoreCase, regularExp)

    entry_store(self.fkey.ent, searchTerm)
    entry_store(self.rkey.ent, replaceTerm)

  def release(self):
    # 循環参照の解除
    del self.fkey.ent
    del self.rkey.ent

  def create_widgets(self, base):
    """構成コンポーネントの作成"""
    blist = []
    cc = self.cc
    # ----- 検索キーワード
    fr = Frame(base).pack(side='top', fill='x', expand=1, padx=3, pady=3)

    cap = 'Search &Word'
    cap = '検索テキスト(&W)'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='left', padx=5)

    var = self.fkey = StringVar()
    tf = Combobox(fr, width=30, textvariable=var).pack(side='left', fill='x', expand=1, padx=3, pady=3)
    var.ent = tf

    tf['values'] = searchWords
    ui.register_entry_popup(tf)
    blist.append(('<Alt-w>', lambda event, wi=tf: entry_focus(wi)))
    tf.focus()

    # ----- 置換キーワード

    fr = Frame(base).pack(side='top', fill='x', expand=1)
    self.replaceFrame = fr
    
    cap = '&Replace With'
    cap = '置換テキスト(&R)'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label,underline=pos).pack(side='left', padx=5)
      
    self.rkey = var = StringVar()
    tf = Combobox(fr, width=30, textvariable=var).pack(side='left', fill='x', expand=1, padx=3, pady=3)
    var.ent = tf
    
    tf['values'] = replaceWords
    ui.register_entry_popup(tf)
    blist.append(('<Alt-r>', lambda event, wi=tf: entry_focus(wi)))

    # ----- 検索方向
    cap = 'Direction'
    cap = '検索方向'
    fr = LabelFrame(base, labelanchor='w', text=cap).pack(side='top', padx=2, pady=2)
    
    self.fdir = var = StringVar()
    cap = '&Forward'
    cap = '文末に向かって(&F)'
    pos, label = item_caption(cap)
    rb = Radiobutton(fr, text=label, underline=pos, variable=var, value='forward')
    rb.pack(side='left')
    blist.append(('<Alt-f>', lambda event, wv=var: wv.set('forward')))

    cap = '&Backward'
    cap = '文頭に向かって(&B)'
    pos, label = item_caption(cap)
    rb = Radiobutton(fr, text=label, underline=pos, variable=var, value='backward')
    rb.pack(side='left')
    blist.append(('<Alt-b>', lambda event, wv=var: wv.set('backward')))
    var.set('forward')

    # ----- オプション
    fr = Frame(base).pack(side='top')

    self.ignoreCase = var = IntVar()
    cap = '&Ignore case'
    cap = '文字のケースを無視(&I)'
    pos, label = item_caption(cap)
    cb = Checkbutton(fr, text=label, underline=pos, variable=var).pack(side='left')
    var.set(0)

    self.regularExp = var = IntVar()
    cap = 'Regular &Expression'
    cap = '正規表現(&E)'
    pos, label = item_caption(cap)
    cb = Checkbutton(fr, text=label, underline=pos, variable=var).pack(side='left')
    var.set(0)

    # ----- ボタンなど
    fr = Frame(base).pack(side='top', fill='x')
        
    cap = 'Find &Next'
    cap = '次を検索(&N)'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self._do_find)
    btn.pack(side='left', padx=3, pady=3)

    cap = 'Replace and Fin&d'
    cap = '置き換えて次を検索(&D)'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self._do_replace)
    btn.pack(side='left', padx=3, pady=3)
    self.replaceButton = btn

    if self.with_hilight:
      cap = '&Hilight'
      pos, label = item_caption(cap)
      btn = Button(fr, text=label, underline=pos, command=self._do_hilight)
      btn.pack(side='left', padx=3, pady=3)

      cap = '&Close'
      cap = '閉じる(&C)'
      pos, label = item_caption(cap)
      btn = Button(fr, text=label , underline=pos, command=self.cc.hide)
      btn.pack(side='left', padx=3, pady=3)

    for ev, cmd in (
        ('<Alt-n>', 'search'),
        ('<Alt-d>', 'replace'),
        ('<Alt-h>', 'hilight'),
        ('<Alt-c>', 'close'),
        ('<Escape>', 'close'),
        ('<Alt-i>', 'ignore'),
        ('<Alt-e>', 'reg'),
    ): cc.bind(ev, self.bind_proc(cmd))

    for bk, proc in blist: cc.bind(bk, proc)

  def open(self, text=None, delegate=None, with_replace=True):
    trace('open', self.fkey.ent, text)
    self.delegate = delegate if delegate else _FindDelegate()
    if not with_replace:
      self.replaceFrame.pack_forget()
      self.replaceButton.pack_forget()
      
    ent = self.fkey.ent
    ent.delete(0, END)
    if text:
      ent.insert(0, text)
      entry_focus(ent)

    self.cc.show()



size_list = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 52, 64, 72]


class FontDialog(ui.App):
  """ フォント選択ダイアログ"""

  def perform(self, cmd, *args):
    """ メニュー選択により動作する機能"""
    if ui.verbose: trace(cmd, args)

    if 'close' == cmd:
      self._do_cancel()

  def _select_family(self, *ev):
    lb = self.family_list
    index = lb.curselection()
    label = lb.get(index)
    self.family.set(label)
    self._update_font_sample()

  def _select_size(self, *ev):
    lb = self.size_list
    index = lb.curselection()
    label = lb.get(index)
    self.size.set(label)
    self._update_font_sample()

  def _assign(self, lb, var, val):
    var.set(val)
    lst = list(lb.get(0, lb.size()))
    index = lst.index(val)
    lb.selection_clear(0, lb.size())
    lb.selection_set(index)
    lb.see(index)

  def _set_size(self, val):
    self._assign(self.size_list, self.size, val)

  def _set_family(self, val):
    self._assign(self.family_list, self.family, val)

  def _change_style(self, *ev):
    self._update_font_sample()

  def _set_font_info(self, font):
    fa = font.actual()
    self._set_family(fa['family'])
    self._set_size(abs(fa['size']))
        
    bold = 1 if fa['weight'] == 'bold' else 0
    self.bold.set(bold)
    italic = 1 if fa['slant'] == 'italic' else 0
    self.italic.set(italic)

  def _get_font_info(self):
    family = self.family.get()
    weight = 'b' if self.bold.get() else 'n'
    slant = 'i' if self.italic.get() else 'r'
    size = int(self.size.get())
    font = ui.find_font('%s-%d-%s-%s' % (family, abs(size), weight, slant))
    return font

  def _update_font_sample(self, *ev):
    new_font = self._get_font_info()
    if ui.verbose: trace(type(new_font), new_font.actual())
    self.sample.cap.config(font=new_font)
    
  def _do_ok(self):
    self._do_apply()
    self.cc.hide()

  def _do_apply(self):
    font = self._get_font_info()
    if ui.verbose: trace(font, type(font), font.actual())
    if hasattr(self, 'target'):
      target = self.target
      if hasattr(target, 'font'):
        target.font = font
      elif hasattr(target, 'set_font'):
        target.set_font(font)

  def _do_cancel(self):
    self.cc.hide()

  def _adjust_size(self,ev):
    if not ev.state & 4 == 4: return
    dir = 1 if ev.delta > 0 or ev.num == 4 else -1

    family = self.family.get()
    weight = 'b' if self.bold.get() else 'n'
    slant = 'i' if self.italic.get() else 'r'
    size = int(self.size.get())

    #print ('%s-%d-%s-%s' % (family,size,weight,slant))
    idx = 0
    try:
      idx = size_list.index(size)
      size = size_list[idx + dir]
      self._set_size(size)
    except:
      self.cc.logger.exception('while resize: %d %d', size, idx)
      return
    #print ('%s-%d-%s-%s' % (family,size,weight,slant))

    new_font = ui.find_font('%s-%d-%s-%s' % (family, abs(size), weight, slant))
    self.sample.cap.config(font=new_font)
       
        
  def create_widgets(self, base):
    cc = self.cc
    fb = Frame(base).pack(side='top', fill='both', expand=1, padx=3, pady=3)

    item_count = 10
    # ----- フォントファミリー

    fr = Frame(fb).pack(side='left', fill='both', expand=1, padx=3, pady=3)

    cap = 'Font &Family'
    cap = 'フォント名(&F)'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos)
    cap.pack(side='top', fill='x', expand=0)

    self.family = var = StringVar()
    var.set('Terminal')
    tf = Entry(fr, width=20, textvariable=var).pack(side='top', fill='x', expand=0, padx=3, pady=3)
    ui.register_entry_popup(tf)
    cc.bind('<Alt-f>', lambda event, wi=tf: entry_focus(wi))

    fl = Frame(fr).pack(side='top', fill='both', expand=1)

    self.family_list = lb = Listbox(fl, height=item_count).pack(side='left', fill='both', expand=1)
    lb.bind('<Double-1>', self._select_family)

    sb = Scrollbar(fl).pack(side='left', fill='y', expand=0)
    sb.config(command=lb.yview)
    lb.config(yscrollcommand=sb.set)

    for nn in tkfont.families():
      lb.insert(END, nn)

    # ----- サイズ

    fr = Frame(fb).pack(side='left', fill='both', expand=0, padx=3, pady=3)

    cap = '&Size'
    cap = '大きさ(&S)'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='top', fill='x', expand=0)

    self.size = var = StringVar()
    var.set('9')
    tf = Entry(fr, width=5, textvariable=var).pack(side='top', fill='x', expand=0, padx=3, pady=3)
    ui.register_entry_popup(tf)

    fl = Frame(fr).pack(side='top', fill='both', expand=1)
    cc.bind('<Alt-s>', lambda event, wi=tf: entry_focus(wi))
    
    lb = self.size_list = Listbox(fl, width=5, height=item_count).pack(side='left', fill='both', expand=1)
    lb.bind('<Double-1>', self._select_size)

    sb = Scrollbar(fl).pack(side='left', fill='y', expand=0)
    sb.config(command=lb.yview)
    lb.config(yscrollcommand=sb.set)
      
    for nn in size_list:
      lb.insert(END, nn)

    # ----- スタイル

    fr = Frame(fb).pack(side='left', fill='x', expand=0, padx=3, pady=3)

    self.bold = var = BooleanVar()
    var.set(1)
    cap = '&Bold'
    cap = '太字(&B)'
    pos, label = item_caption(cap)
    cb = Checkbutton(fr, variable=var, text=label,
                     underline=pos, command=self._change_style).pack()
    cc.bind('<Alt-b>', lambda event, wi=cb: wi.focus())

    self.italic = var = BooleanVar()
    var.set(0)
    cap = '&Italic'
    cap = '斜字(&I)'
    pos, label = item_caption(cap)
    cb = Checkbutton(fr, variable=var, text=label,
                     underline=pos, command=self._change_style).pack()
    cc.bind('<Alt-i>', lambda event, wi=cb: wi.focus())

    # ----- サンプルテキスト
    fr = Frame(base).pack(side='top', fill='x', expand=0, padx=3, pady=3)

    self.sample = var = StringVar()
    var.set('''AaBbCcDdEe\nFfGgHhIiJjK\n1234567890\n#:+=(){}[]
あいうえお\nアイウエオ亜愛
''')
    cap = Label(fr, textvariable=var).pack()
    var.cap = cap

    cc.bind('<MouseWheel>', self._adjust_size, '+')
    cc.bind('<Button-4>', self._adjust_size, '+')
    cc.bind('<Button-5>', self._adjust_size, '+')

    # ----- ボタン等
    fr = Frame(base).pack(side='bottom', fill='x', expand=0, padx=3, pady=3)

    cap = '&OK'
    cap = '選択(&O)'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self._do_ok).pack(side='left', padx=3, pady=3)
    cc.bind('<Alt-o>', lambda event, wi=btn: wi.focus())
        
    cap = '&Apply'
    cap = '適用(&A)'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self._do_apply).pack(side='left', padx=3, pady=3)
    cc.bind('<Alt-a>', lambda event, wi=btn: wi.focus())

    cap = '&Cancel'
    cap = '閉じる(&C)'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self._do_cancel).pack(side='left', padx=3, pady=3)
    cc.bind('<Alt-c>', lambda event, wi=btn: wi.focus())
    
    for ev, cmd in (
        ('<Escape>', 'close'),
        ('<Control-w>', 'close'),
    ): cc.bind(ev, self.bind_proc(cmd))

  def open(self, target):
    font = target.get_font() if hasattr(target, 'get_font') else \
      target.font if hasattr(target, 'font') else target

    if ui.verbose: trace(font, type(font), font.actual())
    self.target = target
    self._set_font_info(font)
    self.sample.cap.config(font=font)
    self.cc.show()


def adjust_font_size(app, dir=0, event=None):
  """マウスホイールでフォントサイズの調整"""
  if event:
    if not event.state & 4 == 4: return
    dir = 1 if event.delta > 0 or event.num == 4 else -1
  
  fa = app.font.actual()
  family = fa['family']
  size = int(fa.get('size', 10))
  weight = 'b' if fa['weight'] == 'bold' else 'n'
  slant = 'i' if fa['slant'] == 'italic' else 'r'
    
  try:
    idx = size_list.index(size)
    size = size_list[idx + dir]
  except:
    size = 11

  fn = '%s-%d-%s-%s' % (family, abs(size), weight, slant)
  app.font = fn
  return 'break'

    
if __name__ == '__main__':
  FindDialog.start()
  FontDialog.start()
  CalendarDialog.run()

