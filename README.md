# hitk

Tkinter を利用した python のGUIアプリケーションのサンプルコードを取りまとめていきます。

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


