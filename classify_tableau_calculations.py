import json
import re
from pathlib import Path

DATA_DIR = Path("data")

INPUT_SCHEMA = DATA_DIR / "parsed_tableau_schema.json"
OUTPUT_FILE = DATA_DIR / "calculation_classification.json"
print("CLASSIFYING TABLEAU CALCULATIONS")

with open(INPUT_SCHEMA, encoding="utf-8") as f:
    datasources= json.load(f)

classified = []

def classify_formula(formula: str):
    f = formula.lower()
    #Tableau specific constructs
    if "fixed" in f or "include" in f or "exclude" in f:
        return "lod_expression", "requires semantic rewrite"

    if "lookup" in f or "window_" in f:
        return "table_calculation", "not directly supported in DAX"

    if "parameter" in f:
        return "parameter_driven", "requires model redesign"

    if re.search(r"\b(sum|avg|min|max|count)\b", f):
        return "simple_aggregation", "directly convertible"

    return "unknown", "manual review required"

for ds in datasources:
    for calc in ds.get("calculations", []):
        formula = calc.get("formula", "")
        calc_type, note = classify_formula(formula)

        classified.append({
            "calculation_name": calc["field_name"],
            "formula": formula,
            "classification": calc_type,
            "note": note
        })
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(classified, f, indent=4)
print(f"Classification complete - results saved to {OUTPUT_FILE}")