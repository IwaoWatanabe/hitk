
## 自分アプリ用パケージmyappの作成

GUIアプリケーションを作成するにあたっては、モジュールが単一で済むことは稀です。
そこで自分アプリ用のパッケージをあらかじめ作成しておくことをお勧めします。

ここからは便宜上 myapp パッケージとして説明していきますが、
自分向けのパッケージに読み替えて作業してみてください。
もちろん myapp そのまま利用してもらっても構いません。

パッケージを作成するには　作業用のフォルダの作成から始めます。

macOSやLinux ではターミナルを開いて次のようにタイプしてみます。

```shell script
$ cd
$ mkdir -p myapp-0.1/myapp
$ touch myapp-0.1/myapp/__init__.py
$ echo  'print("hello")' >> myapp-0.1/myapp/__main__.py
```

これで、myapp パッケージが作成できています。
試しにこれを実際に動作させてみましょう。

```shell script
$ cd myapp-0.1/
$ python -m myapp
hello
$
```

パッケージを指定して動作させるには python コマンドに -m オプションとパッケージ名を指定します。
これで パッケージ名/__main__.py が動作し始めます。
この例では　hello　と表示されれば期待した振る舞いとなります。

この __main__.py の内容はあなたのものなので、内容は好きなようにして構わないのですが、
本稿では説明の都合上、次の内容にしておいてください。


myapp/__main__.py の定義例
```python
from hitk.launcher import run
run()
```

コマンドラインから次のようにタイプするとよいでしょう。
```shell script
$ echo from hitk.launcher import run > myapp/__main__.py
$ echo "run()" >> myapp/__main__.py
```

hitk.launcer.run を利用したアプリの起動方法は後述します。

## 自分パッケージ用の setup.py の準備

開発中の自分パッケージが配置されているフォルダパスを
sys.path に組み込んでおいたほうがいろいろ便利です。
そのために次に示す myapp-setup.py を作成します。
myapp フォルダと同じ場所に配置します。


myapp-setup.py より
```python
from setuptools import setup

setup(name='myapp',
      version='0.1',
      packages=['myapp'],
     )
```

これを次のようなオプションをつけて実行します。

```shell script
$ python myapp-setup.py develop --user
```

この操作により　myapp.egg-info ディレクトリが作成され、そこにパッケージ情報が格納され、
site-packages に egg-link ファイルが作成されます。
そのリンクファイルにより sys.path にパスが加わることになります。

そのため開発中はこれらのファイルは削除しないで下さい。

この setup は最低限の定義しか含めていないので、
作成したパッケージを他人に配布するときにはもう少し内容を充実させてください。

ちなみにこのパス登録を解除するには pip uninstall を呼び出します。

```shell script
$ python -m pip uninstall myapp
```

削除の確認がありますので、それで y を選択するとリンクファイルが削除されます。

