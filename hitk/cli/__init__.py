# coding: utf-8

""" 対話型コマンドを実現するための既定クラスと関連関数を提供する
標準ライブラリの cmd を補完するものである

このパッケージはGUIに依存させないように注意を払って実装する。

Windowsではreadlineは pyreadline を合わせて導入すると使い勝手が良い。
pip install pyreadline --user

"""

from __future__ import print_function
import cmd, functools, logging, os, readline, shlex, subprocess, sys, threading
from datetime import datetime as _dt
from getopt import getopt, GetoptError
from getpass import getpass
from logging import DEBUG, INFO, WARN, ERROR, FATAL, Logger
from string import Template
from traceback import format_exc
from time import time as now


appname = 'cli'

if sys.version_info < (3, 0):
    import ConfigParser as configparser
    from Queue import Queue, LifoQueue, PriorityQueue, Empty, Full

else:
    import configparser
    from queue import Queue, LifoQueue, PriorityQueue, Empty, Full
    unicode = str


verbose = os.environ.get('DEBUG', False)

inteactive = True

debugout = None

def trace(msg, *args, **kwarg):
    file = kwarg.pop('file', sys.stderr)
    if args:
        if msg and '%' in msg:
            print(msg % args, file=file, **kwarg)
        else:
            print(msg, *args, file=file, **kwarg)
    else:
        print(msg, file=file, **kwarg)

        
def _print(*args, **kwarg):
    out = kwarg.pop('file', sysout)
    if args:
        print(*args, file=out, **kwarg)
    else:
        print(file=out, **kwarg)

puts = _print


def trace_text(e):
    """スタック・トレースのテキストを入手する"""
    msg = '%s\n\n%s\n%s\n\n%s' % (e, '-' * 20, e.__class__, format_exc())
    title = '%s - Internal Error' % e.__class__.__name__
    return msg, title


class Preference():
    """設定の入手と保存を対応する基底クラス。
実装クラスを差し替えて、設定ファイルの形式を変更することができる。

実装クラスはスレッドセーフになるように作成する。
これ自体がコンテキストマネージャを実装していて、
threading.RLock() と同じような使い方ができる。
"""
    def __init__(self):
        self.config_type = None
        self.last_modified = None
        self.config_name = None
        self.section = 'default'
        self.lock = threading.RLock()

    def __enter__(self):
        self.lock.acquire()
        return self
    
    def __exit__(self, t, v, tb):
        self.lock.release()

    def value(self, key, default='', section=None):
        """設定パラメータを入手する"""
        return ''

    def key_list(self, section=None, prefix=None, suffix=None):
        """指定するセクションに定義されているキー名を入手する"""
        return []

    def int_value(self, key, default=0, section=None):
        """数値の設定パラメータを入手する"""
        val = self.value(key, '', section)
        if val == '': return default
        try:
            return int(val)
        except:
            return default

    def store(self, key, value, section=None):
        """設定パラメータを一時保存する"""
        pass

    def get_section_names(self):
        """セクション名を入手する"""
        return []

    def get_section(self):
        """デフォルトのセクションを入手する"""
        return self.section

    def set_section(self, section):
        """デフォルト・セセクションを設定する"""
        self.section = section

    def has_section(self, section):
        return False

    def delete_section(self, section):
        """指定するセクション情報をメモリ上から一括して破棄する"""
        return False

    def dict(self, prefix, proc=lambda t:t, section=None):
        "指定するprefixを持つキーからなる辞書データを作成する"
        plen = len(prefix)
        item = { kn[plen:]: proc(self.value(kn, section=section)) \
                 for kn in self.key_list(section) if kn.startswith(prefix) }
        return item

    def load(self, target=None):
        """設定を読み込む"""
        return False

    def save(self, target=None, section=None):
        """設定を永続化する"""
        return False

    def get_config_name(self):
        """読み込んだ設定名を入手する"""
        return self.config_name

    def get_last_modified(self, target=None):
        """読み込んだ設定の最終更新時刻を入手する"""
        if not target: return self.last_modified
        return ""

    def reload(self, target=None, section=None):
        """設定が更新されていれば読み込む"""
        return False

_sysenc = sys.getfilesystemencoding()

if sys.version_info < (3, 0):
    def _encode(tt):
        return tt.encode(_sysenc) if type(tt) == unicode else tt
    def _decode(tt):
        return tt.decode(_sysenc, 'replace') if type(tt) == str else tt
    def _isUCS(tt): return type(tt) == unicode
    pyver = 2

else:
    def _encode(tt): return tt
    def _decode(tt): return tt
    def _isUCS(tt): return type(tt) == str
    pyver = 3
    unicode = str


class INIPreference(Preference):
    """ Windowsでよく利用される ini ファイルを扱う Preferenceの実装クラスを定義する。
    python2の標準ライブラリそのままではうまくUNICODEのKey/Valueが扱えないので
    それを補完するコードを含めている。
    スレッドセーフ。書き込み系はあと勝ちになる。
    """

    def __init__(self, conf=None, section=None):
        Preference.__init__(self)
        self.config_type = "INI"
        self.last_modified = None
        self.last_store = 0
        self.config_name = conf
        self.ini_file = None
        self.ini = configparser.SafeConfigParser()
        if not section and conf:
            section = os.path.basename(conf).split(".")[0]
        self.section = section
        self.mod_interval = 5

    def value(self, key, default="", section=None):
        """設定パラメータを入手する"""
        if not section: section = self.section
        try:
            with self: val = self.ini.get(section, _encode(key))
            if not val: return default
            tt = _decode(val)
            #print type(val), type(tt)
            return tt
        except:
            return default

    def key_list(self, section=None, prefix=None, suffix=None):
        """指定するセクションに定義されているキー名を入手する"""
        if not section: section = self.section
        try:
            with self: names = self.ini.options(section)
            names = map(_decode, names)
            if prefix:
                plen = len(prefix)
                names = [ fn[plen:] for fn in names if fn.startswith(prefix) ]
            if suffix:
                slen = -len(suffix)
                names = [ fn[:slen] for fn in names if fn.endswith(suffix) ]
            return names
        except: return []

    def int_value(self, key, default=0, section=None):
        """数値の設定パラメータを入手する"""
        val = self.value(key, "", section)
        if val == "": return default
        try:
            return int(val)
        except:
            return default

    def has_section(self, section):
        return self.ini.has_section(section)
        
    def store(self, key, value, section=None):
        """設定パラメータを一時保存する"""
        if not section: section = self.section
        ini = self.ini
        with self:
            if not ini.has_section(section): ini.add_section(section)
        key = _encode(key)
        with self:
            if value:
                self.ini.set(section, key, value)
            else:
                self.ini.remove_option(section, key)
        self.last_store = now()

    def dict(self, prefix, proc=lambda t:t, section=None):
        "指定するprefixを持つキーからなる辞書データを作成する"
        plen = len(prefix)
        item = { kn[plen:]: proc(self.value(kn, section=section)) \
                 for kn in self.keyList(section) if kn.startswith(prefix) }
        return item

    def section_names(self):
        """セクション名を入手する"""
        with self: names = self.ini.sections()
        return [_decode(sn) for sn in names]

    def delete_section(self, section):
        """指定するセクション情報をメモリ上から一括して破棄する"""
        with self: return self.ini.remove_section(section)

    def load(self, target=None):
        """設定を読み込む"""
        inifile = target if target else self.ini_file if self.ini_file else self.config_name

        if not os.path.isfile(inifile):
            if not inifile.lower().endswith('.ini'):
                inifile += '.ini'

        sys.stderr.write('INFO: %s loading ..\n' % inifile)
        with self:
            self.ini.read(inifile)
            self.config_name = inifile
            self.ini_file = os.path.abspath(ini_file)
            self.last_modified = os.path.getmtime(inifile)

        return True

    def save(self, target=None, section=None):
        """設定を永続化する"""
        with self: return self._save(target=target, section=section)

    def _save(self, target=None, section=None):
        """設定を永続化する"""
        if not self.last_store: return

        inifile = target if target else self.ini_file if self.ini_file else self.config_name
        if not inifile.lower().endswith('.ini'):
            inifile += '.ini'

        ydir = os.path.dirname(inifile)
        if not os.path.isdir(ydir): os.makedirs(ydir)

        partfile = inifile + '.part'

        if pyver == 2:
            for sec in self.ini.sections():
                for key in self.ini.options(sec):
                    tt = self.ini.get(sec, key)
                    if _isUCS(tt):
                        tt = _encode(tt)
                        self.ini.set(sec, key, tt)

        with open(partfile, 'w') as wf:
            self.ini.write(wf)

        if os.path.isfile(inifile): os.remove(inifile)
        os.rename(partfile, inifile)
        self.config_name = inifile
        if verbose:
            sys.stderr.write('INFO: %s saved.\n' % inifile)

        self.last_store = None
        return True

    def get_last_modified(self, target=None):
        """読み込んだ設定の最終更新時刻を入手する"""
        if not target: return self.last_modified
        return os.path.getmtime(target)

    def reload(self, target=None, section=None):
        """設定が更新されていれば読み込む"""
        if not target: target = self.config_name
        mod = self.get_last_modified(target)
        if mod < self.last_modified + self.mod_interval: return False
        self.load(target)
        return True

    intValue = int_value
    hasSection = has_section
    deleteSection = delete_section
    get_section_names = section_names
    getSectionNames = section_names
    keyList = key_list

    
log = None


def get_logger(app_name, pref, ui=""):
    """　ロガー・インスタンスを設定に基づいて初期化して入手する

param: appName ロガー情報を定義した設定のセクション名
"""
    global log
    if log: return log
    from os.path import  dirname

    cn = app_name
    home = os.path.expanduser('~')
    logfile = pref.value('logfile', os.path.join(home, ui, 'logs', '%s.log' % cn))
    if logfile.find('%s') > 0: logfile = logfile % cn
    sys.stderr.write('INFO: logged to %s\n' % logfile)

    for fn in [ logfile ]:
        ldir = dirname(fn)
        if not os.path.isdir(ldir):
            os.makedirs(ldir)
            sys.stderr.write('INFO: log dir %s created.\n' % ldir)

    log = logging.getLogger(cn)
    log.setLevel(DEBUG)

    from logging.handlers import TimedRotatingFileHandler

    fmtText = pref.value('log-format',
                '%(levelname)s: %(message)s at %(asctime)s', cn)
    fmt = logging.Formatter(fmtText)
    sh = logging.StreamHandler() # コンソールログ
    sh.setFormatter(fmt)
    sh.setLevel(INFO)
    log.addHandler(sh)

    fmtText = pref.value('log-format',
                '%(asctime)s %(levelname)s: %(message)s', cn)
    fmt = logging.Formatter(fmtText)

    if os.name == 'nt':
        sh = logging.FileHandler(filename=logfile)
    else:
        sh = TimedRotatingFileHandler(filename=logfile, when='d')

    sh.setLevel(DEBUG)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    return log



# https://pewpewthespells.com/blog/osx_readline.html

_rl_with_prefix = sys.platform.startswith('win')

if readline.__doc__ and 'libedit' in readline.__doc__:
    # macos標準python向けの設定
    readline.parse_and_bind('bind ^I rl_complete')
    _rl_with_prefix = True
else:
    readline.parse_and_bind('tab: complete')


# 単語の区切り文字の除外
delims = readline.get_completer_delims()
for ch in '+-=,': delims = delims.replace(ch, '')
readline.set_completer_delims(delims)

try:
    import pytz
    tz_name = os.environ.get('ZONE', 'Asia/Tokyo')
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
        

class InterruptedException(Exception):
    '''sleep中に interrupt が呼び出されたら生ずる例外
    あるいは　test_interrupted の呼び出しによっても生ずる
    '''
    pass


def current_thread():
    return threading.current_thread()


def is_interrupted(th):
    '指定したスレッドでinterrupt が呼び出されたか診断する'
    return True if hasattr(th, 'interrupted') and th.interrupted else False


def test_interrupted(th):
    '指定したスレッドでinterrupt が呼び出されていたら 例外を発生させる'
    if is_interrupted(th):
        raise InterruptedException('Interrupted.')

    
def interrupt(th):
    '''指定したスレッドでinterruptフラグを設定する。
    そのスレッドで test_interrupted を呼び出していたら例外が生ずる
    sleepを呼び出していたら、一時停止をやめる
    '''
    if th and isinstance(th, threading.Thread):
        th.interrupted = True
        if hasattr(th, 'sleep_queue'): th.sleep_queue.put('wakeup!')

        
def _en(tt): return tt.name if hasattr(tt, 'name') else tt

def sleep(sec=1.0):
    '指定する秒数だけ停止する'

    th = threading.current_thread()        

    if hasattr(th, 'sleep_queue'):
        q = th.sleep_queue
    else:
        th.sleep_queue = q = Queue()

    try: q.get(block=True, timeout=sec)
    except Empty: return
    raise InterruptedException('sleep break')
    

def nextopt(args, params=None):
    "パラメータのあとにオプションを受け入れるための関数"
    while args:
        tn = args.pop(0)
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
            if not inteactive: return 2

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

    
class InterruptedException(Exception):
    '''sleep中に interrupt が呼び出されたら生ずる例外
    あるいは　test_interrupted の呼び出しによっても生ずる
    '''
    pass


sysin = sysout = out = _MTSIO()


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

            line = Template(line).safe_substitute(dict(os.environ))
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
                            return self.do_help(cmd)

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
            if not inteactive: return 2
                
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
            if opt: print('unkwon option', opt, file=err)
            
            doc = getattr(self, 'do_' + cmd).__doc__
            if doc:
                pos = doc.find('\n-')
                if pos < 0: pos = doc.find('\n\n')
                if pos > 0: doc = doc[:pos]

                #print >>self.stdout, 'pos:', pos
                
                self.stdout.write('%s\n' % str(doc))
                return
        except AttributeError:
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
        """usage: history [-d #]
\thistory [-rw][history-file]
- show command line history.
"""
        global verbose
        cmd = argv.pop(0)
        mode = 'show'
        dline = None
        params = []
        while argv:
            opts, args = getopt(argv, 'rwd:v',(
                'delete=', 'load', 'save',
            ))
            for opt, optarg in opts:
                if opt in ('-d', '--delete'): mode = 'delete'; dline = optarg
                if opt in ('-r', '--load'): mode = 'load'
                if opt in ('-w', '--save'): mode = 'save'
                elif opt in ('-v', '--verbose'): verbose = True
                else: return self.usage()

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
                print(i, readline.get_history_item(i))

        elif mode == 'delete':
            pass

    def _show_threads(self):
        print('\t'.join(('name','daemon','ident','alive','type')))

        ct = 0
        for th in threading.enumerate():
            print(th.name, '\t', th.daemon, '\t', th.ident, '\t', th.is_alive(), type(th))
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
\tpreference -i <file> .. # import
\tpreference -u [-s <section>] [key [value]] # update
\tpreference -d [-s <section>] key .. # remove property data
\tpreference -c <section> # change current section
\tpreference -n <old-section> <new-section> # rename
"""
        # 設定の調整
        cmd = argv.pop(0)
        show_sec_list = False
        delete_sec = False
        section = None
        verbose = False
        all = False
        op = 'show'
        
        params = []
        while argv:
            opts, args = getopt(argv, 'o:c:dls:v',(
                'list', 'change=', 'section=', 'delete', 'verbose',
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
                elif opt in ('-e', '--edit'): op = 'edit'
                elif opt in ('-i', '--import'): op = 'import'
                elif opt in ('-o', '--export'): op = 'export'; output = optarg
                elif opt in ('-s', '--section'): section = optarg
                elif opt in ('-D', '--drop', '--drop-section'): op = 'drop'
                elif opt in ('-d', '--delete', '--delete-data'): op = 'delete'
                elif opt in ('-n', '--rename'): op = 'rename'
                elif opt in ('-u', '--update'): op = 'update'
                elif opt in ('-v', '--verbose'): verbose = True
                else: return self.usage(cmd)
                
            argv = nextopt(args, params)

        if all and op in ('drop', 'delete', 'list', 'edit'):
            params = list(pref.get_section_names())
            
        al = len(params)

        if al == 0 and op in ('drop', 'delete', 'list', 'edit', 'rename'):
            names = sorted(pref.get_section_names())
            show_items(names)
            log.info('%s sections.', len(names) if names else 'no')
            return 1

        if op == 'drop':
            # セクションを指定して削除
            for sec in params:
                if pref.delete_section(sec):
                    log.info('%s droped.', sec)
                else:
                    log.warn('no such section: %s', sec)
            pref.save()
            return

        if al < 1:
            # 登録済のデータ値を出力する
            names = pref.key_list(section)
            names.sort()
            for key in names:
                tt = pref.value(key, '', section)
                print('%s=%s' % (key, tt))
            print()
            log.info('%d entries in %s section.', len(names), section if section else 'default')
            return

        '''
        if al < 2:
            key = args[0]
            print >>sysout, '%s=%s' % (key, pref.value(key,'',section))
            return

        for key, value in zip(args[::2],args[1::2]):
            pref.store(key,value,sectionName)
            print >>sysout, '%s=%s' % (key, pref.value(key,'',section))

        pref.save()
        '''


    @cmd_args
    def export_preference_cmd(self, argv):
        "usage: export_preference [-lnv] <file> [section] .."
        # 設定の調整
        cmd = argv.pop(0)
        opts, args = getopt(argv, 'ls:vn')

        show_sec_list = False
        verbose = False
        dry_run = False

        for opt, optarg in opts:
            if opt == '-l': show_sec_list = True
            elif opt == '-v': verbose = True
            elif opt == '-n': dry_run = True
            else: return self.do_help(cmd)

        al = len(args)

        if al < 1 or show_sec_list:
            names = pref.get_section_names()
            names.sort()
            showList(names)
            print('%d sections.' % len(names), file=syserr)
            return

        pref_name = args[0]

        if not pref_name.lower().endswith('.ini'):
            pref_name += '.ini'

        epref = INIPreference(pref_name)
        names = pref.get_section_names() if al < 2 else args[1:]
        for sec in names:
            if verbose:
                print('[%s]' % (sec, ),file=err)

            for key in pref.keyList(sec):
                tt = pref.value(key, '', section=sec)
                if verbose:
                    print('%s = %s' % (key, tt), file=err)
                epref.store(key, tt, sec)

        if not dry_run:
            epref.save()

        log.info('%s exprted.', pref_name)

    @cmd_args
    def import_preference_cmd(self, argv):
        "usage: import_preference [-rna] <file> [section] .."
        # 設定の調整
        cmd = argv.pop(0)
        opts, args = getopt(argv, 'alrnv')

        dry_run = False
        replace_mode = False
        global verbose

        all_import = False
        load_section = False

        for opt, optarg in opts:
            if opt == '-n': dry_run = True
            elif opt == '-l': load_section = True
            elif opt == '-a': all_import = True
            elif opt == '-r': replace_mode = True
            elif opt == '-v': verbose = True
            else: return self.do_help(cmd)

        al = len(args)
        if al == 0: return self.do_help(cmd)

        pref_name = args.pop(0)

        epref = INIPreference()
        epref.load(pref_name)

        sect = 0

        if args:
            for sec in args:
                sect += 1
                if verbose: print('[%s]' % sec, file=err)
                for key in epref.key_list(sec):
                    tt = epref.value(key, '', section=sec)
                    if verbose: print('%s=%s' % (key, tt))
                    if not dry_run:
                        pref.store(key, tt, sec if load_section else None)
                
        elif all_import:
            for sec in epref.get_section_names():
                sect += 1
                for key in epref.key_list(sec):
                    tt = epref.value(key, '', section=sec)
                    if verbose: print('%s=%s' % (key, tt))
                    if not dry_run: pref.store(key, tt, sec)
                    
        else:
            log.info('no sections import.')
            return 0

        if not dry_run and sect > 0:
            pref.save()
            log.info('%d sections imported.', sect)

    @cmd_args
    def rename_preference_cmd(self, argv):
        """usage: preference_rename old_section new_section
"""
        cmd = argv.pop(0)
        opts, args = getopt(argv, 'lv')

        mode = 'rename'

        for opt, optarg in opts:
            if opt == '-l': mode = 'list'
            else: return self.do_help(cmd)

        
        if len(args) < 2 or mode == 'list':
            sec = pref.get_section_names()
            showList(sec)
            log.info('%d sections.', len(sec))
            return

        pref.rename_section(args[0], args[1])
        pref.save()

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
        return not inteactive

    @classmethod
    def run(cls, *modules, **karg):
        "start interactive mode."
        global history_file, preference_file, pref, log
        from os import environ as ENV
        fqcn = cls.__name__
        argv = karg.get('argv', sys.argv)
        last_history = karg.get('last_history')
        sn = cn = str(fqcn).split('.')[-1]
        pos = fqcn.rfind('.')
        mn = fqcn[0:pos] if pos > 0 else '__main__'
        mod = __import__(mn)

        global verbose, inteactive
        if 'DEBUG' in ENV: verbose = True

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
        if '-' in c0:
            subcmd = c0[c0.find('-')+1:]
            args.insert(0, subcmd)
            
        if args:
            line = _arg_join(args)
            if verbose: print('args', args, file=err)
            inteactive = False
            try:
                rc = cmd.onecmd(line)
            except Exception as e:
                rc = 3
                elog = log.exception if verbose else log.error
                elog('%s while execute\n %s', e, line)
            except KeyboardInterrupt:
                rc = 4
                syserr.write('Interrupted.\n')

            if verbose: print('rc: ', rc, file=err)
            if last_history:
                # カスケード呼びさしされている
                history_file = last_history
                if os.path.exists(history_file): load_history()
                return rc
            sys.exit(rc)

        while True:
            try:
                cmd.cmdloop()
                save_history()
                if last_history:
                    if os.path.exists(last_history): load_history(last_history)
                    history_file = last_history
                pref.save()
                break
            except KeyboardInterrupt:
                # 割り込みをかけても中断させない
                syserr.write('Interrupted.\n')



def split_line(line, useGlob=True, **opts):
    "行テキストをパラメータ分割する"
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
    dp = './' if not path else os.path.expanduser(path) if path.startswith('~') else path
    return dp

class _Local_path_handler:
    "ローカルファイルシステムのパスを入手する"
    def fetch_complete_list(self, path, fname):
        dp = './' if not path else os.path.expanduser(path) if path.startswith('~') else path
        dc = map(_decode, os.listdir(dp))
        fname = _decode(fname) if fname else ''
        return dc, fname


def complete_path(ignore, line, begin, end, **opts):
    "パスの補完"
    path_handler = opts.get('path_handler', _Local_path_handler())
    if debugout:
        print('----------------------------', file=debugout)
        print('complete_path:[%s]' % ignore, 'opts:', opts, 'line:', line, 'begin:', begin, 'end:', end, file=debugout)
        if verbose: print('path_handler:', path_handler, file=debugout)
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
            print('target:', path0, 'path:', path, 'fname:', fname, file=debugout)
            debugout.flush()

        dc, fname = path_handler.fetch_complete_list(path, fname)

        # 前方一致しない対象を除く
        if fname:
            res = [name for name in dc if name.startswith(fname)]
        else:
            # 隠しファイルを対象から除く
            res = [name for name in dc if not name.startswith('.')]

        if debugout:
            print(' ->', res, file=debugout)
            debugout.flush()

        if _rl_with_prefix:
            # WindowsやmacOSはファイル名だけ返してもダメ
            if path == './': return res
            pre = path0[:path0.rfind('/')+1]
            return [ '%s%s' % ( pre, tt) for tt in res ]
        
        return res

    except Exception as e :
        if debugout:
            print(e, 'while complete path', format_exc(), file=debugout)
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


def show_list(lst, outfh=None):
    "画面幅に合わせてリストを表示する"

    if not outfh: outfh = sysout

    columns, lines = getTerminalSize()
    ws = 1
    for ent in lst: ws = max(ws, mbcslen(ent))
    ws += 1
    cols = int(columns / ws)
    llen = len(lst)
    step = int((llen + (cols - 1)) / cols)
#    print ws, 'cols:', columns, 'lines:', lines, 'step:',step
    idx = 0
    row = 0
    buf = ''

    while row < step:
        for nn in range(0, cols):
            if idx >= llen: break
            buf += ljust(lst[idx], ws)
            idx += step

        print(buf, file=outfh) #.encode('mbcs','replace')
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
        if verbose: print('INFO: save history to', fname, file=err)
    except Exception as e:
        print('WARN:', e, 'while save history to', fname, file=err)


def load_history(fname=None, clear=True):
    global history_file
    if not fname: fname = history_file
    if clear: readline.clear_history()
    try:
        fname = expand_path(fname)
        readline.read_history_file(fname)
        history_file = os.path.abspath(fname)
        if verbose: print('INFO: load history from', history_file, file=err)
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
#    print len(lst)
#    print lst


