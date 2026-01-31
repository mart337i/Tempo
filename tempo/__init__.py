import sys
import os
from pkgutil import extend_path
from pathlib import Path

# NOTE: 
# This makes it posible to do `from tempo import x` instead of haveing to do the abselute path.
# This is also called a namespace package.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
__path__ = extend_path(__path__, __name__)

VERSION = "0.1.0"

from . import cli