import json
import os
from pathlib import Path

DATA_DIR = Path("data")

#Input files
SCHEMA_FILE = DATA_DIR / "parsed_hyper_schema.json"
MEASURES_FILE = DATA_DIR / "semantic_model_with_context.json"
RELATIONSHIPS_FILE = DATA_DIR / "inferred_powerbi_relationships.json"

#Output file
OUTPUT_FILE = DATA_DIR / "canonical_powerbi_model.json"

print("BUILDING CANONICAL POWER BI SEMANTIC MODEL")

#Loading the required inputs
with open(SCHEMA_FILE) as f:
    hyper_schema = json.load(f)

with open(MEASURES_FILE) as f:
    semantic_model = json.load(f)

with open(RELATIONSHIPS_FILE) as f:
    relationship_data = json.load(f)

print("Loaded Hyper schema, measures, and inferred relationships")

#Now detect the model type
if len(relationship_data["relationships"]) == 0:
    model_type = "flat_extract"
else:
    model_type = "relational_model"

print(f"Detected model type: {model_type}")

#Build table definitions
tables = {}
for entry in hyper_schema:
    table_name = entry["table"]
    columns = [col["column_name"] for col in entry["columns"]]
    tables[table_name] = {
        "columns": columns,
        "source": "tableau_hyper",
        "confidence": "high"
    }
print(f"Tables defined: {len(tables)}")

#Attach the measures
measures = semantic_model.get("dax_measures", {})

print(f"Measures attached: {len(measures)}")

#Build canonical model structure
canonical_model = {
    "model_type": model_type,
    "tables": tables,
    "measures": measures,
    "relationships": relationship_data["relationships"],
    "provenance": {
        "source": "tableau_to_powerbi_semantic_pipeline",
        "relationship_inference": "data-driven",
        "engine_assumptions": "none"
    }
}
#Save the canonical model
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(canonical_model, f, indent=4)

print(f"\nCanonical Power BI model written to: {OUTPUT_FILE}")