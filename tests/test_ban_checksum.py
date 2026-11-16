"""ban_checksum：spec 寫的比例與實際題集一致，錯答歸因認得出「照修正前規則」與「第 7 位為 7 不特別處理」。"""
import importlib.util
import json
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
FID = "ban_checksum"
FDIR = ROOT / "silver/families" / FID


def _load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


gen = _load("gen_ban", ROOT / "gold/generate.py")
hyp = _load("ban_checksum_hypotheses_t", FDIR / "hypotheses.py")
SPEC = yaml.safe_load((FDIR / "spec.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def generated(n: int, out: str):
    gen.generate(FID, "2099Q1", "public", n, out_dir=Path(out), as_of="2026-11-13")
    return [json.loads(l) for l in (Path(out) / f"{FID}.jsonl").read_text().splitlines()]


@pytest.fixture(scope="module")
def items100(tmp_path_factory):
    return generated(100, str(tmp_path_factory.mktemp("ban100")))


def test_old_rule_differs_share_matches_spec(items100):
    """spec 的分支表寫明差異題占 47%；每題實際以修正前規則重算，比例要和 spec 的 quota 一致。"""
    want = round(100 * sum(b["quota"] for b in SPEC["branches"] if b["old_rule_differs"]))
    got = [it for it in items100 if hyp.hypotheses(it["params"])["old_rule(÷10)"] != it["gold"]]
    assert want == 47 and len(got) == want
    by_branch = {b["id"]: b["old_rule_differs"] for b in SPEC["branches"]}
    assert all(by_branch[it["branch"]] for it in got)


def test_is_valid_answers_are_balanced(items100):
    v = [it["gold"] for it in items100 if it["params"]["task"] == "is_valid"]
    assert len(v) == 50 and v.count(1) == v.count(0) == 25


def test_every_item_uses_the_current_rule_and_has_no_company_name(items100):
    assert {it["params"]["divisor"] for it in items100} == {5}
    assert not any(w in it["prompt"] for it in items100 for w in ("公司名稱", "股份有限公司", "有限公司", "商行"))


def test_lineage_carries_the_bronze_source(items100):
    src = items100[0]["lineage"]["sources"]["mof-ban-checksum"]
    prov = json.loads((ROOT / "bronze/mof-ban-checksum/provenance.json").read_text(encoding="utf-8"))
    assert src["bronze_sha256"] == prov["sha256"] and src["fetched_at"] == prov["fetched_at"]
    assert items100[0]["lineage"]["laws"] == {}


@pytest.mark.parametrize("digits,old,no7_add10,no7_root", [
    ("04595252", 0, 1, 1),      # 官方範例，修正前無效
    ("10458570", 0, 1, 0),      # 官方範例，第 7 位為 7，只有取 0 的 Z2 = 15 整除
    ("10458574", 1, 0, 1),      # 官方範例，只有取 1 的 Z1 = 20 整除
    ("10458579", 0, 0, 1),      # 只有取 1 的 Z1 = 25 整除
])
def test_hypotheses_name_the_two_required_mistakes(digits, old, no7_add10, no7_root):
    h = hyp.hypotheses({"task": "is_valid", "digits": digits, "divisor": 5})
    assert h["correct"] == 1
    assert h["old_rule(÷10)"] == old
    assert h["no7_add10(第7位為7時把10直接加總)"] == no7_add10
    assert h["no7_digit_root(第7位為7時只取1)"] == no7_root


def test_min_check_digit_hypotheses():
    """1045857：現行可填 0、4、5、9，最小 0；修正前 4、5，最小 4；只取 0 的和（照加 10）可填 0、5，最小 0；只取 1 可填 4、9。"""
    h = hyp.hypotheses({"task": "min_check_digit", "digits": "1045857", "divisor": 5})
    assert (h["correct"], h["old_rule(÷10)"], h["no7_add10(第7位為7時把10直接加總)"], h["no7_digit_root(第7位為7時只取1)"]) == (0, 4, 0, 4)
    assert hyp.naive_answer({"task": "min_check_digit", "digits": "0459525", "divisor": 5}) == 7


def test_min_check_digit_items_all_differ_under_the_old_rule(items100):
    """Q4（Calvin 2026-11-13）改題型後，Q1 定的差異題配置不變：這個題型 20 題都是照修正前規則會答錯的題，答案在 0–4。"""
    c = [it for it in items100 if it["params"]["task"] == "min_check_digit"]
    assert len(c) == 20 and all(0 <= it["gold"] <= 4 for it in c)
    assert all(hyp.naive_answer(it["params"]) != it["gold"] for it in c)
