import json
import pandas as pd
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path("data")

with open(DATA_DIR / "parsed_hyper_schema.json") as f:
    hyper_schema = json.load(f)

df = pd.read_csv(DATA_DIR / "hyper_raw_data.csv")

#splitting the data by table
tables = defaultdict(pd.DataFrame)

for col in df.columns:
    if '.' not in col:
        continue 
    table, column = col.split('.', 1)
    tables[table][column] = df[col]


#Column profiling
#this is the engine level evidence not the inference
column_stats = defaultdict(dict)
for table, tdf in tables.items():
    row_count = len(tdf)

    for col in tdf.columns:
        series = tdf[col]
        column_stats[table][col] = {
            "row_count": row_count,
            "distinct_count": series.nunique(dropna=True),
            "null_count": series.isna().sum(),
            "dtype": str(series.dtype)
        }

#Primary key detection
primary_keys = defaultdict(list)

for table, cols in column_stats.items():
    for col, stats in cols.items():
        if (
            stats["distinct_count"] == stats["row_count"]
            and stats["null_count"] == 0
        ):
            primary_keys[table].append(col)

#Foreign key detection
foreign_keys = []

for fact_table, fact_cols in column_stats.items():
    for dim_table, dim_pks in primary_keys.items():
        if fact_table == dim_table:
            continue

        for fk_col, fk_stats in fact_cols.items():
            for pk_col in dim_pks:
                if fk_stats["dtype"] != column_stats[dim_table][pk_col]["dtype"]:
                    continue

                fk_values = tables[fact_table][fk_col].dropna().unique()
                pk_values = tables[dim_table][pk_col].unique()

                coverage = len(set(fk_values) & set(pk_values)) / max(len(fk_values), 1)

                if coverage > 0.95:
                    foreign_keys.append({
                        "from_table": fact_table,
                        "from_column": fk_col,
                        "to_table": dim_table,
                        "to_column": pk_col,
                        "coverage": coverage
                    })

#Cardinality resolution
relationships = []

for fk in foreign_keys:
    relationships.append({
        "from_table": fk["from_table"],
        "from_column": fk["from_column"],
        "to_table": fk["to_table"],
        "to_column": fk["to_column"],
        "cardinality": "ManyToOne",
        "cross_filter_direction": "Single",
        "confidence": round(fk["coverage"], 3),
        "evidence": {
            "fk_coverage": fk["coverage"],
            "pk_verified": True
        }
    })
#Save output
output = {
    "relationships": relationships,
    "unresolved_relationships": []
}

with open(DATA_DIR / "inferred_powerbi_relationships.json", "w") as f:
    json.dump(output, f, indent=4)

