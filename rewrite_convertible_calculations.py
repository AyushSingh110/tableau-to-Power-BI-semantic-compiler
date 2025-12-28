import json
import re
from pathlib import Path
DATA_DIR = Path("data")
CLASSIFICATION_FILE = DATA_DIR / "calculation_classification.json"
OUTPUT_FILE = DATA_DIR / "converted_dax_measures.json"

with open(CLASSIFICATION_FILE, encoding="utf-8") as f:
    calculations = json.load(f)

converted = {}
skipped = []

def rewrite_to_dax(formula: str):
   #Only for simple aggregations
    dax = formula

    # Replace Tableau aggregations with DAX equivalents
    dax = re.sub(r"\bSUM\s*\(", "SUM(", dax, flags=re.IGNORECASE)
    dax = re.sub(r"\bAVG\s*\(", "AVERAGE(", dax, flags=re.IGNORECASE)
    dax = re.sub(r"\bCOUNTD\s*\(", "DISTINCTCOUNT(", dax, flags=re.IGNORECASE)

    # Tableau date functions → DAX
    dax = dax.replace("YEAR(", "YEAR(")
    dax = dax.replace("DATEDIFF('day'", "DATEDIFF(")

    return dax

for calc in calculations:
    name = calc["calculation_name"]
    classification = calc["classification"]
    formula = calc["formula"]

    if classification == "simple_aggregation":
        converted[name] = rewrite_to_dax(formula)
    else:
        skipped.append({
            "calculation_name": name,
            "reason": calc["note"]
        })

output = {
    "converted_measures": converted,
    "skipped_measures": skipped,
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=4)

print(f"\nConverted measures written to {OUTPUT_FILE}")
print(f"Converted: {len(converted)} | Skipped: {len(skipped)}")