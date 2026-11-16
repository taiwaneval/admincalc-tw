"""ban_checksum — Python 實作（pipeline 用的驗證器）。

營利事業統一編號的檢查碼邏輯，依財政部財政資訊中心〈營利事業統一編號檢查碼邏輯修正說明（附件）〉
（bronze/mof-ban-checksum/source.pdf）逐步寫成：
  1. 8 位數字 d1…d8 依序乘上邏輯乘數 1, 2, 1, 2, 1, 2, 4, 1。
  2. 每個乘積「直寫並上下相加」：十位數與個位數相加。
  3. 第 7 位不是 7：各位相加得 Z。
     第 7 位是 7：第 7 位的乘積 28 相加得 10，「最後第二位數取 0 或 1 均可」，所以算兩個和 Z1（取 1）與 Z2（取 0）。
  4. 修正前（附件第一節）：Z 或 Z1、Z2 其中之一能被 10 整除，就符合邏輯。
     修正後（附件第二、三節，現行）：改為能被 5 整除。
題目一律用現行規則（divisor = 5）；divisor = 10 只用在錯答歸因與 golden 的修正前範例。

本檔與 rule.js 是各自獨立的實作，test_agreement.py 以 golden cases 與隨機輸入檢查兩者一致。只用標準庫。
"""
from __future__ import annotations

import re

WEIGHTS = (1, 2, 1, 2, 1, 2, 4, 1)          # 附件「邏輯乘數」列
DIVISORS = (5, 10)                          # 5 = 修正後（現行），10 = 修正前
TASKS = ("is_valid", "min_check_digit", "count_valid")
_DIGITS = re.compile(r"^[0-9]+$")


def _digits(s, length: int) -> list[int]:
    if not isinstance(s, str) or not _DIGITS.match(s) or len(s) != length:
        raise ValueError(f"應為 {length} 位數字（字串，保留前導 0）：{s!r}")
    return [int(c) for c in s]


def _divisor(divisor) -> int:
    # bool 是 int 的子類別，True 不能當成 1 混過去；字串 "5" 也不收（rule.js 收，見 test_agreement 的說明）
    if isinstance(divisor, bool) or divisor not in DIVISORS:
        raise ValueError(f"divisor 只能是 5（現行）或 10（修正前）：{divisor!r}")
    return divisor


def cross_sum(product: int) -> int:
    """乘積直寫並上下相加：十位數加個位數。"""
    return product // 10 + product % 10


def sums(number: str) -> list[int]:
    """附件的 Z（第 7 位不是 7，回傳 [Z]）或 Z1、Z2（第 7 位是 7，回傳 [Z1, Z2]）。"""
    d = _digits(number, 8)
    s = [cross_sum(x * w) for x, w in zip(d, WEIGHTS)]
    if d[6] != 7:
        return [sum(s)]
    rest = sum(s[:6]) + s[7]               # 第 7 位以外
    return [rest + 1, rest + 0]            # 第 7 位的「10」最後第二位數取 1 或取 0


def is_valid(number: str, divisor: int = 5) -> bool:
    """Z（或 Z1、Z2 其中之一）能被 divisor 整除。"""
    k = _divisor(divisor)
    return any(z % k == 0 for z in sums(number))


def valid_check_digits(prefix: str, divisor: int = 5) -> list[int]:
    """給前 7 碼，0–9 之中能讓 8 位號碼符合邏輯的第 8 碼。逐一代入檢查。"""
    _digits(prefix, 7)
    return [x for x in range(10) if is_valid(prefix + str(x), divisor)]


def split_list(numbers: str) -> list[str]:
    """一串號碼以半形逗號分隔（題目參數的正規寫法），每個都要是 8 位數字，且不能重複。"""
    if not isinstance(numbers, str) or not numbers:
        raise ValueError(f"號碼清單應為以逗號分隔的 8 位數字：{numbers!r}")
    out = numbers.split(",")
    for n in out:
        _digits(n, 8)
    if len(set(out)) != len(out):
        raise ValueError(f"號碼清單有重複：{numbers!r}")
    return out


def compute(task: str, digits: str, divisor: int = 5) -> dict:
    """task:
         is_valid            digits 是一個 8 位號碼；符合邏輯答 1，不符合答 0
         min_check_digit     digits 是前 7 碼；答 0–9 之中能讓號碼符合邏輯的第 8 碼裡最小的那一個
                             （現行規則下有 2 或 4 個，答案唯一；Calvin 2026-11-13 Q4）
         count_valid         digits 是以逗號分隔的 8 位號碼；答其中有幾個符合邏輯
    """
    k = _divisor(divisor)
    if task == "is_valid":
        z = sums(digits)
        total = int(is_valid(digits, k))
        detail = {"sums": z}
    elif task == "min_check_digit":
        ok = valid_check_digits(digits, k)      # 任何前 7 碼在兩種除數下都至少有 1 個（test_agreement 5b）
        total = ok[0]
        detail = {"valid_check_digits": ok}
    elif task == "count_valid":
        nums = split_list(digits)
        ok = [n for n in nums if is_valid(n, k)]
        total = len(ok)
        detail = {"valid_numbers": ok}
    else:
        raise ValueError(f"task 只能是 {', '.join(TASKS)}：{task!r}")
    return {**detail, "divisor": k, "total": total, "total_exact": total}


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(compute(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 5), ensure_ascii=False))
