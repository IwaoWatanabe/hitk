## Appendix I Pythonの導入

本稿の内容を試すには、前提として
プログラミング言語Pythonが利用できる状況にもっていく必要があります。

macOSやLinuxではシステムに標準で組み込まれていたりしますが、
新しいバージョンを試したい場合は別途入手して組み込む必要があります。

こちらで紹介するのは 2019年4月現在の 下記に示すそれぞれのプラットフォームにおいて
python を導入するための簡易手順になります。

- macOS (Sierra , High Sierra ,  Mojava)
- Linux (CentOS6 , CentOS7)
- Linux (Ubuntu)
- Linux (OpenSuSE)
- Windows XP/7/10 (コミュニティー版)
- Windows 7/10 (Anaconda)

### macOS(OS標準もしくは brew)

Sirra , High Sierra ,  Mojava であれば特別なことをしなくても
python2.7.x が標準で利用できます。
ただしTkによる日本語入力については問題があるため、
サードパーティのライブラリの導入を検討ください。

この問題は python 3.x でも同様です。　→ 参考：macOS での注意事項

brew を利用して　python を導入している場合は、注意が必要です。
brew python すると2019年4月現在は　python コマンドが
python 3 に置き換わってしまいます。（システム標準では python コマンドは python 2）

## Linux(OpenSuSE)
Leap15であれば、python 2.7.x と python3.6.x が標準で
システムに組み込まれています。
しかしながら標準インストール状態ではTkinter が含まれないようです。

root ユーザで zypper コマンドでパッケージを追加インストールすることにより
利用できるようになります。

```shell script
zypper install python-tk python-idle 
zypper install python3-tk python3-idle 
```

## Windows XP/7/10 コミュニティー版
次のサイトから、Pythonコミュニティー版がダウンロードできます。

**Python Releases for Windows**  
https://www.python.org/downloads/windows/

こちらのサイトにアクセスして、Stable Releases 以下に記載されている
インストーラーをダウンロードします。

2.7.x  では MSI installer を選択すると操作が簡単です。  
3.x  では executable installer  を選択すると操作が簡単です。

「Windows x86」と名前が付いているものは 32ビット版です。  
「Windows x86-64」と名前が付いているものは 64ビット版になります。

メモリが４G以上搭載されていない環境で利用する場合は、
64ビット版を選択してもほとんど意味をなさないので、32ビット版の選択するとよいでしょう。

インストーラを起動すると、ウィザードの指示に従うだけで導入が完了します。
2.7 と 3.x の両方を導入すると、py コマンドが利用できるようになります。

pyコマンドは python コマンドの切り替えができるようなもので、
-2 オプションを指定すると python 2.x が動作して、
-3  オプションを指定すると python 3.x が動作してくるようになります。

## Windows 7/10 (Anaconda)
Continuum Analytics 社が提供している conda というパッケージマネージャーを含む
Python ディストリビューションです。
データサイエンティストたちは、こちらのPythonを好んで使っているようです。

**Anaconda for Windows Installer**  
https://www.anaconda.com/distribution/


