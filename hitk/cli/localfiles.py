# -*- coding: utf-8 -*-

"""
ローカルファイルを操作する基本機能を定義する

"""

import logging, os, platform, re, shutil, stat, subprocess, sys
from glob import glob as _glob;
from time import time as now
from datetime import datetime as _dt
import tempfile as _tempfile
from hitk import cli

log = logging.getLogger(__name__)

class _TempSession(object):
  """
  一時ファイルを操作する一連の機能を提供する
  with 文と併用して利用すると、セッション終了後にフォルダ毎削除する。
  """
  def __init__(self, suffix='.tmp', prefix='work-', base_dir='', delete=True):
    if not base_dir: base_dir = os.getcwd()
    self.tmpdir = None
    self.base_dir = base_dir
    self.delete = delete
    self.suffix = suffix
    self.prefix = prefix
    
  def _find_tmpdir(self):
    tmpdir = self.tmpdir
    if not tmpdir:
      tmpdir = _tempfile.mkdtemp(self.suffix, self.prefix, self.base_dir)
      self.tmpdir = tmpdir
    return tmpdir
    
  def __enter__(self):
    self._find_tmpdir()
    return self
            
  def __exit__(self, t, v, tb):
    if self.delete: self.drop_work_folder()
        
  def __del__(self):
    if self.delete: self.drop_work_folder()
    
  def tempfile(self, mode='w+b', bufsize=-1, suffix='', prefix='tmp', dir=None, delete=False):
    "セッションディレクトリ内部に一時ファイルを作成する"
    if not dir: dir = self._find_tmpdir()
    return _tempfile.NamedTemporaryFile(mode, bufsize, suffix, prefix, self.tmpdir, delete)
        
  def rename(self, oldname, newname):
    return os.rename(oldname, newname)
            
  def no_delete(self):
    self.delete = False

  def drop_work_folder(self):
    "不要になったセッションフォルダを削除する"
    tmpdir = self.tmpdir
    if not tmpdir: return
    if not os.path.isdir(tmpdir): raise IOError('no such tmp dir:%s' % tmpdir)
    shutil.rmtree(tmpdir)
    log.info('%s: tempdir deleted with file.', tmpdir)
    self.tmpdir = None
        
  def list_temp_folder(self):
    "同じプレフィックス・サフィックス規則を持ったフォルダの一覧を入手する"
    pass
            
            
def tempfolder(suffix='.tmp', prefix='work-', base_dir='', delete=True):
  """ 一時作業用のフォルダを作成する
  """
  return _TempSession(suffix, prefix, base_dir, delete)
    

def tempfile(mode='w+b', bufsize=-1, suffix='', prefix='tmp', dir=None, delete=False):
  """ 一時作業用のファイルを作成する
ファイル名は返されるファイルライクオブジェクトの name メンバから取得することができます。
"""
  if not dir: dir = os.getcwd()
  return _tempfile.NamedTemporaryFile(mode, bufsize, suffix, prefix, dir, delete)


def _fetch_entries(dirname):
  # 指定するフォルダのエントリ一式を入手
  return os.listdir(dirname if dirname else '.')


def _build_entry(ent, dirname=None):
  # エントリ名の再構成(ディレクトリであれば、末尾に / を付与する)
  path = os.path.join(dirname, ent) if dirname else ent
  return '%s/' % path if os.path.isdir(path) else path


def folder_walk(dirname='', fetch=_fetch_entries, entry=_build_entry):
  "フォルダを探索して存在するファイル・ディレクトリ・パスを順に返すイテレータを作成する"
  tdir = dirname if dirname else ''

  dirs = []

  while 1:
    entries = fetch(tdir)
    subdirs = []
    while entries:
      en = entries.pop(0)
      tpath = entry(en, tdir)
      if tpath.endswith('/'):
        subdirs.append(tpath)
        continue
      yield tpath

    if subdirs:
      subdirs.extend(dirs)
      dirs = subdirs

    if not dirs: break
    tdir = dirs.pop(0)
    yield tdir


def _copy_stream(outfh, fh, size=512):
  chunk = fh.read(size)
  sum = 0
  while chunk:
    outfh.write(chunk)
    sum += len(chunk)
    chunk = fh.read(size)
  return sum


class LocalFolder(object):
  """ローカルファイルシステムの基本操作をサポートする機能を提供
  一つのフォルダ毎にインスタンスを作成する
  """
    
  def __init__(self, base_path=''):
    self._base = base_path.strip()

  def _path(self, *args):
    "連結したパスを返す"
    base = self._base if self._base else os.getcwd()
    if not args: return base
    return os.path.join(*args)

  def get_folder_name(self):
    """このインスタンスが対象とするフォルダ名を入手する。
インスタンス生成時に渡したパスを返す"""
    return self._path()

  def get_normalized_name(self):
    """このインスタンスが対象とするフォルダ名を入手する。
正規化したパスを返す"""
    path = self._base
    return os.path.abspath(path)

  def get_entries(self, pattern='', dirOnly=False, nocase=True):
    """ 指定するパスに含まれるファイル名一式を入手する"""
    path = self.getFolderName()
    fns = os.listdir(path)

    if pattern:
      from .glob2re import glob2re
      gre = glob2re(pattern, ignore_case=nocase)
      fns = [ fn for fn in fns if gre.match(fn) ]

    if dirOnly:
      fns = [ fn for fn in fns if os.path.isdir(os.path.join(path,fn)) ]

    return fns

  def glob(self, pattern):
    """ パターンにマッチするファイル/フォルダ名を入手する"""
    if not self._base: return _glob(pattern)
    prefix = os.path.join(self._base, '')
    plen =len(prefix)
    dir_pattern = os.path.join(self._base, pattern)
    return [ tt[plen:] for tt in _glob(dir_pattern) ]

  def create_folder(self, name, mode=0o777, recursive=True):
    """ 指定するディレクトリを作成する"""
    path = self._path(name)
    if recursive: return os.makedirs(path)
    return os.mkdir(path,mode)

  def drop_folder(self, name, mode=0o777, recursive=False, force=False):
    """ ディレクトリを削除する。
forceがFalseの場合はファイルは空である必要がある"""
    path = self._path(name)
    if recursive: return os.removedirs(path)
    return os.rmdir(path,mode)
  
  def copy_file(self, srcfile, dstfile=None, withDelete=False):
    "指定するファイルを複製する"
    pass


  def getSize(self, target):
    "指定するターゲットの大きさ(ファイルサイズ)を入手する"
    pass


  def importFile(self, target, srcFile, sizeHint=None, callback=None):
    "Fileライク・オブジェクトを取り込む"
    pass

  def exportFile(self, target, importer=None, callback=None):
    "Fileライク・オブジェクトのインスタンスを入手する"
    pass

  def deleteFile(self, srcfile, mark=False):
    "指定するファイルに削除するマークを付ける"
    pass

  def rename(self, oldName, newName):
    "指定するファイルやフォルダの名称を変更する"
    pass

  getEntries = get_entries
  getFolderName = get_folder_name
  getNormalizedName = get_normalized_name
  createFolder = create_folder
  dropFolder = drop_folder
  copyFile = copy_file

  def readlines(self, name, size=None, skip=0, step=1, lines=None, \
                    encoding = 'utf-8-sig', errors='strict', ws='\r\n'):
    """テキストを行単位で読み込んで返すジェネレータ。末尾の空白は除く
        サフィックスが.gz であれば、gzip展開しながら読み込む
"""
    import codecs, gzip
    path = self._path(name)
    if encoding:
      if path.endswith('.gz'):
        Reader = codecs.getreader(encoding)
        fh = Reader(gzip.open(path,'r'),errors=errors)
      else:
        fh = codecs.open(path,'r',encoding,errors)

      log.debug('%s: (encoding:%s) reading..', path, encoding)

    else:
      fh = gzip.open(path) if path.endswith('.gz') else open(path)
      log.debug('%s(%s,%s,%s): reading..', path, encoding, size, type(fh))

    try:
      if size is None:
        _readline = fh.readline
      else:
        def _readline(): return fh.readline(size)

      ct = 0
      if skip:
        # 行頭スキップ
        while ct < skip:
          line = _readline()
          ct += 1
          if not line: return
        ct = 0

      line = _readline()
      
      if lines is not None:
        # ------------ 扱う行数に上限を設けている ここから
        if step <= 1:
          while line:
            ct += 1
            if ct > lines: return
            yield line.rstrip(ws)
            line = _readline()
          return
        
        # ------------ 複数行扱う
        
        buf = []; cn = 0
        while line:
          ct += 1
          if ct > lines: break
          buf.append(line.rstrip(ws))
          cn += 1
          if cn >= step:
            buf.append('')
            text = '\n'.join(buf); buf = []; cn = 0
            yield text
              
          line = _readline()

        if buf:
          buf.append('')
          text = '\n'.join(buf); buf = None
          yield text
        return
        # ------------ 扱う行数に上限を設けている ここまで
          
      # ------------ 扱う行数に上限を設けていない ここから
      if step <= 1:
        # ------------ 単一行を扱う
        while line:
          yield line.rstrip(ws)
          line = _readline()
        return

      # ------------ 複数行扱う
      buf = []
      while line:
        buf.append(line.rstrip(ws))
        ct += 1
        if ct >= step:
          buf.append('')
          text = '\n'.join(buf); buf = []; ct = 0
          yield text
        line = _readline()

      if buf:
        buf.append('')
        text = '\n'.join(buf); buf = None
        yield text
        
    finally: fh.close()

    
  def read_tsv_lines(self, name, skip=0, step=1, lines=None, \
                     encoding = 'utf-8-sig', errors='strict', ws='\r\n', sep='\t'):
    """TSVテキストを行単位で読み込んで返すジェネレータ。末尾の空白は除く
        サフィックスが.gz であれば、gzip展開しながら読み込む
"""
    import codecs, gzip
    path = self._path(name)
    if encoding:
      if path.endswith('.gz'):
        Reader = codecs.getreader(encoding)
        fh = Reader(gzip.open(path,'r'),errors=errors)
      else:
        fh = codecs.open(path,'r',encoding,errors)

      log.debug('%s: (encoding:%s) reading..', path, encoding)

    else:
      fh = gzip.open(path) if path.endswith('.gz') else open(path)
      log.debug('%s(%s,%s): reading..', path, encoding, type(fh))

    try:
      ct = 0
      if skip:
        while ct < skip:
          line = fh.readline()
          ct += 1
          if not line: return
          
      ct = 0
      line = fh.readline()

      if step <= 1:
        # --- 行単位で返却する ここから
        if not lines:
          # 返却行数の判定を行わない
          while line:
            yield tuple(line.rstrip(ws).split(sep))
            line = fh.readline()
          return
        
        while line:
          ct += 1
          if ct > lines: return
          yield tuple(line.rstrip(ws).split(sep))
          line = fh.readline()
        return
        # --- 行単位で返却する ここまで

      # --- ここから複数行返す
      buf = []
      cn = 0

      if not lines:
        # 返却行数の判定を行わない
        while line:
          buf.append(tuple(line.rstrip(ws).split(sep)))
          cn += 1
          if cn == step: yield buf; buf = []; cn = 0
          line = fh.readline()
        if buf: yield buf
        return

      # --- ここから行数判定を行う
      while line:
        ct += 1
        if ct > lines: break
        buf.append(tuple(line.rstrip(ws).split(sep)))
        cn += 1
        if cn == step: yield buf; buf = []; cn = 0
        line = fh.readline()
      if buf: yield buf
      
    finally: fh.close()


  def read_csv_lines(self, skip=0, step=1, rows=None, \
                     encoding = 'utf-8-sig', errors='strict'):
    """CSVテキストを行単位で読み込んで返すジェネレータ。末尾の空白は除く
        サフィックスが.gz であれば、gzip展開しながら読み込む
"""
    import codecs, gzip, csv
    path = self._path(name)
    if encoding:
      if path.endswith('.gz'):
        Reader = codecs.getreader(encoding)
        fh = Reader(gzip.open(path,'r'),errors=errors)
      else:
        fh = codecs.open(path,'r',encoding,errors)

      log.debug('%s: (encoding:%s) reading..', path, encoding)

    else:
      fh = gzip.open(path) if path.endswith('.gz') else open(path)
      log.debug('%s(%s,%s,%s): reading..', path, encoding, size, type(fh))

    try:
      ct = 0
      reader = csv.reader(fh)
      if skip:
        while ct < skip:
          row = next(reader)
          ct += 1
          if not row: return

      if step <= 1:
        # --- 行単位で返却する ここから
        if not rows:
          # 返却行数の判定を行わない
          for row in reader:
            yield tuple(row)
          return
        
        for row in reader:
          ct += 1
          if ct > rows: return
          yield tuple(row)
        return
        # --- 行単位で返却する ここまで
          
      # --- ここから複数行返す
      buf = []
      cn = 0

      if not rows:
        # 返却行数の判定を行わない
        for row in reader:
          buf.append(tuple(row))
          cn += 1
          if cn == step: yield buf; buf = []; cn = 0
          
        if buf: yield buf
        return

      # --- ここから行数判定を行う
      
      while line:
        ct += 1
        if ct > rows: break
        buf.append(tuple(row))
        cn += 1
        if cn == step: yield buf; buf = []; cn = 0
      if buf: yield buf
      
    finally: fh.close()


class LocalFileManager:
  "ローカルファイルの基本操作機能を提供する"

  @cli.cmd_args
  def cat_cmd(self, argv):
    "usage: cat [file] .."
    cmd = argv.pop(0)

    start = now()
    sum = 0
    if not argv:
      sum += _copy_stream(cli.out, cli.sysin)
      return
        
    for fn in argv:
      if fn == '-':
        sum += _copy_stream(cli.out, cli.sysin)
      else:
        with open(fn) as fh:
          sum += _copy_stream(cli.out, fh)

    log.info('%d bytes read in %.2f sec', sum, now() - start)
        

  def _copy_reguler_file(self, src_file, dst_file, preserve=True):
    """'一般ファイルを複製する"""
    if not os.path.isfile(src_file):
      raise IOError('not reguler file: %s' % src_file)
        
    part_file = '%s.part' % dst_file
    start = now()
    if preserve:
      shutil.copy2(src_file, part_file)
    else:
      shutil.copy(src_file, part_file)
            
    if os.path.exists(dst_file): os.remove(dst_file)
    os.rename(part_file, dst_file)
    size = os.path.getsize(dst_file)
    if cli.verbose:
      log.debug('%s .. copyed %d bytes in %.2f sec.', dst_file, size, now() - start)
    return size

  def _copy_folder(self, src_dir, dst_dir, preserve=True, level=1):
    """フォルダに含まれる一般ファイルを複製する"""
    if not os.path.isdir(src_dir):
      raise IOError('not dir file: %s' % src_dir)

    if not os.path.isdir(dst_dir):
      raise IOError('not dir file: %s' % dst_dir)

    start = now()
    sum = 0
    ct = 1
    for fn in os.listdir(src_dir):
      src_file = os.path.join(src_dir, fn)
      dst_file = os.path.join(dst_dir, fn)

      if os.path.isfile(src_file):
        sum += self._copy_reguler_file(src_file, dst_file, preserve=preserve)
        ct += 1
                
      elif os.path.isdir(src_file):
        mtime = os.path.getmtime(src_file)
        os.makedirs(dst_file)
        bytes, nct = self._copy_folder(src_file, dst_file, preserve=preserve, level=level+1)
        sum += bytes
        ct += nct
        os.utime(dst_file, (None, mtime))
      else:
        log.warn('not reguler file or directory: %s' % src_file)

    if cli.verbose and level == 1:
      log.debug('%s .. copy folder %d files (%d bytes) in %.2f sec.', dst_dir, ct, sum, now() - start)

    return sum, ct
    
  @cli.cmd_args
  def cp_cmd(self, argv):
    """usage: cp [-pn] <src> <dst>
cp -R [-pn] <src> .. <dst-dir>

- copy file """
    # ファイルを複製する
    # 日付は維持する。
    # 複製途中のファイルは出現しないように調整する
    # 複数のファイルを指定した場合は、<dst>
        
    cmd = argv.pop(0)

    preserve = False
    recursive = False
    dryrun = False
    args = []
        
    while argv:
      opts, params = cli.getopt(argv, 'Rpnv', (
              'recursive', 'preserve', 'verbose', 'dryrun',
              ))
      for opt, optarg in opts:
        if opt in ('-p', '--preserve'): preserve = True
        elif opt in ('-R', '--recursive'): recursive = True
        elif opt in ('-n', '--dryrun'): dryrun = True
        elif opt in ('-v', '--verbose'): cli.verbose = 1
        else: return self.usage(cmd)

      argv = cli.nextopt(params, args)

    if len(args) == 2 and not os.path.isdir(args[1]):
      self._copy_reguler_file(args[0], args[1], preserve)
      return 0
        
    dst_dir = args.pop(-1)
    if not os.path.isdir(dst_dir):
      log.error('%s is not directory.', dst_dir)
      return 1

    sum = 0
    ct = 0
    for fn in args:
      if os.path.isfile(fn):
        dst_file = os.path.join(dst_dir, os.path.basename(fn))
        sum += self._copy_reguler_file(fn, dst_file)
        ct += 1
                
      elif recursive and os.path.isdir(fn):
        dst_new = os.path.join(dst_dir, os.path.basename(fn))
        if not os.path.isdir(dst_new): os.makedirs(dst_new)
        mtime = os.path.getmtime(fn)
        bytes, nct = self._copy_folder(fn, dst_new, preserve=preserve)
        #os.utime(dst_new, (None, mtime))
        sum += bytes
        ct += nct
      else:
        log.error('%s not reguler file or directory', fn)

  def _remove_file_or_directory(self, files, base=None, dryrun=False):
    """一般ファイルかディレクトリを削除する"""
    rc = 0
    for tf in files:
      tt = os.path.join(base, tf) if base else tf
      if os.path.isdir(tt):
        if dryrun:
          self._remove_file_or_directory(os.listdir(), base=base, dryrun=dryrun)
        else:
          shutil.rmtree(tt) # 再帰的に削除する
      elif os.path.isfile(tt):
        if dryrun:
          cli.puts()
        else:
          os.remove(tt)
      else:
        log.error('not reguler file or directory: %s', tt)
        rc = 1
    return rc
    
  def _remove_reguler_files(self, files, recursive=False, dryrun=False):
    '一般ファイルを削除する'
    if recursive: return self._remove_file_or_directory(files, dryrun)
    rc = 0
    for tt in files:
      if os.path.isfile(tt):
        if dryrun: cli.puts()
        else: os.remove(tt)
      else:
        log.error('not reguler file: %s', tt)
        rc = 1
    return rc
    
  @cli.cmd_args
  def rm_cmd(self, argv):
    """usage: rm [-nv] <file>
　rm -R[-v] <file-or-directory>

- remove file or directory """
    # 指定するファイルを削除する。
    # ディレクトリも破棄対象とする場合は -R オプションを合わせて指定すること

    recursive = False
    dryrun = False
    args = []
        
    while argv:
      opts, params = cli.getopt(argv, 'Rnv', (
              'recursive', 'verbose', 'dryrun',
              ))
      for opt, optarg in opts:
        if opt in ('-R', '--recursive'): name = optarg
        elif opt in ('-n', '--dryrun'): dryrun = True
        elif opt in ('-v', '--verbose'): cli.verbose = 1
        else: return self.usage(cmd)
          
      argv = cli.nextopt(params, args)
            
    if not args: self.usage(cmd)
    return self._remove_reguler_files(args, recursive)
        
                    
  @cli.cmd_args
  def mv_cmd(self, argv):
    """usage: mv [-nv] <source> <target>
　mv [-nv] <source> .. <target>
- move file """
    # ファイルを移動する
    # rename できない場合は、cp & rm を利用する
    # 複製途中のファイルは破損しないように注意する
        
  @cli.cmd_args
  def lmkdir_cmd(self, argv):
    """usage: mkdir [-n][-p] <dir>
- make directory (folder) """
  # ディレクトリを作成する
    cmd = argv.pop(0)
    opts, args = cli.getopt(argv, 'np', ('dryrun', 'parents', 'help'))
    dry_run = 0
    with_parent = 0
    mode=0o777

    for opt, optarg in opts:
      if opt in ('-n', '--dryrun'): dry_run = 1
      elif opt in ('-p', '--parents'): with_parent = 1
      else: return self.usage(cmd)
        
    rc = 0
    for path in args:
      try:
        if with_parent:
          os.makedirs(path)
          continue
        os.mkdir(path, mode)
      except OSError as e:
        log.error('%s while mkdir %s', e, path)
        rc = 1

  @cli.cmd_args
  def lrmdir_cmd(self, argv):
    """usage: rmdir [-n][-p] <dir>
- remove empty directory (folder) """
  # ディレクトリを削除する
    cmd = argv.pop(0)
    opts, args = cli.getopt(argv, 'np', ('dryrun', 'parents', 'help'))
    dry_run = 0
    with_parent = 0
    mode = 0o777

    for opt, optarg in opts:
      if opt in ('-n', '--dryrun'): dry_run = 1
      elif opt in ('-p', '--parents'): with_parent = 1
      else: return self.usage(cmd)

    rc = 0
    for path in args:
      try:
        if with_parent:
          os.removedirs(path)
          continue
        os.rmdir(path)
      except OSError as e:
        log.error('%s while rmdir %s', path)
        rc = 1

  @cli.cmd_args
  def lhead_cmd(self, argv):
    """usage: lhead [-n line][-s skip] <file>
- show head line of (gziped) file """
    # gzipファイルの先頭部を表示する
    cmd = argv.pop(0)
        
    lines = 10
    skip = 0
    encoding = None
    errors='strict'
    pattern=''
    args = []
    while argv:
      opts, params = cli.getopt(argv, 'n:s:E:T', (
        'lines=','skip=','encoding=','help'
      ))

      for opt, optarg in opts:
        if opt in ('-n', '--lines'): lines = int(optarg)
        elif opt in ('-s', '--skip'): skip = int(optarg)
        elif opt in ('-T', '--tsv'): pattern = r'\s+'
        elif opt in ('-P', '--pattern'): pattern = optarg
        elif opt in ('-E', '--encoding'): encoding = optarg
        else: return self.usage(cmd)

      argv = cli.nextopt(params, args)

    if len(args) == 0: return self.usage(cmd)

    lf = None
    for fn in args:
      basedir = os.path.dirname(fn)
      if not lf or lf.getFolderName() != basedir:
        lf = LocalFolder(basedir)

      fn0 = os.path.basename(fn)

      if not pattern:
        for line in lf.readlines(fn0, skip=skip, lines=lines, encoding=encoding, errors=errors):
          cli.puts(line)
        return

      fs = re.compile(pattern)
      sep = '\t'
      
      for line in lf.readlines(fn0, skip=skip, lines=lines, encoding=encoding, errors=errors):
        ta = fs.split(line)
        cli.puts(sep.join(ta))

    
    @cli.alert
    def glob_cmd(self, line):
        """usage: glob [-d <base-dir>] pattern ..
- check glob pattern"""

        cmd = 'glob'
        argv = cli.split_line(line,useGlob=False)
        
        basedir = ''
        try:
          opts, args = cli.getopt(argv, 'd:')
        except cli.GetoptError: return self.usage(cmd)

        for opt, optarg in opts:
          if opt == '-d': basedir = optarg
          elif opt == '-v': verbose = True

        lf = LocalFolder(basedir)
        cli.puts(lf)

        entries = [ ]
        for pat in args:
          entries.extend(lf.glob(pat))

        cli.show_items(entries)
        
  @cli.alert
  def find_cmd(self, line):
    """usage: find [-v][-t type][-d depth][-u user][-g group]\
        [-n include-pattern][-x exclude-pattern][-m +mod-date][-s +size] [directory] ..
- find directory entry"""
  # ディレクトリを探索して、条件に合致するファイルをレポートする
    cmd = 'find'
    argv = cli.split_line(line,useGlob=False)

    #print [ (idx,tt) for idx, tt in enumerate(argv) ]
    groups = []
    users = []
    depth = 10
    ftype = ''
    includes = []
    excludes = []
    pattern = []
    modtime = 0
    size = None
    args = []
    while argv:
      opts, params = cli.getopt(argv, 't:d:u:g:n:x:m:s:',(
                'group=', 'user=', 'depth=', 'ftype=',
                'name=', 'exclude=', 'size=', 'modified=',
                ))

      for opt, optarg in opts:
        if opt in ('-g', '--group'): groups.append(optarg)
        elif opt in ('-u', '--user'): users.append(optarg)
        elif opt in ('-d', '--depth'): depth = int(optarg)
        elif opt in ('-s', '--size'): size = int(size)
        elif opt in ('-n', '--name'): includes.append(optarg)
        elif opt in ('-x', '--exclude'): exclude.append(optarg)
        elif opt == '-v': cli.verbose = True
        
      argv = cli.nextopt(params, args)

    if not args: args.append('')

    for dirname in args:
      for fn in folder_walk(dirname):
        if fn.startswith('.'): continue
        cli.puts(fn)

  def getent_cmd(self, line):
    pass
    
  @cli.alert
  def grep_cmd(self, line):
    """usage: grep [-invR][-e [RE]] [RE] <text-file> | <directory> ..
- print reguler expression match line """
    cmd = 'grep'
    argv = cli.split_line(line,useGlob=False)

    opts, args = cli.getopt(argv, 'invre:E:')

    recursive = False
    invert = False
    ignoreCase = False
    patterns = []
    lnumber = False
    encoding = 'utf-8'

    for opt, optarg in opts:
      if opt == '-i': ignoreCase = True
      elif opt == '-v': invert = True
      elif opt == '-R': recursive = True
      elif opt == '-n': lnumber = True
      elif opt == '-e': patterns.append(optarg)
      elif opt == '-E': encoding = optarg
        
    ind = 0
    al = len(args)
    if not al: return self.usage(cmd)

    if not patterns:
      patterns.append(args[ind])
      ind += 1

    if ind > al:
        log.error('empty search target')
        return

    if True:
        regexp = []
        reopts = 0
        if ignoreCase: reopts |= re.IGNORECASE
           
        for pat in patterns:
            regexp.append(re.compile(pat, reopts))

    def _grep_file(target):
        # パターンを検索してマッチしたら表示する
        with open(target) as fp:
            ct = 0
            line = fp.readline()
            try:
                while line:
                    ct += 1
                    line = line.decode(encoding, 'replace')
                    #if ct < 3: print ct,':',type(line),line,
                    
                    found = False
                    for reg in regexp:
                        if reg.search(line): found = True; break

                    pflag = not invert if found else invert
                    if pflag:
                        if lnumber:
                            cli.puts('%s: %s: %s' % (target, ct, line), end='')
                        else:
                            cli.puts( '%s: %s' % (target, line), end='')

                    line = fp.readline()
            except Exception as e: 
                cli.puts('ERROR: %s:%s:%s' % (tf, ct, e), file=cli.syserr)
                    
        for tf in cli.glob(args[ind:]):
            _grep_file(tf)

  def __init__(self):
    self.home = os.getcwd()

  @cli.alert
  def host_cmd(self,line):
    "usage: host <host-commnad>"
    os.system(line)

  do_shell = host_cmd

  @cli.cmd_args
  def echo_cmd(self, argv):
    """usage: echo [args] ..
- echo back argument """
    cmd = argv.pop(0)
    sep = ''
    for tt in argv:
        cli.puts(sep, end='')
        cli.puts(tt, end='')
        sep = ' '
    cli.puts()
    
  @cli.cmd_args
  def alert_cmd(self, argv):
    """usage: alert [message] ..
- test for alert  """
    cmd = argv[0]
    # わざと例外を投げる
    raise Exception(' '.join(argv))


  @cli.cmd_args
  def verbose_cmd(self, argv):
    """usage: verbose
- toggle verbose flag  """
    cmd = 'alert'
    cli.verbose = not cli.verbose
    cli.puts('verbose:', cli.verbose, file=cli.syserr)


  @cli.cmd_args
  def lpwd_cmd(self, argv):
    """usage: lpwd
- print local work directory """
    cli.puts(os.getcwd())

        
  @cli.cmd_args
  def lcd_cmd(self, argv):
    "usage: lcd [target-dir]"
    cmd = argv.pop(0)
    wd = argv[0] if len(argv) > 0 else self.home
    os.chdir(wd)
    import dircache
    dircache.reset()

  @cli.cmd_args
  def date_cmd(self,line):
    """usage: date
    """
    #当日の日付情報を入手する
    tt = now()
    pattern = '%Y-%m-%d %H:%M:%S'
    dtext = _dt.fromtimestamp(tt).strftime(pattern)
    cli.puts(dtext)

    
  def _file_format(self,ent,basedir=None):
    path = os.path.join(basedir,ent) if basedir else ent
    pattern = '%Y-%m-%d %H:%M:%S'

    st = os.lstat(path)
    mtime = st.st_mtime
    dtext = _dt.fromtimestamp(mtime).strftime(pattern)
    size = st.st_size
    isdir = stat.S_ISDIR(st.st_mode)
    if isdir:
      buf = '%s <dir>\t%s' % ( dtext, ent)
    elif stat.S_ISREG(st.st_mode):
      buf = '%s %11d %s' % ( dtext, size, ent)
    elif stat.S_ISLNK(st.st_mode):
      buf = '%s <link>\t%s -> %s' % ( dtext, ent, os.readlink(path))
    else:
      buf = '%s - %s' % ( dtext, ent)

    return buf, isdir

  def _lls(self, dirname='', detail=1, recursive=0, all=False):
    "ローカル・ファイル・システムを幅優先で探索してファイル情報を出力する"
    dname = dirname if dirname else '.'        
    if dirname.startswith('./'): dirname = dirname[2:]

    entries = os.listdir(dname)
    entries.sort()
    subdir = []
    if not detail:
      if not all:
          entries = [ ent for ent in entries if not ent.startswith('.') ]

      if dirname:
          cli.puts('%s:' % dirname)

      cli.showList(entries)
      cli.puts()
      for ent in entries:
        if os.path.isdir(os.path.join(dname, ent)): subdir.append(ent)

    else:
      if dirname: cli.puts('%s:' % dirname)
      for ent in entries:
        if not all and ent.startswith('.'): continue
        fmt, isdir = self._file_format(ent, dname)
        cli.puts(fmt)
        if isdir: subdir.append(ent)
      cli.puts()

    if not recursive: return
    del entries
    for dn in subdir:
      dirname = os.path.join(dname, dn)
      self._lls(dirname, detail, recursive, all)


  @cli.cmd_args
  def lls_cmd(self, argv):
    "usage: lls <folder> .."
    cmd = argv[0]
    opts, args = cli.getopt(argv[1:], 'aldCvR')

    lsStyle = 'column'
    recursive = False
    ignoredir = False
    all = False

    for opt, optarg in opts:
      if opt == '-l': lsStyle = 'detail'
      elif opt == '-a': all = True
      elif opt == '-d': ignoredir = True
      elif opt == '-C': lsStyle = 'column'
      elif opt == '-R': recursive = True
      elif opt == '-v': cli.verbose = True
      else: return self.usage(cmd)
        
    detail = lsStyle == 'detail'
    if not args:
      return self._lls('', detail, recursive, all)

    ment = []

    if ignoredir:
      for ent in args:
        fmt, isdir = self._file_format(ent)
        if detail: cli.puts(fmt)
        else: ment.append(ent)
            
      if ment: cli.show_list(ment)
      return 0
        
    for ent in args:
      fmt,isdir = self._file_format(ent)
      if isdir:
        self._lls(ent, detail, recursive, all)
        continue

      if detail: cli.puts(fmt)
      else: ment.append(ent)

    if ment: cli.show_list(ment)


  @cli.cmd_args
  def complete_debug_cmd(self, argv):
    if cli.debugout:
      cli.debugout.close()
      cli.debugout = None
      log.debug('last debug file closed.')

    cmd = argv.pop(0)
    if argv:
      outfile = argv[0]
      cli.debugout = open(outfile,'w')
      log.debug('complete debug out: %s', outfile)

  def complete_complete_debug(self,*args):
    return cli.complate_path(*args)

  @cli.cmd_args
  def hostname_cmd(self, argv):
    'usage: hostname [-a]'
    cmd = argv.pop(0)
    show_all = False
    opts, args = cli.getopt(argv, 'a', ('all'))
    for opt, optarg in opts:
      if opt in ('-a', '--all'): show_all = True
      elif opt == '-v': cli.verbose = True
      else: return self.usage(cmd)
        
    uname = platform.uname()
    if show_all:
      cli.puts(uname)
      return
    cli.puts(uname[1])
        

  @cli.cmd_args
  def env_cmd(self, argv):
    "usage: env [-i][-u var] [name=value].. [cmd [args]] .."
    # 環境変数の確認とコマンドの実行
    cmd = argv[0]
    opts, args = cli.getopt(argv[1:], 'iu:v')

    from os import environ as ENV
    env = dict(ENV)
    
    for opt, optarg in opts:
      if opt == '-u':
        # 指定する変数を除外する
        if optarg in env: env.pop(optarg)
      elif opt == '-i':
        env.clear()
      elif opt == '-v': cli.verbose = True
      else: return self.usage(cmd)

    def show_env():
      for kn in sorted(env.keys()):
        cli.puts('%s=%s' % ( kn, env[kn] ))

    if not args: return show_env()

    ind = 0
    for tt in args:
      p = tt.find('=')
      if p < 1: break
      kn, kv = tt[:p], tt[p+1:]
      env[kn] = kv
      ind += 1
        
    args = list(args[ind:])
    if not args: return show_env()
      
    wd = os.getcwd()

    # 標準入出力は、このプロセスのそれと同じものを利用する
    # コマンドの探索にはPATHを利用してくれる
    pc = subprocess.Popen(args,close_fds=True,cwd=wd,env=env)
    try:
      log.debug('pid: %d', pc.pid)
      rc = pc.wait()
    except:
      rc = 255
      pc.terminate()

    log.debug('rc: %d cmd: %s', rc, ' '.join(args))
    return rc

  @cli.cmd_args
  def less_cmd(self, argv):
    "usage: less [file] .."
    # 外部コマンドのlessを呼び出す
    # 補完しやすいように登録した                                                                                                           

    wd = os.getcwd()
    pc = subprocess.Popen(argv, close_fds=True, cwd=wd)
    try:
      log.debug('pid: %d', pc.pid)
      rc = pc.wait()
    except:
      rc = 255
      pc.terminate()

  @cli.cmd_args
  def sys_cmd(self, argv):
    "usage: sys"
    import readline
    cli.puts('sys.path', sys.path)
    cli.puts('sys.platform', sys.platform)
    cli.puts('sys.version', sys.version)
    cli.puts('readline', readline.__doc__)
    cli.puts('cli', cli.__file__)
      
  @cli.cmd_args
  def tsv_cmd(self, argv):
    """usage: tsv [-n <lines>][-s <skip>][-S <step>][-E <encoding>][-o <outfile>] files ..

options:
  -n #, --lines #
    読み込む総行数

  -s #, --skip #
    読み飛ばす行数。複数のファイルを指定する場合、最初のファイルについてのみ有効
"""
    
    # TSV/CSVファイルを読み込んで表示する
    cmd = argv[0]
    step = 1
    skip = 0
    lines = 0
    encoding = ''
    de = '\t'

    opts, args = cli.getopt(argv[1:], 'n:s:S:E:vd:', (
      'skip=', 'lines=', 'rows=', 'encoding=', 'step=', 'delimiter='))
    
    for opt, optarg in opts:
      if opt in ('-n', '--lines', '--rows'): lines = int(optarg)
      elif opt in ('-d', '--delimiter'): de = optarg
      elif opt in ('-s', '--skip'): skip = int(optarg)
      elif opt in ('-S', '--step'): step = int(optarg)
      elif opt in ('-E', '--encoding'): encoding = optarg
      elif opt == '-v': cli.verbose = True
      else: return self.usage(cmd, opt)

    if step <= 1:
      def xprint(ta):
        cli.puts(de.join(ta))
    else:
      def xprint(rows):
        for ta in rows: cli.puts(de.join(ta))
        
    fm = LocalFolder()

    ct = 0
    for tf in args:
      for ta in fm.read_tsv_lines(
          tf, skip=skip, step=step, lines=lines, encoding=encoding):
        xprint(ta)
        ct += 1

    if cli.verbose:
      log.info('%d time repeat.', ct)
    
  pwd_cmd = lpwd_cmd
  cd_cmd = lcd_cmd
  ls_cmd = lls_cmd
  mkdir_cmd = lmkdir_cmd
  rmdir_cmd = lrmdir_cmd
  head_cmd = lhead_cmd


if __name__ == '__main__':
  class LocalCommand(cli.CommandDispatcher, LocalFileManager): pass
  mod = __import__(__name__)
  LocalCommand.run(mod)
