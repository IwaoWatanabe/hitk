
## Appendix III Python拡張モジュールのビルド

### macOS
brew を利用している人なら、おそらくその過程で　X-Code を導入していると思います。
X-CodeがあればC/C++ コンパイラが利用できますので、
拡張モジュールのビルドができるようになります。

###Linux(CentOS)
開発用追加パッケージを導入すればビルドできるようになります。

```shell script
# yum groupinstall "Development tools"
# yum install gcc zlib-devel bzip2-devel \
 readline-devel sqlite-devel openssl-devel git
```

##Windows での拡張モジュールのビルド事情
Windowsの拡張モジュールは、Pythonのバージョンによって異なるコンパイラを準備する必要があります。
最新のものは商用のコンパイラを入手する必要がありますが、
少し古いものであれば Microsoft が無償版のコンパイラを提供してくれていたりします。

###Windows Python 2.7
Microsoft が提供してくれている Microsoft Visual C++ Compiler for Python 2.7 
を導入するとビルドできるようになります。

###Windows Python 3.4
Windows SDK 7.1 をインストールしましょう。

###Windows Python 3.5
Visual Studio Communitiy Edition あるいは Visual C++ Build tools
 を入手して導入します。

###Windows Python 3.6/3.7
https://www.visualstudio.com/ja/downloads より　Tools for Visual Studio 2017
　を選択してダウンロードします。

