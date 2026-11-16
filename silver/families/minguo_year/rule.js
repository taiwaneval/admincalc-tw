/* minguo_year — JavaScript 實作（規則卡頁面試算用）。
 * 與 rule.py 為獨立實作；test_agreement.py 檢查兩者在 golden cases、全表與隨機輸入上一致。
 *
 * 算法（與 rule.py 等價，寫法不同）：
 *   - 民國紀年從民國元年 = 西元 1912 年起逐年加 1：西元年 = 1912 + (民國年 − 1)，民國年 = (西元年 − 1912) + 1。
 *     範圍是〈年歲對照表〉的民國 1–120 年，也就是西元 1912–2031 年。
 *   - 日期題：月日不變，答案只取年份。日期是否合法，用 Date.UTC 在平年（2001 年）建出那一天，
 *     看月份有沒有被進位到下個月；2001 年沒有 2 月 29 日，所以 2 月 29 日一律不合法（閏年不在範圍）。
 *   - 年份題不使用月、日，傳什麼都忽略。
 * 只收整數型別的數字；字串、布林、小數一律報錯（規則卡的輸入框先以 parseInt 轉成整數）。
 */
const MinguoYearRule = (function () {
  const FIRST_AD = 1912;   // 民國元年
  const LAST_ROC = 120;    // 〈年歲對照表〉的最後一年（2031）

  function intIn(x, label, lo, hi) {
    if (typeof x !== 'number' || !Number.isInteger(x)) throw new Error(label + '應為整數：' + x);
    if (x < lo || x > hi) throw new Error(label + '應在 ' + lo + '–' + hi + '：' + x);
    return x;
  }

  function adOf(roc) { return FIRST_AD + (intIn(roc, '民國年', 1, LAST_ROC) - 1); }
  function rocOf(ad) { return intIn(ad, '西元年', FIRST_AD, FIRST_AD + LAST_ROC - 1) - FIRST_AD + 1; }

  function checkMonthDay(m, d) {
    intIn(m, '月', 1, 12);
    intIn(d, '日', 1, 31);
    const t = new Date(Date.UTC(2001, m - 1, d));       // 平年
    if (t.getUTCMonth() !== m - 1 || t.getUTCDate() !== d) {
      throw new Error(m + ' 月沒有 ' + d + ' 日' + (m === 2 && d === 29 ? '（2 月 29 日只在閏年存在，閏年不在範圍）' : ''));
    }
  }

  const pad = (n, w) => String(n).padStart(w, '0');

  function compute(task, year, month, day) {
    let roc, ad, extra = {};
    switch (task) {
      case 'roc_to_ad': ad = adOf(year); roc = year; break;
      case 'ad_to_roc': roc = rocOf(year); ad = year; break;
      case 'roc_date_to_ad':
        ad = adOf(year); roc = year;
        checkMonthDay(month, day);
        extra = { date: pad(ad, 4) + '-' + pad(month, 2) + '-' + pad(day, 2) };
        break;
      default:
        throw new Error('task 只能是 roc_to_ad、ad_to_roc、roc_date_to_ad：' + task);
    }
    const total = task === 'ad_to_roc' ? roc : ad;
    return Object.assign({ rocYear: roc, adYear: ad }, extra, { total, totalExact: total });
  }

  return { compute, adOf, rocOf };
})();

if (typeof module !== 'undefined') module.exports = MinguoYearRule;
