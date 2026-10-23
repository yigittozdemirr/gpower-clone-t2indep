"""Agent plumbing without network: API-key check and the CONTRACT 8 log line."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

pytest.importorskip("mcp")
import anyio  # noqa: E402

from gpower_clone import agent  # noqa: E402


def test_missing_api_key_turkish_error():
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    proc = subprocess.run([sys.executable, "-m", "gpower_clone.agent", "soru"], env=env,
                          capture_output=True, timeout=60)
    assert proc.returncode == 1
    assert proc.stdout == b""
    assert "ANTHROPIC_API_KEY" in proc.stderr.decode("utf-8", "replace")


class _FakeMessages:
    def __init__(self):
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        assert kwargs["tools"][0]["name"] == "power_analysis"
        if self.calls == 1:
            block = SimpleNamespace(type="tool_use", id="tu_1", name="power_analysis",
                                    input={"test": "t2-indep", "mode": "a-priori", "tails": 2, "d": 0.5,
                                           "alpha": 0.05, "power": 0.8, "ratio": 1})
            return SimpleNamespace(content=[block],
                                   usage=SimpleNamespace(input_tokens=321, output_tokens=45))
        last = kwargs["messages"][-1]["content"][0]
        assert last["type"] == "tool_result" and '"n1": 64' in last["content"]
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="Her grupta 64 kişi.")],
                               usage=SimpleNamespace(input_tokens=400, output_tokens=12))


def test_tool_loop_logs_contract_line(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    async def scenario():
        from mcp.client.session import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        params = StdioServerParameters(command=sys.executable, args=["-m", "gpower_clone.mcp_server"])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                tools = [{"name": t.name, "description": t.description,
                          "input_schema": agent._input_schema(t)} for t in listed.tools]
                client = SimpleNamespace(messages=_FakeMessages())
                ag = agent.Agent(client, session, tools, "fake-model")
                return await ag.ask("Orta etki için kaç hasta gerekir? (kurgusal)")

    answer = anyio.run(scenario)
    assert answer == "Her grupta 64 kişi."
    lines = (tmp_path / "logs" / "agent_calls.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert list(rec) == ["ts", "question", "tool_input", "tool_output", "tokens_in", "tokens_out"]
    assert rec["question"] == "Orta etki için kaç hasta gerekir? (kurgusal)"
    assert rec["tool_input"]["mode"] == "a-priori"
    assert rec["tool_output"]["n1"] == 64 and rec["tool_output"]["n2"] == 64
    assert (rec["tokens_in"], rec["tokens_out"]) == (321, 45)
    assert "T" in rec["ts"] and rec["ts"][-6] in "+-"


def test_system_prompt_rules():
    p = agent.SYSTEM_PROMPT
    assert "KATEGORİ" in p and "0.5" in p
    assert "tek kuyruk" in p and "çift kuyruk" in p
    assert "kendin hesaplama" in p
    assert agent.DEFAULT_MODEL == "claude-sonnet-5-5"
