"""SPEC 6: the real MCP stdio server returns the CLI stdout line byte-for-byte."""

from __future__ import annotations

import sys

import pytest

pytest.importorskip("mcp")
import anyio  # noqa: E402

from conftest import load_vectors, run_cli, to_argv  # noqa: E402

T2 = "t2-indep"

ERROR_AND_EXTRA_INPUTS = [
    {"test": T2, "mode": "post-hoc", "tails": 1, "d": "0,05", "alpha": 0.05, "n1": 10, "n2": 10},
    {"test": T2, "mode": "post-hoc", "tails": 1, "d": 0.5, "alpha": 0.05, "n1": "88.0", "n2": 10},
    {"test": T2, "mode": "post-hoc", "tails": 1, "d": 0.5, "alpha": 0.05, "n1": 10, "n2": 10,
     "power": 0.8},
    {"test": T2, "mode": "post-hoc", "tails": 1, "d": 0.5, "alpha": 0.05, "n1": 10},
    {"test": T2, "mode": "a-priori", "tails": 2, "d": 0.5, "alpha": 0.05, "power": 0.04, "ratio": 1},
    {"test": T2, "mode": "a-priori", "tails": 3, "d": 0.5, "alpha": 0.05, "power": 0.8, "ratio": 1},
    {"test": T2, "mode": "power"},
    {"test": "t-paired", "mode": "a-priori"},
    {"mode": "a-priori"},
    {"test": T2, "mode": "a-priori", "tails": 2, "d": 1e-10, "alpha": 0.05, "power": 0.8, "ratio": 1},
    {"test": T2, "mode": "a-priori", "tails": 2, "d": 0.001, "alpha": 0.05, "power": 0.95, "ratio": 1},
    {"test": T2, "mode": "a-priori", "tails": 2, "d": 10, "alpha": 0.05, "power": 0.8, "ratio": 0.1},
    {"test": T2, "mode": "a-priori", "tails": 2, "d": 0.5, "alpha": 0.05, "power": 0.8, "ratio": 100.5},
    {"test": T2, "mode": "sensitivity", "tails": 2, "alpha": 0.05, "power": 0.05, "n1": 20, "n2": 20},
    {"test": T2, "mode": "a-priori", "tails": 2, "d": 0.3, "alpha": 0.05, "power": 0.8, "ratio": 2.5},
    {"test": T2, "mode": "sensitivity", "tails": 2, "alpha": 0.05, "power": 0.8, "n1": 17, "n2": 23},
]

INPUTS = [v["input"] for v in load_vectors()] + ERROR_AND_EXTRA_INPUTS


async def _mcp_texts(inputs):
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    params = StdioServerParameters(command=sys.executable, args=["-m", "gpower_clone.mcp_server"])
    texts = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert [t.name for t in tools.tools] == ["power_analysis"]
            for args in inputs:
                res = await session.call_tool("power_analysis", dict(args))
                assert len(res.content) == 1 and res.content[0].type == "text"
                texts.append(res.content[0].text)
    return texts


@pytest.fixture(scope="module")
def mcp_texts():
    return anyio.run(_mcp_texts, INPUTS)


def test_25_public_vectors_and_errors_byte_identical(mcp_texts):
    assert len(mcp_texts) == len(INPUTS) == 25 + len(ERROR_AND_EXTRA_INPUTS)
    for args, mcp_text in zip(INPUTS, mcp_texts):
        stdout, _, _, _ = run_cli(to_argv(args))
        assert stdout.endswith(b"\n")
        assert mcp_text.encode("utf-8") == stdout[:-1], args


def test_tool_schema_is_loose():
    from gpower_clone.mcp_server import INPUT_SCHEMA

    assert INPUT_SCHEMA["required"] == ["test", "mode"]
    for name in ("tails", "d", "alpha", "power", "ratio", "n1", "n2", "beta_alpha_ratio"):
        assert set(INPUT_SCHEMA["properties"][name]["type"]) == {"number", "string"}
