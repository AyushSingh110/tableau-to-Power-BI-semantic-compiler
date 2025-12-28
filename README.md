Tableau → Power BI Semantic Compiler

A research-oriented semantic compilation pipeline that transforms Tableau analytical semantics into a Power BI–compatible Tabular Object Model (TOM).

This project does not perform visual migration or file-level conversion.
Instead, it treats Tableau and Power BI as analytical execution engines, not UI or reporting tools.

Project Objective

The objective of this project is to design and implement an engine-safe, explainable, and auditable semantic compiler that:

Extracts Tableau semantics using official and documented APIs only

Preserves analytical intent and meaning, not visual layout

Avoids heuristic-based or speculative conversion of joins, measures, or logic

Produces a valid and executable Power BI Tabular Object Model (TOM)

Explicitly reports unsupported, unsafe, or ambiguous conversions

What This Project Is

Semantic analysis and semantic compilation

Tableau → canonical intermediate representation → Power BI TOM

Engine-aware translation (Tableau vs VertiPaq / DAX)

Data-driven validation instead of metadata assumptions

Research-grade, deterministic, and explainable pipeline

Implemented Pipeline Stages
1. Tableau Parsing (XML Only)

Parses .twb files extracted from .twbx archives

Extracts semantic metadata including:

Datasources

Fields (dimensions and measures)

Calculated fields

Parameters

Filters

Field-to-worksheet usage

Uses only documented Tableau XML structures

No reverse engineering or undocumented attributes

Files

parsing_tableau.py

Outputs: data/parsed_*.json

2. Hyper Extract Access (Official API)

Uses the Tableau Hyper API exclusively

Extracts:

Table schemas

Column-level data types

Row-level data (used strictly for validation and inference)

Files

parsed_hyper_schema.json

hyper_raw_data.csv

3. Logical → Physical Field Mapping

Maps Tableau logical field identifiers to Hyper physical columns

Ensures:

Deterministic mapping

No duplicate or ambiguous ownership

No inferred aliases or heuristic matching

File

logical_physical_mapping.json

4. Canonical Semantic Model

Constructs a tool-agnostic semantic intermediate representation

Explicitly separates:

Tables

Columns

Measures

Relationships

Acts as a compiler IR, decoupled from both Tableau and Power BI

File

canonical_powerbi_model.json

5. Calculation Classification

Analyzes Tableau calculated fields and classifies them into:

Directly convertible semantic logic

Logic requiring manual redesign

Unsupported logic (visual, table calculations, LOD expressions)

No silent drops or implicit rewrites

File

calculation_classification.json

6. Measure Rewriting (Safe DAX Only)

Converts only engine-safe expressions, including:

Simple aggregations

Algebraic combinations of aggregations

Explicitly skips:

LOD expressions

Table calculations

WINDOW / LOOKUP logic

Skipped measures are retained with justification

Files

rewrite_convertible_calculations.py

converted_dax_measures.json

7. Relationship Handling (Engine-Aware)

Detects Tableau modeling strategy:

Logical relationships

Physical joins

Does not infer or guess join keys

Preserves ambiguity where Tableau defers join resolution to query time

Files

extract_relationships_from_twb.py

relationships_from_twb.json

8. Data-Driven Relationship Inference

Uses actual data from Hyper extracts

Performs:

Primary key detection

Foreign key detection

Coverage-based confidence scoring

Emits relationships only when confidence thresholds are met

File

inferred_powerbi_relationships.json

9. Table Context Resolution

Resolves measure-to-table ownership

Required for:

Valid DAX placement

Power BI engine execution

Prevents ambiguous or floating measures

File

semantic_model_with_context.json

10. Final Power BI Semantic Model

Merges:

Canonical semantic model

Converted DAX measures

Relationship evidence

Attaches a full conversion report for auditability

File

final_powerbi_semantic_model.json

11. Power BI Tabular Object Model Export

Generates a valid Power BI Tabular Object Model

Compatible with:

Tabular Editor

Power BI Desktop (import mode)

Includes annotations documenting skipped or unsupported logic

File

powerbi_tom_model.json

Key Design Principles

Engine correctness > visual parity

Explicit uncertainty > silent failure

Data-driven validation > metadata assumptions

Semantic intent > syntactic conversion

Official APIs only
