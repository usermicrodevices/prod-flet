import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("flet_core").setLevel(logging.INFO)

LN = logging.NOTSET
LD = logging.DEBUG
LI = logging.INFO
LW = logging.WARNING
LE = logging.ERROR
LC = logging.CRITICAL
LICONS = {LN:'ℹ', LD:'🇩', LI:'ℹ️', LW:'⚠', LE:'🆘', LC:'👾'}
