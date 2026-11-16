"""讀 bronze/moi-ris-year-table/source.html（內政部戶政司〈年歲對照表〉）的表格，給 test_agreement.py 與 tests/ 核對 golden。

不在簽核對象內，也不給 rule.py、rule.js、sampler.py 使用：規則與抽樣不讀 bronze，golden 與每一題才回頭對表。
只用標準庫。表的列序照原檔：第 1 列是「民國120／2031」，第 120 列是「民國1／1912」，之後是民國前 1–29 年。
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

BRONZE = Path(__file__).resolve().parents[3] / "bronze" / "moi-ris-year-table"
HEADER = ["民國", "西元", "清代", "日據時代", "農曆歲次"]


class _Table(HTMLParser):
    def __init__(self):
        super().__init__()
        self.head: list[str] = []
        self.rows: list[list[str]] = []
        self._in = None          # "th" / "td"
        self._section = None     # "thead" / "tbody"
        self._cell = ""

    def handle_starttag(self, tag, attrs):
        if tag in ("thead", "tbody"):
            self._section = tag
        elif tag == "tr" and self._section == "tbody":
            self.rows.append([])
        elif tag in ("th", "td"):
            self._in, self._cell = tag, ""

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self._in == tag:
            text = self._cell.strip()
            (self.head if self._section == "thead" else self.rows[-1]).append(text)
            self._in = None
        elif tag in ("thead", "tbody"):
            self._section = None

    def handle_data(self, data):
        if self._in:
            self._cell += data


def rows(bronze: Path = BRONZE) -> list[dict]:
    """[{row: 列號（從 1 起）, label: '民國115', roc: 115（民國前 n 年是 -n）, ad: 2026}]，照原檔順序。"""
    prov = json.loads((bronze / "provenance.json").read_text(encoding="utf-8"))
    p = _Table()
    p.feed((bronze / prov["source_file"]).read_text(encoding="utf-8"))
    if p.head != HEADER:
        raise ValueError(f"表頭不是 {HEADER}：{p.head}")
    out = []
    for i, r in enumerate(p.rows, start=1):
        m = re.fullmatch(r"民國(前)?(\d+)", r[0])
        if not m or not re.fullmatch(r"\d{4}", r[1]):
            raise ValueError(f"第 {i} 列看不懂：{r}")
        out.append({"row": i, "label": r[0], "roc": -int(m.group(2)) if m.group(1) else int(m.group(2)), "ad": int(r[1])})
    return out


def roc_rows(bronze: Path = BRONZE) -> dict[int, tuple[int, int]]:
    """民國 1 年以後的列：{民國年: (列號, 西元年)}。"""
    return {r["roc"]: (r["row"], r["ad"]) for r in rows(bronze) if r["roc"] >= 1}
