"""minguo_year：每題對得到〈年歲對照表〉的一列、題數與重複的處理照 spec、錯答歸因認得三種必備錯誤。"""
import importlib.util
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
FID = "minguo_year"
FDIR = ROOT / "silver/families" / FID


def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


gen = _load("gen_minguo", ROOT / "gold/generate.py")
hyp = _load("minguo_year_hypotheses_t", FDIR / "hypotheses.py")
table = _load("minguo_year_bronze_table_t", FDIR / "bronze_table.py")
SPEC = yaml.safe_load((FDIR / "spec.yaml").read_text(encoding="utf-8"))
ROWS = table.roc_rows()


@lru_cache(maxsize=None)
def generated(n: int, out: str):
    gen.generate(FID, "2099Q1", "public", n, out_dir=Path(out), as_of="2026-11-13")
    items = [json.loads(l) for l in (Path(out) / f"{FID}.jsonl").read_text().splitlines()]
    return items, json.loads((Path(out) / f"{FID}.manifest.json").read_text())


@pytest.fixture(scope="module")
def run100(tmp_path_factory):
    return generated(100, str(tmp_path_factory.mktemp("minguo100")))


@pytest.fixture(scope="module")
def run200(tmp_path_factory):
    return generated(200, str(tmp_path_factory.mktemp("minguo200")))


def roc_of(params):
    return params["year"] - 1911 if params["task"] == "ad_to_roc" else params["year"]


# ---- bronze

def test_the_bronze_table_has_120_roc_rows_that_match_the_spec_range():
    lo, hi = SPEC["boundary_values"]["roc_year_range"]
    assert sorted(ROWS) == list(range(lo, hi + 1)) == list(range(1, 121))
    assert ROWS[1] == (120, 1912) and ROWS[115] == (6, 2026) and ROWS[120] == (1, 2031)   # (列號, 西元)


def test_every_item_maps_to_a_row_of_the_table(run100, run200):
    for items, _ in (run100, run200):
        for it in items:
            row, ad = ROWS[roc_of(it["params"])]
            assert it["gold"] == (roc_of(it["params"]) if it["params"]["task"] == "ad_to_roc" else ad), it["item_id"]


def test_lineage_carries_the_bronze_source(run100):
    items, man = run100
    src = man["lineage"]["sources"]["moi-ris-year-table"]
    prov = json.loads((ROOT / "bronze/moi-ris-year-table/provenance.json").read_text(encoding="utf-8"))
    assert src["bronze_sha256"] == prov["sha256"] and src["fetched_at"] == prov["fetched_at"]
    assert man["lineage"]["laws"] == {} and items[0]["lineage"] == man["lineage"]


# ---- 題數、配額與重複

def test_default_split_size_and_branch_quotas(run100):
    items, man = run100
    assert SPEC["default_n_per_split"] == 100 and man["n"] == 100 and man["rejected"] == 0
    assert Counter(it["branch"] for it in items) == {"Y1": 40, "Y2": 30, "D1": 30}


def test_anchor_years_are_the_ones_calvin_chose():
    """Calvin 2026-11-13：建議的六個，加上民國 78 年（1989）。"""
    assert SPEC["boundary_values"]["anchor_roc_years"] == [1, 38, 78, 89, 99, 100, 120]
    assert SPEC["open_questions"] == [] and SPEC["version"] == "0.1.1"


def test_anchor_years_appear_once_per_task(run100):
    items, _ = run100
    anchors = SPEC["boundary_values"]["anchor_roc_years"]
    for b in ("Y1", "Y2", "D1"):
        distinct = {json.dumps(it["params"], sort_keys=True) for it in items if it["branch"] == b}   # 配對題同參數，只算一次
        got = Counter(roc_of(json.loads(k)) for k in distinct)
        assert all(got[a] == 1 for a in anchors), (b, {a: got[a] for a in anchors})


def test_non_anchor_years_are_not_reused_within_a_100_item_split(run100):
    """spec〈題數與重複〉：public 不超過 134 題時，非錨點年份在三種題型之間都不重複（配對題沿用同一題的參數，不算）。"""
    items, _ = run100
    anchors = set(SPEC["boundary_values"]["anchor_roc_years"])
    keys = {json.dumps(it["params"], sort_keys=True): roc_of(it["params"]) for it in items}
    years = Counter(y for y in keys.values() if y not in anchors)
    assert max(years.values()) == 1


def test_at_200_items_a_year_never_repeats_within_one_task(run200):
    items, man = run200
    assert man["diversity"]["param_duplicates"] == 0
    for b in ("Y1", "Y2", "D1"):
        ys = {json.dumps(it["params"], sort_keys=True): roc_of(it["params"]) for it in items if it["branch"] == b}
        assert len(set(ys.values())) == len(ys), b


def test_plan_refuses_a_split_too_large_for_unique_years():
    sampler = _load("minguo_year_sampler_t", FDIR / "sampler.py")
    import random
    with pytest.raises(ValueError, match="120"):
        sampler.plan(SPEC, 400, random.Random(0))


# ---- 題幹

def test_roc_year_1_is_written_as_yuan_nian(run100):
    items, _ = run100
    ones = [it for it in items if it["params"]["task"] != "ad_to_roc" and it["params"]["year"] == 1]
    assert ones and all("元年" in it["prompt"] for it in ones)


def test_dates_never_use_february_29(run200):
    items, _ = run200
    assert not any(it["params"]["month"] == 2 and it["params"]["day"] == 29 for it in items)
    assert all(it["params"]["month"] is None and it["params"]["day"] is None
               for it in items if it["params"]["task"] != "roc_date_to_ad")


# ---- 錯答歸因（ticket 必備的三種錯誤）

@pytest.mark.parametrize("params, key, wrong", [
    ({"task": "roc_to_ad", "year": 115, "month": None, "day": None}, "off_1912(差 1912)", 2027),
    ({"task": "ad_to_roc", "year": 2026, "month": None, "day": None}, "off_1912(差 1912)", 114),
    ({"task": "roc_to_ad", "year": 115, "month": None, "day": None}, "reversed(加減方向相反)", -1796),
    ({"task": "ad_to_roc", "year": 2026, "month": None, "day": None}, "reversed(加減方向相反)", 3937),
    ({"task": "roc_to_ad", "year": 1, "month": None, "day": None}, "yuan_nian_zero(民國元年當 0 年)", 1911),
    ({"task": "roc_date_to_ad", "year": 1, "month": 1, "day": 1}, "yuan_nian_zero(民國元年當 0 年)", 1911),
    ({"task": "ad_to_roc", "year": 1912, "month": None, "day": None}, "yuan_nian_zero(民國元年當 0 年)", 0),
    ({"task": "roc_date_to_ad", "year": 115, "month": 3, "day": 1}, "off_1912(差 1912)", 2027),
])
def test_hypotheses_recognise_the_three_required_mistakes(params, key, wrong):
    h = hyp.hypotheses(params)
    assert next(iter(h)) == "correct" and h["correct"] != wrong
    assert h[key] == wrong
    hit = [k for k, v in h.items() if k != "correct" and v == wrong]
    assert hit[0] == key, hit                                 # 命中優先序：最具體的假說在前


def test_yuan_nian_zero_only_differs_from_the_correct_answer_at_year_one():
    for y in range(2, 121):
        h = hyp.hypotheses({"task": "roc_to_ad", "year": y, "month": None, "day": None})
        assert h["yuan_nian_zero(民國元年當 0 年)"] == h["correct"]


def test_naive_answer_uses_1912():
    assert hyp.naive_answer({"task": "roc_to_ad", "year": 115, "month": None, "day": None}) == 2027
    assert hyp.naive_answer({"task": "ad_to_roc", "year": 2026, "month": None, "day": None}) == 114


# ---- 未來年份只配可以寫未來日期的文件（Calvin 2026-11-13）

def test_future_years_only_appear_with_documents_that_can_carry_them(run100, run200):
    sampler = _load("minguo_year_sampler_t2", FDIR / "sampler.py")
    future = SPEC["boundary_values"]["future_from_roc"][0]
    assert future == 116 == sampler.FUTURE_FROM_ROC
    for items, _ in (run100, run200):
        fut = [it for it in items if roc_of(it["params"]) >= future]
        assert fut
        for it in fut:
            if it["params"]["task"] == "roc_to_ad":
                assert it["knobs"]["doc"] in sampler.ROC_DOCS_FUTURE, (it["item_id"], it["knobs"]["doc"])
            elif it["params"]["task"] == "roc_date_to_ad":
                assert it["knobs"]["doc"] in sampler.DATE_DOCS_FUTURE, (it["item_id"], it["knobs"]["doc"])
        past_only = set(sampler.ROC_DOCS) | set(sampler.DATE_DOCS)
        assert not {"畢業證書", "身分證", "結婚證書"} & set(sampler.ROC_DOCS_FUTURE)
        assert not set(sampler.ROC_DOCS_FUTURE) & set(sampler.ROC_DOCS) and not set(sampler.DATE_DOCS_FUTURE) & set(sampler.DATE_DOCS)
        assert past_only


def test_no_template_asks_about_a_birth_year():
    tpl = yaml.safe_load((FDIR / "templates.yaml").read_text(encoding="utf-8"))
    texts = [t["text"] for pool in ("templates", "ad_templates", "date_templates") for t in tpl[pool]]
    assert not any("出生" in t for t in texts)
