# coding: utf-8

import os, sys
from hitk import cli
from hitk.cli import localfiles as lf

_cli_classes = [
  cli.CommandDispatcher,
]

def _find_class(hn):
  'クラスを入手する'
  ms = hn.split('.')
  mod = __import__('.'.join(ms[:-1]))
  for an in ms[1:]: mod = getattr(mod, an)
  return mod

def _cli_init(self, *args, **kwargs):
  for cn in _cli_classes:
    if hasattr(cn, '__init__'):
      cn.__init__(self, *args, **kwargs)
        
def run():
  mod = __import__(__name__)
  for mn in __name__.split('.')[1:]: mod = getattr(mod, mn)
  _cli_modules = [ mod, lf, ]

  def _load_cli(cli_file):
    if not os.path.exists(cli_file): return
    with open(cli_file) as fh:
      for line in fh:
        cn = line.rstrip().replace('/', '.').replace('.py','')
        if cn.startswith('#'): continue
        try:
          CL = _find_class(cn)
          _cli_modules.append(__import__(CL.__module__))
          _cli_classes.append(CL)
        except Exception as e:
          sys.stderr.write('WARN: %s while load %s\n' % (e, cn))
          
  for cli_file in (
      os.path.expanduser('~/.cli/cli.txt'),
      os.environ.get('CLI', 'cli.txt'),      
  ): _load_cli(cli_file)

  _cli_classes.append(lf.LocalFileManager)

  app = type('cli', tuple(_cli_classes), { '__init__': _cli_init })
  app.run(*_cli_modules)

if __name__ == '__main__': run()
