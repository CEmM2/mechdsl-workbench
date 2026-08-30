from __future__ import annotations

import json
import sys
import time

json.load(sys.stdin)
time.sleep(2.0)
json.dump({"ok": True}, sys.stdout)
