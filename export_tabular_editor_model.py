import json
from pathlib import Path

DATA_DIR = Path("data")

INPUT_TOM = DATA_DIR / "powerbi_tom_model.json"
OUTPUT_MODEL = DATA_DIR / "Model.json"

with open(INPUT_TOM, encoding="utf-8") as f:
    tom = json.load(f)

# Wrap into Tabular Editor–compatible structure
model_json = {
    "model": tom["model"]
}

with open(OUTPUT_MODEL, "w", encoding="utf-8") as f:
    json.dump(model_json, f, indent=2)

print("Model.json generated in Tabular Editor format")
