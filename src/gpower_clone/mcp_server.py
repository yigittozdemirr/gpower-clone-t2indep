"""MCP stdio server exposing one tool, ``power_analysis`` (SPEC 6 / CONTRACT 7).

The tool forwards its arguments unchanged to ``engine.run`` and returns
``engine.to_json(result)`` as a single TextContent: byte-identical to the CLI
stdout line (without the trailing newline).  No calculation or validation
happens here; the input schema is deliberately loose so that type errors are
reported by the engine exactly as on the CLI.
"""

from __future__ import annotations

import sys
from typing import Any

from . import __version__, engine

TOOL_NAME = "power_analysis"

TOOL_DESCRIPTION = (
    "G*Power 't2-indep' güç analizi: iki bağımsız grubun ortalamaları arasındaki fark için t testi "
    "(ör. ilaç ve plasebo grubu). Alan adları CLI ile aynıdır. 'test' her zaman 't2-indep'. "
    "'mode' ve gerekli alanlar: "
    "a-priori: tails, d, alpha, power, ratio (N2/N1) -> n1, n2, n_total, actual_power "
    "(gruplardan biri 2'den küçükse ek 'warning' alanı); "
    "post-hoc: tails, d, alpha, n1, n2 -> power; "
    "compromise: tails, d, beta_alpha_ratio, n1, n2 -> alpha, beta, power; "
    "criterion: tails, d, power, n1, n2 -> alpha; "
    "sensitivity: tails, alpha, power, n1, n2 -> d. "
    "Moda ait olmayan alan göndermeyin (hata verir). Varsayılan değer yoktur. "
    "Çıktı tek satır JSON'dur; hata durumunda {\"error\", \"code\", \"field\"} döner."
)

_NUM = ["number", "string"]

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "test": {"type": "string", "description": "Test kimliği; yalnızca 't2-indep'"},
        "mode": {"type": "string",
                 "description": "a-priori | post-hoc | compromise | criterion | sensitivity"},
        "tails": {"type": _NUM, "description": "Kuyruk sayısı: 1 (yönlü hipotez) ya da 2 (yönsüz)"},
        "d": {"type": _NUM, "description": "Cohen d etki büyüklüğü (> 0)"},
        "alpha": {"type": _NUM, "description": "I. tip hata olasılığı, 0 < alpha < 1"},
        "power": {"type": _NUM, "description": "Hedef güç (1 - beta), 0 < power < 1"},
        "ratio": {"type": _NUM, "description": "Dağıtım oranı N2/N1 (0.01 <= ratio <= 100), yalnızca a-priori"},
        "n1": {"type": _NUM, "description": "Grup 1 örneklem büyüklüğü (tam sayı >= 2)"},
        "n2": {"type": _NUM, "description": "Grup 2 örneklem büyüklüğü (tam sayı >= 2)"},
        "beta_alpha_ratio": {"type": _NUM, "description": "beta/alpha oranı (> 0), yalnızca compromise"},
    },
    "required": ["test", "mode"],
    "additionalProperties": True,
}


def call_power_analysis(arguments: dict[str, Any] | None) -> tuple[str, bool]:
    """Pure function behind the tool: (json text, is_error)."""
    obj, code = engine.run(dict(arguments or {}))
    return engine.to_json(obj), code != 0


def _types():
    from mcp import types  # same classes as the ``mcp_types`` package in mcp >= 2

    return types


def _tool(types):
    return types.Tool(name=TOOL_NAME, description=TOOL_DESCRIPTION, inputSchema=INPUT_SCHEMA)


def _result(types, text: str, is_error: bool):
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)], isError=is_error)


def build_server():
    from mcp.server.lowlevel import Server

    types = _types()

    async def on_list_tools(ctx, params):
        return types.ListToolsResult(tools=[_tool(types)])

    async def on_call_tool(ctx, params):
        if params.name != TOOL_NAME:
            text = engine.to_json({"error": f"Bilinmeyen araç: {params.name}", "code": "UNSUPPORTED",
                                   "field": None})
            return _result(types, text, True)
        text, is_err = call_power_analysis(params.arguments)
        return _result(types, text, is_err)

    try:  # mcp >= 2: constructor-registered handlers
        return Server("gpower-clone", version=__version__,
                      on_list_tools=on_list_tools, on_call_tool=on_call_tool)
    except TypeError:  # pragma: no cover - mcp 1.x decorator API
        server = Server("gpower-clone", version=__version__)

        @server.list_tools()
        async def _list_tools():
            return [_tool(types)]

        try:
            deco = server.call_tool(validate_input=False)
        except TypeError:
            deco = server.call_tool()

        @deco
        async def _call_tool(name: str, arguments: dict):
            if name != TOOL_NAME:
                text = engine.to_json({"error": f"Bilinmeyen araç: {name}", "code": "UNSUPPORTED",
                                       "field": None})
                return _result(types, text, True)
            text, is_err = call_power_analysis(arguments)
            return _result(types, text, is_err)

        return server


async def _serve() -> None:
    from mcp.server.stdio import stdio_server

    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> int:
    try:
        import anyio
    except ImportError:
        sys.stderr.write("MCP sunucusu için 'mcp' paketi gerekli: pip install 'gpower-clone[mcp]'\n")
        return 1
    try:
        import mcp  # noqa: F401
    except ImportError:
        sys.stderr.write("MCP sunucusu için 'mcp' paketi gerekli: pip install 'gpower-clone[mcp]'\n")
        return 1
    anyio.run(_serve)
    return 0


if __name__ == "__main__":
    sys.exit(main())
