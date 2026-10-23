# Oturum 2b — Yazım oturumu, SPEC revizyonu (birebir prompt)

İnceleme oturumu G*Power arayüzünden toplanan kâhin vektörleriyle SPEC.md'yi düzeltti. Bu düzeltme, sıfır bağlamla başlatılan yeni bir yazım ajanına yalnızca SPEC farkı üzerinden uygulatıldı.

---

You are the IMPLEMENTATION session of a clean-room reimplementation, starting fresh. Repository:
`C:\Users\Casper\OneDrive\Masaüstü\Yazılım\Yazılım Gerçekleme ve Test`

CLEAN-ROOM RULES (strict):
- Your specification is `SPEC.md` (and `CONTRACT.md`). The SPEC changed; see exactly what changed with
  `git diff f72c2ec -- SPEC.md`. Implement those changes.
- You may read and modify the implementation you own: `src/gpower_clone/`, `tests/test_*.py` written by the
  implementation session (`test_public_vectors.py`, `test_numerics_oracle.py`, `test_invariants.py`,
  `test_validation.py`, `test_cli.py`, `test_mcp_equivalence.py`, `test_agent.py`, `conftest.py`) and
  `docs/IMPLEMENTATION_NOTES.md`.
- Do NOT open `oracle/`, `rea/`, `LEDGER.md`, `HALLUCINATIONS.md`, `tools/`, `tests/differential.py`,
  `prompts/` (except this brief), any G*Power files, or any temp/scratchpad folder. Never run G*Power.
  Everything you need is in SPEC.md. If something is ambiguous, pick the simplest reading and list it in the notes.
- You MAY run the whole test suite (`uv run pytest -q`). `tests/test_spec_gherkin.py` executes the Gherkin
  tables in SPEC.md §9 and `tests/test_differential.py` compares against external oracles; if they fail, fix the
  implementation according to SPEC.md — do not edit those two files and do not go look at the oracle data.

TASK:
1. Implement the revised a-priori rule (SPEC §3.1): continuous total N* searched for N > 2, N = 2·⌈N*/2 − 1e-9⌉,
   n1 = ⌊N/(1+ratio) + 0.5⌋, n2 = N − n1, outputs recomputed with the integers (actual_power may be below target),
   N ≥ 4 shortcut, degenerate groups (n < 2, including n2 = 0 with ncp = 0, df = n1 + n2 − 2) plus the extra
   `warning` field, and NO_SOLUTION only when N* > 1e13 (no 1e7 limit any more).
2. Validation changes (SPEC §2): ratio must be within [0.01, 100] (else OUT_OF_RANGE, field ratio);
   INCONSISTENT only when power < alpha (strictly) for a-priori and sensitivity; power == alpha is valid.
3. Sensitivity (SPEC §3.5): power == alpha gives d = 0, ncp = 0.
4. Update your own tests to the revised SPEC (invariants in SPEC §8 changed: actual_power ≥ target is no longer
   an invariant; n_total is even and ≥ 4; the split rule; minimality on the continuous path; ratio = 1 ⇒ n1 = n2).
   Keep the 2-second CLI budget (check `--d 0.001` and `--d 0.0000000001` timings).
5. `uv run pytest -q` must be fully green (skips allowed only where already marked).
6. Append a "Revizyon 1" section (Turkish) to `docs/IMPLEMENTATION_NOTES.md`: what changed, ambiguities, test counts, timings.

Do NOT commit. Reply with: files changed, test summary, timings, ambiguities.
