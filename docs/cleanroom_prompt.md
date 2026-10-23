# Yazım oturumuna verilen istem (birebir)

Bu istem, inceleme oturumundan bağımsız, sıfır bağlamla başlatılan ikinci ajan oturumuna verildi. Yazım oturumu G*Power'ı, inceleme betiklerini ya da `rea/` klasörünü görmedi; yalnızca `SPEC.md` ve `CONTRACT.md`'yi okudu.

---

You are the IMPLEMENTATION session of a clean-room reimplementation. Work in the repository at:
`C:\Users\Casper\OneDrive\Masaüstü\Yazılım\Yazılım Gerçekleme ve Test`

CLEAN-ROOM RULES (strict):
- You may read ONLY `SPEC.md` and `CONTRACT.md` in that folder (plus files you create yourself, and public package documentation for `mcp` / `anthropic` if needed).
- Do NOT open anything under `rea/`, `docs/` (except this file is the brief), any scratchpad/temp folder, or anything about G*Power's internals. Do not search the web for G*Power source or decompiled code. You never run G*Power.
- Everything you need is in SPEC.md. If SPEC.md is ambiguous, choose the simplest reading, and list the ambiguity in `docs/IMPLEMENTATION_NOTES.md`.

TASK: implement the `t2-indep` family exactly per SPEC.md and CONTRACT.md, as a Python package with a src layout:

1. `pyproject.toml` (build backend hatchling, `requires-python >=3.10`, console script `gpower-clone = gpower_clone.cli:main`, also `gpower-clone-mcp = gpower_clone.mcp_server:main` and `gpower-clone-agent = gpower_clone.agent:main`). Core has **zero runtime dependencies** (stdlib only, SPEC §1.1 — 2 s budget). Optional extras: `mcp = ["mcp>=1.2"]`, `agent = ["mcp>=1.2", "anthropic>=0.40"]`. Dev dependency group: `pytest`, `scipy`, `mcp`.
2. `src/gpower_clone/numerics.py` — regularized incomplete beta (Lentz continued fraction), central t CDF and inverse, noncentral t CDF (Lenth 1989 AS 243 style Poisson-weighted series summed in both directions, with robust fallbacks for large ncp so nothing returns NaN), and a safeguarded root finder (Brent or bisection). Pure stdlib.
3. `src/gpower_clone/engine.py` — the ONLY place with calculation and validation logic: `run(params: dict) -> tuple[dict, int]` returning the output object (or error object) and the exit code; plus `to_json(obj) -> str` per SPEC §5. Implement the 5 modes, validation order, error codes, and a-priori allocation rule exactly as SPEC §2–§4 say. `--version` info as a function.
4. `src/gpower_clone/cli.py` — thin: argv → dict of strings → `engine.run` → print one JSON line to stdout, exit with code. Handle `--version`. A flag with no value is `INVALID_VALUE`; a positional token is `UNKNOWN_PARAM`. Never print anything else to stdout. Team name in version output: `"gpower-clone-t2indep"`.
5. `src/gpower_clone/mcp_server.py` — thin MCP stdio server (official `mcp` SDK) exposing one tool `power_analysis` whose output text is byte-identical to the CLI stdout line (SPEC §6). Use a hand-written loose JSON input schema (low-level `mcp.server.Server` with `list_tools`/`call_tool` is fine) so that type errors are reported by the engine, not by the MCP layer.
6. `src/gpower_clone/agent.py` — natural-language agent (SPEC §7): uses the `anthropic` SDK (model id default `claude-sonnet-5-5`, overridable by env `GPOWER_AGENT_MODEL`), connects to `gpower-clone-mcp` via the MCP stdio client, lists the tool, runs a tool-use loop, logs every tool call to `logs/agent_calls.jsonl` in exactly the CONTRACT §8 format (tokens from the `usage` of the model response that requested the tool call). Usage: `gpower-clone-agent "soru"` or interactive if no argument. Needs `ANTHROPIC_API_KEY`; if missing, print a clear Turkish error to stderr and exit 1. Write the system prompt in Turkish with the clinical rules in SPEC §7 / CONTRACT §10 (never silently assume "orta etki" = 0.5; state assumptions; never compute numbers itself). Also `agent.py --dry-run "soru"` is NOT needed.
7. Tests in `tests/` (pytest):
   - `public_vectors.jsonl` at repo root containing the 25 vectors from CONTRACT §9 verbatim; `tests/test_public_vectors.py`: the 5 `t2-indep` vectors match within the CONTRACT §6 rule, with integers exact; the other 20 return `UNSUPPORTED` with exit code 2.
   - `tests/test_numerics_oracle.py`: compare numerics against SciPy (`scipy.stats.t`, `scipy.stats.nct`) on a grid (df 1…10000 incl. non-integer df, ncp 0…40, both tails) — absolute error ≤ 1e-9. Note: SciPy's `nct.cdf` can return NaN far in the lower tail for some ncp; treat NaN oracle values as "skip" (and assert ours is < 1e-12 there).
   - `tests/test_invariants.py`: the invariants in SPEC §8 on a randomized but seeded grid (tails 1/2, d 0.1…2, alpha 0.001…0.2, power 0.6…0.99, ratio 0.25…4).
   - `tests/test_validation.py`: every error code in SPEC §2 with field and exit code, including `0,05`, `nan`, `88.0` for n1, duplicate field, irrelevant field (e.g. `--power` in post-hoc), unknown test, unknown mode, missing field, power ≤ alpha.
   - `tests/test_cli.py`: subprocess tests: stdout is exactly one JSON line, ints are JSON ints, exit codes, `--version`, and **wall time < 2 s** per call.
   - `tests/test_mcp_equivalence.py`: start the real MCP server over stdio with the `mcp` client, call `power_analysis` for all 25 public vectors (and a few error inputs) and assert the text equals the CLI stdout line byte-for-byte.
8. Use `uv` (installed) to create the env: `uv sync --all-extras --group dev` (or equivalent) and run `uv run pytest -q`. All tests must pass. Also time `uv run gpower-clone --test t2-indep --mode a-priori --tails 2 --d 0.2 --alpha 0.01 --power 0.99 --ratio 3` and the `.venv` direct executable.
9. Write `docs/IMPLEMENTATION_NOTES.md` (Turkish): what you built, numerical methods, any SPEC ambiguities and how you resolved them, test results with counts, timings.

Do NOT commit to git; the reviewer will. Do NOT create README.md (the reviewer will). When done, reply with: files created, test summary (counts), timing numbers, and every SPEC ambiguity you hit.
