[![Build Status](https://travis-ci.org/andycasey/smhr.svg?branch=master)](https://travis-ci.org/andycasey/smhr)

Spectroscopy Made Harder
------------------------
Gotta pay back that tech debt.


Authors
-------
 - Andrew R. Casey (Monash)
 - Alex Ji (Carnegie Observatories)

VERSION NOTE:
- v0.1 is the current stable version. Things are working and it is being used for papers.
- v0.2 is the active development version.

If you are new to SMH, you should use v0.2, because the underlying data format has changed significantly.
Files are not backwards compatible, but there is a script to convert old save files into new save files.

Installation
------------
This is one way that I (Alex) got things running from a fresh mac install and I'm putting it here as a record of some things I had to do.
Default anaconda does not officially support pyside, but I think conda-forge does. We may switch to that, or a different version of PySide, in the future. For now, this works...

- Download full anaconda with python 2.7
- `conda install pyside`: this will install pyside v1.1.1
- Go to `~/anaconda/lib` and make a new symlink for `libpyside-python2.7.1.1.dylib` from one that looks almost the same (e.g. `libpyside-python2.7.1.1.1.dylib`
- Do the same thing for `libshiboken` when you see the error message.
- install qt4:
```
brew tap cartr/qt4
brew tap-pin cartr/qt4
brew install qt@4
```
- `conda install qt=4.8.7` (you may have to uninstall and downgrade some things for this to work; it should be safe to upgrade those later)
- Clone smhr
- Go into the smhr directory and `python setup.py develop`
- Go to `smhr/smh/gui` and open with `ipython __main__.py`
- If you have problems with `qt_menu.nib`, use `~/anaconda/bin/python.app __main__.py` instead of ipython. (I have fixed this on my laptop by copying it somewhere but I cannot find where.)
- There are some problems with segfaults that we are working out.
