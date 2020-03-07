# coding: utf-8

from hitk import ttk, ui

class HelloApp(ui.App):
  def create_widgets(self, base):
    ttk.Label(base, text=u'Hello,world\n日本語でハロー').pack()

if __name__ == '__main__': HelloApp.run()
