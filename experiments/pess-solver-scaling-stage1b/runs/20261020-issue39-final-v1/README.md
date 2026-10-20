# Preserved runner-failure provenance

This directory is an incomplete first attempt at the final matrix. It is
preserved and is not used as the final result.

- The runner wrote 17 raw records before stopping at job index 17.
- The child was `medium_path_3913.json`, `master_oracle`, endpoint budget 60 s,
  repetition seed 7101.
- The child emitted a valid JSON record followed by the HiGHS diagnostic line
  `HighsMipSolverData::transformNewIntegerFeasibleSolution tmpSolver.run();`.
- The wrapper incorrectly parsed only the last stdout line and raised
  `JSONDecodeError`, so this attempt has no summary and no scientific status.
- The parser fix is committed separately; the final matrix uses a new output
  directory and preserves any non-JSON child stdout in its raw record.
