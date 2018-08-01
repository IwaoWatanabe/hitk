import sys
from hitk import hello, memo01

Apps = [
    hello.HelloApp,
    memo01.MemoApp,
]

args = list(sys.argv)
args.pop(0)

num = int(args[0]) if args else 0

Apps[num].run(args)



