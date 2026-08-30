from __future__ import annotations

import json
import sys

payload = json.load(sys.stdin)
action = payload.get("action")
if action == "compile":
    emitted = "import taichi as ti\n@ti.kernel\ndef run():\n    pass\n"
    result = {
        "ok": True,
        "result_kind": "compile",
        "mode": "mechanics",
        "generated_source": emitted,
        "emitted_source": emitted,
        "element_ir_summary": {
            "element_type": "hex8",
            "dim": 3,
            "n_nodes": 8,
            "n_quadrature_points": 8,
            "formulation": "total_lagrangian",
        },
        "content_hash": "b" * 64,
        "derived_energy_present": False,
    }
elif action == "transpile":
    code = "def pcg():\n    pass\n"
    result = {
        "ok": True,
        "result_kind": "transpile",
        "mode": "algorithm",
        "generated_source": code,
        "code": code,
        "entry_point": "pcg",
        "line_count": 2,
        "valid_python": True,
        "backend": "taichi",
    }
elif action == "capabilities":
    result = {
        "ok": True,
        "capabilities": {
            "version": "0.2.0",
            "profiles": ["mvp"],
            "backends": ["taichi"],
            "actions": ["emit", "transpile", "verify"],
        },
        "packages": {"mechdsl-core": "0.2.0", "algo2code": "0.2.0"},
    }
elif action == "models":
    result = {"ok": True, "models": [{"name": "svk"}]}
else:
    result = {"ok": False, "diagnostic": {"message": "bad action"}}
json.dump(result, sys.stdout)
