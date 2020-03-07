# coding: utf-8

""" imap4の基本操作を行う機能を定義

python付属のimaplibでは低レベルな機能しか提供しないため、
それを補完するための記述が含まれている。
"""

import calendar, email, imaplib, re, sys, time
from time import time as now
from email.header import Header, decode_header
from hitk import cli
from hitk.cli.maildir import LocalMDir, MessageExporter, EMLExporter

SYSTEM_ENCODING = sys.getfilesystemencoding()

def _decode_mime_header(header_text):
    """ MEMEエンコードされたヘッダを元に戻す """
    if not header_text: return header_text
    
    buf = u''.join([ tt.decode(enc, 'replace') if enc else tt \
            for tt, enc in decode_header(header_text) ])

    #print 'decocde',header_text, '=>', buf, type(buf)
    return buf


def _encode_mime_header(header_text, encoding='ISO-2022-JP'):
    """ ヘッダテキストをMIMEエンコードする """    
    if not header_text: return header_text
    return Header(header_text, encoding).encode()


def _get_body_encoding(m):
    ch = m.get_content_charset()
    return ch


class _EAddress(object):
    """emailアドレスを操作する"""
    def __init__(self, addr=None, realname=None):
        if not addr:
            self.addr = None
            self.realname = None
        elif type(addr) == str:
            self.addr = addr
            self.realname = realname
        else:
            #print addr
            self.addr = addr[1]
            self.realname = _decode_mime_header(addr[0])

    def __str__(self):
        rt = u'%s <%s>' % (self.realname, self.addr)
        return rt.encode(SYSTEM_ENCODING)

    def __repr__(self): return self.__str__()

    def encode(self):
        realname = _encode_mime_header(self.realname)
        return email.utils.formataddr((realname, self.addr))

    @staticmethod
    def parse(addr):
        if type(addr) == list or type(addr) == tuple:
            pa = email.utils.getaddresses(addr)
            return [ _EAddress(ent) for ent in pa ]

        pe = email.utils.parseaddr(addr)
        return _EAddress(pe)


class EMessage(object):
    """Emailメッセージ・テキストの基本操作の機能を定義する
生テキストの分析
正規化したヘッダ・テキストの入手
"""
    def __init__(self, emlfile=None, rawtext=None, multipart=False):
        self.msg = None
        self.uid = None # 識別番号
        self.received = None # 受信日時
        from email.parser import Parser
        self.parser = Parser()
        if rawtext:
            self.parse(rawtext)
            return
        elif emlfile:
            self.load(emlfile)
            return

    def parse(self, rawtext, headersonly=False):
        """生テキストを解析して保持する"""
        msg = self.parser.parsestr(rawtext,headersonly)
        self.msg = msg
        return msg

    def load(self, emlfile, headersonly=False):
        """ローカルファイルから入手して保持する"""
        with open(emlfile, 'r') as fp:
            msg = self.parser.parse(fp, headersonly)  # ファイルの分析
            self.msg = msg
        return msg

    def get_header(self, header_name, default_text=None, decode=False):
        """ヘッダ情報の入手"""
        hvalue = self.msg[header_name]
        try:
            if decode: hvalue = _decode_mime_header(hvalue)
        finally:
            return hvalue

    def get_subject(self, default_text=None):
        """subjectの入手"""
        if not default_text: default_text= '[No Subject]'
        text = self.get_header('Subject', default_text, True)
        return text

    def get_recipients(self, headerKey='To', default_text=None):
        """宛先の入手"""
        if not default_text: default_text= '[No Recipients]'
        hvalues = self.msg.get_all(headerKey,[])
        rec = _EAddress.parse(hvalues)
        return rec

    def get_date(self, date_field='Date'):
        dt = self.msg[date_field]
        pd = email.utils.parsedate(dt)
        return pd

    def recipients_text(self, rep):
        buf = ['%s <%s>' % (rec.realname, rec.addr) if rec.realname else rec.addr for rec in rep]
        return u', '.join(buf)

    def get_header_text(self):
        buf = []
        rec = self.get_recipients('From')
        if rec: buf.append('From: %s' % rec[0])

        sub = self.get_subject()
        #print(sub, type(sub))
        if sub: buf.append('Subject: %s' % sub)

        pd = self.get_date()
        if pd: buf.append('Date: %s' % time.strftime('%Y-%m-%d %H:%M:%S', pd))

        rec = self.get_recipients('To')
        if rec: buf.append('To: %s' % self.recipients_text(rec))

        rec = self.get_recipients('Cc')
        if rec: buf.append('Cc: %s' % self.recipients_text(rec))

        rec = self.get_recipients('Bcc')
        if rec: buf.appned('Bcc: %s' % self.recipients_text(rec))

        return '\n'.join(buf)

    def get_message_text(self):
        buf = ''
        body = ''
        m = self.msg
        benc = _get_body_encoding(m)

        if not m.is_multipart():
            body = m.get_payload(decode=True)
            # マルチパートの場合は動作しない(Noneが返る)
            if benc: body = body.decode(benc, 'replace')
            #print body

        return body

puts = cli.puts

def _show_eml_list():
    from glob import glob

    msg = EMessage()
    
    for fn in glob('work/*.eml'):
        m = msg.load(fn)

        puts('--' * 10, fn, type(m), 'Multpart:', m.is_multipart())
        puts(m.items()) # ヘッダの表示

        sub = m['Subject']
        puts('Subject:', msg.get_subject())
        puts('From:', '\t\n'.join(map(str, msg.get_recipients('From'))))
        pd = msg.get_date()
        puts('Date:', time.strftime('%Y-%m-%d %H:%M:%S', pd))
        puts('To:', msg.get_recipients())
        puts()

        benc = _get_body_encoding(m)

        if not m.is_multipart():
            body = m.get_payload(decode=True)
            # マルチパートの場合は動作しない(Noneが返る)
            if benc: body = body.decode(benc)
            #print body

#if __name__ == '__main__': _show_eml_list()

def _encode_MUTF7(fn):
    """IMAPのフォルダ名に変換する"""
    if type(fn) == str: fn = unicode(fn, 'utf-8')
    return fn.encode('imap4-utf-7')


def _decode_MUTF7(fn):
    """IMAPのフォルダ名からUCSに変換する"""
    return fn.decode('imap4-utf-7')


FOLDER_PATTERN = re.compile(r'\((.*)\)\s"(.*)"\s"?(.*)"?')
STATUS_PATTERN = re.compile(r'"?(.*)"?\s\(([^)]+)\)')
UID_PATTERN = re.compile(r'UID\s+(\d+)')
SIZE_PATTERN = re.compile(r'RFC822\.SIZE\s+(\d+)')

# フラグで指定するテキスト
ANSWERD = '\\Answered'
FLAGED = '\\Flagged'
SEEN = '\\Seen'
DELETED = '\\Deleted'
DRAFT = '\\Draft'
RECENT = '\\Recent'



class IMAPtool(MessageExporter):
    """ IMAP操作をサポートするクラス
    """

    def search(self, search_criterion, charset=None,
               sort_criteria=None, threading_algorithm=None):
        """ メッセージを検索し、idを入手する
        """
        if not self.imap: raise IOError(self.not_connected)

        if threading_algorithm:
            if not charset: raise IOError('thread need charset.')

            rc, res = self.imap.thread(threading_algorithm, charset, search_criterion)
            if cli.verbose:
                log.debug('thread: %s: %s', rc, threading_algorithm, charset)
                log.debug('res: %s', res)

            return res[0] if rc == 'OK' else None

        if sort_criteria:
            if not charset: raise IOError('sort need charset.')

            rc, res = self.imap.sort(sort_criteria, charset, search_criterion)
            if cli.verbose:
                log.debug('sort: %s: %s', rc, sort_criteria, charset)
                log.debug('res: %s', res)

            return res[0] if rc == 'OK' else None

        rc, res = self.imap.search(charset, '(%s)' % search_criterion)
        if cli.verbose:
            log.debug('search: %s: %s, %s', rc, charset, search_criterion)
            log.debug('res: %s', res)

        return res[0].split() if rc == 'OK' else None


    def __list_folder(self, lst):
        da = []
        for fi in lst:
            #print fi, type(fi)
            if fi:
                #print fi
                mr = FOLDER_PATTERN.match(fi)
                if mr:
                    flags,delm,name = mr.groups()
                    while name[-1] == '"': name = name[:-1]
                    name = _decode_MUTF7(name)
                    da.append(name)
        return da

    def uid2id(self, uid):
        "uid に対応する id を入手する"
        rc, res = self.imap.uid('FETCH', uid, '(FLAGS)')
        if rc == 'OK' and res[0]:
            rt = res[0]
            return int(rt[0: rt.find(' ')])
        return None

    def __flag(self, msgset, cmd, flags, with_silent=True):
        ft = type(flags)
        if ft == list or ft == tuple or ft == set:
            flags = ' '.join(flags)

        rc, res = self.imap.store(msgset, cmd, flags)
        if not rc == 'OK' or with_silent: return None

        rc = []
        for rt in res:
            mid = int(rt[0:rt.find(' ')])
            flags = imaplib.ParseFlags(rt)
            rc.append((mid, flags))
        #print (rc)

    def add_flag(self, msgset, flags, with_silent=False):
        """メッセージにフラグを追加する"""
        if not self.imap: raise IOError(self.not_connected)
        cmd = '+FLAGS.SILENT' if with_silent else '+FLAGS'
        return self.__flag(msgset, cmd, flags, with_silent)

    def del_flag(self, msgset, flags, with_silent=False):
        """メッセージからフラグを除去する"""
        if not self.imap: raise IOError(self.not_connected)
        cmd = '-FLAGS.SILENT' if with_silent else '-FLAGS'
        return self.__flag(msgset, cmd, flags, with_silent)

    def expunge(self):
        """削除マークがついたメッセージを削除する"""
        if not self.imap: raise IOError(self.not_connected)

        rc, res = self.imap.expunge()
        if cli.verbose: cli.puts(rc, res)

        if rc == 'OK':
            # メッセージ数の修正
            rd = self.status(self.cur, '(MESSAGES)')
            self.msgCount = int(rd['MESSAGES'])

        return rc == 'OK'

    def noop(self):
        "サーバとの接続が生きているか確認する"
        if not self.imap: raise IOError(self.not_connected)
        rc, tt = self.imap.noop()
        if cli.verbose: log.debug('noop: %s: %s', rc, tt[0])

    def copy_message(self, folder_name, msgset, with_delete=False):
        """ メッセージを複製/移動する
削除はマークするに留める
"""
        if not self.imap: raise IOError(self.not_connected)
        fn = _encode_MUTF7(folder_name)

        def copy_or_move(self,mid,fn,flag):
            rc, res = self.imap.copy(mid, fn)
            if cli.verbose: log.debug('copy: %s %s: %s', mid, rc, res[0])
            if rc != 'OK': return False
            if flag:
                rc, rec = self.imap.store(mid, '+FLAGS.SILENT', DELETED)
                if cli.verbose: log.debug('store-delete: %s: %s', rc, res[0])
                if rc != 'OK': return False

            uid = self.id2uid(mid)
            self.lastUID = uid
            return True

        mt = type(msgset)
        if mt == list or mt == tuple or mt == set:
            ct = 0
            for mid in msgset:
                if not copy_or_move(self, mid, fn, with_delete): return ct
                ct += 1
            return ct
        else:
            return 1 if copy_or_move(self, msgset, fn, with_delete) else 0

    def subscribe(self, folder_name=None):
        "購読するフォルダを設定する"
        if not self.imap: raise IOError(self.not_connected)
        if not folder_name:
            """ フォルダ名を与えない場合は、未購読フォルダの一覧を入手して返却する
        """
            rc, lst = self.imap.list()
            if rc != 'OK':
                log.debug('cat not get folder list')
                return

            fns = self.__list_folder(lst)
            #if cli.verbose: log.debug('all-folder: %d folder.', len(fns), fns)

            rc, lst = self.imap.lsub()
            if rc != 'OK':
                log.debug('cat not get subscribed folder list')
                return []
            subs = set(self.__list_folder(lst))
            unsub = [ fn for fn in fns if fn not in subs ]
            unsub.sort()
            return unsub

        fn = _encode_MUTF7(folder_name)
        rc, tt = self.imap.subscribe(fn)
        if cli.verbose: log.debug('subscribe: %s: %s', rc, tt[0])
        return rc == 'OK'

    def unsubscribe(self, folder_name=None):
        "購読するフォルダを解除する"
        if not self.imap: raise IOError(self.not_connected)

        if not folder_name:
            """ フォルダ名を与えない場合は、購読済フォルダの一覧を入手して表示する"""
            rc, lst = self.imap.lsub()
            if rc != 'OK':
                log.debug('cat not get subscribed folder list')
                return []
            fns = self.__list_folder(lst)
            fns.sort()
            if cli.verbose:
                log.debug('subscribed %d folder: %s',len(fns), fns)
            return fns

        fn = _encode_MUTF7(folder_name)
        rc, tt = self.imap.unsubscribe(fn)
        if cli.verbose: log.debug('unsubscribe: %s: %s', rc, tt[0])
        return rc == 'OK'

    def create_folder(self, folder_name):
        "フォルダを作成する"
        if not self.imap: raise IOError(self.not_connected)
        if not folder_name: raise Exception('empty folder name')
        if cli.verbose: log.debug('create folder %s ..', folder_name)
        fn = _encode_MUTF7(folder_name)
        rc, tt = self.imap.create(fn)
        if cli.verbose: log.debug('create: %s: %s', rc, tt[0])
        return rc == 'OK'

    def drop_folder(self, folder_name):
        "フォルダを削除する"
        if not self.imap: raise IOError(self.not_connected)
        if not folder_name: raise Exception('empty folder name')
        if cli.verbose: log.debug('drop folder %s ..', folder_name)
        fn = _encode_MUTF7(folder_name)
        rc, tt = self.imap.delete(fn)
        if cli.verbose: log.debug('drop: %s: %s',rc, tt[0])
        return rc == 'OK'

    def rename_folder(self, old_name, new_name):
        "フォルダの名称を変更する"
        if not self.imap: raise IOError(self.not_connected)
        if cli.verbose: log.debug('rename folder %s to %s ..', old_name, new_name)
        if not old_name: raise Exception('empty old folder name')
        ofn = _encode_MUTF7(old_name)
        if not new_name: raise Exception('empty new folder name')
        nfn = _encode_MUTF7(new_name)
        rc, tt = self.imap.rename(ofn,nfn)
        if cli.verbose: log.debug('rename: %s: %s',rc, tt[0])
        return rc == 'OK'

    def status(self, folder_name=None, request='(MESSAGES RECENT UIDNEXT UIDVALIDITY UNSEEN)'):
        if not self.imap: raise IOError(self.not_connected)
        if not folder_name: folder_name = self.cur # 前回選択されているフォルダ
        if not folder_name: folder_name = 'INBOX'
        if cli.verbose: log.debug('status folder %s ..',folder_name)
        fn = _encode_MUTF7(folder_name)
        rc, tt = self.imap.status(fn, request)
        if cli.verbose: log.debug('status: %s: %s', rc, tt[0])
        if rc == 'OK':
            mr = STATUS_PATTERN.match(tt[0])
            if not mr: raise IOError('invalid format: imap status: %s' % tt[0])
            fn, text = mr.groups()
            lt = text.split()
            res = dict(zip(lt[0::2], [nn for nn in lt[1::2]]))
            res['folder'] = _decode_MUTF7(fn)
            return res

        return None

    def select(self, folder_name=None, readonly=False):
        "注目フォルダを変更する"
        if not self.imap: raise IOError(self.not_connected)
        if not folder_name: folder_name = 'INBOX'
        if cli.verbose: log.debug('select folder %s',folder_name)
        fn = _encode_MUTF7(folder_name)
        rc, tt = self.imap.select(fn, readonly)
        if cli.verbose: log.debug('select: %s: %s',rc, tt[0])

        if rc == 'OK':
            self.cur = folder_name
            self.msgCount = int(tt[0])

        return rc == 'OK'

    def get_selected_folder(self):
        if not self.imap: raise IOError(self.not_connected)
        return self.cur
    
    def get_message_count(self):
        if not self.imap: raise IOError(self.not_connected)
        return self.msgCount

    def recent(self):
        if not self.imap: raise IOError(self.not_connected)
        rc, tt = self.imap.recent()
        log.debug('recent: %s: %s',rc, tt)
        return rc == 'OK'

    def _fetch(self, emessage_set, message_parts):
        rc, res = self.imap.fetch(emessage_set, message_parts)
        if not rc == 'OK': return None
        return res

    def fetch_header(self, mid):
        "ヘッダ情報を取得する"
        if not self.imap: raise IOError(self.not_connected)

        parts = '(UID FLAGS INTERNALDATE RFC822.HEADER)'
        rc, res = self.imap.fetch(mid, parts)
        if not rc == 'OK':
            raise IOError('unkown fetch response(%s)' % res)

        msgs = []
        rlen = len(res)
        #print mid, 'rlen:', rlen

        ct = 0
        ect = 0
        mid = 0
        while ct + 2 <= rlen:
            try:
                #print res[ct:ct+2]
                ((res1, rawhead), ep) = res[ct:ct+2]

                emsg = EMessage()
                mid = res1.split()[0]
                emsg.id = int(mid)
                emsg.received = imaplib.Internaldate2tuple(res1)

                flags = imaplib.ParseFlags(res1)
                emsg.flags = flag_text(flags)

                mr = UID_PATTERN.search(res1)
                if not mr: raise IOError('no uid response(%s)' % res1)
                emsg.uid = int(mr.group(1))

                mr = SIZE_PATTERN.search(res1)
                emsg.size = int(mr.group(1)) if mr else None

                #print res1, ep
                #print 'uid', uid, 'received', received
                emsg.parse(rawhead,headersonly=True)

                msgs.append(emsg)
            except Exception as e:
                ect += 1
                if log:
                    if ect == 1:
                        log.exception('parse: %s: %s' , mid, e)
                    else:
                        log.warn('parse: %s: %s', mid, e)
                else:
                    log.debug('WARN: parse: %s: %s' , mid, e)
            finally:
                ct += 2

        return msgs

    def fetch_source(self, mid):
        if not self.imap: raise IOError(self.not_connected)

        parts = '(UID INTERNALDATE RFC822.HEADER BODY.PEEK[TEXT])'
        rc, res = self.imap.fetch(mid, parts)
        if not rc == 'OK':
            raise IOError('unkown fetch response(%s)' % res)

        #print rc, res
        if False:
            xres = list(res)
            for xr in res:
                t = type(xr)
                if t == tuple:
                    trace (t, '(',xr[0],'.. %d' % len(xr),')')
                else:
                    trace (t, xr)

        rlen = len(res)
        msgs = []
        ct = 0
        mid = 0
        while ct + 3 <= rlen:
            ((res1, rawhead), (res2, rawtext), ep) = res[ct:ct+3]

            mid = int(res1.split()[0])
            received = imaplib.Internaldate2tuple(res1)

            mr = UID_PATTERN.search(res1)
            if not mr: raise IOError('no uid response(%s)' % res1)
            uid = int(mr.group(1))

            #print rc, res1, res2, ep
            #print 'uid', uid, 'received', received

            msgs.append((rawhead, rawtext, received, uid, mid))
            ct += 3

        return msgs

    def fetch_message(self, mid):
        """メッセージを取得する"""
        if not self.imap: raise IOError(self.not_connected)

        parts = '(UID INTERNALDATE RFC822.HEADER BODY.PEEK[TEXT])'
        rc, res = self.imap.fetch(mid, parts)
        if not rc == 'OK':
            raise IOError('unkown fetch response(%s)' % res)

        msgs = []
        rlen = len(res)
        #print mid, 'rlen:', rlen

        ct = 0
        mid = 0
        while ct + 3 <= rlen:
            ((res1, rawhead), (res2, rawtext), ep) = res[ct:ct+3]

            emsg = EMessage()
            mid = res1[0:res1.find(' ')]
            emsg.id = int(mid)
            emsg.received = imaplib.Internaldate2tuple(res1)

            mr = UID_PATTERN.search(res1)
            if not mr:
                raise IOError('no uid response(%s)' % res1)
            emsg.uid = int(mr.group(1))

            mr = SIZE_PATTERN.search(res1)
            emsg.size = int(mr.group(1)) if mr else None

            #print res1, ep
            #print 'uid', uid, 'received', received
            m = emsg.parse('%s%s' % (rawhead, rawtext))
            msgs.append(emsg)
            ct += 3

        return msgs

    def export_message(self, exp, msgset, name=None, with_delete=False):
        """ 選択フォルダのメッセージを外部に複製/移動する
削除はマークするに留める
"""
        if not self.imap: raise IOError(self.not_connected)

        def export_and_remove(mid, exp, flag):
            parts = '(UID INTERNALDATE RFC822.HEADER BODY.PEEK[TEXT])'

            rc, res = self.imap.fetch(mid, parts)
            if not rc == 'OK': raise IOError('unkown fetch response(%s)' % res)

            ((res1, rawhead), (res2, rawtext), ep) = res

            received = imaplib.Internaldate2tuple(res1)
            mu = UID_PATTERN.search(res1)
            if not mu: raise IOError('no uid response(%s)' % res1)
            uid = int(mu.group(1))

            #print rc, res1, res2, ep
            #print 'uid', uid, 'received', received

            exp.write_message('%s%s' % (rawhead, rawtext), received, uid)

            if rc != 'OK': return False

            self.lastUID = uid
            
            if flag:
                rc, rec = self.imap.store(mid, '+FLAGS.SILENT', DELETED)
                if cli.verbose: log.debug('store-delete: %s: %s', rc, res[0])
                if rc != 'OK': return False
            return True

        try:
            exp.begin_export(name)

            mt = type(msgset)
            if mt == list or mt == tuple or mt == set:
                ct = 0
                for mid in msgset:
                    if not export_and_remove(mid, exp, with_delete): return ct
                    ct += 1
                return ct
            else:
                return 1 if export_and_remove(msgset, exp, with_delete) else 0

        finally: exp.end_export()

    def id2uid(self, mid):
        rc, res = self.imap.fetch(mid, '(UID)')
        if rc == 'OK':
            mr = UID_PATTERN.search(res[0])
            return int(mr.group(1)) if mr else None
        return None

    def find_next_id(self,uid):
        """uidを超える、次のuidに対応するidを探す"""
        uid = int(uid)
        mid = self.uid2id(uid)
        if mid: return mid + 1

        mct = self.get_message_count()
        if not mct: return 1

        nuid = self.id2uid(1)
        # 先頭が既に前回の処理IDより大きい
        if not nuid or nuid > uid: return 1
        
        nuid = self.id2uid(mct)
        # 末尾が既に前回の処理IDより大きい
        if nuid > uid: return mct

        # 末尾から走査するべたな実装
        last = mct
        
        while nuid > uid:
            mct -= 1
            if mct == 1: return 1
            nuid = self.id2uid(mct)
            if nuid <= uid: return last
            last = mct
            
        return 1

    def sync_message(self, dst, pref, box=None, exporter=None, srcPrefix=''):
        """ メッセージを差分転送する
選択フォルダに含まれる全メッセージを、指定するフォルダ dst に転送する。
どこまで転送したか記録し、2回目以後は、その続きを転送する。

exporter を指定すれば、ソースを入手して転送する
"""

        if not self.imap: raise IOError(self.not_connected)
        if not self.cur: raise IOError('folder not slected.')

        src = srcPrefix + self.cur

        rd = self.status(self.cur, '(UIDVALIDITY)')
        uidvalidity = rd['UIDVALIDITY']
        lastUV = pref.value('%s.uidvalidity' % src, None, box)
        lastUID = pref.value('%s.sync.%s.uid' % (dst, src), None, box)

        # 転送を開始するIDを決める
        start_mid = 1
        if uidvalidity == lastUV and lastUID:
            mid = self.find_next_id(lastUID)
            if mid: start_mid = mid

        if cli.verbose: cli.trace('lastUV:',lastUV, 'lastUID:',lastUID, 'UV:', uidvalidity)
            
        end_mid = self.get_message_count()

        if start_mid >= end_mid:
            if log: log.info('no need transport.')
            return 0

        estart = now()
        step = 10
        rct = 0
        self.lastUID = None

        try:
            log.debug('exporting.. %d to %d', start_mid, end_mid)
            
            for nn in xrange(start_mid, end_mid, step):
                msgset = range(nn, min(nn + step, end_mid))
                if exporter:
                    rc = self.export_message(exporter, msgset, dst)
                    rct += rc
                else:
                    #print 'exporting.. dst: %s: ', msgset
                    rc = self.copy_message(dst, msgset)
                    rct += rc
        finally:
            uid = self.lastUID
            if uid:
                pref.store('%s.uidvalidity' % src, uidvalidity, box)
                pref.store('%s.sync.%s.uid' % (dst, src), str(uid), box)
                pref.save()

        esec = now() - estart
        log.debug('INFO: export %d files in %.2fs (%.2f/s)' , rct, esec, float(rct)/esec )
        return rct


    not_connected = 'not connected.'

    def __init__(self):
        self.imap = None
        self.cur = None # 選択中のフォルダ
        self.eof_hook = self.disconnect

    def connect(self, host, port=None, prot='imap', user=None, password=None):
        """ 指定するホストにIMAP/IMAPS接続する
        """
        self.disconnect()

        if 'imap' == prot:
            from imaplib import IMAP4
            IMAP = IMAP4
            IMAP.port = imaplib.IMAP4_PORT
        elif 'imaps' == prot:
            from imaplib import IMAP4_SSL
            IMAP = IMAP4_SSL
            IMAP.port = imaplib.IMAP4_SSL_PORT
        else:
            raise Exception('unkown proptocl: %s' % prot)

        if not user:
            from netrc import netrc
            try:
                nc = netrc()
                user, account, password = nc.authenticators(host)
            except Exception as e:
                log.warn(e)

        if not user:
            from getpass import getuser
            user = getuser()
        if not password:
            password = ''

        if host.find(':') > 0: host, port = host.split(':')

        if cli.verbose: log.debug('try to connect %s@%s ..', user, host )
        port = int(port) if port else IMAP.port

        c = IMAP(host,port)
        c.login(user,password)

        if log:
            log.info('server: %s %s', host, c.PROTOCOL_VERSION)
        elif cli.verbose:
            log.debug('server: %s', host, c.PROTOCOL_VERSION)

        self.imap = c
        self.cur = None

        return c

    def disconnect(self):
        """ IMAP接続を解除する
        """
        if not self.imap: return
        try:
            # 現在選択されているメールボックスを閉じる
            if self.cur: self.imap.close()
        finally:
            self.cur = None
            try:
                # IMAP接続を解除する
                self.imap.logout()
                if cli.verbose: log.debug('disconnected.')
            finally:
                self.imap = None


def flag_text(flags):
    """フラグ情報をテキストで表現する"""
    flags = set(flags)
    ft = '%s%s%s%s%s%s ' % (
        'D' if DELETED in flags else '',
        'A' if ANSWERD in flags else '',
        'F' if FLAGED in flags else '',
        'S' if SEEN in flags else '',
        'T' if DRAFT in flags else '',
        'R' if RECENT in flags else '',
    )
    return ft if len(ft) > 1 else ''

if False:
    fn = u'あああ'
    puts(_encode_MUTF7(fn))
    fn = 'INBOX.あああ'
    puts(_encode_MUTF7(fn))


def _show(tt): puts(tt)

if __name__ == '__main__':

    pref = cli.INIPreference('test.ini')
    pref.load()
    sec = 'test-mbox'

    log = cli.get_logger('mbox', pref)
    log.info('start')

    cli.maildir.log = log

    host = pref.value('imap-host', 'localhost:143',sec)
    user = pref.value('imap-user', None, sec)
    passwd = pref.value('imap-passwd', user, sec)

    mbox = IMAPtool()
    pref.section = sec
    
    cli.trace(host,user,passwd,pref.section)
    c = mbox.connect(host,user=user,password=passwd)
    try:
        log.debug('connected.')
        mbox.select()
        cli.printf('%s: %s', mbox.get_selected_folder(), mbox.get_message_count())

        # 存在しないフォルダに移動
        fn = u'いいい'
        mbox.select(fn)

        fn = u'あああ'
        mbox.select(fn)

        lst = mbox.unsubscribe()
        if False:
            for fn in lst: cli.printf(fn)

        if False:
            mbox.create_folder(u'Trash')

            mbox.create_folder(u'INBOX.てすと01') and _show('OK')

            # 存在しているものをもう一度作成しようとした
            mbox.create_folder(u'INBOX.てすと01') or _show('OK')

            #　存在しないフォルダを削除しようとした
            mbox.drop_folder(u'INBOX.てすと02') or _show('OK')

            #　フォルダ名の変更（ゴミ箱以下に移動）
            mbox.rename_folder(u'INBOX.てすと01', u'Trash.てすと99') and _show('OK')

            mbox.drop_folder(u'Trash.てすと99') and _show('OK')

            lst = mbox.subscribe()
            if False:
                for fn in lst: puts(fn)

            fn='INBOX.あああ'
            mbox.create(fn) and _show('OK')
            status = mbox.status(fn)
            puts(status)

            mbox.noop()

        if False:
            mbox.select()
            # 外部フォルダに転送する
            exp = EMLExporter(basedir='work')
            # MailDirに転送する
            exp = LocalMDir()
            dst = 'aa'
            box = 'work.local-mbox'
            mbox.sync_message(dst, pref, box, exp)
            
        if True:
            mbox.select()
            dst = 'aa'
            box = 'iwao.mbox'
            mbox.sync_message(dst, pref, box)

        
        if False:
            mbox.select()
            idx = EMessageIndex(basedir='work')
            mbox.update_index(idx, 'aa')


        if False:
            mbox.select()

            status = mbox.status()
            puts(status)

            part = '(UID INTERNALDATE RFC822.HEADER BODY.PEEK[TEXT])'
            part = '(UID INTERNALDATE RFC822.SIZE FLAGS )'
            msgset = '34:36'
            #if 'MESSAGES' in status: msgset = status['MESSAGES']

            tt = mbox._fetch(msgset, part)
            puts(len(tt))
            for tn in tt:
                puts(len(tn), type(tn))
                if type(tn) == tuple:
                    mr = SIZE_PATTERN.search(tn[0])
                    if mr: puts ('size:', int(mr.group(1)))

                    for uu in tn:
                        if len(uu) > 30:
                            cli.printf ('%s ..', uu[0:30])
                        else:
                            puts (uu)
                else:
                    mr = SIZE_PATTERN.search(tn)
                    if mr: puts('size:', int(mr.group(1)))

                    received = imaplib.Internaldate2tuple(tn)
                    if received: puts ('received', time.strftime('%Y-%m-%d %H:%M:%S', received))
                    puts(tn)

    finally:
        mbox.disconnect()
        puts('done.')
        

