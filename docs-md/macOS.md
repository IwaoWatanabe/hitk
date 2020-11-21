
## macOS での注意事項

macOSにおいてTkinter は日本語テキストの入力について少々難があります。 
OS標準でPythonが導入されていることは嬉しいのですが、
そのOS 付属のpythonでは日本語入力ができません。
閲覧や別アプリからのテキストのコピー・ペーストには問題ありません。

サードパーティ製の Tcl/Tk を導入すると、多少問題は改善するのですが、
日本語変換途中のテキストがうまく表示されない問題が残ります。
2018年11月最新のMojaveにおいても残念ながら改善されておりません。
フレームワーク提供者に修正を期待します。

## ActiveState社製の Tcl/Tk の導入（mac）

**Download And Install Tcl: ActiveTcl**  
http://www.activestate.com/activetcl/downloads

macOSの利用者は、先に示した日本語入力問題に対応するために、
上のリンクから Version 8.5.18 の Mac Disk Image （dmgファイル）を入手しください。
その中に含まれる Active-Tcl-8.5.pkg を導入してください。

pkg ファイオルをファインダーで開いて、そのまま指示に従って操作すれば
 Tkinter で日本語入力が行えるようになります。
