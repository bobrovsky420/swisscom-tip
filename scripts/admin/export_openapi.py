"""Export the API contract for the generated TypeScript SDK. No database calls."""
import json
from pathlib import Path
from swisstip.control.api import app

path = Path(__file__).resolve().parents[2] / 'apps/admin-console/openapi.json'
path.write_text(json.dumps(app.openapi(), indent=2) + '\n', encoding='utf-8')
print('Exported apps/admin-console/openapi.json')
