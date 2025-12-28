import json
from pathlib import Path

DATA_DIR = Path("data")

SEMANTIC_MODEL = DATA_DIR / "final_powerbi_semantic_model.json"
HYPER_SCHEMA = DATA_DIR / "parsed_hyper_schema.json"
OUTPUT_TOM = DATA_DIR / "powerbi_tom_model.json"

print("EXPORTING POWER BI TABULAR OBJECT MODEL (TOM)")

#LOading final semantic model
with open(SEMANTIC_MODEL, encoding="utf-8") as f:
    semantic_model = json.load(f)

with open(HYPER_SCHEMA, encoding="utf-8") as f:
    hyper_schema = json.load(f)

#Build the type lookup from hyper
type_lookup = {}
for table in hyper_schema:
    tname = table["table"]
    for col in table["columns"]:
        raw = col["data_type"].lower()
        if "int" in raw:
            dtype = "int64"
        elif "double" in raw or "float" in raw or "numeric" in raw:
            dtype = "double"
        elif "date" in raw or "time" in raw:
            dtype = "dateTime"
        else:
            dtype = "string"
        type_lookup[(tname, col["column_name"])] = dtype

#Building TOM structure
tom_model = {
    "name": "Tableau_Migrated_Model",
    "compatibilityLevel": 1567,
    "model": {
        "tables": [],
        "relationships": [],
        "annotations": []
    }
}

#Create the tebles and the columns
for table_name, table_info in semantic_model["tables"].items():
    tom_table = {
        "name": table_name,
        "columns": [],
        "measures": []
    }

    for col in table_info["columns"]:
        tom_table["columns"].append({
            "name": col,
            "dataType": type_lookup.get((table_name, col), "string"),
            "sourceColumn": col
        })

    tom_model["model"]["tables"].append(tom_table)

print(f"Tables exported: {len(tom_model['model']['tables'])}")

#create measures
# Build table lookup
table_map = {
    table["name"]: table
    for table in tom_model["model"]["tables"]
}

# semantic_model["measure_table_map"] must exist
measure_table_map = semantic_model.get("measure_table_map", {})

for measure_name, dax_expr in semantic_model["measures"].items():

    target_table = measure_table_map.get(measure_name)

    if not target_table or target_table not in table_map:
        tom_model["model"]["annotations"].append({
            "name": f"UnplacedMeasure::{measure_name}",
            "value": "No reliable table context"
        })
        continue

    table = table_map[target_table]

    table["measures"].append({
        "name": measure_name,
        "expression": dax_expr,
        "formatString": "General"
    })

print(f"Measures exported: {sum(len(t['measures']) for t in tom_model['model']['tables'])}")

#Create relationships
for rel in semantic_model.get("relationships", []):
    tom_model["model"]["relationships"].append({
        "fromTable": rel["from_table"],
        "fromColumn": rel["from_column"],
        "toTable": rel["to_table"],
        "toColumn": rel["to_column"],
        "cardinality": rel["cardinality"],
        "crossFilteringBehavior": rel["cross_filter_direction"]
    })

print(f"Relationships exported: {len(tom_model['model']['relationships'])}")

#Add the global annotations
tom_model["model"]["annotations"].append({
    "name": "MigrationNote",
    "value": "Generated via semantic-preserving Tableau → Power BI pipeline"
})
#save the TOM model
with open(OUTPUT_TOM, "w", encoding="utf-8") as f:
    json.dump(tom_model, f, indent=4)

print(f"\nPower BI TOM model written to {OUTPUT_TOM}")
