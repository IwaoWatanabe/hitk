# coding: utf-8
from hitk import tk, ui

class MemoApp(ui.App):
  def create_widgets(self, base, rows=15, column=60):
    tk.Text(base, width=column, height=rows,
            undo=1,maxundo=1000).pack(fill='both', expand=1)

if __name__ == '__main__': MemoApp.run()
