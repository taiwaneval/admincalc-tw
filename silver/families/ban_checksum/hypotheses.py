"""ban_checksum 的錯規則假說與 naive 假 solver。

供 eval/attribute_errors.py（錯答歸因）與 eval/tasks/rules_registry.py（naive 假 solver）依 family 載入。
介面：hypotheses(params) -> dict[str, int]（第一鍵 "correct"，dict 順序 = 命中優先序）；naive_answer(params) -> int。
本檔不在簽核對象內（docs/family-admission.md A5）。

假說都以「判斷單一號碼」的錯法定義，再套到三種題型（是否有效、最小的有效第 8 碼、清單中有效個數）：
  old_rule(÷10)            照修正前規則：能被 10 整除才算符合
  no7_add10                第 7 位為 7 不特別處理：28 的 2 + 8 = 10 直接加進總和（只檢查 S，等於只取 0 的 Z2）
  no7_digit_root           第 7 位為 7 時把 10 再加一次變成 1（只檢查取 1 的 Z1）
  old_rule+no7_add10       上面兩種錯同時發生
  no_cross_sum             乘積不做十位加個位，直接把乘積相加（第 7 位為 7 時同樣取 Z1、Z2 兩個和）
答案只有 0–10 的小整數，不同假說常常給出同一個數，所以一個錯答可能同時歸到幾個假說。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load_sibling(name: str):
    """以唯一模組名載入同目錄的 .py（不用裸名稱 import，避免多個 family 的 rule.py 互相覆蓋）。"""
    s = importlib.util.spec_from_file_location(f"{HERE.name}_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


rule = _load_sibling("rule")
ATTRIBUTION_TOL = 0   # 計數題：差 1 就是不同的判斷


def _contributions(number: str, cross: bool = True) -> list[int]:
    d = [int(c) for c in number]
    return [rule.cross_sum(x * w) if cross else x * w for x, w in zip(d, rule.WEIGHTS)]


def _valid_no7_add10(number: str, k: int) -> bool:
    return sum(_contributions(number)) % k == 0


def _valid_no7_digit_root(number: str, k: int) -> bool:
    c = _contributions(number)
    if number[6] == "7":
        c[6] = 1
    return sum(c) % k == 0


def _valid_no_cross_sum(number: str, k: int) -> bool:
    c = _contributions(number, cross=False)
    if number[6] != "7":
        return sum(c) % k == 0
    rest = sum(c) - c[6]
    return (rest + 1) % k == 0 or rest % k == 0


def _answer(params: dict, valid) -> int:
    """把「判斷單一號碼」的函式套到題型上。"""
    task, digits = params["task"], params["digits"]
    if task == "is_valid":
        return int(valid(digits))
    if task == "min_check_digit":
        ok = [x for x in range(10) if valid(digits + str(x))]
        return ok[0] if ok else -1                # 錯規則下可能沒有任何第 8 碼符合；-1 不會與正解相同
    if task == "count_valid":
        return sum(valid(n) for n in digits.split(","))
    raise ValueError(task)


def hypotheses(params: dict) -> dict[str, int]:
    k = params.get("divisor", 5)
    H = {"correct": rule.compute(params["task"], params["digits"], k)["total"]}
    H["old_rule(÷10)"] = _answer(params, lambda n: rule.is_valid(n, 10))
    H["no7_add10(第7位為7時把10直接加總)"] = _answer(params, lambda n: _valid_no7_add10(n, 5))
    H["no7_digit_root(第7位為7時只取1)"] = _answer(params, lambda n: _valid_no7_digit_root(n, 5))
    H["old_rule+no7_add10"] = _answer(params, lambda n: _valid_no7_add10(n, 10))
    H["no_cross_sum(乘積不做十位加個位)"] = _answer(params, lambda n: _valid_no_cross_sum(n, 5))
    if params["task"] == "is_valid":
        H["flip(1、0 對調)"] = 1 - H["correct"]
    return H


def naive_answer(params: dict) -> int:
    """模擬「只知道修正前規則（÷10）」的弱模型：錯在新舊規則答案不同的題（V2、V5、C1、C2、L1）。"""
    return _answer(params, lambda n: rule.is_valid(n, 10))
