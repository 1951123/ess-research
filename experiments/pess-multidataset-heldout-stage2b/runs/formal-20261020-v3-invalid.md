# Formal run v3 validity note

Evidence label: **Superseded / invalidated by implementation audit.**

The v3 run completed PostgreSQL measurement, but it must not be used for the
Stage 2B decision. Post-run code audit found that `run_formal.py` enumerated
feasible candidate sets with a fixed bit position, so Nominal and PESS did not
search the declared candidate space. The v3 held-out rows and hashes are
preserved unchanged under `runs/formal-20261020-v3/`; no result was tuned from
those held-out outcomes. A corrected rerun under the unchanged frozen protocol
is recorded separately as the authoritative formal run.
