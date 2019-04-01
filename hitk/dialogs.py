# -*- coding: utf-8 -*-

"""　パッケージで提供するカスタム・ダイアログを定義
"""

import calendar
from datetime import datetime as _dt
from hitk import ui, Button, Frame, Label, StringVar, Treeview, trace

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

    btn = Button(fr, text='select', command=self._pickup_date)
    btn.pack(side='left', padx=3, pady=3)   
        
    btn = Button(fr, text='today', command=self._this_month)
    btn.pack(side='left', padx=3, pady=3)

    btn = Button(fr, text='previous', command=self._previous_month)
    btn.pack(side='left', padx=3, pady=3)

    btn = Button(fr, text='next', command=self._next_month)
    btn.pack(side='left', padx=3)

    var = StringVar()
    self.today = var
    now = _dt.now()
    var.set('today: %s-%s-%s' % (now.year, now.month, now.day))
    cap = Label(fr, textvariable=var).pack(side='left', padx=3)

    cc.bind('<Alt-p>', self._previous_month)
    cc.bind('<Alt-n>', self._next_month)
    cc.bind('<Alt-m>', self._this_month)
    cc.bind('<Control-w>', self.close)
    cc.bind('<Escape>', self.close)
    cal1.table.focus_set()
        
  def open(self, entry=None):
    if entry:
        entry.action = self.close
        self.cal1.ent = entry
        self.cal2.ent = entry
        
if __name__ == '__main__':
  CalendarDialog.run()

