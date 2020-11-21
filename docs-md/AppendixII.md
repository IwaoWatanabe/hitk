
## Appendix II pipの導入

### pipの入手と導入
python 3.4  からは pip はpythonに同梱されているのですが、
それ以前のバージョンではpip は後から追加導入する必要があります。

入手のためのコマンドは
```shell script
wget https://bootstrap.pypa.io/get-pip.py
```
あるいは
```shell script
curl -o get-pip.py https://bootstrap.pypa.io/get-pip.py
```

ファイルを入手したあとは、それを実行すると導入できます。

```shell script
python get-pip.py --user
```

### setuptools の入手と導入
python 3.4 の場合は、lssetuptools が含まれていないかもしれません。
こちらも同様にスクリプトを入手して実行すると導入できます。

```shell script
curl -o ez_setup.py https://bootstrap.pypa.io/ez_setup.py 

python ez_setup.py --user
```

