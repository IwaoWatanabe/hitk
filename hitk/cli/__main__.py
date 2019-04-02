# coding: utf-8

from hitk import cli
from hitk.cli import localfiles as lf

def run():
    class app(cli.CommandDispatcher, lf.LocalFileManager):

        def __init__(self):
            lf.LocalFileManager.__init__(self)

    mod = __import__(__name__)
    for mn in __name__.split(".")[1:]: mod = getattr(mod, mn)
    app.run(mod, lf)

if __name__ == '__main__': run()
