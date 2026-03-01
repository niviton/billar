import sys
path = "/home/SEU_USUARIO/"
if path not in sys.path:
    sys.path.append(path)

from app import app as application
