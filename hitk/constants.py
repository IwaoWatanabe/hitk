# Symbolic constants for Tk
import sys

if sys.version_info < (3, 0):
  from Tkconstants import *
else:
  from tkinter.constants import *
