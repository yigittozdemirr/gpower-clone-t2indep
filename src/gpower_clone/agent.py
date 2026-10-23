"""Natural-language agent (SPEC 7 / CONTRACT 8, 10).

Claude + MCP stdio client.  The agent never computes numbers itself: every
number comes from the ``power_analysis`` tool of ``gpower-clone-mcp``.
Every tool call is appended to ``logs/agent_calls.jsonl``.

Usage:
    gpower-clone-agent "soru"      # single question
    gpower-clone-agent             # interactive (empty line / Ctrl+Z / Ctrl+D quits)

Environment:
    ANTHROPIC_API_KEY   required
    GPOWER_AGENT_MODEL  model id (default: claude-sonnet-5-5)
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "claude-sonnet-5-5"
LOG_PATH = Path("logs") / "agent_calls.jsonl"
MAX_TOOL_ROUNDS = 8
MAX_TOKENS = 2048

SYSTEM_PROMPT = """\
Sen klinik araştırmacılara örneklem büyüklüğü ve güç analizi konusunda yardım eden bir asistansın.
Tek bir aracın var: `power_analysis`. Bu araç G*Power'daki "t tests – Means: Difference between two
independent means (two groups)" analizini (test kimliği `t2-indep`) yapar; örnek: ilaç grubu ile plasebo grubu.

KESİN KURALLAR
1. Hiçbir sayıyı kendin hesaplama, tahmin etme ya da yuvarlayarak türetme. Örneklem büyüklüğü, güç,
   alpha, kritik t, etki büyüklüğü gibi her sayısal sonuç yalnızca `power_analysis` aracından gelir.
   Aracın döndürdüğü değerleri aktar; n1, n2, n_total ve df değerlerini aynen yaz. Kayıp/terk oranına
   göre büyütme gibi ek aritmetik yapma; gerekirse bunu kullanıcıya nitel olarak hatırlat.
2. Etki büyüklüğü: "küçük / orta / büyük etki" bir KATEGORİDİR, bir değer değildir. Cohen'in (1988)
   geleneksel eşikleri d için 0.2 / 0.5 / 0.8'dir. Kullanıcı yalnızca kategori söylediyse değeri sessizce
   varsayma: ya kullanıcıya hangi d değerini kullanmak istediğini sor ya da varsayımını yanıtında AÇIKÇA
   yaz (ör. "Orta etki için Cohen'in geleneksel d = 0.5 değerini varsaydım; mümkünse literatürden ya da
   pilot çalışmadan gelen bir değer kullanın.").
3. Hipotez yönü (`tails`): Araştırmacı yön iddia ediyorsa ("daha iyi", "daha az", "azaltır", "artırır",
   "üstün") tek kuyruk (1) öner; yalnızca "fark var mı / farklı mı" diyorsa çift kuyruk (2) kullan.
   Yön açık değilse daha temkinli olan çift kuyruğu seç. Hangisini neden seçtiğini yanıtında söyle;
   bu kararın veriden önce, etik kurula sunulan hipotezde verilmesi gerektiğini hatırlat.
4. Eksik bilgi: Etki büyüklüğü, alpha, hedef güç (ya da modun gerektirdiği n1/n2) eksikse aracı
   çağırmadan ÖNCE kullanıcıya sor. Değer uydurma. Kullanıcı "standart değerler" derse alpha = 0.05 ve
   güç = 0.80 kullan ve bunu açıkça söyle. Grup oranı belirtilmemişse eşit grupları (ratio = 1)
   varsayabilirsin ama bunu açıkça yaz.
5. Yalnızca kurgusal araştırma senaryoları. Gerçek hasta verisi, kimlik bilgisi ya da bir kişiyi
   tanımlayabilecek bilgi isteme, kaydetme, tekrar etme; kullanıcı böyle bir bilgi verirse bunu
   kullanmayacağını söyle.

ARAÇ KULLANIMI
- `test` her zaman "t2-indep". `mode` şunlardan biri:
  a-priori (gerekli örneklem: tails, d, alpha, power, ratio = N2/N1),
  post-hoc (ulaşılan güç: tails, d, alpha, n1, n2),
  compromise (β/α oranına göre α ve güç: tails, d, beta_alpha_ratio, n1, n2),
  criterion (gerekli α: tails, d, power, n1, n2),
  sensitivity (saptanabilir en küçük d: tails, alpha, power, n1, n2).
- Yalnızca o modun alanlarını gönder; varsayılan değer yoktur.
- Araç hata JSON'u ({"error", "code", "field"}) döndürürse hatayı kullanıcıya açıkla; girdiyi
  düzeltebiliyorsan düzeltip yeniden çağır, düzeltemiyorsan sor.

YANIT BİÇİMİ (Türkçe, kısa)
- Kullanılan girdiler ve yaptığın her varsayım (etki büyüklüğü, kuyruk sayısı, oran).
- Araçtan gelen sonuçlar (ör. n1, n2, toplam N, gerçekleşen güç).
- Bir iki cümlelik klinik yorum.
"""


def _now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def log_tool_call(question: str, tool_input: dict, tool_output_text: str,
                  tokens_in: int, tokens_out: int, path: Path = LOG_PATH) -> dict:
    """Append one CONTRACT 8 line to logs/agent_calls.jsonl and return the record."""
    try:
        parsed: Any = json.loads(tool_output_text)
    except (TypeError, ValueError):
        parsed = {"raw": tool_output_text}
    rec = {
        "ts": _now_iso(),
        "question": question,
        "tool_input": tool_input,
        "tool_output": parsed,
        "tokens_in": int(tokens_in),
        "tokens_out": int(tokens_out),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def _server_params():
    from mcp.client.stdio import StdioServerParameters

    exe = shutil.which("gpower-clone-mcp")
    if exe:
        return StdioServerParameters(command=exe, args=[])
    return StdioServerParameters(command=sys.executable, args=["-m", "gpower_clone.mcp_server"])


def _tool_text(result) -> str:
    parts = []
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "".join(parts)


def _input_schema(tool) -> dict:
    schema = getattr(tool, "input_schema", None)
    if schema is None:
        schema = getattr(tool, "inputSchema", None)
    return dict(schema or {"type": "object"})


def _block_param(block) -> dict:
    """Response content block -> request content block (assistant turn replay)."""
    kind = getattr(block, "type", "")
    if kind == "text":
        return {"type": "text", "text": block.text}
    if kind == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": dict(block.input or {})}
    return block.model_dump(exclude_none=True)


class Agent:
    def __init__(self, client, session, tools: list[dict], model: str):
        self.client = client
        self.session = session
        self.tools = tools
        self.model = model
        self.messages: list[dict] = []

    async def ask(self, question: str) -> str:
        self.messages.append({"role": "user", "content": question})
        final_text = ""
        for _ in range(MAX_TOOL_ROUNDS + 1):
            resp = await self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=self.tools,
                messages=self.messages,
            )
            assistant_content = [_block_param(b) for b in resp.content]
            self.messages.append({"role": "assistant", "content": assistant_content})
            texts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
            final_text = "\n".join(t for t in texts if t)
            tool_uses = [b for b in resp.content if getattr(b, "type", "") == "tool_use"]
            if not tool_uses:
                return final_text
            usage = getattr(resp, "usage", None)
            tin = getattr(usage, "input_tokens", 0) or 0
            tout = getattr(usage, "output_tokens", 0) or 0
            results = []
            for tu in tool_uses:
                args = dict(tu.input or {})
                res = await self.session.call_tool(tu.name, args)
                text = _tool_text(res)
                log_tool_call(question, args, text, tin, tout)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": text,
                    "is_error": bool(getattr(res, "is_error", getattr(res, "isError", False))),
                })
            self.messages.append({"role": "user", "content": results})
        return final_text or "Araç çağrısı sınırına ulaşıldı; lütfen soruyu daraltın."


async def _run(question: str | None) -> int:
    import anyio
    from anthropic import AsyncAnthropic
    from mcp.client.session import ClientSession
    from mcp.client.stdio import stdio_client

    model = os.environ.get("GPOWER_AGENT_MODEL") or DEFAULT_MODEL
    client = AsyncAnthropic()
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            tools = [{"name": t.name, "description": t.description or "",
                      "input_schema": _input_schema(t)} for t in listed.tools]
            agent = Agent(client, session, tools, model)
            if question is not None:
                print(await agent.ask(question))
                return 0
            print("gpower-clone ajanı (t2-indep). Çıkmak için boş satır girin.", file=sys.stderr)
            while True:
                try:
                    q = await anyio.to_thread.run_sync(input, "Soru> ")
                except EOFError:
                    break
                if not q.strip():
                    break
                print(await agent.ask(q.strip()))
                print()
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.stderr.write(
            "Hata: ANTHROPIC_API_KEY ortam değişkeni tanımlı değil. Ajanı çalıştırmak için Anthropic API "
            "anahtarınızı bu değişkene atayın (ör. PowerShell: $env:ANTHROPIC_API_KEY = \"...\").\n")
        return 1
    try:
        import anthropic  # noqa: F401
        import anyio
        import mcp  # noqa: F401
    except ImportError:
        sys.stderr.write("Hata: ajan için 'anthropic' ve 'mcp' paketleri gerekli: "
                         "pip install 'gpower-clone[agent]'\n")
        return 1
    question = " ".join(argv).strip() if argv else None
    try:
        return anyio.run(_run, question or None)
    except KeyboardInterrupt:
        return 130
    except Exception as e:  # network / API errors: Turkish message, exit 1
        sys.stderr.write(f"Hata: ajan çalıştırılamadı: {type(e).__name__}: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
