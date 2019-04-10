# coding: utf-8

"""
行入力コンポーネントのサンプルコード
Entry と Combobox を利用した、行入力コンポーネントの基本的な振る舞いが理解できます。
"""

from hitk import Button, Combobox, Entry, Frame, Label, \
  StringVar, item_caption, entry_focus, ui, trace

class Entry01(ui.App):
  def create_widgets(self, base):
    cc = self.cc

  # -- entry
    fr = Frame(base).pack(side='top')
    cap = 'エントリ(&E)'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='left', padx=3)
    
    var = self.input = StringVar()
    var.set('AAA')
    ent = Entry(fr, width=25, textvariable=var).pack(side='left', padx=3, pady=3)
    ent.bind('<Return>', self.bind_proc('input'))
    cc.bind('<Alt-e>', lambda event, wi=ent: entry_focus(wi))
    entry_focus(ent)

  # -- passwod entry
    fr = Frame(base).pack(side='top')
    cap = 'パスワード(&P)'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    var = self.passwd = StringVar()
    var.set('BBB')
    ent = Entry(fr, show='*', width=25, textvariable=var).pack(side='left', padx=3, pady=3)
    ent.bind('<Return>', self.bind_proc('input'))
    cc.bind('<Alt-p>', lambda event, wi=ent: entry_focus(wi))

  # -- combobox(Edit)
    fr = Frame(base).pack(side='top')
    cap = 'コンボボックス(&B)'
    pos, label = item_caption(cap)
    cap = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    var = self.combo = StringVar()
    ent = Combobox(fr, width=25, textvariable=var).pack(side='left', padx=3, pady=3)
    ent['values'] = ('AA', 'BB', 'CC')
    ent.current(1)
    var.set('CCC')

    ent.bind('<<ComboboxSelected>>', self.bind_proc('combo'))
    ent.bind('<Return>', self.bind_proc('combo'))
    ent.bind('<Control-j>', self.bind_proc('combo'))
    cc.bind('<Alt-b>', lambda event, wi=ent: entry_focus(wi))

    # -- readonly text
    self.msg = StringVar()
    ent = Entry(base, width=25, textvariable=self.msg, takefocus=0, state='readonly',
                style='TLabel').pack(side='top', padx=3, pady=3)

    # -- button
    fr = Frame(base).pack(side='top')
    cap = 'ボタン(&A)'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos,
                 command=self.menu_proc('apply')).pack(side='left', padx=3, pady=3)
    cc.bind('<Alt-a>', lambda ev, wi=btn: wi.invoke())

    cap = 'close'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self.menu_proc('close'))
    btn.pack(side='left', padx=3, pady=3)
    cc.bind('<Escape>', lambda ev, wi=btn: wi.invoke())

  def perform(self, cmd, *args):
    """メニュー選択により動作する機能"""
    trace(cmd, args)

    if cmd == 'input' or cmd == 'combo' or cmd == 'apply':
      txt = 'entry:%s pass:%s combo:%s' % (
          self.input.get(), self.passwd.get(), self.combo.get())
      trace(txt)
      self.msg.set(txt)

    elif cmd == 'close': self.close()

    
if __name__ == '__main__': Entry01.run()
