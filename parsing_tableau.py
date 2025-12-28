import zipfile
import os
import json
import xml.etree.ElementTree as ET
from tableauhyperapi import HyperProcess, Connection, CreateMode, Telemetry
import pandas as pd

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ========== CONFIGURATION ==========
twbx_path = 'Superstore.twbx'
extract_dir = "twbx_extracted"

# ========== PART 1: EXTRACT TWBX FILE ==========
os.makedirs(extract_dir, exist_ok=True)

with zipfile.ZipFile(twbx_path, 'r') as z:
    file_list = z.namelist()
    z.extractall(extract_dir)

print(f"[1/9] TWBX extracted - {len(file_list)} files found")

# ========== PART 2: LOCATE HYPER FILES ==========
hyper_files = []

for root_dir, _, files in os.walk(extract_dir):
    for f in files:
        if f.lower().endswith(".hyper"):
            hyper_files.append(os.path.join(root_dir, f))

if not hyper_files:
    raise FileNotFoundError("No .hyper extract found inside TWBX")

print(f"[2/9] Hyper files located - {len(hyper_files)} file(s)")

# ========== PART 3: LOCATE AND PARSE TWB FILE ==========
twb_path = None

for file in file_list:
    if file.lower().endswith(".twb"):
        twb_path = os.path.join(extract_dir, file)
        break

if not twb_path:
    raise FileNotFoundError("No .twb file found inside TWBX")

# Parse TWB XML
tree = ET.parse(twb_path)
root = tree.getroot()

# Extract major components
worksheets = root.findall(".//worksheet")
dashboards = root.findall(".//dashboard")
datasources = root.findall(".//datasource")

print(f"[3/9] TWB parsed - {len(worksheets)} worksheets, {len(dashboards)} dashboards, {len(datasources)} datasources")

# ========== PART 4: PARSE DATASOURCE FIELDS AND CALCULATIONS ==========
datasource_details = []

for ds in datasources:
    ds_name = ds.attrib.get('name', 'Unnamed Datasource')
    
    fields = []
    calculations = []
    
    for col in ds.findall(".//column"):
        field_name = col.attrib.get("name")
        field_role = col.attrib.get("role")
        field_type = col.attrib.get("datatype")
        
        calc = col.find("calculation")
        if calc is not None:
            formula = calc.attrib.get("formula", "")
            calculations.append({
                "field_name": field_name,
                "formula": formula
            })
        else:
            fields.append({
                "field_name": field_name,
                "role": field_role,
                "data_type": field_type
            })
    
    datasource_details.append({
        "datasource_name": ds_name,
        "fields": fields,
        "calculations": calculations
    })

with open(os.path.join(DATA_DIR, "parsed_tableau_schema.json"), "w", encoding="utf-8") as f:
    json.dump(datasource_details, f, indent=4)


total_fields = sum(len(ds["fields"]) for ds in datasource_details)
total_calcs = sum(len(ds["calculations"]) for ds in datasource_details)
print(f"[4/9] Schema parsed - {total_fields} fields, {total_calcs} calculations")

# ========== PART 5: PARSE FILTERS AND PARAMETERS ==========
filters_output = []
parameters_output = []

for worksheet in root.findall(".//worksheet"):
    ws_name = worksheet.attrib.get("name", "Unnamed Worksheet")
    
    for flt in worksheet.findall(".//filter"):
        filters_output.append({
            "worksheet": ws_name,
            "field": flt.attrib.get("field"),
            "class": flt.attrib.get("class"),
            "expression": flt.attrib.get("expression")
        })

for ds in root.findall(".//datasource"):
    if ds.attrib.get("name") == "Parameters":
        for col in ds.findall(".//column"):
            calc = col.find("calculation")
            if calc is not None:
                parameters_output.append({
                    "parameter_name": col.attrib.get("name"),
                    "default_value": calc.attrib.get("formula")
                })

with open(os.path.join(DATA_DIR, "parsed_tableau_filters.json"), "w", encoding="utf-8") as f:
    json.dump(filters_output, f, indent=4)

with open(os.path.join(DATA_DIR, "parsed_tableau_parameters.json"), "w", encoding="utf-8") as f:
    json.dump(parameters_output, f, indent=4)

print(f"[5/9] Filters & parameters parsed - {len(filters_output)} filters, {len(parameters_output)} parameters")

# ========== PART 6: MAP FIELDS TO WORKSHEETS ==========
field_usage = []

for worksheet in root.findall(".//worksheet"):
    ws_name = worksheet.attrib.get("name", "Unnamed Worksheet")
    used_fields = set()
    
    for enc in worksheet.findall(".//encoding"):
        field = enc.attrib.get("field")
        if field:
            used_fields.add(field)
    
    for calc in worksheet.findall(".//calculation"):
        formula = calc.attrib.get("formula")
        if formula:
            used_fields.add(formula)
    
    field_usage.append({
        "worksheet": ws_name,
        "used_fields_or_calculations": list(used_fields)
    })

with open(os.path.join(DATA_DIR, "parsed_tableau_field_usage.json"), "w", encoding="utf-8") as f:
    json.dump(field_usage, f, indent=4)


total_mappings = sum(len(ws["used_fields_or_calculations"]) for ws in field_usage)
print(f"[6/9] Field usage mapped - {total_mappings} field references across worksheets")

# ========== PART 7: PARSE HYPER EXTRACT SCHEMA ==========
def open_hyper(hyper_path):
    """Open a connection to the Hyper extract (read-only)"""
    hyper = HyperProcess(
        telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU
    )

    connection = Connection(
        endpoint=hyper.endpoint,
        database=hyper_path,
        create_mode=CreateMode.NONE  
    )

    return hyper, connection


def extract_hyper_schema(connection):
    """Extract schema information from Hyper file"""
    schema_info = []
    
    schemas = connection.catalog.get_schema_names()
    for schema in schemas:
        tables = connection.catalog.get_table_names(schema)
        for table in tables:
            table_def = connection.catalog.get_table_definition(table)
            columns = [
                {
                    "column_name": col.name.unescaped,
                    "data_type": str(col.type)
                }
                for col in table_def.columns
            ]
            
            schema_info.append({
                "schema": schema.name.unescaped,
                "table": table.name.unescaped,
                "columns": columns
            })
    
    return schema_info

hyper, conn = open_hyper(hyper_files[0])
schema = extract_hyper_schema(conn)

with open(os.path.join(DATA_DIR, "parsed_hyper_schema.json"), "w") as f:
    json.dump(schema, f, indent=4)

total_tables = len(schema)
total_cols = sum(len(table["columns"]) for table in schema)
print(f"[7/9] Hyper schema extracted - {total_tables} tables, {total_cols} columns")

# PART 8: EXTRACT RAW DATA FROM HYPER 
from tableauhyperapi import TableName

def export_table_to_df(connection, schema_name, table_name):
    """
    Export a Hyper table into a Pandas DataFrame
    using the official Hyper API (no DB-API hacks).
    """
    table = TableName(schema_name, table_name)

    columns = [
        col.name.unescaped
        for col in connection.catalog.get_table_definition(table).columns
    ]

    rows = []
    with connection.execute_query(f'SELECT * FROM {table}') as result:
        for row in result:
            rows.append(list(row))

    return pd.DataFrame(rows, columns=columns)
schema_name = schema[0]["schema"]
table_name = schema[0]["table"]

df = export_table_to_df(conn, schema_name, table_name)

df.to_csv(os.path.join(DATA_DIR, "hyper_raw_data.csv"), index=False)

print(f"[8/9] Raw data exported - {len(df)} rows, {len(df.columns)} columns")
# PART 9: MAP LOGICAL TO PHYSICAL FIELDS 
def map_logical_to_physical(twb_fields, hyper_schema):
    seen = set()
    mappings = []

    for ds in twb_fields:
        for field in ds["fields"]:
            lf = field["field_name"]
            if not lf:
                continue

            for table in hyper_schema:
                for col in table["columns"]:
                    pc = col["column_name"]
                    if pc and lf.lower() == pc.lower(): 
                        key = (lf, pc, table["table"])
                        if key not in seen:
                            seen.add(key)
                            mappings.append({
                                "logical_field": lf,
                                "physical_column": pc,
                                "table": table["table"],
                                "schema": table["schema"]
                            })
    return mappings


logical_physical_map = map_logical_to_physical(datasource_details, schema)

with open(os.path.join(DATA_DIR, "logical_physical_mapping.json"), "w") as f:
    json.dump(logical_physical_map, f, indent=4)


print(f"[9/9] Logical-physical mapping complete - {len(logical_physical_map)} mappings found")

#  CLEANUP 
conn.close()
hyper.close()

# FINAL SUMMARY
print("PARSING COMPLETE")
print("\nOutput Files Generated:")
print("  1. parsed_tableau_schema.json")
print("  2. parsed_tableau_filters.json")
print("  3. parsed_tableau_parameters.json")
print("  4. parsed_tableau_field_usage.json")
print("  5. parsed_hyper_schema.json")
print("  6. hyper_raw_data.csv")
print("  7. logical_physical_mapping.json")
