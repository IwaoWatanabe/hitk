# coding: utf-8

"""
行入力コンポーネントのサンプルコード
Entry と Combobox を利用した、行入力コンポーネントの基本的な振る舞いが理解できます。
"""

from hitk import Button, Combobox, Entry, Frame, Label, \
  StringRef, item_caption, entry_focus, ui, trace

class Entry01(ui.App):

  input = StringRef()
  passwd = StringRef()
  combo = StringRef()
  message = StringRef()
    
  def create_widgets(self, base):
    cc = self.cc

  # -- entry
    fr = fr1 = Frame(base).pack(side='top')
    cap = 'エントリ(&E)'
    pos, label = item_caption(cap)
    lab = Label(fr, text=label, underline=pos).pack(side='left', padx=3)
    ent = Entry(fr, name='input', width=25).pack(side='left', padx=3, pady=3)
    ent.bind('<Return>', self.bind_proc('input'))
    self.input = 'AAA'
    lab.label_for = ent
    ent.after_idle(lambda wi=ent:entry_focus(wi))

  # -- passwod entry
    fr = Frame(base).pack(side='top')
    cap = 'パスワード(&P)'
    pos, label = item_caption(cap)
    lab = Label(fr, text=label, underline=pos).pack(side='left', padx=3)
    
    ent = Entry(fr, name='passwd', show='*', width=25).pack(side='left', padx=3, pady=3)
    ent.bind('<Return>', self.bind_proc('input'))
    self.passwd = 'BBB'
    lab.label_for = ent

  # -- combobox(Edit)
    fr = Frame(base).pack(side='top')
    cap = 'コンボボックス(&B)'
    pos, label = item_caption(cap)
    lab = Label(fr, text=label, underline=pos).pack(side='left', padx=3)

    ent = Combobox(fr, name='combo', width=25).pack(side='left', padx=3, pady=3)
    ent['values'] = ('AA', 'BB', 'CC')
    ent.current(1)
    self.combo = 'CCC'
    lab.label_for = ent
    
    ent.bind('<<ComboboxSelected>>', self.bind_proc('combo'))
    ent.bind('<Return>', self.bind_proc('combo'))
    ent.bind('<Control-j>', self.bind_proc('combo'))

  # -- readonly text
    ent = Entry(base, name='message', width=25, takefocus=0, state='readonly',
                style='TLabel').pack(side='top', padx=3, pady=3, before=fr1)
    self.message = 'Uneditable Text'
    
  # -- button
    fr = Frame(base).pack(side='top')
    cap = 'ボタン(&A)'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos,
                 command=self.menu_proc('apply')).pack(side='left', padx=3, pady=3)

    cap = 'close'
    pos, label = item_caption(cap)
    btn = Button(fr, text=label, underline=pos, command=self.menu_proc('close'))
    btn.pack(side='left', padx=3, pady=3)
    cc.bind('<Escape>', lambda ev, wi=btn: wi.invoke())

  def perform(self, cmd, *args):
    """メニュー選択により動作する機能"""
    trace(cmd, args)

    if cmd == 'input' or cmd == 'combo' or cmd == 'apply':
      self.message = 'entry:%s pass:%s combo:%s' % (
          self.input, self.passwd, self.combo)

    elif cmd == 'close': self.close()

    
if __name__ == '__main__': Entry01.run()
