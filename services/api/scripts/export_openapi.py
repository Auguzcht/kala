"""Write the OpenAPI schema to openapi.json for the frontend type generator.
Run from services/api:  python scripts/export_openapi.py
Then in apps/web:        pnpm gen:api"""
import json
import pathlib
import sys

# ensure the services/api directory (which contains the `app` package) is importable
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

out = pathlib.Path(__file__).resolve().parents[1] / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2))
print(f"wrote {out}")
