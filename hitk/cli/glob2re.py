# -*- coding: utf-8 -*-

# Python glob but against a list of strings rather than the filesystem
# http://stackoverflow.com/questions/27726545/python-glob-but-against-a-list-of-strings-rather-than-the-filesystem

import re, os


def glob2re(pattern, ignore_case=False):
    """Translate a shell PATTERN to a regular expression.
    There is no way to quote meta-characters.
    """
    flags = re.IGNORECASE if ignore_case else 0
    i, n = 0, len(pattern)
    res = []
    while i < n:
        c = pattern[i]
        i += 1
        if c == '*':
            #res = res + '.*'
            res.append('[^/]*')
        elif c == '?':
            #res = res + '.'
            res.append('[^/]')
        elif c == '[':
            j = i
            if j < n and pattern[j] == '!':
                j += 1
            if j < n and pattern[j] == ']':
                j += 1
            while j < n and pattern[j] != ']':
                j += 1
            if j >= n:
                res.append('\\[')
            else:
                stuff = pattern[i:j].replace('\\', '\\\\')
                i = j + 1
                if stuff[0] == '!':
                    stuff = '^' + stuff[1:]
                elif stuff[0] == '^':
                    stuff = '\\' + stuff
                res.append('[%s]' % (stuff,))
        else:
            res.append(re.escape(c))
    res.append('\Z(?ms)')
    return re.compile(''.join(res), flags)


def find(path, pattern="", dir_type=False):
    """ファイル・システムから指定するglobパターンに合致するファイル名を抽出する"""
    pt = type(pattern)
    if pt == list or pt == tuple:
        pat = [re.compile(glob2re(pp)) for pp in pattern]
        if len(pat) == 1: pat = pat[0]
    elif not pattern:
        pat = "*"
    else:
        pat = re.compile(glob2re(pattern))

    #print >>sys.stderr, [ pt.pattern for pt in pat ]

    if "*" == pat:
        def match(tt): return True
    
    elif type(pat) == list:
        def match(tt):
            for mt in pat:
                if mt.match(tt): return True
            return False
    else:
        def match(tt): return pat.match(tt)

    if dir_type:
        for (root, dirs, files) in os.walk(path):
            for fn in dirs:
                if match(fn): yield (fn, root)
    else:
        for (root, dirs, files) in os.walk(path):
            for fn in files:
                if match(fn): yield (fn, root)


if __name__ == '__main__':
    path = os.path.abspath(os.getcwd())

    for fn, folder in find(path, ('t*.py', '*.pyc')):
        print(os.path.join(folder, fn))

    print()
    print('-- dirs')

    # ディレクトリのみの探索（幅優先）

    for fn, base in find(path, dir_type=True):
        print(os.path.join(base, fn))
