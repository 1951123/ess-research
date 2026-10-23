# Issue #74 single-case B=2 recovery stop report

**Evidence class:** Experimentally observed. This is an interrupted, nonpassing
attempt; it does not establish a solver result or a selected-set comparison.

## Authorization and frozen scope

Execution-gate PR [#81](https://github.com/1951123/ess-research/pull/81) was
reviewed and merged to `main` at
`498763d849bb57ac6fcced77e7a41f866b54da8c`. The reviewed runner HEAD was
`d1b1ec659e9d17f65218e5fb446cbeabe4906e4e`; both Python/evidence and paper PDF
checks passed on that HEAD. The recorded single-attempt grant covered only
Forest10 valid-only (10,000 tasks, 45 candidates), fixed-priority Nominal,
B=2, with Advisor `369d90217e931c7d1b0cd6e82c88527a25cc7129`, a 12 GiB memory
cap, 900 s outer wall cap, 600 s Advisor per-case/total cap, and no retry.
The unchanged base protocol SHA-256 is
`5971ded0a9a458b86dbf1e885bd5dd58260a6dab90a0ca9cccd53b18755c6ed3`; the
execution-gate SHA-256 is
`7992eb3fe824593b8bd71c3e62db3598c40f14069ae48c40bd74022d0b9c5237`.

## Attempt and outcome

- Run ID: `issue74-forest10-nominal-b2-recovery-20261023`.
- Environment: Python 3.12.3, `pess-ess` 0.1.0 at the pinned Advisor commit,
  NumPy 2.5.4, SciPy 1.18.1.
- Request SHA-256 recorded in the phase journal:
  `369cd6082202d8e3bcb97c187544630991a51df078ed17cdd513ff0d07b3f09f`.
- Input checks passed for the frozen selection and coefficient artifact; the
  adapter prepared 10,000 tasks and 45 candidates. The matrix had 1,330,848
  rows, 174,133 columns, and 3,952,586 stored entries.
- Observed preparation durations: Python constraints 3.994 s; COO assembly
  1.378 s; COO-to-CSR conversion 0.161 s; remaining solver input preparation
  0.148 s. These are this attempt's phase observations only.
- The HiGHS call did not return by the 600 s Advisor wall limit. At the first
  check after the limit, the durable phase timer read 602.6 s; the scope's
  termination checkpoint followed at 607.2 s from invocation start. The
  runner was stopped with SIGTERM (`systemd_exit_code=-15`) and returned code
  2. The command-level termination therefore exceeded the configured 600 s
  limit by about 7 s; this is recorded as a limit overrun, not normalized
  away. Outer wall limit was not reached.
- systemd retained `MemoryPeak=2433056768` bytes (about 2.27 GiB) and
  `Result=success`; the command exit status was `-15`. The runner correctly
  classified the outcome as `STOP_FOR_REVIEW` because there was no child
  result. No Advisor response, solver status, or exact Fraction selected-set
  comparison exists. `time.txt` and `runner.log` are empty after termination.
- The one-shot authorization claim remains consumed. No retry, other budget,
  case, dataset, or solver configuration is authorized by this outcome.

## Retained evidence

Raw evidence remains under
`$ESS_RUNTIME_PARENT/ess-research/issue74/runs/issue74-forest10-nominal-b2-recovery-20261023/`.
The run metadata records the protocol, gate, runner, Advisor, systemd and
outcome pins. SHA-256 values for key files are:

| File | SHA-256 |
| --- | --- |
| `case-result.json` | `4ddadf4fa68e4a18a1c820a8b0bd475acf42326bb94611fa6e4f94a813a6db31` |
| `phase-events.jsonl` | `8c7277d8726519ec689cc64a7d6970aaf0b1f9cc22e2e2db3f6ad7b174337666` |
| `phase-checkpoint.json` | `e5ab4e1239dee838773ab1eb81842b6a4378357a8e3d5182dac8a166b0444139` |
| `run-metadata.json` | `e3bccc6dcf2c3b0f9b835a7176b7d313511338a7b0bbbb8dc1b6df30c9517035` |

Reproduce the run setup with the pinned runtime and command recorded in
`run-metadata.json`; do **not** invoke it again. The single authorization has
been consumed, and any further solver work requires a new reviewed protocol
and explicit authorization.
