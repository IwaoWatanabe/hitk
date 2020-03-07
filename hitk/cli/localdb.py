# -*- coding: utf-8 -*-

"""
ローカルデータベース(sqlite)を操作する基本機能を定義する
"""
import codecs, os, sqlite3, threading, sys
from datetime import datetime as _dt
from time import time as now
from hitk import cli


log = cli.getLogger(__name__)


def _now(): return _dt.now().strftime('%Y-%m-%d %H:%M:%S')
def _today(): return _dt.today().strftime('%Y-%m-%d')


def _find_localdb(dbname, base_dir=None):
    """ローカルデータベースを開く"""
    if not base_dir:
        base_dir = pref.value('localdb-basedir', 'work')

    dbfile = os.path.join(base_dir, dbname)
    dirpath = os.path.dirname(dbfile)
    if not os.path.isdir(dirpath): os.makedirs(dirpath)
    path, ext = os.path.splitext(dbfile)
    if not ext: dbfile += '.sqlite'
    dbc = sqlite3.connect(dbfile)
    dbc.create_function('now', 0, _now)
    dbc.create_function('today', 0, _today)
    log.info('%s opened.', dbfile)
    return dbc


def _list_localdb(base_dir=None, suffixes=('.sqlite', '.sqlite3', '.db')):
    "所定のパス配下に存在するローカルデータベースの一覧を入手する"
    if not base_dir:
        base_dir = pref.value('localdb-basedir', '.')
    if not os.path.isdir(base_dir): os.makedirs(base_dir)

    dblist = []
    for fn in os.listdir(base_dir):
        for sfx in suffixes:
            if fn.endswith(sfx):
                dblist.append(fn if base_dir == '.' else os.path.join(base_dir, fn))
    return dblist


def _fetch_table_names(cur):
    "スキーマに登録されているテーブル名を入手する"
    cur.execute("""SELECT name
FROM sqlite_master
WHERE type = 'table'""")
    return [ row[0] for row in cur ]


def _fetch_column_names(tableName,cur):
    "指定するテーブルのカラム名を入手する"
    cur.execute("""SELECT *
FROM %s
WHERE 0=1""" % tableName)
    return [ ct[0] for ct in cur.description ]


class DBError(IOError):
    "このパッケージから投げられる例外"
    pass


class _DBManager():
    """データベース操作の基本操作を提供する。

    データベース操作のためのスレッドを用意し、非同期で指令を入手してデータベース操作を行う。
こちらのインスタンス一つにつき、一つのスレッドを占有する形にする。

    テーブル名、カラム名の入手
    クエリの実行
    結果セットの取り出し
    処理のキャンセル
    TSV/CSVデータのテーブル取り込み（予定）
    クエリの履歴管理（予定）
"""

    def __init__(self, name):
        self.name = name
        self.queue = cli.Queue()
        self.result = None
        self.end_flag = False
        self.status = 'not-connected' # 'ready'|'execute'|'fetch'|'upload'
        self.db = None
        self.thread = None
        self.qids = {}

    def connect(self, name=None, timeout=3.0):
        """データベースに接続する。
この実装はCLI向けなので、GUI向けには調整の必要あり。
認証が必要なDBもこちらを修正することになるだろう。
        """
        start = now()
        self._engine_stop(timeout)
        if name: self.name = name
        dt = now() - start
        if dt < timeout:
            self._engine_start(timeout - dt)
        else:
            raise DBError('ldb:timeout')

    def is_connected(self):
        """データベース操作スレッドが有効であるか診断する
"""
        th = self.thread
        if not th or not th.is_alive: return
        return True
    
    def disconnect(self):
        """データベース接続を解除する
        """
        self._engine_stop()

    def query(self, qtext, timeout=3.0, callback=None):
        '''データベースにクエリを要求して結果を入手する
callbackを指定しなければ同期処理になる
        '''
        if self.status != 'ready': raise DBError('ldb:not ready')
            
        req = self.queue
        rep = self.result
        rbuf = []
        try:
            start = now()
            for query_text in self._read_query(qtext):
                if self._run_command(req, query_text): continue
                if callback:
                    req.put(('async', query_text, callback))
                    continue
                
                if self.status != 'ready': raise DBError('not ready')
                req.put(('exec', query_text))
                res = rep.get(block=True)
                rbuf.append(res)

            self.elapsed_time = now() - start
            return None if not rbuf else rbuf.pop(0) if len(rbuf) == 1 else rbuf
                
        except Interrupt:
            if self.status == 'execute': self.cancel()
            raise

    def fetch_next(self, rs, timeout=3.0, callback=None):
        '''続きのデータを入手する
        '''
        #log.info('fetch-next:%s %s', rs, type(rs))
        if not isinstance(rs, _CurRows): raise DBError('ldb:not result set')
        return self.query('fetch %s' % rs.qid, timeout, callback)
    
    def _run_command(self, rq, text):
        """拡張コマンドの解釈を行う。通常のクエリとして処理する場合はFalseを返す
        """
        return False

    def cancel(self):
        '処理中のクエリをキャンセルする'
        ldb = self.db
        if ldb: ldb.interrupt()

    def _engine_stop(self, timeout=5.0):
        'クエリ処理スレッドを停止する'
        th = self.thread
        if not th or not th.is_alive: return
        self.end_flag = True
        self.cancel()
        self.queue.put(None)
        th.join(timeout)
        
    def _engine_init(self):
        self.result = cli.Queue()
        self.start = start = now()
        self.end_flag = False
        self.thread = None

    def _engine_start(self, timeout):
        'バックグラウンドでクエリを処理するスレッドを起動する'
        self._engine_init()
        th = threading.Thread(name='db-%s' % self.name, args=(self.name, timeout), target=self._engine_loop)
        th.setDaemon(True)
        th.start()
        self.thread = th
        # ログイン状態になるまで待機する
        res = self.result.get(block=True, timeout=timeout)
        if res[0] != 'stat' and res[1] != 'connected':
            raise DBError(' '.join(res))
        
    def _read_query(self, qtext, sep=';'):
        '複数のクエリテキストからクエリを一つ入手するジェネレータ'
        buf = []
        for qt in qtext.split('\n'):
            cp = qt.find('--')
            line = qt[:cp].rstrip() if qt >= 0 else cp.rstrip()
            buf.append(qt)
            if not line: continue
            if line.endswith(sep):
                if not buf: continue
                yield '\n'.join(buf)
        if buf: yield '\n'.join(buf)
    
    def _engine_loop(self, dbname, timeout):
        'デーテベースに接続して以後、キュー経由で入手するクエリを処理して、結果を返す'
        self.thread = threading.current_thread()
        self.status = 'init'
        res = self.result
        try:
            self._connect(dbname)
        except Exception as e:
            res.put(('stat','%s:%s' % (e, e.__class__.__name__)))

        res.put(('stat','connected'))

        ldb = self.db
        cur = None
        cb = None
        
        while not self.end_flag:
            try:
                self.status = 'ready'
                qr = self.queue.get(block=True)
                if not qr: continue

                cb = qr[2] if qr[0] == 'async' else None
                qtext = qr[1].lstrip()
                lqtext = qtext.lower()
                
                if qtext.startswith('fetch '):
                    self.status = 'fetch'
                    rows = self._next_rows(qtext)
                    if cb:
                        cb('next-result', rows)
                        continue
                    
                    res.put(('next-result', rows))
                    continue

                if lqtext.startswith('show'):
                    opt = lqtext.split()
                    opt.pop(0)
                    names = _CurRows()
                    if not cur: cur = ldb.cursor()
                    if opt[0] == 'tables':
                        names._load_names('table', _fetch_table_names(cur))
                    elif opt[0] == 'columns':
                        names._load_names('column', _fetch_column_names(opt[1], cur))
                    else:
                        raise DBError('invalid query')
                    
                    if cb:
                        cb('result', names)
                    else:
                        res.put(('result', names))
                    continue
                
                self.status = 'execute'
                names = ()
                estart = now()
                if not cur: cur = ldb.cursor()
                cur.execute(qtext)
                esec = now() - estart
                if cli.verbose: log.info('elapsed_time: %.ff\n %s', esec, qtext)

                self.status = 'fetch'
                rows = self._fetch_rows(cur)
                if cb:
                    if rows:
                        cb('result', rows)
                    else:
                        cb('affected-rows', cur.rowcount)
                    continue

                if rows:
                    res.put(('result', rows))
                else:
                    res.put(('affected-rows', cur.rowcount))
                
            except Exception as e:
                elog = log.exception if cli.verbose else log.error
                elog('%s(%s) while execute query.', e, e.__class__.__name__)
                if cb:
                    cb('fail', e)
                else:
                    res.put(('fail', '%s:%s' % (e, e.__class__.__name__)))
                try:
                    if cur: cur.close()
                except: pass
                # 例外が生じたらカーソルを再作成する。それに失敗したらDB接続を閉じる
                cur = None

        self._disconnect()
        # database thread end

    def _next_rows(self, qtext):
        # 結果セットの次の塊を入手する
        qid = qtext.split(' ')[1]
        cr = self.qids.pop(qid)
        if not cr: return

        nr = cr._fetch_next_rows()
        if nr: self.qids[qid] = nr
        return nr

    def _fetch_rows(self, cur, limit=1000):
        # 結果セットが返ったらこのメソッドで塊を読み取る
        if not cur.description: return
        cr = _CurRows(cur, limit)
        cr._fetch_next_rows(limit)
        if cr and cr.rows: self.qids[str(cr.qid)] = cr
        return cr

    def _disconnect(self):
        ldb = self.db
        if not ldb: return

        for rs in self.qids.values():
            try: rs._close()
            except: pass
            
        try:
            ldb.close()
            if cli.verbose: log.info('localdb %s closed.', self.name)
        finally:
            self.db = None
            self.status = 'not connected'

    def _connect(self,dbname,**option):
        self._disconnect()
        ldb = _find_localdb(dbname, base_dir=option.get('base_dir'))
        self.db = ldb
        self.qids = {}
        self.status = 'connected'


_next_qid = 0


class _CurRows():
    """ データベースの行データを所定行数ずつ読み込む
    """
    def __init__(self, cur=None, limit=1000):
        global _next_qid
        self.cur = cur
        self.limit = limit
        self.columns = ()
        self.qid = _next_qid
        self.rows = []
        self.elapsed_time = 0
        _next_qid += 1        

    def _close(self):
        cur = self.cur
        if cur: cur.close()

    def _load_names(self, column, names):
        self.columns = [column]
        self.rows = [(tt,) for tt in names]
        
    def _fetch_next_rows(self, step=1000):
        "次の行データを入手する"
        cur = self.cur
        if not cur: return

        if not self.columns:
            self.columns = [tt[0] for tt in cur.description]

        ct = 0
        limit = self.limit
        start = now()

        self.rows = res = []
        while ct < limit:
            if cur.arraysize < limit:
                rows = cur.fetchmany()
                if not rows: break
                res.extend(rows)
                ct += len(rows)
                continue

            rows = cur.fetchmany(size=step)
            if not rows: break
            res.extend(rows)
            ct += len(rows)

        self.elapsed_time = now() - start
        if ct < limit: self.cur = None
        return self

    def as_list(self, column=0):
        '特定カラムの値をリスト値として入手する'
        if type(column) == str: column = self.columns.index(column)
        return [ tt[column] for row in self.rows ]

    def value(self, column=0):
        '先頭行の特定カラムの値を入手する'
        if type(column) == str: column = self.columns.index(column)
        return self.rows[0][column]

    def show_tsv(self, fh=None, sep='\t', encoding='utf-8', errors='replace', with_header=True):
        '保持するデータをTSV出力'
        if with_header: cli.puts('\t'.join(self.columns), file=fh)

        def _ucs(tt):
            return tt.decode(encoding,errors) if type(tt) == unicode else str(tt)

        rows = self.rows
        for row in rows:
            text = sep.join(map(_ucs,row))
            cli.puts(text, file=fh)
        if len(rows) == self.limit: return self # 続きのデータがあるかもしれない
            
            
_local_db = {}


def find_db(dbname):
    'データベース操作インスタンスの入手'
    ldb = _local_db.get(dbname)
    if not ldb:
        ldb = _DBManager(dbname)
        _local_db[dbname] = ldb
    return ldb
    

class LocalDBManager:
  "ローカルデータベースファイルの基本操作機能を提供する"

  @cli.cmd_args
  def use_cmd(self, argv):
    "usage: use [dbfile] .."
    cmd = argv.pop(0)

    if not argv:
        names = _list_localdb()
        cli.show_items(names)
        log.info('%s local db found.', len(names) if names else 'no')
        return

    dbname = argv.pop(0)
    find_db(dbname).connect()
    pref.store('last-db', dbname)

  @cli.cmd_args
  def execute_cmd(self, argv):
    "usage: use [dbfile] .."
    cmd = argv.pop(0)
    
    dbname = pref.value('last-db', 'db01')
    if dbname not in _local_db:
        log.error('%s not connected.', dbname)
        return

    ldb = find_db(dbname)

    query_text = ' '.join(argv)
    res = ldb.query(query_text)

    if res[0] == 'result':
        rt = res[1].show_tsv(cli.out);
        while rt:
            res = ldb.fetch_next(rt)
            if not res or res[0] != 'result': break
            rt = res[1].show_tsv(file=cli.out, with_header=False)
        return
    cli.puts(res)
    
  @cli.cmd_args
  def disconnect_cmd(self, argv):
    "usage: disconnect [dbname] .."
    cmd = argv.pop(0)

    if argv:
        dbname = argv.pop(0)
    else:
        dbname = pref.value('last-db')
        if not dbname: return self.usage(cmd)

    if dbname not in _local_db: return

    find_db(dbname).disconnect()

    
if __name__ == '__main__':
  class LocalDBCommand(cli.CommandDispatcher, LocalDBManager): pass
  mod = __import__(__name__)
  LocalDBCommand.run(mod)
    
