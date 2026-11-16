"""ban_checksum 抽樣器：依分支抽號碼、前 7 碼或號碼清單；號碼寫法與出現場合為旋鈕。

契約見 silver/families/overtime_pay/sampler.py 檔頭。分支定義在 spec.branches：
  number  單一 8 位號碼（is_valid）。先抽前 7 碼（第 7 位依 d7 決定是否為 7），再從 0–9 中挑出符合 status 的第 8 碼。
          status：both = 修正前、修正後都符合；new_only = 只有修正後（現行）符合；invalid = 都不符合。
          三種類別在任何前 7 碼下都至少有一個第 8 碼（第 7 位非 7：1、1、8 個；為 7：2、2、6 個），所以不必拒絕抽樣。
  prefix  前 7 碼（min_check_digit），第 7 位依 d7 決定；照修正前規則作答的答案是否不同依 old_rule_differs，
          隨機前 7 碼約一半不同，所以以拒絕抽樣挑出（MAX_ATTEMPTS 次內必中）。
  list    3–6 個不重複的 8 位號碼（count_valid）。長度依 spec.boundary_values.list_length 輪流；
          每個號碼的類別依 list_class_weights 抽，L1 至少一個 new_only，L2 不抽 new_only；第 7 位為 7 的機率是 list_seven_rate。
題目的 divisor 一律是 5（現行規則）。號碼可能剛好是已配賦的真實號碼；題幹不搭配公司名稱（TAI-662 Constraints）。
"""
from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools"))
from sampling import allocate_quota, pick_weighted  # noqa: E402


def _load_sibling(name: str):
    """以唯一模組名載入同目錄的 .py。不用裸名稱 `import rule`：多個 family 的 rule.py 在同一 process 會互相覆蓋。"""
    s = importlib.util.spec_from_file_location(f"{HERE.name}_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


rule = _load_sibling("rule")

CURRENT = 5     # 題目一律用現行規則
OLD = 10
CLASSES = ("both", "new_only", "invalid")
MAX_ATTEMPTS = 200

# 號碼的寫法：半形數字、加「」、全形數字。全形與半形遮掉數字後骨架相同，「」會改變骨架。
NUMBER_STYLES = [("plain", 0.60), ("bracket", 0.25), ("fullwidth", 0.15)]
# 清單的分隔符號
LIST_SEPARATORS = [("dun", "、", 0.50), ("comma", "，", 0.30), ("semicolon", "；", 0.20)]
# 號碼出現的場合（只有部分模板用到 {where}）；不含公司名稱
WHERE = ["發票上", "報帳單據上", "採購單上", "客戶填寫的資料上", "廠商請款單上", "線上表單裡"]
_FULLWIDTH = str.maketrans("0123456789", "０１２３４５６７８９")


def classify(number: str) -> str:
    """both／new_only／invalid（新規則包含舊規則，沒有只有修正前符合的號碼）。"""
    if rule.is_valid(number, OLD):
        return "both"
    return "new_only" if rule.is_valid(number, CURRENT) else "invalid"


def _prefix(rng: random.Random, seven: bool) -> str:
    head = "".join(str(rng.randint(0, 9)) for _ in range(6))
    d7 = 7 if seven else rng.choice([0, 1, 2, 3, 4, 5, 6, 8, 9])
    return head + str(d7)


def _number(rng: random.Random, seven: bool, status: str) -> str:
    p = _prefix(rng, seven)
    options = [p + str(x) for x in range(10) if classify(p + str(x)) == status]
    return rng.choice(options)


def plan(spec: dict, n: int, rng: random.Random) -> list[dict]:
    """依 quota 分配題數；count_valid 的清單長度在分支內輪流（每個長度至少 ⌊n_branch / 長度數⌋ 題）。
    old_rule_differs 由 spec 帶進 knobs，coverage 會列出直方圖；實際是否不同由 coverage_keys 依 rule 重算。"""
    counts = allocate_quota(spec["branches"], n)
    bv = spec["boundary_values"]
    out = []
    for b in spec["branches"]:
        for i in range(counts[b["id"]]):
            p = {"branch": b["id"], "kind": b["kind"], "task": b["task"],
                 "template_pool": b.get("template_pool", "templates"),
                 "knobs": {"old_rule_differs": bool(b["old_rule_differs"])}}
            if b["kind"] == "number":
                p.update(seven=b["d7"] == "seven", status=b["status"])
            elif b["kind"] == "prefix":
                p.update(seven=b["d7"] == "seven", old_rule_differs=bool(b["old_rule_differs"]))
            elif b["kind"] == "list":
                k = bv["list_length"][i % len(bv["list_length"])]
                p.update(length=k, new_only=b["new_only"], seven_rate=bv["list_seven_rate"][0],
                         class_weights=list(bv["list_class_weights"]))
                p["knobs"]["list_length"] = k
            else:
                raise ValueError(f"未知的 kind：{b['kind']!r}")
            out.append(p)
    rng.shuffle(out)
    return out


def _list(rng: random.Random, planned: dict) -> list[str]:
    weights = dict(zip(CLASSES, planned["class_weights"]))
    if planned["new_only"] == "none":
        weights["new_only"] = 0.0
    total = sum(weights.values())
    pairs = [(c, w / total) for c, w in weights.items() if w > 0]
    classes = ["new_only"] if planned["new_only"] == "at_least_one" else []
    while len(classes) < planned["length"]:
        classes.append(pick_weighted(rng, pairs))
    rng.shuffle(classes)
    nums: list[str] = []
    for c in classes:
        while True:
            x = _number(rng, rng.random() < planned["seven_rate"], c)
            if x not in nums:
                nums.append(x)
                break
    return nums


def sample(rng: random.Random, planned: dict) -> dict:
    """只用傳入的 rng，確定性。回傳的鍵 = spec.implementation.arg_order。"""
    if planned["kind"] == "number":
        digits = _number(rng, planned["seven"], planned["status"])
    elif planned["kind"] == "prefix":
        for _ in range(MAX_ATTEMPTS):
            digits = _prefix(rng, planned["seven"])
            differs = rule.compute("min_check_digit", digits, CURRENT)["total"] != rule.compute("min_check_digit", digits, OLD)["total"]
            if differs == planned["old_rule_differs"]:
                break
        else:
            raise RuntimeError(f"{MAX_ATTEMPTS} 次都抽不到符合 branch 的前 7 碼：{planned}")
    else:
        digits = ",".join(_list(rng, planned))
    return {"task": planned["task"], "digits": digits, "divisor": CURRENT}


def format_number(s: str, style: str) -> str:
    if style == "plain":
        return s
    if style == "bracket":
        return f"「{s}」"
    if style == "fullwidth":
        return s.translate(_FULLWIDTH)
    raise ValueError(style)


def context(rng: random.Random, params: dict, tpl: dict) -> tuple[dict, dict]:
    style = pick_weighted(rng, NUMBER_STYLES)
    where = rng.choice(WHERE)
    fields = {"where": where}
    knobs = {"number_style": style, "where": where}
    if params["task"] == "count_valid":
        nums = params["digits"].split(",")
        sep_id, sep = pick_weighted(rng, [((i, s), w) for i, s, w in LIST_SEPARATORS])
        fields.update(numbers=sep.join(format_number(x, style) for x in nums), k=str(len(nums)))
        knobs["separator"] = sep_id
    elif params["task"] == "min_check_digit":
        fields["prefix"] = format_number(params["digits"], style)
    else:
        fields["number"] = format_number(params["digits"], style)
    return fields, knobs


def visible(params: dict, fields: dict) -> list[set[str]]:
    """題幹要能找回每一個號碼（或前 7 碼），任一種寫法。"""
    parts = params["digits"].split(",") if params["task"] == "count_valid" else [params["digits"]]
    return [{format_number(x, s) for s, _ in NUMBER_STYLES} for x in parts]


def coverage_keys(params: dict) -> dict[str, str]:
    cur = rule.compute(params["task"], params["digits"], CURRENT)["total"]
    old = rule.compute(params["task"], params["digits"], OLD)["total"]
    out = {"answer": str(cur), "old_rule_answer_differs": str(cur != old)}
    if params["task"] == "is_valid":
        out["d7_is_7"] = str(params["digits"][6] == "7")
        z = rule.sums(params["digits"])
        if len(z) == 2 and cur:
            out["via"] = "Z1" if z[0] % CURRENT == 0 else "Z2"   # 第 7 位為 7 且符合：取 1 或取 0 的和整除
    return out
