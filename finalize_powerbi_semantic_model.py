import json
from pathlib import Path

print("FINALIZING POWER BI SEMANTIC MODEL")

DATA_DIR = Path("data")

CANONICAL_MODEL_FILE = DATA_DIR / "canonical_powerbi_model.json"
CONVERTED_MEASURES_FILE = DATA_DIR / "converted_dax_measures.json"
SEMANTIC_CONTEXT_FILE = DATA_DIR / "semantic_model_with_context.json"
OUTPUT_FILE = DATA_DIR / "final_powerbi_semantic_model.json"

# -------------------------------------------------------------------
# 1. LOAD CANONICAL MODEL
# -------------------------------------------------------------------
with open(CANONICAL_MODEL_FILE, encoding="utf-8") as f:
    model = json.load(f)

print("Loaded canonical_powerbi_model.json")

# -------------------------------------------------------------------
# 2. LOAD CONTEXT-AWARE SEMANTIC MODEL (TABLE OWNERSHIP)
# -------------------------------------------------------------------
with open(SEMANTIC_CONTEXT_FILE, encoding="utf-8") as f:
    context_model = json.load(f)

if "measure_table_map" not in context_model:
    raise KeyError("measure_table_map missing from semantic_model_with_context.json")

model["measure_table_map"] = context_model["measure_table_map"]

print(f"Loaded measure_table_map ({len(model['measure_table_map'])} entries)")

# -------------------------------------------------------------------
# 3. LOAD CONVERTED MEASURES
# -------------------------------------------------------------------
with open(CONVERTED_MEASURES_FILE, encoding="utf-8") as f:
    conversion = json.load(f)

converted_measures = conversion.get("converted_measures", {})
skipped_measures = conversion.get("skipped_measures", [])

print(f"Converted measures: {len(converted_measures)}")
print(f"Skipped measures: {len(skipped_measures)}")

# -------------------------------------------------------------------
# 4. ATTACH MEASURES TO FINAL MODEL
# -------------------------------------------------------------------
model["measures"] = converted_measures

# Attach explicit conversion report (audit-safe)
model["conversion_report"] = {
    "converted_count": len(converted_measures),
    "skipped_count": len(skipped_measures),
    "skipped_measures": skipped_measures,
}

# -------------------------------------------------------------------
# 5. SAVE FINAL SEMANTIC MODEL
# -------------------------------------------------------------------
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(model, f, indent=4)

print("\nFinal Power BI semantic model written to:")
print(f" → {OUTPUT_FILE}")
