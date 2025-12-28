import json
from collections import defaultdict
import os

print("Resolving Table Context For Measures")

DATA_DIR = "data"
INPUT_SEMANTIC_MODEL = os.path.join(DATA_DIR, "semantic_model.json")
INPUT_MAPPING = os.path.join(DATA_DIR, "logical_physical_mapping.json")
OUTPUT_MODEL = os.path.join(DATA_DIR, "semantic_model_with_context.json")

# LOAD INPUT FILES
with open(INPUT_SEMANTIC_MODEL, encoding="utf-8") as f:
    semantic_model = json.load(f)

with open(INPUT_MAPPING, encoding="utf-8") as f:
    mappings = json.load(f)

print("Loaded semantic_model.json")
print("Loaded logical_physical_mapping.json")

# HELPERS
def normalize_field_name(field: str) -> str:
    if not field:
        return None
    return field.strip().strip("[]").lower()


# [1/4] BUILD FIELD → TABLE LOOKUP (NORMALIZED)
print("\n[1/4] Building field-to-table lookup...")

field_to_tables = defaultdict(set)

for m in mappings:
    logical_field = normalize_field_name(m["logical_field"])
    field_to_tables[logical_field].add(m["table"])

field_to_table = {}

for field, tables in field_to_tables.items():
    if len(tables) == 1:
        field_to_table[field] = list(tables)[0]
    else:
        # Prefer fact table if ambiguous
        fact_tables = [
            t for t in tables
            if semantic_model["tables"].get(t, {}).get("type") == "fact"
        ]
        field_to_table[field] = fact_tables[0] if fact_tables else list(tables)[0]

print(f"Resolved {len(field_to_table)} field-to-table mappings")


# [2/4] ENRICH AST WITH TABLE CONTEXT
print("\n[2/4] Enriching measure ASTs with table context...")

def enrich_ast(ast):
    node_type = ast.get("node")

    if node_type == "binary":
        left = ast.get("left", {})
        right = ast.get("right", {})

        left_field = normalize_field_name(left.get("field"))
        right_field = normalize_field_name(right.get("field"))

        left["table"] = field_to_table.get(left_field)
        right["table"] = field_to_table.get(right_field)

    elif node_type == "single":
        field = normalize_field_name(ast.get("field"))
        ast["table"] = field_to_table.get(field)

    elif node_type == "raw":
        ast["table_context"] = {
            field: table
            for field, table in field_to_table.items()
            if field in ast.get("formula", "").lower()
        }

    return ast

for name, measure in semantic_model["measures"].items():
    measure["ast"] = enrich_ast(measure["ast"])

print(f"Updated table context for {len(semantic_model['measures'])} measures")

# [3/4] REGENERATE DAX WITH TABLE CONTEXT
print("\n[3/4] Regenerating DAX expressions...")

def ast_to_dax(ast):
    node_type = ast.get("node")

    if node_type == "binary":
        l, r = ast["left"], ast["right"]
        if not l.get("table") or not r.get("table"):
            return "-- TABLE CONTEXT MISSING"
        return (
            f"{l['agg']}({l['table']}[{l['field']}]) "
            f"{ast['op']} "
            f"{r['agg']}({r['table']}[{r['field']}])"
        )

    if node_type == "single":
        if not ast.get("table"):
            return "-- TABLE CONTEXT MISSING"
        return f"{ast['agg']}({ast['table']}[{ast['field']}])"

    return "-- UNSUPPORTED TABLEAU LOGIC"

semantic_model["dax_measures"] = {
    name: ast_to_dax(measure["ast"])
    for name, measure in semantic_model["measures"].items()
}

print("DAX regeneration complete")

# [4/4] BUILD MEASURE → TABLE OWNERSHIP MAP
measure_table_map = {}

for name, measure in semantic_model["measures"].items():
    ast = measure["ast"]
    node_type = ast.get("node")

    if node_type == "single":
        measure_table_map[name] = ast.get("table")

    elif node_type == "binary":
        measure_table_map[name] = ast.get("left", {}).get("table")

semantic_model["measure_table_map"] = measure_table_map
print(f"Measure-to-table ownership mapping complete: {len(measure_table_map)} mapped")

# SAVE OUTPUT
with open(OUTPUT_MODEL, "w", encoding="utf-8") as f:
    json.dump(semantic_model, f, indent=4)

print("\nsemantic_model_with_context.json written to data/")
