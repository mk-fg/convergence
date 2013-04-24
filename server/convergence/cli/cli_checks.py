#-*- coding: utf-8 -*-
from __future__ import print_function

from os.path import realpath, dirname
import sys

def prerun_checks(top_level_path):
    # Check python version
    if sys.version_info < (2, 7):
        print('Sorry, convergence requires at least Python 2.7', file=sys.stderr)
        sys.exit(3)

    # Extend sys.path, if run from the checkout tree
    try: import convergence
    except ImportError:
        pkg_cli, pkg_root = (realpath(dirname(f)) for f in [__file__, top_level_path])
        if pkg_root == pkg_cli: pkg_root = pkg_cli.rsplit('/convergence/', 1)[0]
        sys.path.insert(0, pkg_root)
