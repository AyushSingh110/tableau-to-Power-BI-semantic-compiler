import xml.etree.ElementTree as ET
import json
import re
import os

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


print("EXTRACTING RELATIONSHIPS FROM TWB XML")

##Locate the TWB file
def find_twb_file(extract_dir):
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.lower().endswith(".twb"):
                return os.path.join(root, f)
    return None
extract_dir = "twbx_extracted"
twb_path = find_twb_file(extract_dir)

if not twb_path:
    raise FileNotFoundError("No TWB file found in extracted TWBX")

print(f"TWB file located: {twb_path}")

#Parse the TWB XML
tree = ET.parse(twb_path)
root = tree.getroot()

#Detect the modeling model(logical or it is physical)
has_physical_joins = bool(root.findall(".//relation[@type='join']"))
has_logical_relationships = bool(root.findall(".//relationship"))

print("\nDetected modeling mode:")
if has_logical_relationships:
    print(" - Logical Relationships (Tableau semantic layer)")
if has_physical_joins:
    print(" - Physical Joins (SQL-based)")
if not has_physical_joins and not has_logical_relationships:
    print(" - No explicit relationships found")

#Extract physical joins
def extract_physical_joins(root):
    joins = []

    join_pattern = re.compile(
        r"\[([^\]]+)\]\.\[([^\]]+)\]\s*=\s*\[([^\]]+)\]\.\[([^\]]+)\]"
    )

    for rel in root.findall(".//relation[@type='join']"):
        join_type = rel.attrib.get("join", "inner")
        clause = rel.find("clause")

        if clause is None:
            continue

        expr = clause.attrib.get("expression")
        if not expr:
            continue

        match = join_pattern.search(expr)
        if not match:
            continue

        left_table, left_col, right_table, right_col = match.groups()

        joins.append({
            "from_table": left_table,
            "from_column": left_col,
            "to_table": right_table,
            "to_column": right_col,
            "join_type": join_type,
            "mode": "physical_join",
            "expression": expr
        })

    return joins

#Extract Logical relationships
def extract_logical_relationships(root):
    relationships = []

    for rel in root.findall(".//relationship"):
        from_table = rel.attrib.get("from-table")
        to_table = rel.attrib.get("to-table")

        # Some versions store column pairs explicitly
        for col in rel.findall(".//column"):
            relationships.append({
                "from_table": from_table,
                "from_column": col.attrib.get("from"),
                "to_table": to_table,
                "to_column": col.attrib.get("to"),
                "mode": "logical_relationship",
                "raw_attributes": rel.attrib
            })

        # Fallback: store raw relationship if no columns found
        if not rel.findall(".//column"):
            relationships.append({
                "mode": "logical_relationship_raw",
                "raw_attributes": rel.attrib,
                "note": "Tableau logical relationship – join keys resolved at query time",
                "confidence": "engine-resolved"
            })

    return relationships

# NOTE:
# If both logical and physical are present, Tableau prefers logical.
# We mirror that behavior here.
#Conditional extraction
relationships = []

if has_logical_relationships:
    print("\n[✓] Extracting logical relationships...")
    relationships = extract_logical_relationships(root)

elif has_physical_joins:
    print("\n[✓] Extracting physical joins...")
    relationships = extract_physical_joins(root)

else:
    print("\n[!] No relationships detected — model may rely on single table")

#Save relationships to JSON
output_file = os.path.join(DATA_DIR, "relationships_from_twb.json")
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(relationships, f, indent=4)

print(f"\nRelationships extracted and saved to {output_file}")
