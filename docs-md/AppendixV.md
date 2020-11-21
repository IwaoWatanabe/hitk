
## Appendix V git コマンドの入手と基本操作

サンプルコードを入手するためのgitコマンドですが、OSには標準状態では含まれていません。
こちらで簡単な導入手順を示します。

### macOS (Sierra , High Sierra ,  Mojava) にgit を導入
Homebrewを導入すれば利用できるようになります。
Homebrew はMacOSで利用出来るパッケージ管理ツールの一つです。
Homebrew においては、導入するアプリケーションはフォーミュラと呼ばれます。
brew自体が git を利用してフォーミュラを管理しているのです。

最新の導入手順は配布元に記載されています。サイトを参照してください。  
https://brew.sh/index_ja.html

### Linux (CentOS/Ubuntu/OpenSuSE)にgit を導入
標準インストールでは含まれていなくても、パッケージ追加で利用できるようになります。

```shell script
yum install git     # CentOS/RedHat

apt-get install git  # Ubuntu

zypper install git # OpenSuSE
```

古い OpenSuSE では
```shell script
zypper install git-core
```
とする必要がありました。

### Windows にgit を導入
いくつか種類がありますが、コマンドライン操作なら git for Windows がお勧めです。

https://gitforwindows.org/  
こちらからインストーラを入手して実行します。

いろいろ尋ねられるけど、単にコードを入手するだけに利用するなら 
全部[NEXT>]を選択しても問題はありません。

コンソールの設定「Configuration the terminal emulator to use with Git Bash」の
選択のところで、「Use Min TTY」というのを選べば、
unix の bashが利用できる画面が導入できます。

Unixのシェルが好みの人はそちらを選択すればよいでしょう。
その場合は「スタート」「全てのプログラム」「Git」「Git bash」を選択して起動して操作します。

PATH  が通っていれば通常のコマンドラインからでも利用できます。

### ユーザ情報を登録する(git config)
コード修正をコミットするつもりなら、git導入後にユーザ情報
（名前と連絡先メールアドレス）を設定する必要があります。

コードを入手して眺めるだけならその必要はありません。

```shell script
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

設定の確認は

```shell script
git config -l
```

### サンプルコードを入手(git clone)
gitコマンドでソースコード一式を入手するには、通常は git clone を行います。

```shell script
git clone  <サンプルコードの入手元のURL>  [出力フォルダ]
```

出力フォルダは省略できて、その場合はURLの末尾が自動的に採用されます。

### 最新のコードを入手(git pull)
clone してきたフォルダに移動して pull すると、
配布元で修正があったファイルが最新の状態に置き換わります。

```shell script
git pull
```

ただし手元でコードを修正していたらこの操作は失敗します。
その場合は、編集済みのコードを戻してから もう一度 pull する必用があります。

### 編集済みコードの確認(git status)
pull に失敗したら、どのファイルを編集してしまったか確認する必要があります。
status を使います。

```shell script
git status
```

### 編集済みコードを戻す(git chekout)
編集してしまったファイルを戻すにはファイル名を指定して checkout します。
先の status で modified: として表示されたファイル名を checkout の後に指定します。
ファイル名は複数指定することができます。

```shell script
git checkout <編集したファイル名> ..
```
