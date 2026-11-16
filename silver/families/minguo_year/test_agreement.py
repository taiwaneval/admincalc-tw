"""出貨前檢查：
1. golden cases 全過 Python 實作
2. golden cases 全過 JS 實作（Node）
3. 每筆 golden 標的 bronze_row 確實是〈年歲對照表〉的那一列，民國年與西元年和 golden 一致
4. 表上民國 1–120 年的每一列：兩份實作的兩個方向都等於表（全量，不抽樣）；表上沒有任何一列與「民國 = 西元 − 1911」衝突
5. 隨機 N 組合法輸入（三種題型），Python 與 JS 答案逐一相同（N-version agreement）
6. 不合法的輸入兩份實作都報錯
7. 性質：
   a. 來回換算回到原值（民國 → 西元 → 民國）
   b. 民國年每加 1，西元年也加 1
   c. 日期題的答案與月日無關（每個合法月日都與同年的年份題相同）
"""
from __future__ import annotations

import importlib.util
import json
import random
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent


def _load_sibling(name: str):
    """以唯一模組名載入同目錄的 .py（不用裸名稱 import rule，避免與其他 family 的 rule 模組衝突）。"""
    s = importlib.util.spec_from_file_location(f"{HERE.name}_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


rule = _load_sibling("rule")
table = _load_sibling("bronze_table")

RUNNER = """
const R = require(process.argv[2]);
let s=''; process.stdin.on('data', d => s += d).on('end', () => {
  const cases = JSON.parse(s);
  process.stdout.write(JSON.stringify(cases.map(c => {
    try { return R.compute(c.task, c.year, c.month, c.day).total; } catch (e) { return 'ERR'; }
  })));
});
"""

N = None
INVALID = [
    {"task": "roc_to_ad", "year": 0, "month": N, "day": N},          # 沒有民國 0 年
    {"task": "roc_to_ad", "year": -1, "month": N, "day": N},         # 民國前不在範圍
    {"task": "roc_to_ad", "year": 121, "month": N, "day": N},        # 表只到民國 120 年
    {"task": "roc_to_ad", "year": 115.5, "month": N, "day": N},      # 不是整數
    # 115.0 不列：Python 拒絕 float，但經 JSON 傳給 JS 後就是整數 115，JS 分辨不出來
    {"task": "roc_to_ad", "year": "115", "month": N, "day": N},      # 字串
    {"task": "roc_to_ad", "year": True, "month": N, "day": N},       # bool
    {"task": "roc_to_ad", "year": N, "month": N, "day": N},
    {"task": "ad_to_roc", "year": 1911, "month": N, "day": N},       # 民國前 1 年
    {"task": "ad_to_roc", "year": 2032, "month": N, "day": N},
    {"task": "ad_to_roc", "year": 115, "month": N, "day": N},        # 把民國年當西元年輸入
    {"task": "roc_date_to_ad", "year": 115, "month": 2, "day": 29},  # 2 月 29 日不在範圍（閏年另開票）
    {"task": "roc_date_to_ad", "year": 113, "month": 2, "day": 29},  # 2024 是閏年，仍不在範圍
    {"task": "roc_date_to_ad", "year": 115, "month": 2, "day": 30},
    {"task": "roc_date_to_ad", "year": 115, "month": 4, "day": 31},
    {"task": "roc_date_to_ad", "year": 115, "month": 13, "day": 1},
    {"task": "roc_date_to_ad", "year": 115, "month": 0, "day": 1},
    {"task": "roc_date_to_ad", "year": 115, "month": 1, "day": 0},
    {"task": "roc_date_to_ad", "year": 115, "month": 1, "day": 32},
    {"task": "roc_date_to_ad", "year": 115, "month": N, "day": 1},
    {"task": "roc_date_to_ad", "year": 115, "month": 3, "day": N},
    {"task": "roc_date_to_ad", "year": 115, "month": "3", "day": 1},
    {"task": "roc_date_to_ad", "year": 0, "month": 1, "day": 1},
    {"task": "roc_date_to_ad", "year": 121, "month": 1, "day": 1},
    {"task": "ad_date_to_roc", "year": 2026, "month": 3, "day": 1},  # 未知題型
]

DAYS = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}   # 2 月 29 日不在範圍


def run_js(cases: list[dict]) -> list:
    runner = HERE / ".runner.js"
    runner.write_text(RUNNER)
    out = subprocess.run(["node", str(runner), str(HERE / "rule.js")],
                         input=json.dumps(cases), capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def py_total(c: dict):
    try:
        return rule.compute(c["task"], c["year"], c["month"], c["day"])["total"]
    except ValueError:
        return "ERR"


def random_cases(rng: random.Random, n: int) -> list[dict]:
    out = []
    for i in range(n):
        t = ("roc_to_ad", "ad_to_roc", "roc_date_to_ad")[i % 3]
        roc = rng.randint(1, 120)
        if t == "ad_to_roc":
            out.append({"task": t, "year": roc + 1911, "month": N, "day": N})
        elif t == "roc_to_ad":
            # 年份題不使用月日：偶爾帶入任意值，兩份實作都要忽略
            m, d = (rng.randint(-5, 40), rng.randint(-5, 40)) if rng.random() < 0.2 else (N, N)
            out.append({"task": t, "year": roc, "month": m, "day": d})
        else:
            m = rng.randint(1, 12)
            out.append({"task": t, "year": roc, "month": m, "day": rng.randint(1, DAYS[m])})
    return out


def main(n_random: int = 6000, seed: int = 20261113) -> int:
    spec = yaml.safe_load((HERE / "spec.yaml").read_text(encoding="utf-8"))
    golden = spec["golden_cases"]
    rows = {r["row"]: r for r in table.rows()}
    fails = 0

    # 1. golden vs Python
    for g in golden:
        got = py_total(g["input"])
        ok = got == g["expected"]
        fails += not ok
        print(f"[py ] {g['id']} {'OK ' if ok else 'FAIL'} expected={g['expected']} got={got} ({g['status']})")

    # 2. golden vs JS
    for g, got in zip(golden, run_js([g["input"] for g in golden])):
        ok = got == g["expected"]
        fails += not ok
        print(f"[js ] {g['id']} {'OK ' if ok else 'FAIL'} expected={g['expected']} got={got}")

    # 3. golden 標的列
    for g in golden:
        r = rows.get(g.get("bronze_row"))
        i = g["input"]
        roc = i["year"] - 1911 if i["task"] == "ad_to_roc" else i["year"]   # 只用來找列；答案仍以表的另一欄核對
        if r is None:
            ok = False
        elif i["task"] == "ad_to_roc":
            ok = r["ad"] == i["year"] and r["roc"] == g["expected"]
        else:
            ok = r["roc"] == i["year"] and r["ad"] == g["expected"]
        ok = ok and f"第 {g.get('bronze_row')} 列" in g["source"] and r["label"] in g["source"] and roc >= 1
        fails += not ok
        print(f"[row] {g['id']} {'OK ' if ok else 'FAIL'} bronze_row={g.get('bronze_row')} {r and (r['label'], r['ad'])}")

    # 4. 全表
    all_rows = list(rows.values())
    conflict = [r for r in all_rows if r["ad"] != (r["roc"] + 1911 if r["roc"] >= 1 else 1912 + r["roc"])]
    roc_rows = [r for r in all_rows if r["roc"] >= 1]
    cases = ([{"task": "roc_to_ad", "year": r["roc"], "month": N, "day": N} for r in roc_rows]
             + [{"task": "ad_to_roc", "year": r["ad"], "month": N, "day": N} for r in roc_rows])
    want = [r["ad"] for r in roc_rows] + [r["roc"] for r in roc_rows]
    py, js = [py_total(c) for c in cases], run_js(cases)
    table_fail = sum(p != w for p, w in zip(py, want)) + sum(j != w for j, w in zip(js, want))
    fails += len(conflict) + table_fail + (len(roc_rows) != 120) + (len(all_rows) != 149)
    print(f"[tbl] rows={len(all_rows)} roc>=1 rows={len(roc_rows)} conflicts_with_minus_1911={len(conflict)} "
          f"py/js_mismatch_vs_table={table_fail}")

    # 5. random agreement
    rng = random.Random(seed)
    cases = random_cases(rng, n_random)
    py, js = [py_total(c) for c in cases], run_js(cases)
    mism = [(c, p, j) for c, p, j in zip(cases, py, js) if p != j]
    fails += len(mism) + py.count("ERR")
    print(f"[agr] random n={n_random} seed={seed} mismatches={len(mism)} py_errors={py.count('ERR')}")
    for c, p, j in mism[:10]:
        print("      ", c, "py=", p, "js=", j)

    # 6. 不合法的輸入：兩份實作都要拒絕
    js_bad = run_js(INVALID)
    not_rejected = [(c, py_total(c), j) for c, j in zip(INVALID, js_bad) if (py_total(c), j) != ("ERR", "ERR")]
    fails += len(not_rejected)
    print(f"[bad] invalid inputs n={len(INVALID)} not_rejected_by_both={len(not_rejected)}")
    for c, p, j in not_rejected:
        print("      ", c, "py=", p, "js=", j)

    # 7. 性質
    roundtrip = sum(rule.compute("ad_to_roc", rule.compute("roc_to_ad", y)["total"])["total"] != y for y in range(1, 121))
    step = sum(rule.compute("roc_to_ad", y + 1)["total"] - rule.compute("roc_to_ad", y)["total"] != 1 for y in range(1, 120))
    date_cases = [{"task": "roc_date_to_ad", "year": y, "month": m, "day": d}
                  for y in (1, 38, 89, 100, 115, 120) for m in DAYS for d in range(1, DAYS[m] + 1)]
    date_want = [rule.compute("roc_to_ad", c["year"])["total"] for c in date_cases]
    date_py, date_js = [py_total(c) for c in date_cases], run_js(date_cases)
    date_viol = sum(p != w for p, w in zip(date_py, date_want)) + sum(j != w for j, w in zip(date_js, date_want))
    fails += roundtrip + step + date_viol
    print(f"[prop] roundtrip_violations={roundtrip} step_violations={step} "
          f"date_depends_on_month_day={date_viol} (n={len(date_cases)} dates × 2 implementations)")

    print("RESULT:", "PASS" if fails == 0 else f"FAIL ({fails})")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
