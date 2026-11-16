"""minguo_year 抽樣器：依分支決定題型與年份，日期題另抽月日；數字寫法、日期寫法與文件場合為旋鈕。

契約見 silver/families/overtime_pay/sampler.py 檔頭。分支定義在 spec.branches，年份範圍與錨點在 spec.boundary_values。

年份在 plan() 決定（spec〈題數與重複〉）：
  - 每種題型先放錨點年份（anchor_roc_years），每個各一題。
  - 其餘年份從「範圍內、不是錨點」的年份洗牌後依序發出，發完才重洗；同一題型不重複。
    所以題集不超過 錨點題數 + 非錨點年份數（7 × 3 + 113 = 134）題時，非錨點年份在三種題型之間都不重複。
  - 年份題的參數只有題型與年份，一種題型最多「範圍內年份數」題，超過時拒絕產生（ValueError），不讓產生器出重複題。
sample() 只為日期題抽月日（平年的合法日期，不抽 2 月 29 日）；年份題的 month、day 是 None。
每一題的年份都在 roc_year_range（〈年歲對照表〉民國 1–120 年）內，tests/test_minguo_year.py 逐題對表。
未來年份（spec.boundary_values.future_from_roc 以後）只配可以寫未來日期的文件（Calvin 2026-11-13），例如契約，不配畢業證書。
年份不影響文件的抽法以外的任何事，答案不變。
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

# 數字的寫法：半形或全形阿拉伯數字（遮掉數字後骨架相同）。國字數字不出（spec scope.excludes）。
NUMBER_STYLES = [("arabic", 0.80), ("fullwidth", 0.20)]
# 日期的寫法：「民國……年……月……日」或公文的「中華民國……年……月……日」
DATE_STYLES = [("minguo", 0.70), ("zhonghua_minguo", 0.30)]
# 題幹裡年份出現的文件或場合（不影響答案）
# 只記載過去年份的文件；未來年份改用 *_FUTURE（可以寫未來日期的文件）。兩組不重疊。
ROC_DOCS = ["身分證", "戶籍謄本", "畢業證書", "公文", "房屋所有權狀", "勞保投保資料", "土地登記謄本", "獎狀", "結婚證書", "存款證明"]
ROC_DOCS_FUTURE = ["租賃契約", "定期存單", "工程合約", "分期付款契約", "保險單"]
AD_FORMS = ["戶政事務所的申請書", "勞保局的表格", "國稅局的申報書", "公所的補助申請表", "學校的學籍資料",
            "健保署的申請書", "法院的書狀", "監理站的申請表"]
DATE_DOCS = ["公文的發文日期", "契約的簽約日期", "收據上的日期", "戶籍謄本上的登記日期", "畢業證書的發證日期",
             "判決書的日期", "存證信函的日期", "房屋所有權狀的登記日期"]
DATE_DOCS_FUTURE = ["租賃契約的到期日", "定期存單的到期日", "工程合約的完工期限", "保險單的保險期間屆滿日", "分期付款的最後一期繳款日"]
_FULLWIDTH = str.maketrans("0123456789", "０１２３４５６７８９")


def plan(spec: dict, n: int, rng: random.Random) -> list[dict]:
    counts = allocate_quota(spec["branches"], n)
    lo, hi = spec["boundary_values"]["roc_year_range"]
    span = list(range(lo, hi + 1))
    anchors = [y for y in spec["boundary_values"]["anchor_roc_years"] if lo <= y <= hi]
    rest = [y for y in span if y not in anchors]
    for b in spec["branches"]:
        if counts[b["id"]] > len(span):
            raise ValueError(f"{b['id']} 要 {counts[b['id']]} 題，但民國 {lo}–{hi} 年只有 {len(span)} 個年份；"
                             "同一題型的年份不能重複，請減少每個 split 的題數")
    deck: list[int] = []

    def draw(used: set[int]) -> int:
        nonlocal deck
        for _ in range(2):                         # 目前這一副牌沒有可用的年份，就換一副新洗的
            for i, y in enumerate(deck):
                if y not in used:
                    return deck.pop(i)
            deck = rest[:]
            rng.shuffle(deck)
        raise ValueError("抽不到沒用過的年份")      # plan 開頭已擋下題數超過年份數的情況，不會到這裡

    out = []
    for b in spec["branches"]:
        used: set[int] = set()
        for i in range(counts[b["id"]]):
            anchor = i < len(anchors)
            roc = anchors[i] if anchor else draw(used)
            used.add(roc)
            out.append({"branch": b["id"], "task": b["task"], "roc": roc,
                        "template_pool": b.get("template_pool", "templates"), "knobs": {"anchor": anchor}})
    rng.shuffle(out)
    return out


def sample(rng: random.Random, planned: dict) -> dict:
    """只用傳入的 rng，確定性。回傳的鍵 = spec.implementation.arg_order。"""
    roc, task = planned["roc"], planned["task"]
    if task == "ad_to_roc":
        return {"task": task, "year": roc + rule.OFFSET, "month": None, "day": None}
    if task == "roc_to_ad":
        return {"task": task, "year": roc, "month": None, "day": None}
    month = rng.randint(1, 12)
    day = rng.randint(1, rule.MONTH_DAYS[month - 1])        # 2 月只到 28 日
    return {"task": task, "year": roc, "month": month, "day": day}


def num(x: int, style: str) -> str:
    s = str(x)
    return s.translate(_FULLWIDTH) if style == "fullwidth" else s


def roc_text(roc: int, style: str) -> str:
    """「民國{roc}年」裡的 {roc}：民國 1 年寫成「元」（民國元年）。"""
    return "元" if roc == 1 else num(roc, style)


def date_text(p: dict, numstyle: str, datestyle: str) -> str:
    prefix = "中華民國" if datestyle == "zhonghua_minguo" else "民國"
    return f"{prefix}{roc_text(p['year'], numstyle)}年{num(p['month'], numstyle)}月{num(p['day'], numstyle)}日"


FUTURE_FROM_ROC = 116    # 與 spec.boundary_values.future_from_roc 相同（context() 拿不到 spec；tests/test_minguo_year.py 核對兩者一致）


def context(rng: random.Random, params: dict, tpl: dict) -> tuple[dict, dict]:
    style = pick_weighted(rng, NUMBER_STYLES)
    knobs = {"number_style": style}
    future = params["task"] != "ad_to_roc" and params["year"] >= FUTURE_FROM_ROC
    if params["task"] == "roc_to_ad":
        doc = rng.choice(ROC_DOCS_FUTURE if future else ROC_DOCS)
        fields = {"roc": roc_text(params["year"], style), "doc": doc}
    elif params["task"] == "ad_to_roc":
        doc = rng.choice(AD_FORMS)
        fields = {"ad": num(params["year"], style), "form": doc}
    else:
        doc = rng.choice(DATE_DOCS_FUTURE if future else DATE_DOCS)
        ds = pick_weighted(rng, DATE_STYLES)
        fields = {"date": date_text(params, style, ds), "doc": doc}
        knobs["date_style"] = ds
    knobs["doc"] = doc
    return fields, knobs


def visible(params: dict, fields: dict) -> list[set[str]]:
    """題幹要能找回年份（任一種寫法）；日期題另要找回完整日期。"""
    if params["task"] == "ad_to_roc":
        return [{num(params["year"], s) + "年" for s, _ in NUMBER_STYLES}]
    years = {f"民國{roc_text(params['year'], s)}年" for s, _ in NUMBER_STYLES}
    if params["task"] == "roc_to_ad":
        return [years]
    return [years, {date_text(params, s, d) for s, _ in NUMBER_STYLES for d, _ in DATE_STYLES}]


def coverage_keys(params: dict) -> dict[str, str]:
    roc = params["year"] - rule.OFFSET if params["task"] == "ad_to_roc" else params["year"]
    era = "1-38" if roc <= 38 else ("39-88" if roc <= 88 else "89-120")
    return {"roc_digits": str(len(str(roc))), "roc_era": era, "yuan_nian": str(roc == 1)}
