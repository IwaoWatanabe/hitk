# -*- coding: utf-8 -*-

""" ローカル・ファイルシステムにメールを配置する仕掛けを提供
"""

import os, sys, time
from time import time as now
from mailbox import Maildir, NoSuchMailboxError
import hitk.cli.utf7

Maildir.colon = '!'

log = None

if sys.version_info < (3, 0):
    def _encode_mutf7(fn):
        if type(fn) == str: fn = unicode(fn, 'utf-8')
        return fn.encode('imap4-utf-7')
else:
    def _encode_mutf7(fn):
        return fn.encode('imap4-utf-7')


def _decode_mutf7(fn):
    return fn.decode('imap4-utf-7')


def _decode_mime_header(header_text):
    """ MEMEエンコードされたヘッダを元にに戻す """
    from email.header import decode_header
    buf = ''
    for tt, enc in decode_header(header_text):
        if enc:
            buf = buf + tt.decode(enc)
        elif tt:
            buf = buf + tt
    return buf


def mkdirs(base, sub=None):
    """ディレクトリが無ければ作成する"""
    dn = os.path.join(base,sub) if sub else base
    if not os.path.isdir(dn): os.makedirs(dn)
    if not os.path.isdir(dn):
        raise IOError('%s is not directory or no permission' % dn)
    return dn


class MessageExporter:
    """インターネットメッセージを連続して出力するインタフェース"""

    def begin_export(self, name=None):
        """Exportの開始前に呼び出される"""
        pass

    def end_export(self):
        """Exportの後始末処理のために呼び出される"""
        pass

    def write_message(self,rawtext,received,uid):
        """メッセージを書き出す"""
        pass


class EMLExporter(MessageExporter):
    """EMLテキストとしてファイル・システムに出力する"""

    def __init__(self, basedir='work'):
        self.basedir = basedir
        self.outdir = None

    def begin_export(self, name=None):
        self.outdir = mkdirs(self.basedir, name)

        from email.parser import Parser
        self.parser = Parser()
        self.starttime = now()
        self.counter = 0

    def end_export(self):
        self.endtime = now()
        #log.info('export %d files in %s sec' % (
        #    self.counter, self.endtime - self.starttime))

    def _message_name(self, name):
        "フォルダで被らないファイル名を得る"
        name = name.replace('\n',' ').replace('\t',' ').\
            replace('\r',' ').replace('  ',' ')

        for ch in "\\/:*?\'<>|=":
            if ch in name: name = name.replace(ch,'')
        if len(name) > 80: name = name[:80]

        fn = os.path.join(self.outdir, '%s.eml' % name)
        ct = 0
        while os.path.exists(fn):
            ct += 1
            fn = os.path.join(self.outdir, '%s-%d.eml' % (name, ct))
        return fn

    def write_message(self, rawtext, received, uid):
        "メッセージを書き出す"
        msg = self.parser.parsestr(rawtext, headersonly=True)
        sub = msg['Subject']
        if not sub: sub = 'no subject'
        else:
            sub = _decode_mime_header(sub)

        fn = self._message_name(sub)

        partfile = '%s.part' % fn
        try:
            with open(partfile, 'wb') as fh:
                fh.write(rawtext)

            if received:
                mtime = time.mktime(received)
                atime = mtime
                os.utime(partfile, (atime, mtime))
            os.rename(partfile, fn)
        except:
            if os.path.exists(partfile):
                os.remove(partfile)
            raise

        self.counter += 1


user_mailbox = '~/mailbox'

class LocalMDir(MessageExporter):
    """ Maildirを使ってローカルmboxを操作するクラス
    """

    def __init__(self):
        self.mdir = None
        self.cur = None
        self.fld = None
        self.verbose = None
        self.basedir = None

    def open(self, basedir=None):
        """Maildirの利用を開始する"""
        if not basedir: basedir = os.path.expanduser(user_mailbox)

        mdir = Maildir(basedir, None)
        self.mdir = mdir
        self.cur = ''
        self.fld = mdir
        self.basedir = basedir
        #print mdir

    def close(self):
        """Maildirの利用を終了する"""
        if self.mdir == None: return
        self.mdir = None
        self.fld = None

    def get_folder_list(self):
        """保持するフォルダの一覧を入手する"""
        fns = self.mdir.list_folders()
        return [ _decode_mutf7(fn) for fn in fns ]

    def create_folder(self,name):
        """フォルダを作成する"""
        mdir = self.mdir
        try:
            fn = _encode_mutf7(name)
            fld = mdir.get_folder(fn)
            #log.warn('folder %s already exists.', name)
            return False

        except NoSuchMailboxError as e:
            fld = mdir.add_folder(fn)
            print(fld)
            log.info('folder %s created.', name)
            return True

        except Exception as e:
            log.exception('folder %s cannot created.', name)
            return False

    def drop_folder(self, name, force=False):
        """フォルダを破棄する"""
        mdir = self.mdir
        try:
            fn = _encode_mutf7(name)
            if force:
                # 含まれるメッセージを削除する
                fld = mdir.get_folder(fn)
                for key in fld.iterkeys(): discard(key)

            mdir.remove_folder(fn)
            log.info('folder %s droped.', name)
            return True

        except NoSuchMailboxError as e:
            log.warn('no such drop folder: %s', name)
            return False


    def get_select_folder(self): return self.cur

    def select(self, name):
        mdir = self.mdir
        if not name:
            self.cur = ''
            self.fld = mdir
            return True

        fn = _encode_mutf7(name)
        fld = mdir.get_folder(fn)
        self.cur = name
        self.fld = mdir
        log.info('folder %s selected.', name)
        return True

#   ----- ここから Exporterとしての実装

    def begin_export(self, name=None):
        if not self.mdir: self.open()
        if not name:
            fld = self.mdir
        else:
            self.create_folder(name)
            fn = _encode_mutf7(name)
            fld = self.mdir.get_folder(fn)

        self.expfld = fld
        self.starttime = now()
        self.expCounter= 0

    def end_export(self):
        self.endtime = now()
        #log.info('export %d files in %s sec',
        #    self.expCounter, self.endtime - self.starttime)
        self.expfld = None

    def write_message(self, rawtext, received, uid):
        """メッセージを書き出す"""
        if self.expfld == None:
            raise Exception('call beginExport before wirteMessage')
        self.expfld.add(rawtext)
        self.expCounter += 1

#   ----- ここまで Exporterとしての実装

    def export_message(self, target, exporter, name=None):
        """　メッセージを出力する"""

        if 'all' == target:
            pass


if __name__ == '__main__':
    from hitk import cli
    pref = cli.INIPreference('test.ini')
    pref.load()
    log = cli.get_logger('mbox', pref)
    log.info('start')
    mbox = LocalMDir()
    mbox.verbose = True

    try:
        mbox.open()
        for fn in ('あああ','いいい','AAA'):
            mbox.create_folder(fn)

        flds = mbox.get_folder_list()
        print('\n'.join(flds))

        mbox.drop_folder(fn)
    finally:
        mbox.close()
        log.info('done.')
