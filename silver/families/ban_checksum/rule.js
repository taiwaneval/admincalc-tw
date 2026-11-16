/* ban_checksum — JavaScript 實作（規則卡頁面試算用）。
 * 與 rule.py 為獨立實作；test_agreement.py 檢查兩者在 golden cases 與隨機輸入上一致。
 *
 * 算法（與附件等價，寫法不同於 rule.py）：
 *   - 每一位乘上乘數後，把乘積的十進位數字逐字相加，得到這一位的貢獻；八位貢獻加總為 S。
 *     第 7 位是 7 時，貢獻是 2 + 8 = 10，S 已經把它當 10 計入。
 *   - 附件說第 7 位是 7 時「最後第二位數取 0 或 1 均可」：把貢獻 10 換成 1 或 0，
 *     等於 S − 9 或 S − 10。所以候選和是 [S]（第 7 位不是 7）或 [S − 9, S − 10]（第 7 位是 7）。
 *   - 任一候選和能被除數整除即符合邏輯。除數 5 是修正後（現行），10 是修正前。
 *   - 能用的第 8 碼不逐一代入：第 8 位的乘數是 1，候選和 c + x（x 為第 8 碼）能被 k 整除的 x
 *     就是 0–9 之中 x ≡ −c (mod k) 的數，對每個候選和求出這些 x 再取聯集；最小的有效第 8 碼是聯集的最小值。
 * 除數也接受字串 "5"、"10"（規則卡的下拉選單給的是字串）。
 */
const BanChecksumRule = (function () {
  const MULT = [1, 2, 1, 2, 1, 2, 4, 1];

  function toDigits(s, n) {
    if (typeof s !== 'string' || !new RegExp('^\\d{' + n + '}$').test(s)) {
      throw new Error('應為 ' + n + ' 位數字（字串，保留前導 0）：' + s);
    }
    return Array.from(s, ch => ch.charCodeAt(0) - 48);
  }

  function toDivisor(k) {
    const v = typeof k === 'string' && /^\d+$/.test(k) ? Number(k) : k;
    if (v !== 5 && v !== 10) throw new Error('除數只能是 5（現行）或 10（修正前）：' + k);
    return v;
  }

  // 乘積的十進位數字逐字相加
  function digitSum(p) {
    return String(p).split('').reduce((a, ch) => a + Number(ch), 0);
  }

  // 前 n 位（n = 7 或 8）的貢獻和，以及第 7 位是否為 7
  function partial(d) {
    let s = 0;
    for (let i = 0; i < d.length; i++) s += digitSum(d[i] * MULT[i]);
    return { s, seven: d[6] === 7 };
  }

  function candidates(number) {
    const p = partial(toDigits(number, 8));
    return p.seven ? [p.s - 9, p.s - 10] : [p.s];
  }

  function isValid(number, k) {
    const div = toDivisor(k === undefined ? 5 : k);
    return candidates(number).some(z => z % div === 0);
  }

  function checkDigits(prefix, k) {
    const div = toDivisor(k === undefined ? 5 : k);
    const p = partial(toDigits(prefix, 7));
    const bases = p.seven ? [p.s - 9, p.s - 10] : [p.s];
    const found = new Set();
    for (const c of bases) {
      for (let x = ((-c % div) + div) % div; x <= 9; x += div) found.add(x);
    }
    return Array.from(found).sort((a, b) => a - b);
  }

  function parseList(s) {
    if (typeof s !== 'string' || s.length === 0) throw new Error('號碼清單應為以逗號分隔的 8 位數字：' + s);
    const parts = s.split(',');
    parts.forEach(x => toDigits(x, 8));
    if (new Set(parts).size !== parts.length) throw new Error('號碼清單有重複：' + s);
    return parts;
  }

  function compute(task, digits, divisor) {
    const k = toDivisor(divisor === undefined ? 5 : divisor);
    let total, extra;
    switch (task) {
      case 'is_valid': {
        const z = candidates(digits);
        total = z.some(v => v % k === 0) ? 1 : 0;
        extra = { sums: z.join(' / ') };
        break;
      }
      case 'min_check_digit': {
        const xs = checkDigits(digits, k);
        if (xs.length === 0) throw new Error('沒有能讓號碼符合邏輯的第 8 碼：' + digits);
        total = Math.min(...xs);
        extra = { validCheckDigits: xs.join(', ') };
        break;
      }
      case 'count_valid': {
        const ok = parseList(digits).filter(n => isValid(n, k));
        total = ok.length;
        extra = { validNumbers: ok.join(', ') || '（無）' };
        break;
      }
      default:
        throw new Error('task 只能是 is_valid、min_check_digit、count_valid：' + task);
    }
    return Object.assign(extra, { divisor: k, total, totalExact: total });
  }

  return { compute, isValid, checkDigits, candidates };
})();

if (typeof module !== 'undefined') module.exports = BanChecksumRule;
