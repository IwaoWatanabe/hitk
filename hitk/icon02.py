# -*- coding: utf-8 -*-
# このスクリプトは macOSのAPIを利用しているため、macOSでのみ動作します。

import sys, os, cStringIO
from AppKit import NSImage, NSWorkspace
from PIL import Image, ImageTk
from hitk import tk



if __name__ == "__main__":
  tkimg = None
  img = None
  
  if len(sys.argv) > 1:
    nsi = NSImage.alloc().initWithContentsOfFile_(sys.argv[1])

    nssize = nsi.size()
    wi, he = int(nssize.width), int(nssize.height)
    data = nsi.TIFFRepresentation()
    ##img = Image.frombytes('RGB', (wi, he), data)
    img = Image.open(cStringIO.StringIO(data))

  can = tk.Canvas(width=1000,height=800).pack()

  if img:
    tkimg = ImageTk.PhotoImage(img)


ws = NSWorkspace.sharedWorkspace()
sfxs = {}
him = 0

def get_icon(path, size='small', multi=False, limit=100, hold_image=False):
    if size == 'small': limit = 16
    fp, sfx = os.path.splitext(path)
    if not multi and sfx in sfxs: return sfxs[sfx]

    global him
    nsi = ws.iconForFile_(os.path.abspath(path))
    phs = set()
    for rp in nsi.representations():
      hi = rp.pixelsHigh()
      if hi >= 64 or hi in phs:
        nsi.removeRepresentation_(rp)
        continue
      if him < hi: him = hi
      phs.add(hi)

    #print 'him', him
    #nssize = nsi.size()
    #wi, he = int(nssize.width), int(nssize.height)
    data = nsi.TIFFRepresentation()
    img = Image.open(cStringIO.StringIO(data))

    icons = []
    for fi in range(img.n_frames):
      img.seek(fi)
      #print fi, img.width, img.height
      if img.height > limit: continue
      
      ti = ImageTk.PhotoImage(img)
      ti.image = img if hold_image else None
      sfxs[sfx] = ti
      sfxs['%s-%s' %(sfx,fi)] = ti
      if not multi: return ti
      icons.append(ti)
      
    return icons

if __name__ == "__main__":
  cx = cy = 100
  dn = '.'
  him = 0

  for fn in os.listdir(dn):
    path = os.path.abspath(os.path.join(dn, fn))
    fp, sfx = os.path.splitext(path)
    if sfx in sfxs: continue
    print path
    
    for ti in get_icons(path, multi=True):
      
      cimg = can.create_image(cx, cy, image=ti)
      print cx, cy, ti.width(), ti.height(), cimg, sfx
      cx += (him + 10)
      if cx + him > 1000: cy += (him + 10); cx = 100

  if tkimg:
    can.create_image(cx, cy, image=tkimg)

  can.mainloop()

