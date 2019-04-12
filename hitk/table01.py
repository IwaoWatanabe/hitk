# -*- coding: utf-8 -*-

'''
テーブルを表示編集するサンプルコードが含まれます
'''

from hitk import Frame, Scrollbar, Treeview, sorter, END, ui, trace, dialogs

class _EmptyTableData:
  """空白のテーブルデータを定義する"""

  def __init__(self, rows=1000, cols=10, **opts):
    self.rows = rows
    self.cols = cols
    self.offset = 0

  @property
  def column_info(self):
    """カラムの構成情報を入手する"""
    # cid, label, width, stretch, [ sort_cid, is_float ]
    hinfo = []
    for col in range(0, self.cols):
      c0 = chr(ord('A') + col % 26)
      cn = c0 if col < 26 else chr(ord('A') + int(col / 26) - 1) + c0
      hinfo.append(( cn, cn, 80, False, ))
    return hinfo

  @property
  def allow_load(self):
    """widget生成時に行データ読み込みが可能であるか"""
    return True

  def begin_scan(self, **opt):
    """scan前に呼び出されるメソッド"""
    pass

  def end_scan(self):
    """scan後に呼び出されるメソッド"""
    pass

  def next_row_data(self, step=100, offset=None):
    """データ行を入手する"""
    if self.offset > self.rows: return None
    if offset is None: offset = self.offset
    
    row = tuple([''] * self.cols)
    nstep = min(step, self.rows - offset)
    self.offset = offset + nstep
    return [row] * nstep

if 1:
  ed = _EmptyTableData(rows=7, cols=5)
  trace(ed.next_row_data(3))
  trace(ed.next_row_data(3))
  trace(ed.next_row_data(3))



class TsvEditor(ui.App):
  """テーブル表示の振る舞いを確認する"""

  menu_items = [
    [ 'tsv-shortcut;',
      'copy;クリップボードに選択テキストを複製(&C)',
      'paste;&Paste;',
      'select-all;Select &All',
        'duplicate;&Duplicate',
      '-',
      'delete;&Delete',
      'property;&Property',
      '-',
      'close;&Close;ctrl-W',
    ],
  ]

  def perform(self, cmd, *args):
    """メニュー選択により動作する機能"""
    trace(cmd, args)
    cc = self.cc
    tbl = self.table

    if 'copy' == cmd:
      # 選択した行のテキストをクリップボードに転記
      items = tbl.selection()
      rows = []
      for iid in items:
        row_array = tbl.item(iid, 'values')
        rows.append('\t'.join(row_array))

      trace(len(rows),'rows copy.')
      rows.append('')
      buf = '\n'.join(rows)
      tbl.clipboard_clear()
      tbl.clipboard_append(buf)

    elif 'paste' == cmd:
      # クリップボードのTSVテキストをカレント行に挿入
      iid = tbl.focus()
      pos = tbl.index(iid) if iid else 0
      
      text = tbl.selection_get(selection='CLIPBOARD')
      trace(text)
      text = text.rstrip('\n')
      for line in text.split('\n'):
        row = line.split('\t') if line else ('',)
        trace(row)
        np = pos
        pos += 1
        tbl.insert('' , np, text='%d' % pos, values=row, tag='normal')

        # TODO 行番号の修正

    elif 'delete' == cmd:
      #選択した要素を削除する
      items = tbl.selection()
      pos = tbl.index(items[0]) # 削除対象の行位置を検出
      if len(tbl.get_children()) - 1 == pos: pos -= 1
      tbl.delete(*items)

      children = tbl.get_children()
      if not children: return 'break'

      it = children[pos]
      tbl.selection_set(it)
      tbl.focus(it)
      return 'break'

    elif 'select-all' == cmd:
      items = tbl.get_children()
      tbl.selection_set(items)

    elif 'close' == cmd:
      cc.close()

  def __init__(self):
    self.table = None

  def _append_rows(self,rows):
    """行データを末尾へ追加読み込み"""
    tbl = self.table
    nrow = len(tbl.get_children())
    for row in rows:
      nrow += 1
      tbl.insert('', END, text='%d' % nrow, values=row, tag='normal')

  def _set_focus(self, iid=None, tbl=None):
    """指定する行にフォーカスを当てる"""
    if not tbl: tbl = self.table
    it = tbl.get_children()[0] if not iid else iid
    tbl.selection_set(it)
    tbl.focus(it)
    tbl.focus_set()

  def _load_table_data(self, td, **opts):
    """テーブルデータの読み込み"""
    if not td.allow_load: return
        
    td.begin_scan(**opts)
    try:
      rd = td.next_row_data()
      while rd:
        self._append_rows(rd)
        rd = td.next_row_data()
    finally: td.end_scan()
    self._set_focus()

  @property
  def font(self):
    tbl = self.table
    fn = tbl.tag_configure('normal')['font']
    # trace('get-font', fn, type(fn))
    fn = ui.find_font(fn)
    return fn

  @font.setter
  def font(self, fn):
    # trace('font', fn)p
    tbl = self.table
    font = ui.find_font(fn)
    trace('font', font.name, type(font.name))

    tbl.tag_configure('normal', font=font)
    tbl.cell.font = font

    # フォントを調整しただけだとうまく動作しなかったため、スタイルも変えている
    linespace = str(font.metrics()['linespace'])
    #trace('linespace', linespace, type(linespace))
    ui.style.configure(self.style_name, rowheight=linespace)
    tbl.update()

  def _adjust_font_size(self, ev):
    # マウスホイールでフォントサイズの調整
    return dialogs.adjust_font_size(self, event=ev)

  def create_widgets(self, base, ModelClass=_EmptyTableData, *args, **opts):
    """コンポーネントを作成する"""
    cc = self.cc
    td = ModelClass(*args, **opts)
    hinfo = td.column_info

    cols = [ hi[0] for hi in hinfo ]
    if not cols: raise ui.AppException('no column')

    fr = Frame(base)
    self.style_name = tree_style = 'Sheet%d.Treeview' % 1
    self.table = tbl = Treeview(fr, takefocus=1, show='tree headings', columns=cols, style=tree_style)
    fr.pack(side='top', expand=1, fill='both')
    ysb = Scrollbar(fr, orient='vertical', command=tbl.yview)
    tbl.configure(yscroll=ysb.set)
    ysb.pack(side='right', fill='y')

    xsb = Scrollbar(base, orient='horizontal', command=tbl.xview)
    tbl.configure(xscroll=xsb.set)
    xsb.bind('<MouseWheel>', lambda e, wi=tbl: wi.xview_scroll(-1*(1 if e.delta > 0 else -1),'page'))
    xsb.bind('<Enter>',lambda e, wi=xsb: wi.focus_set())

    if len(hinfo[0]) == 4:
      for col, cap, w, st in hinfo:
        tbl.heading(col, text=cap, command=lambda c=col: sorter(tbl, c, c, 0))
        tbl.column(col, stretch=st, width=w)

    elif len(hinfo[0]) == 6:
      for col, cap, w, st, sc, isFloat in hinfo:
        tbl.heading(col, text=cap, command=lambda tc=col,c=sc,fc=isFloat: sorter(tbl, tc, c, 0, fc ))
        tbl.column(col, stretch=st, width=w)

    tbl.column('#0', stretch=False, width=80, anchor='e')
    #tbl.heading('#0', anchor='e')

    tbl.pack(side='left', expand=1, fill='both')
    xsb.pack(side='top', fill='x')
    ui.register_editable_cell(tbl)
    
    self._load_table_data(td)

    if 0:
      # フォントを指定する場合
      def set_font(font): self.font = font
      fn = 'Times-10-normal'
      tbl.after_idle(lambda font=fn: set_font(font))

    shortcut = self.find_menu('tsv-shortcut')
    ui.register_shortcut(tbl, shortcut)

    for ev, cmd in (
        ('<Control-a>', 'select-all'),
        ('<Control-c>', 'copy'),
        ('<Control-d>', 'delete'),
        ('<Control-Insert>', 'copy'),
        ('<Control-v>', 'paste'),
        ('<Shift-Insert>', 'paste'),
        ('<Control-d>', 'duplicate'),
        ('<Control-q>', 'exit'),
        ('<Control-w>', 'close'),
        ('<Delete>', 'delete'),
    ): tbl.bind(ev, self.bind_proc(cmd))

    cc.bind('<MouseWheel>', self._adjust_font_size, '+')
    cc.bind('<Button-4>', self._adjust_font_size, '+')
    cc.bind('<Button-5>', self._adjust_font_size, '+')

    
if __name__ == '__main__': TsvEditor.run()

