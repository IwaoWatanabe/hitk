# -*- coding: utf-8 -*-

"""多くのモジュールで共通して利用される機能が定義さrています

- コンソール出力
- スレッド制御
- 設定値の参照
- ログ機能
"""

from __future__ import print_function
import logging, os, platform, re, sys, threading
from logging import DEBUG, INFO, WARN, ERROR, FATAL, getLogger
from traceback import format_exc
from time import time as now

if sys.version_info < (3, 0):
    import ConfigParser as configparser
    from Queue import Queue, LifoQueue, PriorityQueue, Empty, Full
else:
    import configparser
    from queue import Queue, LifoQueue, PriorityQueue, Empty, Full
    unicode = str


verbose = os.environ.get("DEBUG", False)

log = None


def trace(msg, *args, **kwarg):
    file = kwarg.get("file", sys.stderr)
    if args:
        if msg and '%' in msg:
            print(msg % args, file=file)
        else:
            print(msg, *args, file=file)
    else:
        print(msg, file=file)


def trace_text(e):
    """スタック・トレースのテキストを入手する"""
    msg = "%s\n\n%s\n%s\n\n%s" % (e, "-" * 20, e.__class__, format_exc())
    title = "%s - Internal Error" % e.__class__.__name__
    return msg, title


class Preference():
    """設定の入手と保存を対応する基底クラス。
実装クラスを差し替えて、設定ファイルの形式を変更することができる。

実装クラスはスレッドセーフになるように作成する。
これ自体がコンテキストマネージャを実装していて、
threading.RLock() と同じような使い方ができる。
"""
    def __init__(self, *args, **kwargs):
        self.config_type = None
        self._last_modified = None
        self._config_name = None
        self._section = 'default'
        self.lock = threading.RLock()
        self.ref = kwargs.get('ref', 'ref')
        self.expand = kwargs.get('expand', True)

    def __enter__(self):
        self.lock.acquire()
        return self
    
    def __exit__(self, t, v, tb):
        self.lock.release()

    def value(self, key, default='', section=None):
        """設定パラメータを入手する"""
        return ''

    def list_value(self, prefix, section=None):
        """prefix が合致する設定値をリストで入手する"""
        value = self.value
        lst = [value(kn, section=section) for kn in self.key_list(self, section=section, prefix=prefix)]
        return lst        

    def key_list(self, section=None, prefix=None, suffix=None, strip=False):
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

    def dict(self, prefix, proc=lambda t:t, section=None):
        "指定するprefixを持つキーからなる辞書データを作成する"
        plen = len(prefix)
        item = { kn[plen:]: proc(self.value(kn, section=section)) \
                 for kn in self.key_list(section, prefix=prefix) }
        return item

    def store(self, key, value, section=None):
        """設定パラメータを一時保存する"""
        pass

    def get_section_names(self, prefix='', suffix='', strip=False):
        """セクション名を入手する"""
        return []

    @property
    def section_names(self):
        return self.get_section_names()
    
    def get_section(self):
        """デフォルトのセクションを入手する"""
        return self._section

    def set_section(self, section):
        """デフォルト・セセクションを設定する"""
        self._section = section

    @property
    def section(self):
        return self.get_section()

    @section.setter
    def section(self, value):
        return self.set_section(value)
    
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
        return self._config_name

    @property
    def config_name(self):
        return self.get_config_name()

    def get_last_modified(self, target=None):
        """読み込んだ設定の最終更新時刻を入手する"""
        if not target: return self._last_modified
        return None

    @property
    def last_modified(self):
        """読み込んだ設定の最終更新時刻を入手する"""
        return self.get_last_modified()

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

    
def _select_names(names, prefix='', suffix='', strip=False):
    """条件に合致する名称を入手する"""
    if not strip:
        if prefix:
            names = [fn for fn in names if fn.startswith(prefix)]
        if suffix:
            names = [fn for fn in names if fn.endswith(suffix)]
    else:
        if prefix:
            plen = len(prefix)
            names = [fn[plen:] for fn in names if fn.startswith(prefix)]
        if suffix:
            slen = -len(suffix)
            names = [fn[:slen] for fn in names if fn.endswith(suffix)]
    return names


_VAR_PATTERN = re.compile(r'\${(\w+)}')


def _env_repl(mr):
    var = mr.group(1)
    val = os.environ.get(var, '')
    return val

  
def _env_value(tt):
    return tt if tt is None or type(tt) == int else re.sub(_VAR_PATTERN, _env_repl, tt)

  
# 環境固有名。デフォルトはホスト名
env = os.environ.get('ENV', platform.uname()[1])


class INIPreference(Preference):
    """ Windowsでよく利用される ini ファイルを扱う Preferenceの実装クラスを定義する。
    python2の標準ライブラリそのままではうまくUNICODEのKey/Valueが扱えないので
    それを補完するコードを含めている。
    スレッドセーフ。書き込み系はあと勝ちになる。
    """

    def __init__(self, conf=None, section=None):
        Preference.__init__(self)
        self.config_type = 'INI'
        self.last_store = 0
        self._config_name = conf
        self._last_modified = None
        self.ini_file = None
        self.ini = configparser.SafeConfigParser()
        if not section and conf:
            section = os.path.basename(conf).split('.')[0]
        self._section = section
        self.mod_interval = 5

    def value(self, key, default='', section=None):
        """設定パラメータを入手する"""
        if not section: section = self._section
        REFS = self.ref
        try:
            self.lock.acquire()
            if type(default) == str and '$' in default: default = _env_value(default)
            ini = self.ini
            val = ini.get(section,_encode(key))
            if not val:
                # カスケード検索
                if not REFS or not ini.has_option(section, REFS): return default
                refs = ini.get(section, REFS)
                if not refs: return default
                for ref in refs.split(','):
                    val = self.value(key, '', ref)
                    if val: return val
                return default
            tt = _decode(val)
            #print type(val), type(tt)
            if self.expand: tt = _env_value(tt)
            return tt
        except Exception as e:
            if not REFS or not ini.has_option(section, REFS): return default
            refs = ini.get(section, REFS)
            if not refs: return default
            for ref in refs.split(','):
                val = self.value(key,'',ref)
                if val: return val
            return default
        finally:
            self.lock.release()

    def key_list(self, section=None, prefix='', suffix='', strip=False):
        """指定するセクションに定義されているキー名を入手する"""
        if not section: section = self._section
        try:
            with self: names = self.ini.options(section)
            names = map(_decode, names)
            return _select_names(names, prefix, suffix, strip)
        except: return []

    def int_value(self, key, default=0, section=None):
        """数値の設定パラメータを入手する"""
        val = self.value(key, '', section)
        if val == '': return default
        try:
            return int(val)
        except:
            return default

    def has_section(self, section):
        return self.ini.has_section(section)
        
    def store(self, key, value, section=None):
        """設定パラメータを一時保存する"""
        if not section: section = self._section
        ini = self.ini
        with self:
            if not ini.has_section(section): ini.add_section(section)
        key = _encode(key)
        with self:
            if value:
                ini.set(section, key, value)
            elif len(value) == 0:
                ini.remove_option(section, key)
        self.last_store = now()

    def get_section_names(self, prefix='', suffix='', strip=False):
        """セクション名を入手する"""
        with self: names = self.ini.sections()
        names = [_decode(sn) for sn in names]
        return _select_names(names, prefix, suffix, strip)

    def delete_section(self, section):
        """指定するセクション情報をメモリ上から一括して破棄する"""
        with self: return self.ini.remove_section(section)

    def _load(self, inifile):
        "INIファイルの読み込み"

        sys.stderr.write("INFO: %s loading ..\n" % inifile)
        if pyver == 2:
            try:
                self.ini.read(inifile)
            except configparser.MissingSectionHeaderError as e:
                sys.stderr.write("WARN: %s\n" % e)
                import codecs
                with codecs.open(inifile, encoding='utf_8_sig') as f:
                    self.ini.read(f)
        else:
            self.ini.read(inifile, encoding='utf-8')

        
    def load(self, target=None):
        """設定を読み込む"""
        inifile = target if target else self.ini_file if self.ini_file else self._config_name

        if not os.path.isfile(inifile):
            if not inifile.lower().endswith('.ini'):
                inifile += '.ini'

        with self: self._load(inifile)

        self._config_name = inifile
        self._last_modified = os.path.getmtime(inifile)

        prefix, suffix = os.path.splitext(inifile)
        envinifile = "%s-%s%s" % ( prefix, env, suffix)
        if os.path.isfile(envinifile):
            with self: self._load(envinifile)
            # 環境固有設定ファイルがあれば、そちらに設定を書き出す
            self._config_name = envinifile
            lmod = os.path.getmtime(envinifile)
            if lmod > self._last_modified:
                self._last_modified = lmod
                
        return True

    def save(self, target=None, section=None):
        """設定を永続化する"""
        with self: return self._save(target=target, section=section)

    def _save(self, target=None, section=None):
        """設定を永続化する"""
        if not self.last_store: return

        inifile = target if target else self.ini_file if self.ini_file else self._config_name
        if not inifile.lower().endswith('.ini'):
            inifile += '.ini'

        ydir = os.path.dirname(inifile)
        if ydir and not os.path.isdir(ydir): os.makedirs(ydir)

        partfile = inifile + '.part'
        ini = self.ini
        if pyver == 2:
            for sec in ini.sections():
                for key in ini.options(sec):
                    tt = ini.get(sec, key)
                    if _isUCS(tt):
                        tt = _encode(tt)
                        ini.set(sec, key, tt)

        with open(partfile, 'w') as wf:
            ini.write(wf)

        if os.path.isfile(inifile): os.remove(inifile)
        os.rename(partfile, inifile)
        self._config_name = inifile
        if verbose: sys.stderr.write('INFO: %s saved.\n' % inifile)

        self.last_store = None
        return True

    def get_last_modified(self, target=None):
        """読み込んだ設定の最終更新時刻を入手する"""
        if not target: return self._last_modified
        return os.path.getmtime(target)

    def reload(self, target=None, section=None):
        """設定が更新されていれば読み込む"""
        if not target: target = self._config_name
        mod = self.get_last_modified(target)
        if mod < self._last_modified + self.mod_interval: return False
        self.load(target)
        return True

    intValue = int_value
    hasSection = has_section
    deleteSection = delete_section
    getSectionNames = get_section_names
    keyList = key_list

    
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
    logfile = os.environ.get('LOGFILE', logfile)
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

    fmtText = pref.value('console-log-format', '%(levelname)s: %(message)s at %(asctime)s', cn)
    fmt = logging.Formatter(fmtText)
    sh = logging.StreamHandler() # コンソールログ
    sh.setFormatter(fmt)
    sh.setLevel(DEBUG if verbose else INFO)
    log.addHandler(sh)

    fmtText = pref.value('log-format', '%(asctime)s %(levelname)s: %(message)s', cn)
    fmt = logging.Formatter(fmtText)

    if os.name == 'nt':
        sh = logging.FileHandler(filename=logfile)
    else:
        sh = TimedRotatingFileHandler(filename=logfile, when='d')

    sh.setLevel(DEBUG)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    return log


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
  

def __testLogger():
    """ ログ操作処理のサンプル
"""
    pref = INIPreference("test.ini")
    pref.load()
    log = get_logger("log01", pref)

    log.info("処理開始")
    try:
        log.debug("デバグメッセージ")
        log.warn("警告メッセージ（テスト）")
        log.error("エラーメッセージ（テスト）")
        raise IOError("例外発生!")

    except Exception as e:
        log.exception("ログのサンプル実行中に例外が生じました: %s" % e)

    finally:
        log.info("処理終了")


if __name__ == '__main__':
    __testLogger()

