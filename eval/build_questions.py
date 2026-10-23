"""Build eval/questions.jsonl: 10 fictional clinical questions with the expected family, parameters and result.

Expected numbers come from the engine (the agent must reproduce them through the MCP tool).
    uv run python eval/build_questions.py
"""

import json
from pathlib import Path

from gpower_clone import engine

QUESTIONS = [
    ("Q01", "Yeni bir antihipertansif ilacı plaseboyla karşılaştıracağız. Literatürde etki büyüklüğü d = 0.5. "
            "İki grup arasında fark olup olmadığına bakacağız; alfa 0.05, güç %80, gruplar eşit. Her gruba kaç hasta gerekir?",
     "t2-indep", {"mode": "a-priori", "tails": 2, "d": 0.5, "alpha": 0.05, "power": 0.8, "ratio": 1}),
    ("Q02", "Yeni ağrı kesicinin ağrıyı plasebodan DAHA FAZLA azalttığını göstermek istiyoruz. d = 0.4, alfa 0.05, "
            "güç 0.90, eşit gruplar. Toplam kaç katılımcı lazım?",
     "t2-indep", {"mode": "a-priori", "tails": 1, "d": 0.4, "alpha": 0.05, "power": 0.9, "ratio": 1}),
    ("Q03", "Grup 1 ilaç, grup 2 plasebo olsun. Etik nedenlerle plasebo grubu ilaç grubunun yarısı kadar olacak "
            "(N2/N1 = 0.5). d = 0.6, iki yönlü test, alfa 0.05, güç 0.80. Grup büyüklükleri ne olmalı?",
     "t2-indep", {"mode": "a-priori", "tails": 2, "d": 0.6, "alpha": 0.05, "power": 0.8, "ratio": 0.5}),
    ("Q04", "Kurgusal pilot çalışmamızda ilaç grubunda 25, plasebo grubunda 20 kişi var. d = 0.7 bekliyorsak, "
            "iki yönlü alfa 0.05 ile testin gücü ne olur?",
     "t2-indep", {"mode": "post-hoc", "tails": 2, "d": 0.7, "alpha": 0.05, "n1": 25, "n2": 20}),
    ("Q05", "İlaç ve plasebo gruplarının her birinde 40 kişi olacak. İki yönlü alfa 0.05 ve %80 güçle "
            "saptayabileceğimiz en küçük etki büyüklüğü d nedir?",
     "t2-indep", {"mode": "sensitivity", "tails": 2, "alpha": 0.05, "power": 0.8, "n1": 40, "n2": 40}),
    ("Q06", "İlaç ile plaseboyu karşılaştıracağız, orta düzeyde bir etki bekliyoruz. Kaç kişi gerekir?",
     "ambiguous", None),
    ("Q07", "Aynı hastaların tansiyonunu tedaviden önce ve sonra ölçeceğiz. dz = 0.5, alfa 0.05, güç 0.95. "
            "Kaç hasta gerekir?",
     "t-paired", None),
    ("Q08", "Üç farklı doz grubunu (düşük, orta, yüksek) karşılaştıracağız. f = 0.25, alfa 0.05, güç 0.80. "
            "Toplam kaç hasta gerekir?",
     "anova-oneway", None),
    ("Q09", "Her grupta 30 hasta var; ilaç ve plasebo arasında d = 0.5'lik bir farkı iki yönlü testte %80 güçle "
            "yakalamak istiyoruz. Bunun için alfa ne olmalı?",
     "t2-indep", {"mode": "criterion", "tails": 2, "d": 0.5, "power": 0.8, "n1": 30, "n2": 30}),
    ("Q10", "Grup 1 plasebo, grup 2 ilaç olsun; ilaç grubu plasebonun iki katı olacak (N2/N1 = 2). d = 0.3, "
            "iki yönlü test, alfa 0.01, güç 0.90. Her gruba kaç kişi?",
     "t2-indep", {"mode": "a-priori", "tails": 2, "d": 0.3, "alpha": 0.01, "power": 0.9, "ratio": 2}),
]


def main() -> None:
    out = Path(__file__).with_name("questions.jsonl")
    with open(out, "w", encoding="utf-8") as fh:
        for qid, question, family, params in QUESTIONS:
            expected = None
            if params:
                expected, code = engine.run({"test": "t2-indep", **params})
                assert code == 0, expected
            fh.write(json.dumps({"id": qid, "question": question, "expected_family": family,
                                 "expected_input": params, "expected_output": expected},
                                ensure_ascii=False) + "\n")
    print(f"{len(QUESTIONS)} questions -> {out.name}")


if __name__ == "__main__":
    main()
