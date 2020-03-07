# hitk

Tkinter を利用した python のGUIアプリケーションのサンプルコードを取りまとめています。

## hitkパッケージとは

Tkinterのウィジェット組み立ての記述をパッケージに取りまとめました。
これを利用すると、ユーザコードは個々のアプリケーション固有の記述に集中することが出来ます。

macOSとWindowsの両方で動作するように注意しながら作成しています。

## サンプルコードの取り寄せ方

こちらのコードは github で作成しています。
git コマンドで次のように入手できます。

```bash
$ git clone https://github.com/IwaoWatanabe/hitk.git
```

## 開発者インストール

setup.py を用意していますので、確認しながら動作させたいなら　develop インストールしてみてください。

```bash
$ cd hitk
$ python setup.py develop --user
```

develop インストールすると、ソースコードがそのまま sys.path に配置されたかのように動作します。 --user はお好みでどうぞ。
こちらをつけるとシステムに組み込まれないで、ユーザのホームディレクトリ以下に組み込まれます。


