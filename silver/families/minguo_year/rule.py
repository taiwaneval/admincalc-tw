"""minguo_year — Python 實作（pipeline 用的驗證器）。

民國紀年與西元紀年的換算，依內政部戶政司〈年歲對照表〉（bronze/moi-ris-year-table/source.html）：
  民國 N 年 = 西元 N + 1911 年（民國元年 = 1912，沒有民國 0 年）；西元 Y 年 = 民國 Y − 1911 年。
範圍是表上的民國 1–120 年（西元 1912–2031 年），表外一律報錯。
日期題：月日沿用國曆、換算時不變（spec 的 DEF-MONTH-DAY，定義性規則），答案只取年份；
2 月 29 日只存在於閏年，閏年不在範圍（TAI-665），所以報錯。
年份題（roc_to_ad、ad_to_roc）不使用 month、day，傳什麼都忽略。

本檔與 rule.js 是各自獨立的實作，test_agreement.py 以 golden cases、全表與隨機輸入檢查兩者一致。只用標準庫。
"""
from __future__ import annotations

OFFSET = 1911                    # 民國元年的前一個西元年
ROC_MIN, ROC_MAX = 1, 120        # 〈年歲對照表〉民國 1 年（1912）到民國 120 年（2031）
TASKS = ("roc_to_ad", "ad_to_roc", "roc_date_to_ad")
MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)   # 2 月只到 28 日（2 月 29 日不在範圍）


def _int(x, name: str, lo: int, hi: int) -> int:
    # bool 是 int 的子類別，True 不能當 1 混過去；float、字串也不收
    if isinstance(x, bool) or not isinstance(x, int):
        raise ValueError(f"{name} 應為整數：{x!r}")
    if not lo <= x <= hi:
        raise ValueError(f"{name} 應在 {lo}–{hi}：{x}")
    return x


def roc_to_ad(roc: int) -> int:
    return _int(roc, "民國年", ROC_MIN, ROC_MAX) + OFFSET


def ad_to_roc(ad: int) -> int:
    return _int(ad, "西元年", ROC_MIN + OFFSET, ROC_MAX + OFFSET) - OFFSET


def compute(task: str, year: int, month: int | None = None, day: int | None = None) -> dict:
    """task:
         roc_to_ad       year 是民國年；答西元年
         ad_to_roc       year 是西元年；答民國年
         roc_date_to_ad  year／month／day 是民國日期；答換算後的西元年份（月日不變）
    """
    if task == "roc_to_ad":
        roc, ad = year, roc_to_ad(year)
        total, detail = ad, {}
    elif task == "ad_to_roc":
        ad, roc = year, ad_to_roc(year)
        total, detail = roc, {}
    elif task == "roc_date_to_ad":
        ad = roc_to_ad(year)
        roc = year
        m = _int(month, "月", 1, 12)
        if m == 2 and day == 29:
            raise ValueError("2 月 29 日只在閏年存在；閏年不在本 family 的範圍")
        d = _int(day, "日", 1, MONTH_DAYS[m - 1])
        total, detail = ad, {"date": f"{ad:04d}-{m:02d}-{d:02d}"}
    else:
        raise ValueError(f"task 只能是 {', '.join(TASKS)}：{task!r}")
    return {"roc_year": roc, "ad_year": ad, **detail, "total": total, "total_exact": total}


if __name__ == "__main__":
    import json
    import sys
    args = [int(a) for a in sys.argv[2:]]
    print(json.dumps(compute(sys.argv[1], *args), ensure_ascii=False))
