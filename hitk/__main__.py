# coding: utf-8

import os, sys, types
from hitk import trace, ui

app_classes = [
    'hitk.hello.HelloApp',
    'hitk.memo01.MemoApp01',
]

def _find_class(hn):
  'クラスを入手する'
  ms = hn.split('.')
  mod = __import__('.'.join(ms[:-1]))
  for an in ms[1:]: mod = getattr(mod, an)
  return mod

def _find_module(hn):
  'モジュールを入手する'
  ms = hn.split('.')
  mod = __import__(hn)
  for an in ms[1:]: mod = getattr(mod, an)
  return mod

def _apdic(cn):
  cns = cn.rstrip().split(':'); cn = cns.pop(0)
  return cns[0] if cns else cn.split('.')[-1].replace('App','').replace('Dialog','').lower(), cn

aplst = [_apdic(cn) for cn in app_classes]

def _load_apps(apps='apps.txt'):
  with open(os.environ.get('APPS', apps)) as fh:
    aplst.extend([_apdic(cn) for cn in fh if cn.strip() and not cn.startswith('#')])
    
if sys.version_info < (3, 0):
  def _class_scan(mod):
    for mn in dir(mod):
      mm = getattr(mod, mn)
      if type(mm) in (types.ClassType, types.TypeType): yield mm
else:
  def _class_scan(mod):
    for mn in dir(mod):
      mm = getattr(mod, mn)
      if type(mm) == type(int): yield mm

def _find_app(mod, lst):
  for mm in _class_scan(mod):
    if issubclass(mm, ui.UIClient) and not mm.__name__.startswith('_'):
      lst.append(_apdic("%s.%s" % (mm.__module__, mm.__name__)))

def _load_apps(apps='apps.txt'):
  with open(os.environ.get('APPS', apps)) as fh:
    for tt in fh:
      tt = tt.strip().replace('/', '.')
      if not tt or tt.startswith('#'): continue
      try: _find_app(_find_module(tt), aplst)
      except ImportError:
        aplst.extend([_apdic(tt)])

try: _load_apps()
except Exception as e: trace('WARN: %s' % e)

apdic = { an: (an, cn) for an, cn in aplst }
                         
apname = sys.argv[1] if len(sys.argv) > 1 else ""
mm = apdic.get(apname, aplst[-1]) # 見つからなければ、末尾のアプリを動かす

if os.environ.get("LIST", ""):
  trace("apps", sorted(apdic.values(), key=lambda x: x[0]))

if os.environ.get("ALL", ""):
  apdic.pop(mm[0], None)
  for apname, hn in apdic.values():
    _find_class(hn).start()

_find_class(mm[1]).run(sys.argv[1:])

