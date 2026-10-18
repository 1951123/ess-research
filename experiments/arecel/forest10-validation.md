# Forest10 full-data validation status

**Status: BLOCKED / NOT RUN.**

No independently supplied Forest10 source root was provided for this bounded
PR. In accordance with the three-project-only contract, the historical
`extstats-advisor-research` checkout, global benchmark directories, old
archives, databases and credentials were not inspected or used. Therefore the
following historical expectations remain unverified in this environment:

- 581,012 CSV rows and the ten-column nullable `DOUBLE PRECISION` schema;
- CSV SHA256 `3484f3037f890f6bae46ae51fb387ee883351119667139c5894654276789a73c`;
- 10,000 valid and 10,000 test canonical workload records;
- workload/label/canonical artifact hashes recorded in
  `docs/arecel-asset-inventory.md`.

The fail-closed offline command is:

```sh
PYTHONPATH=src .venv/bin/python -m ess_research.arecel.forest10 inspect \
  --data-root /absolute/path/to/explicit/arecel-root
```

When the root is absent or incomplete it reports `BLOCKED_MISSING_INPUT` and
does not create or substitute any data. A real validation can be run later
only after a human supplies the pinned archive and audit metadata under an
explicit root. It must retain the archive/file hashes, exact counts, license
decision, and generated artifact manifest.

The executed evidence in this PR is offline synthetic validation in
`tests/test_forest10_etl.py`; it is not full-data validation and makes no
claim about the original Forest10 dataset contents.
