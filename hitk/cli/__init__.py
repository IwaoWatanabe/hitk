# coding: utf-8

""" 対話型コマンドを実現するための既定クラスと関連関数を提供する
標準ライブラリの cmd を補完するものである

このパッケージはGUIに依存させないように注意を払って実装する。

Windowsではreadlineは pyreadline を合わせて導入すると使い勝手が良い。
pip install pyreadline --user

"""

from __future__ import print_function
import cmd, functools, logging, os, platform, re, shlex, subprocess, sys, threading
from datetime import datetime as _dt
from getopt import getopt, GetoptError
from logging import DEBUG, INFO, WARN, ERROR, FATAL, Logger, getLogger
from string import Template

try: import readline
except: readline = None

from hitk.common import *
from hitk.common import _decode

def _print(*args, **kwarg):
    out = kwarg.pop('file', sysout)
    if args:
        print(*args, file=out, **kwarg)
    else:
        print(file=out, **kwarg)

puts = _print

def _eprint(*args, **kwarg):
    out = kwarg.pop('file', syserr)
    kwarg['file'] = out
    return puts(*args, **kwarg)

eputs = _eprint

def printf(*args, **kwarg):
    #trace('printf', args, kwarg)
    out = kwarg.pop('file', sysout)
    if args:
        if '%' in args[0]:
            opts = args[1:]
            print(args[0] % opts, file=out, **kwarg)
        else:
            print(*args, file=out, **kwarg)
    else:
        print(file=out, **kwarg)


def eprintf(*args, **kwarg):
    out = kwarg.pop('file', syserr)
    kwarg['file'] = out
    return printf(*args, **kwarg)


appname = os.environ.get('APP_NAME', 'cli')

verbose = os.environ.get('DEBUG', False)

interactive = True

debugout = None

log = logging.getLogger(__name__)

# https://pewpewthespells.com/blog/osx_readline.html

_rl_with_prefix = sys.platform.startswith('win')

if readline:
  if readline.__doc__ and 'libedit' in readline.__doc__:
    # macos標準python向けの設定
    readline.parse_and_bind('bind ^I rl_complete')
    _rl_with_prefix = True
  else:
    readline.parse_and_bind('tab: complete')

  # 単語の区切り文字の除外
  _delims = readline.get_completer_delims()
  for ch in '+-=,': _delims = _delims.replace(ch, '')
  readline.set_completer_delims(_delims)

try:
    import pytz
    tz_name = os.environ.get('TZ', os.environ.get('ZONE', 'Asia/Tokyo'))
    local_zone = pytz.timezone(tz_name)
    utc = pytz.utc
except:
    local_zone = None
    utc = None

if sys.platform.startswith('java'):
    if not hasattr(sys,'ps'):
        sys.ps2 = '>'


# 標準出力（CommandDispatcherにより変更されることがある）
out = sysout = sys.stdout

# 標準入力（CommandDispatcherにより変更されることがある）
sysin = sys.stdin

syserr = err = sys.stderr
        

def _en(tt): return tt.name if hasattr(tt, 'name') else tt


def nextopt(args, params=None):
    "パラメータのあとにオプションを受け入れるための関数"
    while args:
        tn = args.pop(0)
        if tn == '-': break
        if tn.startswith('-'): args.insert(0, tn); break
        if params is not None: params.append(tn)
    return args

def strftime(pattern='%Y-%m%d-%H%M', unixtime=None):
    tt = _dt.fromtimestamp(unixtime) if unixtime else _dt.now()
    return tt.strftime(pattern)


def alert(func):
    "例外が生じたらそれを表示するデコレータ"
    @functools.wraps(func)
    def _elog(*args, **kwargs):
        "生じた例外を表示する"
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            if verbose:
                log.exception('%s', e)
            else:
                log.error('%s (%s)', e, e.__class__.__name__)
            if not interactive: return 2

    return _elog


# 入出力をマルチスレッドに対応させる

tl = threading.local()

class _MTSIO(object):
    '''スレッド固有のI/Oを提供する'''
    
    def init(self, infile=None, outfile=None, proc=None):
        tl.fout = None
        tl.fin = None
        tl.proc = proc
        tl.outfile = outfile
        tl.infile = infile
        return self
    
    def __enter__(self):
        infile = tl.infile
        tl.fin = open(infile, 'rb') if infile else sys.stdin
        sp = tl.proc
        outfile = tl.outfile
        if sp:
            tl.fout = sp.stdin
        elif outfile:
            tl.fout = open(outfile, 'wb')
        else:
            tl.fout = sys.stdout
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if tl.infile: tl.fin.close()
        finally:
            try:
                if tl.outfile: tl.fout.close()
            finally:
                sp = tl.proc
                if sp and sp.poll() is not None:
                    try: sp.terminate()
                    except Exception as e:
                        log.warn('%s while terminate subprocess.', e)
        
    def __get__(self): return self

    def wait(self):
        sp = tl.proc
        sp.stdin.close()
        rc = sp.wait()
        tl.proc = None
        
    def write(self, tt): return tl.fout.write(tt)
    def writelines(self, tt): return tl.fout.writelines(tt)
    def read(self, tt): return tl.fin.read(tt)

    def readline(self, size=-1): return tl.fin.readline(size)
    def readlines(self, size=-1): return tl.fin.readlines(size)
    
    def flush(self):
        out = tl.fout
        if out: out.flush()
        
    def close(self):
        out = tl.fout
        if out: out.flush()

    def isatty(self):
        out = tl.fout
        return out.isatty() if out else tl.fin.isatty()


sysin = sysout = out = _MTSIO()

tl.fout = sys.stdout

var = dict()

def cmd_args(func):
    "コマンドラインの要素分解するデコレータ.生じた例外も表示する"
    @functools.wraps(func)
    def _elog(*args, **kwargs):
        "生じた例外を表示する"
        cmd = func.__name__[3:] if func.__name__.startswith('do_') else \
              func.__name__[:-4] if func.__name__.endswith('_cmd') else 'unkown_cmd'

        sp = th = None
        outfile = infile = ''

        try:
            self, line = args
            infile = self.infile if hasattr(self,'infile') else None

            line = Template(line.replace('\\$','$$')).safe_substitute(dict(os.environ))
            pline = ''
            if '|' in line:
                # 外部コマンド呼び出しのサポート
                pos = line.find('|')
                pline = line[pos + 1:]
                line = line[:pos]
                if pline.rstrip().endswith('&'):
                    pline = pline.rstrip()[:-1]
                    line += ' &'

            elif '>' in line:
                # 出力リダイレクトのサポート
                pos = line.find('>')
                outfile = line[pos + 1:].strip()
                line = line[:pos].strip()
                if outfile.rstrip().endswith('&'):
                    outfile = outfile.rstrip()[:-1].rstrip()
                    line += ' &'

            argv = split_line(line)
            argv.insert(0, cmd)

            try:
                # 入力リダイレクトが指定されているか
                ipos = argv.index('<')
                argv.pop(ipos)
                infile = argv.pop(ipos)
            except ValueError: pass
            
            if pline:
                sp = subprocess.Popen(pline, shell=True, stdin=subprocess.PIPE)

            rc_queue = Queue()

            def _exec_command(infile, outfile, sp, report, argv, kwargs):
                'コマンド・メソッドを実行する'
                th = threading.current_thread()
                if 1:
                    with sysout.init(infile, outfile, sp) as tt:
                        if report:
                            log.info('[%s] start ..', th.name)
                        try:
                            result = func(self, argv, **kwargs)
                            if sp: result = tt.wait()
                            if report:
                                log.info('[%s] done (rc:%s)', th.name, result)

                        except GetoptError:
                            return self.usage(cmd)

                        except Exception as e:
                            result = -1
                                
                            if verbose:
                                log.exception('[%s] %s (%s)', th.name, e, _en(e.__class__))
                            else:
                                log.error('[%s] %s (%s)', th.name, e, _en(e.__class__))
                            
                rc_queue.put(result)
                return result
                
            wait_thread = True
            
            if argv[-1] == '&':
                argv.pop()
                wait_thread = False

            if not wait_thread:
                th = threading.Thread(target=_exec_command, args=( 
                    infile, outfile, sp, True, argv, kwargs))
                th.daemon = True
                th.start()
                rc = 0
            else:
                rc = _exec_command(infile, outfile, sp, False, argv, kwargs)
                
            return rc

        except KeyboardInterrupt:
            interrupt(th)
            raise
        
        except Exception as e:
            if verbose:
                log.exception('%s', e)
            else:
                log.error('%s (%s)', e, _en(e.__class__))
            if not interactive: return 2
                
    return _elog


def _arg_join(args):
    "コマンドライン解釈用のテキストに変更"
    args = [ '"%s"' % tt.replace('"',r'\"') if ' ' in tt or '"' in tt else tt for tt in args ]
    return " ".join(args)


def find_handler(hn, defaultClassName=None, section=None):
    "クラスを入手する"

    if not defaultClassName is None:
        saved_hn = hn
        hn = pref.value(hn, defaultClassName, section)
        log.info('handler: %s: %s', saved_hn, hn)
    else:
        log.info('handler: %s', hn)


    pn = hn.rfind('.')
    if pn < 0:
        Handler = globals()[hn]
    else:
        __import__(hn[0:pn])
        ms = hn.split('.')

        module_name = ms[0]
        mod = __import__(module_name)
        last_mod = None
        for an in ms[1:]:
            last_mod = mod
            mod = getattr(last_mod,an)
        
        Handler = mod
        if last_mod:
            # ログや設定を差し込む
            if hasattr(last_mod,'pref'): last_mod.pref = pref
            if hasattr(last_mod,'log'): last_mod.log = log
    return Handler

findHandler = find_handler


class CommandDispatcher(cmd.Cmd, object):
    "サブクラスで対話的に呼び出すメソッドを定義する"

    # ユーザ入力を促すテキスト
    prompt = 'ready> '

    def __init__(self):
        cmd.Cmd.__init__(self)
        self.eof_hook = None # quit で呼び出される処理
        self._update_cmd_method()

    def _update_cmd_method(self, debug=False):
        for fn in self.get_names():
            for sfx, pre in (
                ('_cmd', 'do_'),
                ('_comp', 'complete_'),
                ('_desc', 'help_'),
            ):
                if fn.endswith(sfx):
                    #print(pre + fn[:-len(sfx)], getattr(self.__class__, fn))
                    setattr(self.__class__, pre + fn[:-len(sfx)], getattr(self, fn))
                    break

        for fn in self.get_names():
            if not fn.endswith('_cmd'): continue
            cmp = 'complete_%s' % fn[:-4]
            if hasattr(self.__class__, cmp): continue
            setattr(self.__class__, cmp, self.complete_local_files)
            
        if debug: show_items(sorted(self.get_names()))

    def usage(self, cmd, opt=None):
        try:
            if opt: puts('unkwon option', opt, file=err)
            
            doc = getattr(self, 'do_' + cmd).__doc__
            if doc:
                pos = doc.find('\n\n')
                if pos < 0: pos = doc.find('\n-')
                if pos > 0: doc = doc[:pos]
                #print >>self.stdout, 'pos:', pos
                
                self.stdout.write('%s\n' % str(doc))
                return
        except AttributeError as e:
            raise

        self.stdout.write('%s\n'%str(self.nohelp % (cmd,)))
        return 2

    def do_EOF(self,line):
        'exit interactive mode.'
        if self.eof_hook: self.eof_hook()
        if verbose: syserr.write('done.\n')
        return 1

    do_quit = do_EOF


    def emptyline(self):
        " 入力が空の時に呼び出される"
        pass

    @cmd_args
    def clear_cmd(self, argv):
        """usage: clear

- clear screen
"""
        if not os.isatty(1): return
        os.system('cls' if os.name == 'nt' else 'clear')

    @cmd_args
    def history_cmd(self, argv):
        """usage: history [-d #]\thistory [-rw][history-file]
- show command line history.
"""
        global verbose
        cmd = argv.pop(0)
        mode = 'show'
        dline = None
        params = []
        while argv:
            opts, args = getopt(argv, 'rwd:v?',(
                'delete=', 'load', 'save',
            ))
            for opt, optarg in opts:
                if opt in ('-d', '--delete'): mode = 'delete'; dline = optarg
                if opt in ('-r', '--load'): mode = 'load'
                if opt in ('-w', '--save'): mode = 'save'
                elif opt in ('-v', '--verbose'): verbose = True
                else: return self.usage(cmd, opt)

            argv = nextopt(args, params)

        if mode == 'load':
            fn = args[0] if len(args) else None
            load_history(fn)

        elif mode == 'save':
            fn = args[0] if len(args) else None
            save_history(fn)

        elif mode == 'show':
            cur = readline.get_current_history_length()
            for i in xrange(1, cur + 1):
                puts(i, readline.get_history_item(i))

        elif mode == 'delete':
            pass

    def _show_threads(self):
        puts('\t'.join(('name','daemon','ident','alive','type')))

        ct = 0
        for th in threading.enumerate():
            puts(th.name, '\t', th.daemon, '\t', th.ident, '\t', th.is_alive(), type(th))
            ct += 1

        log.info('%s threads aviable.', ct if ct else 'no')
        
    @cmd_args
    def threads_cmd(self, argv):
        """usage: threads"""
        cmd = argv.pop(0)
        self._show_threads()

    jobs_cmd = threads_cmd
                    
    @cmd_args
    def sleep_cmd(self, argv):
        """usage: sleep [sec]"""
        cmd = argv.pop(0)
        verbose = False
        sec = 1.0

        opts, args = getopt(argv, 'vh', ('verbose','help'))
        for opt, optarg in opts:
            if opt in ('-v', '--verbose'): verbose = True
            elif opt in ('-?', '--help'): self.do_help(cmd)
            else: return self.usage(cmd, opt)
            
        if args:
            sec = float(args.pop(0))
        if verbose: log.debug('sleep %.3f sec..', sec)
        sleep(sec)
        return 0

    @cmd_args
    def interrupt_cmd(self, argv):
        """usage: interrupt [tn] .."""
        cmd = argv.pop(0)

        opts, args = getopt(argv, 'vh', ('verbose','help'))
        for opt, optarg in opts:
            if opt in ('-v', '--verbose'): verbose = True
            elif opt in ('-?', '--help'): self.do_help(cmd)
            else: return self.usage(cmd, opt)

        if not args: return self._show_threads()

        args = set(args)
        
        for th in threading.enumerate():
            if th.name in args or str(th.ident) in args:
                interrupt(th)
        
        return 0

    @cmd_args
    def wait_cmd(self, argv):
        """usage: wait tn"""
        cmd = argv.pop(0)
        timeout = None
        opts, args = getopt(argv, 'vht:', ('verbose','help','timeout='))
        for opt, optarg in opts:
            if opt in ('-v', '--verbose'): verbose = True
            elif opt in ('-t', '--timeout'): timeout = float(optarg)
            elif opt in ('-?', '--help'): self.do_help(cmd)
            else: return self.usage(cmd, opt)

        if not args: return self._show_threads()
        args = set(args)

        jt = timeout if timeout else 100000

        start = now()
        for th in threading.enumerate():
            tn = th.name
            if tn == 'MainThread': continue
            if tn in args or str(th.ident) in args:
                while 1:
                    th.join(timeout=jt)
                    if not th.isAlive() or now() - start > jt: break
        
        return 0
    
    @cmd_args
    def preference_cmd(self, argv):
        """usage: preference [-aelDv][-o <export>] [section] ..  #show/export/drop
\tpreference -i <file> [section[:new_name]] .. # import
\tpreference -u [-s <section>] [<key> <value>].. # update
\tpreference -d [-s <section>] key .. # remove property data
\tpreference -c <section> # change current section
\tpreference -n [<old-section>[:]<new-section>] .. # rename
"""
        # 設定の調整
        cmd = argv.pop(0)
        section = ''
        verbose = False
        all = False
        op = 'show'
        infile = ''
        outfile = ''
        args = []
        while argv:
            opts, params = getopt(argv, 'ae:lc:Ei:s:Ddnuv',(
                'all', 'list', 'change=', 'section=', 'delete', 'verbose', 'import=',
                'export=', 'drop', 'drop-section', 'delete', 'delete-data', 'update', 'edit',
            ))
            for opt, optarg in opts:
                if opt in ('-l', '--list'): op = 'show'
                elif opt in ('-a', '--all'): all = True
                elif opt in ('-c', '--change'):
                    last = pref.get_section()
                    pref.set_section(optarg)
                    log.info('preference change from: %s', last)
                    return
                elif opt in ('-E', '--edit'): op = 'edit'
                elif opt in ('-i', '--import'): op = 'import'; infile = optarg
                elif opt in ('-e', '--export'): op = 'export'; outfile = optarg
                elif opt in ('-s', '--section'): section = optarg
                elif opt in ('-D', '--drop', '--drop-section'): op = 'drop'
                elif opt in ('-d', '--delete', '--delete-data'): op = 'delete'
                elif opt in ('-n', '--rename'): op = 'rename'
                elif opt in ('-u', '--update'): op = 'update'
                elif opt in ('-v', '--verbose'): verbose = True
                else: return self.usage(cmd)
                
            argv = nextopt(params, args)

        if all and op in ('drop', 'delete', 'list', 'edit'):
            args = list(pref.get_section_names())
            
        al = len(args)

        if not args and not all and op in ('drop', 'delete', 'list', 'edit', 'rename', 'export'):
            names = sorted(pref.get_section_names())
            show_items(names)
            log.info('%s sections.', len(names) if names else 'no')
            return 1

        if op == 'export':
            saved_expand = pref.expand
            try:
                pref.expand = False
                return self._export_preference(outfile, all=all, sections=args)
            finally:
                pref.expand = saved_expand
            
        if op == 'import':
            names = self._import_preference(infile, all=all, sections=args)
            if not args and not all:
                show_items(names)
                log.info('%s sections found.', len(names) if names else 'no')
                return
            
        if op == 'rename':
            # セクション名の変更
            if not args: return self.usage(cmd)
            ct = 0
            while args:
                sec = args.pop(0)
                if ':' in sec:
                    old_sec, new_sec = sec.split(':')[:2]
                elif not args:
                    break
                else:
                    old_sec = sec
                    new_sec = args.pop(0)

                pref.rename_section(old_sec, new_sec)
                ct += 1
            if ct: pref.save()
            return
        
        if op == 'drop':
            # セクションを指定して削除
            nosec = []
            ct = 0
            for sec in args:
                if pref.delete_section(sec):
                    log.info('%s droped.', sec)
                    ct += 1
                else:
                    nosec.append(sec)
            if nosec:
                log.warn('no such section: %s', ', '.join(nosec))
                
            if ct: pref.save()
            return

        if op == 'delete':
            # キーを指定して削除する
            ct = 0
            for pn in args:
                if '*' not in pn:
                    pref.store(pn, '', section)
                    ct += 1
                    continue
                    
                if pn.count('*') > 1:
                    log.warn('invalid key pattern (ignored): %s', pn)
                    continue

                pre, sfx = pn.split('*')
                for kn in pref.key_list(section, pre, sfx):
                    pref.store(kn, '', section)
                    ct += 1
            if ct: pref.save()
            return

        if op == 'update':
            ct = 0
            while args:
                key = args.pop(0)
                if not args: break
                tt = args.pop(0)
                pref.store(key, tt, section)
                ct + 1
                printf('%s=%s', key, tt)
            if ct: pref.save()
            return
        
        if op == 'show':
            # 登録済のデータ値を出力する
            names = pref.key_list(section)
            names.sort()
            try:
                saved_expand = pref.expand
                for key in names:
                    tt = pref.value(key, '', section)
                    printf('%s=%s', key, tt)
            finally:
                pref.expand = saved_expand
                
            puts()
            log.info('%d entries in %s section.', len(names), section if section else 'default')
            return


    def _export_preference(self, pref_name, sections=(), all=False, dry_run=False, PreferenceClass=None):
        # 設定を出力する
        if not PreferenceClass: PreferenceClass=INIPreference
        epref = INIPreference(pref_name)

        trace('export', pref_name)
        
        verb = pref_name in ('-','') or verbose

        if all: sections = pref.section_names
        sect = 0
        ct = 0
        for sn in sections:
            sl = sn.split(':')
            sec = sl[0]
            dn = sl[1] if len(sl) > 1 else sec

            if not pref.has_section(sec):
                log.warn('no such section (ignored): %s', sec)
                continue
            
            if verb: printf('[%s]', dn)
            kl = pref.key_list(sec)
            for key in kl:
                tt = pref.value(key, '', section=sec)
                if verb: printf('%s=%s', key, tt)
                if not dry_run:
                    epref.store(key, tt, dn)
                    ct += 1
            if kl: sect += 1
        if ct:
            if verb != '-': epref.save()
            log.info('%d entry %d sections exported.', ct, sect)
        else:
            log.info('no sections exported.')
            

    def _import_preference(self, pref_name, sections=(), all=False, dry_run=False, PreferenceClass=None):
        # 設定を読み込んで指定するセクションを自身に取り込む
        # 存在するセクション名の一覧を返却する

        if not PreferenceClass: PreferenceClass=INIPreference
        epref = PreferenceClass()
        epref.load(pref_name)
        epref.expand = False

        names = epref.get_section_names()
        if all: sections = names

        sect = 0
        ct = 0
        for sn in sections:
            sl = sn.split(':')
            sec = sl[0]
            dn = sl[1] if len(sl) > 1 else sec

            if not epref.has_section(sec):
                log.warn('no such section (ignored): %s', sec)
                continue

            if verbose: eprintf('[%s]',dn)
            kl = epref.key_list(sec)
            for key in kl:
                tt = epref.value(key, '', section=sec)
                if verbose: eprintf('%s=%s', key, tt)
                if not dry_run:
                    pref.store(key, tt, dn)
                    ct += 1
                    
            if kl: sect += 1

        if ct:
            log.info('%d entry %d sections imported.', ct, sect)
            pref.save()
        else:
            log.info('no sections imported.')

        return names
    
        
    def complete_local_files(self, *args):
        return complete_path(*args)

    def precmd(self, line):
        #global sysin
        self.infile = self.infh = None
        tline = line.lstrip()
        if not tline.startswith('<'):
            return tline
        tline = tline[1:].lstrip()
        pos = tline.find(' ')
        self.infile = infile = tline[:pos]
        #self.infh = sysin = open(infile)
        tline = tline[pos+1:].lstrip()
        return tline
        
    def postcmd(self, stop, line):
        #global sysin
        infh = self.infh
        if infh:
            try: infh.close()
            finally: self.infh = None; #sysin = sys.stdin
            
        if line in ( 'quit', 'EOF' ): return 1
        #if verbose: log.debug('rc: %s cmd:%s', stop, line)
        return not interactive

    @classmethod
    def run(cls, *modules, **karg):
        "start interactive mode."
        logging.basicConfig()
        global history_file, preference_file, pref, log
        from os import environ as ENV
        fqcn = cls.__name__
        argv = karg.get('argv', sys.argv)
        last_history = karg.get('last_history')
        sn = cn = str(fqcn).split('.')[-1]
        pos = fqcn.rfind('.')
        mn = fqcn[0:pos] if pos > 0 else '__main__'
        mod = __import__(mn)

        global verbose, interactive
        if 'DEBUG' in ENV: verbose = True
        if verbose: print("argv: %s" % " ".join(argv), file=sys.stderr)
		
        preference_name = os.path.expanduser('~/.%s/%s' % (appname, cn))

        opts, args = getopt(argv[1:], 'vp:D:', (
            'verbose', 'define=', 'preference=',
        ))

        defs = []

        for opt, optarg in opts:
            if opt in ('-v', '--verbose'): verbose = True
            elif opt in ('-D', '--define'):
                key, value = optarg.split('=')
                defs.append((key, value))
            elif opt in ('-p', '--preference'):
                preference_name = optarg
                pt = optarg.find(':')
                if pt > 0:
                    preference_name = optarg[:pt]
                    sn = optarg[pt+1:]
                verbose = True

        pref = INIPreference(preference_name)
        try: pref.load()
        except: pass

        pref.set_section(sn)

        for key, value in defs:
            pref.store(key, value)

        if last_history: save_history(last_history)

        home = os.path.expanduser('~')
        history_file = pref.value('history-file', os.path.join(home, 'logs', '%s.history' % cn))
        if os.path.exists(history_file): load_history()

        if verbose:
            pref.store('console-log-level', 'DEBUG')

        log = get_logger(cn, pref=pref)
        mod.pref = pref
        mod.log = log

        cmd = cls()
        cmd.pref = pref

        for mod in modules:
            mod.pref = pref
            mod.log = log

        c0 = os.path.basename(argv[0])
        if '-' in c0 and not c0.endswith('.py'):
            subcmd = c0[c0.find('-')+1:]
            args.insert(0, subcmd)
            
        if args:
            line = _arg_join(args)
            if verbose: puts('args', args, file=err)
            interactive = False
            try:
                rc = cmd.onecmd(line)
            except Exception as e:
                rc = 3
                elog = log.exception if verbose else log.error
                elog('%s while execute\n %s', e, line)
            except KeyboardInterrupt:
                rc = 4
                syserr.write('Interrupted.\n')

            if verbose: puts('rc: ', rc, file=err)
            if last_history:
                # カスケード呼び出しされている
                history_file = last_history
                if os.path.exists(history_file): load_history()
                return rc
            sys.exit(rc)

        interactive = True
        while True:
            try:
                cmd.cmdloop()
                save_history()
                if last_history:
                    if os.path.exists(last_history): load_history(last_history)
                    history_file = last_history
                pref.save()
                break
            except KeyboardInterrupt as e:
                # 割り込みをかけても中断させない
                if verbose:
                    log.exception('%s while cmdloop', e)
                else:
                    syserr.write('Interrupted.\n')

_br_pattern = re.compile('(\[[^]]*\])')

def split_line(line, useGlob=True, use_bracket=True, **opts):
    "行テキストをパラメータ分割する"
    if use_bracket:
        line = _br_pattern.sub(r'"\1"', line)
        line = line.replace('""[', '"[').replace(']""',']"')
    args = [ _decode(tt) for tt in shlex.split(line) ]
    if 'use_glob' in opts: useGlob = opts['use_glob']
    if useGlob: args = glob(args)

    return args


def glob(args, base=''):
    from glob import glob as _glob

    xargs = [ ]

    if not base:
        for tt in args:
            gt = _glob(tt)
            if gt:
                xargs.extend(gt)
            else:
                xargs.append(tt)
    else:
        #基準ディレクトリが指定された
        prefix = os.path.join(base, '')
        plen = len(prefix)

        for tt in args:
            t0 = os.path.join(base,tt)
            gt = _glob(t0)
            if gt:
                xargs.extend([ uu[plen:] for uu in gt ])
            else:
                xargs.append(tt)

    return xargs



def expand_path(path):
    #path = Template(path.replace('\\$','$$')).safe_substitute(dict(os.environ))
    dp = './' if not path else os.path.expanduser(path) if path.startswith('~') else path
    return dp

class _Local_path_handler:
    "ローカルファイルシステムのパスを入手する"
    def fetch_complete_list(self, path, fname):
        dc = map(_decode, os.listdir(expand_path(path)))
        fname = _decode(fname) if fname else ''
        return dc, fname


def complete_path(ignore, line, begin, end, **opts):
    "パスの補完"
    path_handler = opts.get('path_handler', _Local_path_handler())
    if debugout:
        puts('----------------------------', file=debugout)
        puts('complete_path:[%s]' % ignore, 'opts:', opts, 'line:', line, 'begin:', begin, 'end:', end, file=debugout)
        if verbose: puts('path_handler:', path_handler, file=debugout)
        debugout.flush()

    def _find_path(line, begin, end):
        "補完対象を入手する"
        if begin == end:
            if line[begin-1:begin] == ' ':
                return '', '.', ''

        begin = line.rfind(' ',0,begin) + 1
        path0 = line[begin:end]

        if path0.endswith('/'):
            fname = ''
            path = path0
        elif '/' in path0:
            i = path0.rfind('/')
            fname = path0[i+1:]
            path = path0[:i+1]
        else:
            fname = path0
            path = './'
        return path0, path, fname

    try:
        path0, path, fname = _find_path(line, begin, end)

        if debugout:
            eputs('target:', path0, 'path:', path, 'fname:', fname, file=debugout)
            debugout.flush()

        dc, fname = path_handler.fetch_complete_list(path, fname)

        # 前方一致しない対象を除く
        if fname:
            res = [name for name in dc if name.startswith(fname)]
        else:
            # 隠しファイルを対象から除く
            res = [name for name in dc if not name.startswith('.')]

        if debugout:
            puts(' ->', res, file=debugout)
            debugout.flush()

        if _rl_with_prefix:
            # WindowsやmacOSはファイル名だけ返してもダメ
            if path == './': return res
            pre = path0[:path0.rfind('/')+1]
            return [ '%s%s' % ( pre, tt) for tt in res ]
        
        return res

    except Exception as e :
        if debugout:
            puts(e, 'while complete path', format_exc(), file=debugout)
        else:
            log.exception('%s while complete path', e)

# 過去互換（スペルミス）
complate_path = complete_path


complete_local_path = CommandDispatcher.complete_local_files

def mbcslen(tt):
    "画面にテキストを表示するときの表示幅を計算する"
    if type(tt) == unicode:
        return len(tt.encode('euc-jp', 'replace'))
    return len(tt)


from .term01 import getTerminalSize

def ljust(tt,n):
    mlen = mbcslen(tt)
    return tt + (n - mlen) * ' '


def show_list(lst, outfh=None, columns=None):
    "画面幅に合わせてリストを表示する"

    if not outfh: outfh = sysout
    if not columns: columns, _ = getTerminalSize()

    ws = 1
    for ent in lst: ws = max(ws, mbcslen(ent))
    ws += 1
    #print('ws', ws, 'cols:', columns)
    cols = int(columns / ws) if ws < columns else 1
    llen = len(lst)
    step = int((llen + (cols - 1)) / cols)
    #print(ws, 'cols:', columns, cols, 'step:',step)
    idx = 0
    row = 0
    buf = ''

    while row < step:
        for nn in range(0, cols):
            if idx >= llen: break
            buf += ljust(lst[idx], ws)
            idx += step

        puts(buf, file=outfh) #.encode('mbcs','replace')
        row += 1
        idx = row
        buf = ''

showList = show_list
show_items = show_list


history_file = '~/.history'

def save_history(fname=None):
    if not fname: fname = history_file
    try:
        fname = expand_path(fname)
        readline.write_history_file(fname)
        if verbose: puts('INFO: save history to', fname, file=err)
    except Exception as e:
        puts('WARN:', e, 'while save history to', fname, file=err)


def load_history(fname=None, clear=True):
    global history_file
    if not fname: fname = history_file
    if clear: readline.clear_history()
    try:
        fname = expand_path(fname)
        readline.read_history_file(fname)
        history_file = os.path.abspath(fname)
        if verbose: puts('INFO: load history from', history_file, file=err)
    except:
        pass


def editor(text_file):
    "テキスト・エディタを起動する"
    editor = os.environ.get('EDITOR')
    if not editor:
        if sys.platform == 'win32':
            editor = 'notepad.exe'
            #log.info('text_file: %s', text_file)
            #text_file = '"%s"' % text_file
        else:
            editor = 'vi'
    rc = subprocess.call([editor, text_file], shell=False)
    return rc

        
def eval(cmd, trim=False):
    '外部コマンドを実行してその出力テキストを得'
    args = shlex.split(cmd) if type(cmd) == str else cmd
    p = subprocess.Popen(args, stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out.rstrip() if trim else out


if __name__ == '__main__':
    lst = os.listdir('.')
    showList(lst)


