# Follow-up checker negative tests

These tests are offline mutations of the committed follow-up logs. They do
not start PostgreSQL and do not modify the committed raw evidence.

## Pytest mutation tests

Command:

```text
.venv/bin/python -m pytest -q \
  experiments/pg-tracing/test_analyze_mcv_numeric_followup.py
```

Result:

```text
....                                                                     [100%]
4 passed in 0.01s
```

The tests cover:

1. Equal correction factors (`r_ab=r_bc=r_cd=2.0`) are rejected by the
   absolute-spread threshold of `0.1`.
2. A displayed EXPLAIN row changed from `185` to `184` is rejected even when
   the trace row remains unchanged.
3. A missing numeric MCV marker is rejected.
4. A duplicate numeric MCV marker is rejected.

The equal-factor mutation keeps the raw predictions and displayed rows
internally consistent, so the failure specifically exercises the previously
unreachable heterogeneity assertion rather than an earlier consistency check.

## CLI mutation smoke tests

Using temporary copies of the committed `psql.stdout.log` and
`psql.stderr.log`:

```text
sed '/stat_clause_count=.*hetero_pair_bc/d' stderr.mutated
.venv/bin/python experiments/pg-tracing/analyze_mcv_numeric_followup.py \
  --stdout stdout \
  --stderr stderr.mutated \
  --output missing.json
```

Result: nonzero exit (`missing_numeric_mcv_cli=nonzero`). The deletion removes
only the numeric MCV line and leaves the base trace present.

The displayed-row mutation replaced the first `rows=185 width` occurrence in
the heterogeneous full-query output with `rows=184 width` and reran the same
checker. Result: nonzero exit (`explain_rows_cli=nonzero`).

The successful unmodified run remains recorded in
`numeric-followup-analysis.json` with `"acceptance": "passed"`.
