"""出貨前檢查：
1. golden cases 全過 Python 實作
2. golden cases 全過 JS 實作（Node）
3. 隨機 N 組合法輸入（三種題型 × 兩種除數），Python 與 JS 答案逐一相同（N-version agreement）
4. 不合法的輸入兩份實作都報錯
5. 性質：
   a. 舊規則有效 ⇒ 新規則有效（新規則包含舊規則；附件第二節只改整除條件）
   b. 能用的第 8 碼個數只由第 7 位是否為 7 決定：現行 2 或 4、修正前 1 或 2（依財政資訊中心附件的整除規則推得）；
      所以 min_check_digit 一定有答案，且現行規則的答案在 0–4 之間
   c. 第 7 位為 7 且符合現行規則時，Z1、Z2 恰有一個能被 5 整除（兩者差 1）
   d. 全部 10^8 個號碼中，現行有效 22,000,000 個、修正前 11,000,000 個（由 b 對 10^7 個前 7 碼加總）

除數的型別：Python 只收整數 5、10；JS 另外收字串 "5"、"10"（規則卡的下拉選單給的是字串）。
所以「字串除數」不列入第 4 項的不合法輸入。
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

RUNNER = """
const R = require(process.argv[2]);
let s=''; process.stdin.on('data', d => s += d).on('end', () => {
  const cases = JSON.parse(s);
  process.stdout.write(JSON.stringify(cases.map(c => {
    try { return R.compute(c.task, c.digits, c.divisor).total; } catch (e) { return 'ERR'; }
  })));
});
"""

INVALID = [
    {"task": "is_valid", "digits": "0459525", "divisor": 5},        # 7 位
    {"task": "is_valid", "digits": "045952570", "divisor": 5},      # 9 位
    {"task": "is_valid", "digits": "0459525a", "divisor": 5},       # 非數字
    {"task": "is_valid", "digits": "０４５９５２５７", "divisor": 5},  # 全形數字
    {"task": "is_valid", "digits": " 04595257", "divisor": 5},      # 空白
    {"task": "is_valid", "digits": "", "divisor": 5},
    {"task": "is_valid", "digits": 4595257, "divisor": 5},          # 不是字串
    {"task": "is_valid", "digits": "04595257", "divisor": 3},       # 除數
    {"task": "is_valid", "digits": "04595257", "divisor": 0},
    {"task": "is_valid", "digits": "04595257", "divisor": None},
    {"task": "min_check_digit", "digits": "04595257", "divisor": 5},   # 前 7 碼給了 8 位
    {"task": "min_check_digit", "digits": "045952", "divisor": 5},
    {"task": "count_valid", "digits": "", "divisor": 5},
    {"task": "count_valid", "digits": "04595257,", "divisor": 5},
    {"task": "count_valid", "digits": "04595257,04595257", "divisor": 5},  # 重複
    {"task": "count_valid", "digits": "04595257, 04595252", "divisor": 5},  # 空白
    {"task": "count_valid", "digits": "04595257;04595252", "divisor": 5},
    {"task": "check_digit", "digits": "0459525", "divisor": 5},     # 未知題型
]


def run_js(cases: list[dict]) -> list:
    runner = HERE / ".runner.js"
    runner.write_text(RUNNER)
    out = subprocess.run(["node", str(runner), str(HERE / "rule.js")],
                         input=json.dumps(cases), capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def py_total(c: dict):
    try:
        return rule.compute(c["task"], c["digits"], c["divisor"])["total"]
    except ValueError:
        return "ERR"


def rand_digits(rng: random.Random, n: int) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(n))


def random_cases(rng: random.Random, n: int) -> list[dict]:
    out = []
    for i in range(n):
        k = (5, 10)[i % 2]
        t = ("is_valid", "min_check_digit", "count_valid")[i % 3]
        if t == "is_valid":
            d = rand_digits(rng, 8)
            if rng.random() < 0.3:
                d = d[:6] + "7" + d[7]                    # 第 7 位為 7 的比例拉高
        elif t == "min_check_digit":
            d = rand_digits(rng, 7)
            if rng.random() < 0.3:
                d = d[:6] + "7"
        else:
            nums: list[str] = []
            while len(nums) < rng.randint(1, 8):
                x = rand_digits(rng, 8)
                if x not in nums:
                    nums.append(x)
            d = ",".join(nums)
        out.append({"task": t, "digits": d, "divisor": k})
    return out


def main(n_random: int = 6000, seed: int = 20261113) -> int:
    spec = yaml.safe_load((HERE / "spec.yaml").read_text(encoding="utf-8"))
    golden = spec["golden_cases"]
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

    # 3. random agreement
    rng = random.Random(seed)
    cases = random_cases(rng, n_random)
    py = [py_total(c) for c in cases]
    js = run_js(cases)
    mism = [(c, p, j) for c, p, j in zip(cases, py, js) if p != j]
    fails += len(mism) + py.count("ERR")
    print(f"[agr] random n={n_random} seed={seed} mismatches={len(mism)} py_errors={py.count('ERR')}")
    for c, p, j in mism[:10]:
        print("      ", c, "py=", p, "js=", j)

    # 4. 不合法的輸入：兩份實作都要拒絕
    js_bad = run_js(INVALID)
    not_rejected = [(c, p, j) for c in INVALID for p, j in [(py_total(c), js_bad[INVALID.index(c)])] if (p, j) != ("ERR", "ERR")]
    fails += len(not_rejected)
    print(f"[bad] invalid inputs n={len(INVALID)} not_rejected_by_both={len(not_rejected)}")
    for c, p, j in not_rejected:
        print("      ", c, "py=", p, "js=", j)

    # 5a–c. 性質（隨機 20 萬個號碼）
    prng = random.Random(seed + 1)
    superset = exactly_one = 0
    for _ in range(200_000):
        n = rand_digits(prng, 8)
        if prng.random() < 0.3:
            n = n[:6] + "7" + n[7]
        superset += rule.is_valid(n, 10) and not rule.is_valid(n, 5)
        z = rule.sums(n)
        if len(z) == 2 and rule.is_valid(n, 5):
            exactly_one += sum(v % 5 == 0 for v in z) != 1
    fails += superset + exactly_one
    print(f"[prop] old-valid-but-new-invalid={superset} seven_not_exactly_one_of_Z1_Z2={exactly_one}")

    # 5b. 第 8 碼個數只看第 7 位是不是 7（隨機 2 萬個前 7 碼，第 7 位 0–9 平均）
    expect = {5: (2, 4), 10: (1, 2)}
    count_viol = 0
    for i in range(20_000):
        p = rand_digits(prng, 6) + str(i % 10)
        for k in (5, 10):
            count_viol += len(rule.valid_check_digits(p, k)) != expect[k][p[6] == "7"]
        count_viol += not 0 <= rule.compute("min_check_digit", p, 5)["total"] <= 4
    fails += count_viol
    print(f"[prop] check-digit count violations={count_viol} (n=20000 prefixes × 2 divisors)")

    # 5d. 全量計數：以各位貢獻的分布做卷積數出 10^8 個號碼中有效的個數（不經過 5b 的性質），
    #     現行 22,000,000、修正前 11,000,000（依財政資訊中心附件的整除規則推得）。逐位的貢獻用 rule 的 WEIGHTS 與 cross_sum。
    dist = {0: 1}                                   # 第 7 位以外七個位數的貢獻和 → 個數
    for i, w in enumerate(rule.WEIGHTS):
        if i == 6:
            continue
        nxt: dict[int, int] = {}
        for s, c in dist.items():
            for x in range(10):
                t = s + rule.cross_sum(x * w)
                nxt[t] = nxt.get(t, 0) + c
        dist = nxt
    totals = {}
    for k in (5, 10):
        n_ok = 0
        for s, c in dist.items():
            for d7 in range(10):
                cands = [s + 1, s] if d7 == 7 else [s + rule.cross_sum(d7 * 4)]
                n_ok += c * any(z % k == 0 for z in cands)
        totals[k] = n_ok
    fails += (totals[5] != 22_000_000) + (totals[10] != 11_000_000)
    print(f"[prop] exhaustive totals ÷5={totals[5]:,} ÷10={totals[10]:,} (expected 22,000,000 / 11,000,000)")

    print("RESULT:", "PASS" if fails == 0 else f"FAIL ({fails})")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
