---
name: p50k-leak-scan
description: Check new, modified and staged files for real TEFAS price values, real fund names and non-target fund codes before a commit. Use before every commit or push, and whenever fixtures, docs or test data were written.
---

# Pre-commit leak scan

Project rule: real TEFAS/KAP values never enter git, and committed files name only the eight liquidated
targets (THF, TP2, TLY, DFI, DOH, PRY, KHA, PNU). Tests use synthetic data.

Run from the repository root with the project interpreter (`.venv/bin/python`, or
`.venv/Scripts/python.exe` on Windows):

```sh
$PY "${CLAUDE_SKILL_DIR}/leak_scan.py"
```

The script:

- reads every price file in `raw/tefas/prices/` (all funds are open, DEC-029) and the fund names in every snapshot
  database it finds (`raw/snapshots/`, `$P50K_DATA_DIR`, `~/.local/share/project-50k`, including the forward
  database);
- checks complete non-target ticker tokens from the top-100 list (`top100_funds.txt`); checks all saved fund-list
  codes as complete quoted values and filenames in tests, fixtures, seeds and JSON/CSV. Unit labels, environment
  names, license identifiers and mixed-case dependency hashes are not fund identifiers;
- includes names from the entire saved fund list and price files in external overnight output;
- in a clone without private data, set `P50K_RAW_DIR` to another checkout's `raw/` directory;
- scans the working copy and, when staged, the index copy of every new, modified or staged text file, including
  names with non-ASCII characters;
- reports any changed or staged path under `raw/`, or matching `.gitignore`, as a hit;
- reports counts and `file:line` locations, never the matching values.

Exit code 0 means no hits; 1 means hits to fix before committing; 2 means the private data is absent, so the
value and name checks were skipped (the code check still ran). Never commit with hits.
