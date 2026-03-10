# Semantic Enrichment Notebook Guide

This folder contains:

- `Phase0_TESTING_jsonlds.ipynb`

## Scope

The notebook is now a pure JSON semantic explorer.

- It does not import `phase0` modules.
- It does not call or connect to IDA ICE.
- It only reads input JSON and builds an RDF graph for exploration.

## What It Does

1. Loads JSON from `data/` (v2 compact format or a legacy expanded list).
2. Normalizes it locally inside the notebook.
3. Builds RDF triples (`rdflib`) for zones, walls, windows, and properties.
4. Runs SPARQL queries for multipliers, WWR, constructions, and window data.
5. Exports graph files and creates a visualization for only the first `NORTH` zone.

## Input

Default:

- `data/example_case_v2.sample.json`

Change `INPUT_JSON` in the notebook to inspect another file.

## Output

- `Semantic Enrichment/phase0_semantic_graph.ttl`
- `Semantic Enrichment/phase0_semantic_graph.jsonld`
- `Semantic Enrichment/phase0_semantic_graph_north.html` (if `pyvis` is installed)

## Dependencies

- `rdflib`
- `pandas`
- `pyvis` (optional)

Install:

```powershell
pip install rdflib pandas pyvis
```
