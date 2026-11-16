"""minguo_year 的錯規則假說與 naive 假 solver。

供 eval/attribute_errors.py（錯答歸因）與 eval/tasks/rules_registry.py（naive 假 solver）依 family 載入。
介面：hypotheses(params) -> dict[str, int]（第一鍵 "correct"，dict 順序 = 命中優先序）；naive_answer(params) -> int。
本檔不在簽核對象內（docs/family-admission.md A5）。

假說（民國→西元的寫法；西元→民國與日期題照同一個錯法換算）：
  yuan_nian_zero  把民國元年當 0 年：只有元年答錯（民國元年 → 1911；西元 1912 → 民國 0）。排在最前，
                  因為它只在元年這一題與正解不同，命中時比下面兩個「每一年都錯」的假說更具體。
  off_1912        差 1912 與差 1911 混淆：民國 N → N + 1912；西元 Y → Y − 1912（元年就是 1912，所以加 1912）
  off_1910        另一側差一：民國 N → N + 1910；西元 Y → Y − 1910
  reversed        加減方向相反：民國 N → N − 1911；西元 Y → Y + 1911
  no_conversion   照抄題目的年份，沒有換算
ticket 要求的三種錯誤是 off_1912、reversed、yuan_nian_zero。
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
ATTRIBUTION_TOL = 0   # 年份差 1 就是不同的錯


def _with_offset(params: dict, offset: int) -> int:
    """以錯的差值 offset 換算：民國→西元加 offset，西元→民國減 offset。"""
    y = params["year"]
    return y - offset if params["task"] == "ad_to_roc" else y + offset


def hypotheses(params: dict) -> dict[str, int]:
    correct = rule.compute(params["task"], params["year"], params.get("month"), params.get("day"))["total"]
    y = params["year"]
    H = {"correct": correct}
    if params["task"] == "ad_to_roc":
        H["yuan_nian_zero(民國元年當 0 年)"] = 0 if y == 1912 else correct
        H["reversed(加減方向相反)"] = y + 1911
    else:
        H["yuan_nian_zero(民國元年當 0 年)"] = 1911 if y == 1 else correct
        H["reversed(加減方向相反)"] = y - 1911
    H["off_1912(差 1912)"] = _with_offset(params, 1912)
    H["off_1910(差 1910)"] = _with_offset(params, 1910)
    H["no_conversion(照抄年份)"] = y
    # 命中優先序：元年專屬的假說最先，接著是最常見的差 1912、方向相反
    order = ["correct", "yuan_nian_zero(民國元年當 0 年)", "off_1912(差 1912)", "reversed(加減方向相反)",
             "off_1910(差 1910)", "no_conversion(照抄年份)"]
    return {k: H[k] for k in order}


def naive_answer(params: dict) -> int:
    """模擬「以為元年是 1912 所以加減 1912」的弱模型：每一題都差 1。"""
    return _with_offset(params, 1912)
