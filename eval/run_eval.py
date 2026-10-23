"""Run the 10-question evaluation through the real agent (Claude + MCP) and write eval/EVAL_REPORT.md.

    $env:ANTHROPIC_API_KEY = "..."        # PowerShell; never commit the key
    uv run --all-extras python eval/run_eval.py
    uv run --all-extras python eval/run_eval.py --gui-screenshot oracle/screenshots/V01.png --gui-steps 7

Scoring per question:
- family:  t2-indep questions must call `power_analysis` with test t2-indep and the expected mode;
           other families (t-paired, anova-oneway) must NOT be computed as t2-indep;
           "ambiguous" must not silently assume d (either no call, or the reply states the assumed value).
- params:  the last tool_input equals the expected input (numbers compared exactly after float()).
- N / result: the last tool_output equals the engine's expected output (ints exact, floats 1e-9).

GUI comparison: the same answer through G*Power's GUI costs at least `gui_steps` screenshots. The
per-screenshot token cost is MEASURED with the API's count_tokens on a real G*Power screenshot.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "eval" / "questions.jsonl"
REPORT = ROOT / "eval" / "EVAL_REPORT.md"
RESULTS = ROOT / "eval" / "results.jsonl"

from gpower_clone import agent as agent_mod  # noqa: E402


def _same_input(got: dict, expected: dict) -> bool:
    got = {k: v for k, v in got.items() if k != "test" and v is not None}
    return set(got) == set(expected) and all(float(got[k]) == float(v) if k != "mode" else got[k] == v
                                             for k, v in expected.items())


def _same_output(got: dict, expected: dict) -> bool:
    for key, value in expected.items():
        if key not in got:
            return False
        if isinstance(value, int):
            if got[key] != value:
                return False
        elif abs(got[key] - value) > 1e-9:
            return False
    return True


def score(item: dict, calls: list[dict], reply: str) -> dict:
    family = item["expected_family"]
    t2_calls = [c for c in calls if c["tool_input"].get("test") == "t2-indep"
                and "error" not in c["tool_output"]]
    if family == "t2-indep":
        last = t2_calls[-1] if t2_calls else None
        family_ok = last is not None and last["tool_input"].get("mode") == item["expected_input"]["mode"]
        params_ok = bool(last) and _same_input(last["tool_input"], item["expected_input"])
        result_ok = bool(last) and _same_output(last["tool_output"], item["expected_output"])
    elif family == "ambiguous":
        stated = any(s in reply for s in ("0.5", "0,5"))
        family_ok = not t2_calls or stated
        params_ok = result_ok = None
    else:
        family_ok = not t2_calls
        params_ok = result_ok = None
    return {"family_ok": family_ok, "params_ok": params_ok, "result_ok": result_ok}


async def run_all(model: str) -> list[dict]:
    from anthropic import AsyncAnthropic
    from mcp.client.session import ClientSession
    from mcp.client.stdio import stdio_client

    items = [json.loads(line) for line in QUESTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
    log_path = ROOT / agent_mod.LOG_PATH
    client = AsyncAnthropic()
    rows = []
    async with stdio_client(agent_mod._server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            tools = [{"name": t.name, "description": t.description or "",
                      "input_schema": agent_mod._input_schema(t)} for t in listed.tools]
            for item in items:
                before = log_path.read_text(encoding="utf-8").count("\n") if log_path.exists() else 0
                agent = agent_mod.Agent(client, session, tools, model)
                t0 = time.perf_counter()
                reply = await agent.ask(item["question"])
                seconds = time.perf_counter() - t0
                lines = log_path.read_text(encoding="utf-8").splitlines()[before:] if log_path.exists() else []
                calls = [json.loads(line) for line in lines]
                tokens_in = sum(c["tokens_in"] for c in calls)
                tokens_out = sum(c["tokens_out"] for c in calls)
                row = {"id": item["id"], "expected_family": item["expected_family"], "reply": reply,
                       "calls": len(calls), "tokens_in": tokens_in, "tokens_out": tokens_out,
                       "seconds": round(seconds, 2), **score(item, calls, reply)}
                rows.append(row)
                print(f"{item['id']}: family_ok={row['family_ok']} params_ok={row['params_ok']} "
                      f"result_ok={row['result_ok']} ({seconds:.1f}s)", file=sys.stderr)
    return rows


def measure_screenshot_tokens(path: Path, model: str) -> int:
    from anthropic import Anthropic

    data = base64.standard_b64encode(path.read_bytes()).decode()
    media = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    with_image = Anthropic().messages.count_tokens(model=model, messages=[{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}},
        {"type": "text", "text": "x"}]}])
    without = Anthropic().messages.count_tokens(model=model, messages=[{"role": "user", "content": "x"}])
    return with_image.input_tokens - without.input_tokens


def _pct(rows, key) -> str:
    vals = [r[key] for r in rows if r[key] is not None]
    return f"{sum(vals)}/{len(vals)} (%{100 * sum(vals) / len(vals):.0f})" if vals else "—"


def write_report(rows: list[dict], model: str, gui: dict | None) -> None:
    lines = [
        "# Ajan değerlendirme raporu",
        "",
        f"Model: `{model}` · Araç: MCP `power_analysis` · Sorular: [questions.jsonl](questions.jsonl) (kurgusal)",
        "",
        "| Ölçüt | Sonuç |",
        "|---|---|",
        f"| Doğru test ailesi / davranış seçimi | {_pct(rows, 'family_ok')} |",
        f"| Doğru parametreler (t2-indep soruları) | {_pct(rows, 'params_ok')} |",
        f"| Doğru sonuç (N, güç, α, d) | {_pct(rows, 'result_ok')} |",
        "",
        "| Soru | Beklenen aile | Aile | Parametre | Sonuç | Araç çağrısı | Token (girdi/çıktı) | Süre (s) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        mark = {True: "✔", False: "✘", None: "—"}
        lines.append(f"| {r['id']} | {r['expected_family']} | {mark[r['family_ok']]} | {mark[r['params_ok']]} | "
                     f"{mark[r['result_ok']]} | {r['calls']} | {r['tokens_in']}/{r['tokens_out']} | {r['seconds']} |")
    total_in = sum(r["tokens_in"] for r in rows)
    total_out = sum(r["tokens_out"] for r in rows)
    lines += ["", "## MCP yolu ile GUI yolu", "",
              f"- MCP yolu (ölçülen, araç çağıran yanıtların usage toplamı): {total_in} girdi + {total_out} çıktı token, "
              f"{sum(r['seconds'] for r in rows):.1f} s, 10 soruda."]
    if gui:
        per_q = gui["tokens_per_screenshot"] * gui["steps"]
        lines += [f"- GUI yolu: gerçek bir G*Power ekran görüntüsü `count_tokens` ile **{gui['tokens_per_screenshot']} token** "
                  f"ölçüldü (`{gui['screenshot']}`). Bir soruyu GUI'den çözmek en az {gui['steps']} ekran görüntüsü "
                  f"gerektiriyor; soru başına ≥ {per_q} token yalnızca görüntüler için, 10 soruda ≥ {10 * per_q}."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with open(RESULTS, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui-screenshot", type=Path)
    parser.add_argument("--gui-steps", type=int, default=7)
    args = parser.parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY tanımlı değil.", file=sys.stderr)
        return 1
    model = os.environ.get("GPOWER_AGENT_MODEL") or agent_mod.DEFAULT_MODEL
    os.chdir(ROOT)
    rows = asyncio.run(run_all(model))
    gui = None
    if args.gui_screenshot:
        gui = {"screenshot": str(args.gui_screenshot), "steps": args.gui_steps,
               "tokens_per_screenshot": measure_screenshot_tokens(args.gui_screenshot, model)}
    write_report(rows, model, gui)
    print(f"wrote {REPORT.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
