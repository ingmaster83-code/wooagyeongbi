# -*- coding: utf-8 -*-
"""우아경비율 정적 사이트 생성기 → _site/.  입력: data/rates_2025.json (국세청 고시 2026-14호 표: [업종코드, 업종명, 단순경비율 기본율, 초과율, 기준경비율])"""
import sys, json, re, shutil, time, collections, statistics
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *

YEAR = "2025"
RAW = json.loads((ROOT / "data" / "rates_2025.json").read_text(encoding="utf-8"))
NOTE = ("경비율은 국세청 고시 제2026-14호(2025년 귀속 경비율 고시, 2026. 3. 30.)의 표를 그대로 옮긴 값입니다. 세금 금액은 기본공제 150만원과 표준세액공제 7만원만 반영한 추정이며 "
        "다른 소득·공제·장부 작성 여부에 따라 실제 세액이 달라집니다. 신고 전 국세청 홈택스나 세무전문가에게 확인하세요.")

def table(heads, rows, num=()):
    th = "".join('<th%s>%s</th>' % (' class="num"' if i in num else "", h) for i, h in enumerate(heads))
    body = "".join("<tr>%s</tr>" % "".join('<td%s>%s</td>' % (' class="num"' if i in num else "", v) for i, v in enumerate(r)) for r in rows)
    return '<div class="tbl-wrap"><table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (th, body)
def chips(items): return '<div class="chips">%s</div>' % "".join('<a class="chip" href="%s">%s</a>' % (u, esc(t)) for t, u in items)
def sl(s): return re.sub(r"[^0-9A-Za-z가-힣]+", "-", s).strip("-") or "x"
def won(x): return "{:,}원".format(int(round(x)))
def man(x):
    v = int(round(x / 1e4))
    if v >= 10000: return ("%s억원" % "{:,}".format(v // 10000)) if v % 10000 == 0 else "%s억 %s만원" % ("{:,}".format(v // 10000), "{:,}".format(v % 10000))
    return "{:,}만원".format(v)
def pct(x): return "%.1f%%" % x

BR = [(14e6, .06, 0), (50e6, .15, 1.26e6), (88e6, .24, 5.76e6), (150e6, .35, 15.44e6), (300e6, .38, 19.94e6), (500e6, .40, 25.94e6), (1e9, .42, 35.94e6), (float("inf"), .45, 65.94e6)]
def inc_tax(taxable):
    for lim, r, ded in BR:
        if taxable <= lim: return max(0.0, taxable * r - ded)
def calc(rev, base, excess=None):
    exp = (min(rev, 4e7) * base / 100 + max(0, rev - 4e7) * excess / 100) if excess is not None else rev * base / 100
    income = rev - exp; taxable = max(0.0, income - 1.5e6)
    t = max(0.0, inc_tax(taxable) - 70000); loc = t * .1
    return {"exp": exp, "income": income, "tax": t, "local": loc, "total": t + loc}

# ───────────────────────── 데이터 ─────────────────────────
D = []
used = set()
for c, nm, sb, ex, st in RAW:
    cat, _, sub = nm.partition(" / ")
    d = {"c": c, "full": nm, "cat": cat, "sub": sub or nm, "s": float(sb), "x": float(ex) if ex else None, "b": float(st)}
    d["freel"] = c.startswith("940")
    d["path"] = "/code/%s/" % c
    d["valid"] = d["s"] > 0
    D.append(d)
BY = {d["c"]: d for d in D}
CATS = collections.OrderedDict()
for d in D: CATS.setdefault(d["cat"], []).append(d)
CAT_SLUG = {k: sl(k) for k in CATS}
VALID = [d for d in D if d["valid"]]
MED = statistics.median(d["s"] for d in VALID)
def name_dup(d): return sum(1 for e in D if e["sub"] == d["sub"] and e["cat"] == d["cat"]) > 1
SUBCNT = collections.Counter(e["sub"] for e in D)
def title_name(d): return ("%s %s" % (d["cat"], d["sub"])) if SUBCNT[d["sub"]] > 1 else d["sub"]
SCEN = [3e7, 5e7, 8e7, 1e8, 1.5e8]
def rank_in(d, lst, key, rev=True):
    s = sorted(lst, key=lambda x: (-key(x) if rev else key(x), x["c"]))
    for i, x in enumerate(s):
        if x is d: return i + 1, len(s)
def dlink(d, text=None): return '<a href="%s">%s</a>' % (d["path"], esc(text or d["sub"]))

# ───────────────────────── 업종코드 페이지 ─────────────────────────
def page_code(d):
    s, x, b = d["s"], d["x"], d["b"]; path = d["path"]; peers = [e for e in CATS[d["cat"]] if e["valid"]]
    cat_med = statistics.median(e["s"] for e in peers) if len(peers) >= 3 else None
    r_all = rank_in(d, VALID, lambda e: e["s"]) if d["valid"] else None
    r_cat = rank_in(d, peers, lambda e: e["s"]) if d["valid"] and len(peers) >= 3 else None
    if not d["valid"]:
        lead = "<b>%s</b>(업종코드 %s)은(는) 2025년 귀속 고시에서 단순경비율이 0.0%%이고 기준경비율이 %s로 공시되어 있어, 이 업종은 단순경비율을 적용할 수 없는 업종으로 안내됩니다. 실제 적용 가능 여부는 홈택스에서 확인하세요." % (esc(title_name(d)), d["c"], pct(b))
    else:
        lead = ("<b>%s</b>(업종코드 %s)의 2025년 귀속 <b>단순경비율은 %s</b>%s, <b>기준경비율은 %s</b>입니다. 이는 %s 장부 없이 신고할 때 소득금액은 수입의 약 %s로 계산됩니다.%s" % (
            esc(title_name(d)), d["c"], pct(s), ("(수입 4천만원 초과분은 초과율 %s)" % pct(x)) if x is not None else "", pct(b), "전체 업종 중앙값(%s)보다 %s 편입니다." % (pct(MED), "높은" if s > MED else "낮은"), pct(100 - s),
            (" 같은 분류(%s) 안에서는 단순경비율이 %d번째로 높습니다(%d개 업종)." % (d["cat"], r_cat[0], r_cat[1])) if r_cat else ""))
    rows = []; faq_val = None
    if d["valid"]:
        for rev in SCEN:
            r = calc(rev, s, x)
            rows.append([man(rev), man(r["exp"]), man(r["income"]), won(r["total"]) if r["total"] else "0원", pct(r["total"] / rev * 100)])
        t_calc = table(["연 수입금액", "인정 경비(단순경비율)", "소득금액", "종합소득세+지방세(추정)", "수입 대비 세부담"], rows, (0, 1, 2, 3, 4))
        faq_val = calc(1e8, s, x)
    else: t_calc = ""
    # 기준경비율 예시
    ex_html = ""
    if d["valid"]:
        rev = 1e8; main = 3e7; cap_m = 2.8
        simple_inc = rev - rev * s / 100 if x is None else calc(rev, s, x)["income"]
        inc_std = rev - main - rev * b / 100; capped = min(inc_std, simple_inc * cap_m)
        ex_html = f"""<h2 class="group-title">📐 기준경비율로 신고하면? (예시)</h2>
<p class="lead">단순경비율 대상이 아니면 기준경비율로 소득금액을 계산합니다. 수입 1억원, 매입·임차료·인건비 등 <b>주요경비 3,000만원</b>을 증빙으로 인정받고 기준경비율 {pct(b)}를 적용한다고 가정하면 소득금액은 1억원 − 3,000만원 − 1억원×{pct(b)} = <b>{man(inc_std)}</b>입니다. 간편장부 대상자의 경우 단순경비율 방식 소득금액({man(simple_inc)})의 2.8배({man(simple_inc * cap_m)})가 상한이므로 {'상한이 적용되어 ' if inc_std > simple_inc * cap_m else ''}최종 추계 소득금액은 약 <b>{man(capped)}</b>이 됩니다.</p>"""
    peer = sorted([e for e in CATS[d["cat"]] if e is not d and e["c"][:4] == d["c"][:4]], key=lambda e: e["c"])[:12]
    if len(peer) < 5: peer = sorted([e for e in CATS[d["cat"]] if e is not d], key=lambda e: abs(e["s"] - s))[:12]
    peer_t = table(["업종코드", "업종", "단순경비율", "기준경비율"], [[e["c"], dlink(e, e["sub"]), pct(e["s"]), pct(e["b"])] for e in peer], (2, 3)) if peer else ""
    fr = ""
    if d["freel"]: fr = '<p class="lead">업종코드 940으로 시작하는 <b>인적용역 사업소득</b>(프리랜서 등)은 2025년 귀속 수입금액 4천만원 이하분에는 단순경비율 기본율(%s), 4천만원 초과분에는 초과율(%s)을 적용합니다. 3.3%%를 떼고 받은 뒤 5월에 정산하는 방법은 <a href="https://wooatax.wooahouse.com/freelancer/">우아세금 프리랜서 3.3%% 환급</a>에서 계산해 볼 수 있습니다.</p>' % (pct(s), pct(x) if x is not None else "-")
    body = f"""
<div class="page-head"><h1>{esc(title_name(d))} 단순경비율·기준경비율 (업종코드 {d['c']})</h1><p>2025년 귀속 · 국세청 고시 제2026-14호</p></div>
<p class="lead">{lead}</p>
{fr}
{ad()}
<h2 class="group-title">📋 경비율</h2>
{table(['항목', '내용'], [['업종코드', d['c']], ['업종명', esc(d['full'])], ['단순경비율' + (' (기본율)' if x is not None else ''), pct(s) if d['valid'] else '해당 없음(0.0%)'], ['단순경비율 초과율', pct(x) if x is not None else '-'], ['기준경비율', pct(b)], ['분류', '<a href="/category/%s/">%s</a>' % (CAT_SLUG[d['cat']], esc(d['cat']))], ['단순경비율 전체 순위', ('%s위 / %s개 업종 (높은 순)' % (r_all[0], r_all[1])) if r_all else '-']])}
{('<h2 class="group-title">💰 수입금액별 소득·세금 추정 (단순경비율 적용)</h2>' + t_calc) if t_calc else ''}
{ex_html}
{('<h2 class="group-title">🔎 비슷한 업종</h2>' + peer_t) if peer_t else ''}
<p class="note">{NOTE} 단순경비율은 직전 연도 수입금액이 업종별 기준(농업·도소매 등 6,000만원, 제조·음식점·건설·운수 등 3,600만원, 서비스·부동산임대업 등 2,400만원)에 못 미치는 등 대상자 요건을 충족해야 쓸 수 있습니다.</p>
{chips([(d['cat'] + ' 업종', '/category/%s/' % CAT_SLUG[d['cat']]), ('단순경비율 순위', '/rank/simple/'), ('신고 가이드', '/guide/'), ('업종 검색', '/code/')])}
"""
    faq = []
    if d["valid"]:
        faq.append(("%s 단순경비율은 얼마인가요?" % title_name(d), "2025년 귀속 기준 %s입니다%s. 기준경비율은 %s입니다." % (pct(s), ("(4천만원 초과분 %s)" % pct(x)) if x is not None else "", pct(b))))
        faq.append(("%s 수입 1억원이면 세금은?" % title_name(d), "단순경비율 %s를 적용하면 소득금액 약 %s이고 종합소득세·지방소득세는 약 %s로 추정됩니다(기본공제 150만원, 표준세액공제 7만원만 반영)." % (pct(s), man(faq_val["income"]), won(faq_val["total"]))))
    else:
        faq.append(("%s에 단순경비율을 쓸 수 있나요?" % title_name(d), "고시표에 단순경비율이 0.0%%로 공시되어 단순경비율이 없는 업종입니다. 기준경비율은 %s입니다." % pct(b)))
    faq.append(("단순경비율과 기준경비율은 뭐가 다른가요?", "단순경비율은 수입금액에 비율을 곱해 경비를 인정하는 간편한 방식이고, 기준경비율은 매입·임차료·인건비 증빙(주요경비)을 별도로 인정받고 나머지에만 비율을 적용하는 방식입니다."))
    desc = "%s(업종코드 %s) 2025년 귀속 단순경비율 %s, 기준경비율 %s. 수입금액별 소득금액·종합소득세 추정과 비슷한 업종 비교." % (title_name(d), d["c"], pct(s) if d["valid"] else "해당 없음", pct(b))
    ttl = "%s 단순경비율·기준경비율 (업종코드 %s)" % (title_name(d), d["c"])
    write(path, layout(path, ttl, desc, body, faq, [("홈", "/"), ("업종", "/code/"), (d["cat"], "/category/%s/" % CAT_SLUG[d["cat"]]), (d["sub"], path)]), "0.6")

# ───────────────────────── 분류 · 순위 ─────────────────────────
H = ["업종코드", "업종", "단순경비율", "기준경비율"]
def rows_of(lst): return [[e["c"], dlink(e, e["full"]), pct(e["s"]) if e["valid"] else "-", pct(e["b"])] for e in lst]
def page_category(cat):
    lst = CATS[cat]; v = [e for e in lst if e["valid"]]; path = "/category/%s/" % CAT_SLUG[cat]
    med = statistics.median(e["s"] for e in v) if v else None
    hi = max(v, key=lambda e: e["s"]) if v else None; lo = min(v, key=lambda e: e["s"]) if v else None
    body = f"""
<div class="page-head"><h1>{esc(cat)} 업종 경비율 — {len(lst)}개 업종코드 (2025년 귀속)</h1><p>단순경비율·기준경비율 · 국세청 고시 제2026-14호</p></div>
<p class="lead"><b>{esc(cat)}</b> 분류에는 업종코드 {len(lst)}개가 있습니다. 단순경비율 중앙값은 {pct(med) if med else '-'}이고 가장 높은 업종은 {esc(hi['sub']) if hi else '-'}({pct(hi['s']) if hi else '-'}), 가장 낮은 업종은 {esc(lo['sub']) if lo else '-'}({pct(lo['s']) if lo else '-'})입니다. 업종을 누르면 수입금액별 소득·세금 추정을 볼 수 있습니다.</p>
{ad()}
{table(H, rows_of(sorted(lst, key=lambda e: e['c'])), (2, 3))}
<p class="note">{NOTE}</p>
{chips([("분류 전체", "/category/"), ("단순경비율 순위", "/rank/simple/"), ("업종 검색", "/code/")])}
"""
    faq = [("%s 단순경비율 평균은?" % cat, "중앙값 기준 %s입니다(2025년 귀속, 단순경비율이 있는 %d개 업종)." % (pct(med) if med else "-", len(v)))]
    write(path, layout(path, "%s 업종 경비율 — %d개 업종코드 단순·기준경비율 (2025년 귀속)" % (cat, len(lst)), "%s 분류 %d개 업종의 단순경비율·기준경비율. 단순경비율 중앙값 %s." % (cat, len(lst), pct(med) if med else "-"), body, faq, [("홈", "/"), ("분류", "/category/"), (cat, path)]), "0.7")
def hub_category():
    rows = []
    for k, lst in CATS.items():
        v = [e for e in lst if e["valid"]]
        rows.append(['<a href="/category/%s/">%s</a>' % (CAT_SLUG[k], esc(k)), len(lst), pct(statistics.median(e["s"] for e in v)) if v else "-", pct(statistics.median(e["b"] for e in lst))])
    body = f"""
<div class="page-head"><h1>업종 분류별 경비율 — {len(CATS)}개 분류 (2025년 귀속)</h1><p>제조·서비스·도소매·음식 등</p></div>
<p class="lead">업종코드 {len(D):,}개를 {len(CATS)}개 분류로 나눠 정리했습니다. 분류를 누르면 해당 업종의 단순경비율·기준경비율 전체 목록을 볼 수 있습니다.</p>
{ad()}
{table(['분류', '업종코드 수', '단순경비율 중앙값', '기준경비율 중앙값'], rows, (1, 2, 3))}
<p class="note">{NOTE}</p>
{chips([("단순경비율 순위", "/rank/simple/"), ("기준경비율 순위", "/rank/standard/"), ("프리랜서 경비율", "/freelancer/")])}
"""
    write("/category/", layout("/category/", "업종 분류별 경비율 — 제조·서비스·도소매·음식 (2025년 귀속)", "업종코드 %s개를 %d개 분류로 나눈 단순경비율·기준경비율 목록." % (format(len(D), ","), len(CATS)), body, None, [("홈", "/"), ("분류", "/category/")], coupang=True), "0.8")
def page_rank(slug, title, h1, lst, lead, sub):
    path = "/rank/%s/" % slug
    body = f"""
<div class="page-head"><h1>{h1}</h1><p>{sub}</p></div>
<p class="lead">{lead}</p>
{ad()}
{table(['순위'] + H, [[str(i + 1)] + r for i, r in enumerate(rows_of(lst[:100]))], (0, 3, 4))}
<p class="note">{NOTE}</p>
{chips([("단순경비율 높은 업종", "/rank/simple/"), ("단순경비율 낮은 업종", "/rank/simple-low/"), ("기준경비율 높은 업종", "/rank/standard/"), ("기준경비율 낮은 업종", "/rank/standard-low/")])}
"""
    faq = [("순위는 어떤 기준인가요?", "국세청 고시 제2026-14호(2025년 귀속)의 업종별 경비율 표를 기준으로 하며 단순경비율이 0.0%인 업종은 단순경비율 순위에서 제외했습니다.")]
    write(path, layout(path, title, lead[:150], body, faq, [("홈", "/"), ("순위", "/rank/simple/"), (h1.split(" —")[0], path)], coupang=True), "0.8")
def pages_rank():
    sh = sorted(VALID, key=lambda e: (-e["s"], e["c"])); sl_ = sorted(VALID, key=lambda e: (e["s"], e["c"])); bh = sorted(D, key=lambda e: (-e["b"], e["c"])); bl = sorted([e for e in D if e["b"] > 0], key=lambda e: (e["b"], e["c"]))
    page_rank("simple", "단순경비율 높은 업종 TOP 100 (2025년 귀속)", "단순경비율 높은 업종 TOP 100", sh, "단순경비율이 높은 업종은 장부 없이 신고할 때 인정되는 경비가 커서 소득금액이 작게 잡힙니다. 가장 높은 업종은 %s(%s)이고 전체 중앙값은 %s입니다." % (sh[0]["full"], pct(sh[0]["s"]), pct(MED)), "수입 대비 인정 경비 비율이 높은 순")
    page_rank("simple-low", "단순경비율 낮은 업종 TOP 100 (2025년 귀속)", "단순경비율 낮은 업종 TOP 100", sl_, "단순경비율이 낮은 업종은 인정 경비가 적어 같은 수입이라도 소득금액이 크게 잡힙니다. 가장 낮은 업종은 %s(%s)입니다." % (sl_[0]["full"], pct(sl_[0]["s"])), "수입 대비 인정 경비 비율이 낮은 순")
    page_rank("standard", "기준경비율 높은 업종 TOP 100 (2025년 귀속)", "기준경비율 높은 업종 TOP 100", bh, "기준경비율은 주요경비(매입·임차료·인건비) 외 기타 경비를 인정하는 비율입니다. 가장 높은 업종은 %s(%s)입니다." % (bh[0]["full"], pct(bh[0]["b"])), "기준경비율 높은 순")
    page_rank("standard-low", "기준경비율 낮은 업종 TOP 100 (2025년 귀속)", "기준경비율 낮은 업종 TOP 100", bl, "기준경비율이 낮은 업종은 증빙 없는 기타 경비 인정이 적습니다. 가장 낮은 업종은 %s(%s)입니다." % (bl[0]["full"], pct(bl[0]["b"])), "기준경비율 낮은 순")

def page_freelancer():
    lst = sorted([e for e in D if e["freel"]], key=lambda e: e["c"])
    rows = [[e["c"], dlink(e, e["sub"]), pct(e["s"]), pct(e["x"]) if e["x"] is not None else "-", pct(e["b"])] for e in lst]
    ex = [e for e in lst if e["c"] == "940909"] or lst[:1]
    sample = ex[0]; r = calc(5e7, sample["s"], sample["x"])
    body = f"""
<div class="page-head"><h1>프리랜서 경비율 — 인적용역 업종코드 940 단순경비율 ({len(lst)}개)</h1><p>2025년 귀속 · 3.3% 사업소득</p></div>
<p class="lead">프리랜서·작가·모델·배우 같은 <b>인적용역 사업소득자</b>는 업종코드가 940으로 시작합니다. 고시 제4조에 따라 2025년 귀속 수입금액 <b>4천만원 이하분은 단순경비율 기본율, 4천만원 초과분은 초과율</b>을 적용합니다. 예를 들어 {esc(sample['sub'])}({sample['c']})로 연 수입 5,000만원이면 인정 경비 {man(r['exp'])}, 소득금액 {man(r['income'])}으로 추정됩니다.</p>
{ad()}
{table(['업종코드', '업종', '단순경비율(기본율, 4천만원 이하)', '초과율(4천만원 초과분)', '기준경비율'], rows, (2, 3, 4))}
<p class="note">{NOTE} 3.3% 원천징수 후 5월 종합소득세 신고로 정산하는 계산은 <a href="https://wooatax.wooahouse.com/freelancer/">우아세금</a>을 참고하세요.</p>
{chips([("신고 가이드", "/guide/"), ("업종 검색", "/code/"), ("단순경비율 순위", "/rank/simple/")])}
"""
    faq = [("프리랜서 단순경비율은 얼마인가요?", "업종코드 940***마다 다르며 이 페이지 표에서 확인할 수 있습니다. 수입 4천만원 이하분은 기본율, 초과분은 초과율을 적용합니다."), ("3.3%를 뗐는데 왜 5월에 신고하나요?", "3.3%는 미리 낸 세금(원천징수)이고 실제 세액은 5월 종합소득세 확정신고에서 정산해 환급받거나 추가 납부합니다.")]
    write("/freelancer/", layout("/freelancer/", "프리랜서 경비율 — 인적용역 940 업종 단순경비율 (2025년 귀속)", "프리랜서·작가·모델·배우 등 인적용역 업종코드 940의 단순경비율 기본율·초과율(4천만원 기준)과 기준경비율.", body, faq, [("홈", "/"), ("프리랜서", "/freelancer/")], coupang=True), "0.9")

# ───────────────────────── 가이드 ─────────────────────────
GUIDES = [
    ("simple-vs-standard", "단순경비율과 기준경비율 차이 — 어떤 방식으로 신고하나", [
        ("단순경비율", "수입금액에 업종별 단순경비율을 곱한 금액을 경비로 인정합니다. 장부와 증빙이 없어도 되어 신고가 간단하지만 대상자 요건(직전 연도 수입금액 등)을 충족해야 합니다."),
        ("기준경비율", "매입비용·임차료·인건비는 증빙으로 인정받고(주요경비), 그 외 경비는 수입금액에 기준경비율을 곱해 인정합니다. 단순경비율 대상이 아닌 사업자가 장부 없이 신고할 때 쓰며 소득금액에는 단순경비율 방식 소득의 일정 배수(간편장부 대상 2.8배, 복식부기 의무자 3.4배) 상한이 있습니다."),
        ("장부(실제 경비)", "간편장부나 복식부기로 실제 수입과 경비를 기록하면 가장 정확한 소득금액으로 신고합니다. 경비가 많은 사업자는 장부 신고가 유리하고 복식부기 신고 시 기장세액공제 등을 받을 수 있습니다."),
        ("선택 기준", "수입이 적고 경비 증빙이 부족하면 단순경비율, 증빙이 충분하면 기준경비율이나 장부가 유리할 수 있습니다. 업종코드별 경비율은 이 사이트의 업종 페이지에서 확인하세요.")],
     [("단순경비율은 누구나 쓸 수 있나요?", "아닙니다. 신규 사업자나 직전 연도 수입금액이 업종별 기준 미만인 사업자 등 요건이 있습니다."), ("기준경비율이 단순경비율보다 낮은 이유는?", "기준경비율은 매입 등 주요경비를 따로 증빙으로 인정받는 전제의 비율이라 상대적으로 낮습니다.")]),
    ("who", "단순경비율 대상자 요건 — 수입금액 기준 정리", [
        ("신규 사업자", "해당 과세기간에 신규로 사업을 시작한 사업자는 그 해 수입금액이 일정 금액 미만이면 단순경비율로 추계신고할 수 있습니다."),
        ("직전 연도 수입금액 기준", "일반적으로 농업·임업·어업·광업·도소매업·부동산매매업은 6,000만원 미만, 제조업·음식점업·건설업·운수업·정보통신업·금융보험업 등은 3,600만원 미만, 부동산임대업·서비스업 등은 2,400만원 미만이 기준입니다."),
        ("당해 연도 수입금액 기준", "직전 연도 요건을 충족해도 해당 과세기간 수입금액이 일정 금액(1억 5천만원) 이상이면 단순경비율 대상에서 제외됩니다."),
        ("제외되는 경우", "전문직 사업자, 현금영수증 가맹점 가입 의무 불이행 등 일부 사업자는 대상에서 제외될 수 있습니다. 정확한 요건은 국세청 안내를 확인하세요.")],
     [("수입금액 기준은 매년 바뀌나요?", "시행령이 개정되면 달라질 수 있으니 신고 전 국세청 안내를 확인하세요."), ("업종이 여러 개면?", "업종별 수입금액을 합산해 주업종 기준으로 판단하는 등 별도 규정이 있어 세무서 확인이 필요합니다.")]),
    ("find-code", "업종코드 찾는 법 — 사업자등록증·홈택스에서 확인", [
        ("사업자등록증", "사업자등록증의 ‘업태·종목’ 옆이나 하단에 업종코드 6자리가 적혀 있습니다."),
        ("홈택스 조회", "홈택스에서 사업자 정보 조회나 종합소득세 신고 화면에서 업종코드를 검색할 수 있습니다."),
        ("이 사이트에서 검색", "업종 검색 페이지에서 업종명 일부(예: 한식, 학원, 작가)를 입력하면 비슷한 업종코드와 경비율을 바로 볼 수 있습니다."),
        ("업종코드가 여러 개라면", "주업종 외에 부업종이 있으면 코드가 여러 개일 수 있습니다. 신고에는 사업장별·업종별 코드를 사용합니다.")],
     [("업종코드는 몇 자리인가요?", "경비율 고시표의 업종코드는 6자리입니다."), ("업종코드를 잘못 쓰면?", "신고 시 코드가 틀리면 경비율이 달라질 수 있어 수정신고가 필요할 수 있습니다.")]),
    ("report", "종합소득세 신고 방법 — 5월 신고 순서", [
        ("신고 기간", "매년 5월 1일부터 31일까지 전년도 소득을 종합소득세로 신고합니다. 성실신고확인 대상자는 6월 30일까지입니다."),
        ("준비물", "사업자등록번호, 업종코드, 수입금액(홈택스 조회 가능), 경비 증빙, 공제 자료(국민연금·건강보험료·소득공제 항목)가 필요합니다."),
        ("신고 유형 선택", "장부 신고, 기준경비율 신고, 단순경비율 신고 중 요건에 맞는 유형을 선택합니다. 홈택스 ‘모두채움’ 안내를 받으면 더 간편합니다."),
        ("납부와 환급", "신고 후 납부세액은 5월 말까지 내며 3.3% 원천징수 등 이미 낸 세금이 더 많으면 환급받습니다.")],
     [("종합소득세 신고는 꼭 해야 하나요?", "사업소득이 있으면 원칙적으로 신고 대상이고 3.3%를 뗐더라도 환급을 받으려면 신고해야 합니다."), ("신고를 못 하면?", "기한 후 신고가 가능하지만 무신고가산세가 붙을 수 있습니다.")]),
]
def pages_guide():
    for slug, title, secs, faq in GUIDES:
        path = "/guide/%s/" % slug
        body = f"""
<div class="page-head"><h1>{title}</h1><p>종합소득세 · 경비율</p></div>
<p class="lead">{esc(secs[0][1])}</p>
{ad()}
{''.join('<h2 class="group-title">%d. %s</h2><p class="lead">%s</p>' % (i + 1, esc(t), esc(d)) for i, (t, d) in enumerate(secs))}
<p class="note">일반적인 안내이며 개별 상황에 대한 세무 조언이 아닙니다. 구체적인 요건은 국세청 홈택스·세무서에서 확인하세요.</p>
{chips([("업종 검색", "/code/"), ("단순경비율 순위", "/rank/simple/"), ("프리랜서 경비율", "/freelancer/"), ("가이드 목록", "/guide/")])}
"""
        write(path, layout(path, title, esc(secs[0][1])[:150], body, faq, [("홈", "/"), ("가이드", "/guide/"), (title, path)]), "0.7")
    rows = [['<a href="/guide/%s/">%s</a>' % (s, t)] for s, t, *_ in GUIDES]
    body = f"""
<div class="page-head"><h1>경비율·종합소득세 신고 가이드</h1><p>단순경비율·기준경비율·업종코드</p></div>
<p class="lead">단순경비율과 기준경비율의 차이, 단순경비율 대상자 요건, 업종코드 찾는 법, 종합소득세 신고 방법을 정리했습니다.</p>
{ad()}
{table(['가이드'], rows)}
{chips([("업종 검색", "/code/"), ("프리랜서 경비율", "/freelancer/")])}
"""
    write("/guide/", layout("/guide/", "경비율·종합소득세 신고 가이드 — 단순경비율·기준경비율·업종코드", "단순경비율과 기준경비율 차이, 단순경비율 대상자 요건, 업종코드 찾는 법, 5월 종합소득세 신고 방법.", body, None, [("홈", "/"), ("가이드", "/guide/")], coupang=True), "0.8")

# ───────────────────────── 검색·계산기 허브 · 홈 ─────────────────────────
def page_code_hub():
    body = f"""
<div class="page-head"><h1>업종코드·경비율 검색 + 소득세 계산기 (2025년 귀속)</h1><p>업종명 또는 업종코드로 검색</p></div>
<p class="lead">업종명(예: 한식, 학원, 작가)이나 업종코드 6자리를 입력하면 단순경비율·기준경비율을 찾고, 연 수입을 넣으면 단순경비율 신고 시 소득금액과 종합소득세를 추정해 줍니다.</p>
<div class="search-box"><input id="q" type="search" placeholder="업종명 또는 코드 (예: 한식, 940909)" autocomplete="off" aria-label="업종 검색"><div id="res" class="search-res"></div></div>
<div class="calc-box" id="calc" style="display:none;margin:14px 0;padding:14px;border:1px solid var(--border);border-radius:12px;background:#fff">
<b id="cn"></b><div style="margin-top:8px">연 수입금액(원) <input id="rev" type="number" value="50000000" step="1000000" style="padding:8px;border:1px solid var(--border);border-radius:8px;width:180px"></div>
<div id="cout" style="margin-top:10px;line-height:1.8"></div></div>
{ad()}
<h2 class="group-title">📚 분류로 찾기</h2>
{chips([(k, "/category/%s/" % CAT_SLUG[k]) for k in CATS])}
<p class="note">{NOTE}</p>
<script>
(function(){{var q=document.getElementById('q'),res=document.getElementById('res'),calc=document.getElementById('calc'),rev=document.getElementById('rev'),idx=null,cur=null;
var BR=[[14e6,.06,0],[50e6,.15,1.26e6],[88e6,.24,5.76e6],[150e6,.35,15.44e6],[300e6,.38,19.94e6],[500e6,.40,25.94e6],[1e9,.42,35.94e6],[1e18,.45,65.94e6]];
function tax(t){{for(var i=0;i<BR.length;i++)if(t<=BR[i][0])return Math.max(0,t*BR[i][1]-BR[i][2]);}}
function load(cb){{if(idx)return cb();fetch('/assets/rates.json').then(function(r){{return r.json()}}).then(function(j){{idx=j;cb()}});}}
function esc(s){{return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')}}
function f(n){{return Math.round(n).toLocaleString('ko-KR')}}
function go(){{var v=q.value.trim().toLowerCase();if(!v){{res.innerHTML='';return}}load(function(){{var out=[];for(var i=0;i<idx.length&&out.length<30;i++){{if(idx[i][1].toLowerCase().indexOf(v)>-1||idx[i][0].indexOf(v)===0)out.push(i)}}
res.innerHTML=out.length?out.map(function(i){{return '<a href="#" data-i="'+i+'">'+idx[i][0]+' '+esc(idx[i][1])+' <span>단순 '+idx[i][2]+'%</span></a>'}}).join(''):'<p>검색 결과가 없습니다.</p>';}});}}
function show(){{if(!cur)return;var s=+cur[2],x=cur[3]===''?null:+cur[3],r=+rev.value||0,e=x===null?r*s/100:Math.min(r,4e7)*s/100+Math.max(0,r-4e7)*x/100,inc=r-e,t=Math.max(0,tax(Math.max(0,inc-1.5e6))-70000),tot=t*1.1;
document.getElementById('cn').innerHTML=cur[0]+' '+esc(cur[1])+' · 단순경비율 '+s+'% · 기준경비율 '+cur[4]+'% · <a href="/code/'+cur[0]+'/">상세 보기</a>';
document.getElementById('cout').innerHTML='인정 경비 '+f(e)+'원<br>소득금액 '+f(inc)+'원<br><b>종합소득세+지방소득세(추정) '+f(tot)+'원</b> (수입 대비 '+(r?(tot/r*100).toFixed(1):0)+'%)<br><small>기본공제 150만원·표준세액공제 7만원만 반영한 추정입니다.</small>';}}
q.addEventListener('input',go);rev.addEventListener('input',show);
res.addEventListener('click',function(ev){{var a=ev.target.closest('a');if(!a||!a.dataset.i)return;ev.preventDefault();cur=idx[+a.dataset.i];calc.style.display='block';show();}});}})();
</script>
"""
    write("/code/", layout("/code/", "업종코드·경비율 검색 + 종합소득세 계산기 (2025년 귀속)", "업종명·업종코드로 단순경비율·기준경비율을 찾고 연 수입에 따른 소득금액·종합소득세를 추정하세요.", body, None, [("홈", "/"), ("업종 검색", "/code/")]), "0.9")
def mini(lst, n=5): return table(["업종코드", "업종", "경비율"], [[e["c"], dlink(e, e["full"]), pct(e["s"])] for e in lst[:n]], (2,))
def page_home():
    sh = sorted(VALID, key=lambda e: (-e["s"], e["c"]))
    body = f"""
<div class="hero"><h1>🧾 업종별 단순경비율·기준경비율 — {len(D):,}개 업종코드</h1><p>2025년 귀속 국세청 고시 · 소득세 계산기</p></div>
{ad()}
<div class="card-grid">
<a class="card" href="/code/"><b>🔍 업종 검색·계산기</b><span>업종명·코드로 경비율 찾기</span></a>
<a class="card" href="/rank/simple/"><b>🏆 단순경비율 순위</b><span>높은·낮은 업종 TOP 100</span></a>
<a class="card" href="/freelancer/"><b>✍️ 프리랜서 경비율</b><span>인적용역 940 업종</span></a>
<a class="card" href="/category/"><b>🗂️ 업종 분류</b><span>{len(CATS)}개 분류</span></a>
<a class="card" href="/guide/"><b>📖 신고 가이드</b><span>단순·기준경비율 차이</span></a>
</div>
<h2 class="group-title">🏆 단순경비율 높은 업종 TOP 5</h2>{mini(sh)}
<p class="lead">우아경비율은 국세청 고시 제2026-14호(2025년 귀속 경비율 고시)의 업종코드 {len(D):,}개 단순경비율·기준경비율을 업종별로 정리한 사이트입니다. 업종 페이지에서 수입금액별 소득금액과 종합소득세를 추정하고 단순경비율과 기준경비율 방식을 비교할 수 있습니다. 단순경비율 중앙값은 {pct(MED)}입니다. 자세한 기준은 <a href="/about/">데이터 설명</a>을 참고하세요.</p>
"""
    faq = [("경비율은 어느 연도 기준인가요?", "2025년 귀속(2026년 5월 신고분) 국세청 고시 제2026-14호입니다. 매년 3월 전후 새 고시가 나옵니다."), ("단순경비율이 높으면 세금이 적은가요?", "같은 수입이라면 인정 경비가 커서 소득금액이 작아지고 세금이 줄어듭니다. 다만 단순경비율은 요건을 충족해야 쓸 수 있습니다.")]
    write("/", layout("/", "우아경비율 — 업종별 단순경비율·기준경비율 (2025년 귀속) 검색", "국세청 고시 업종코드 %s개의 단순경비율·기준경비율과 수입금액별 종합소득세 추정, 프리랜서 경비율, 신고 가이드." % format(len(D), ","), body, faq), "1.0")
def page_about():
    body = f"""
<div class="page-head"><h1>데이터 설명</h1><p>정보의 출처와 한계</p></div>
<h2 class="group-title">📚 출처</h2><p class="lead">국세청 고시 제2026-14호 ‘2025년 귀속 경비율 고시’(2026. 3. 30.)의 업종코드별 단순경비율(기본율·초과율)과 기준경비율 표 {len(D):,}행을 사용했습니다. 공공데이터포털에도 ‘국세청_기준경비율_단순경비율’(15036323)로 등록되어 있습니다.</p>
<h2 class="group-title">🧮 계산 방법</h2><p class="lead">소득금액은 수입금액에서 단순경비율에 따른 경비를 뺀 값이고 인적용역(940***) 업종은 수입 4천만원 이하분에 기본율, 초과분에 초과율을 적용했습니다. 세액은 2025년 귀속 종합소득세율을 적용하고 기본공제 150만원과 표준세액공제 7만원만 반영한 뒤 지방소득세 10%를 더한 추정이며 다른 소득·공제는 반영하지 않았습니다.</p>
<h2 class="group-title">⚠️ 한계</h2><p class="lead">2026년 귀속 경비율은 보통 이듬해 3월에 고시되므로 이 사이트의 값은 2025년 귀속(2026년 5월 신고분) 기준입니다. 단순경비율 대상자 요건과 신고 방식은 개별 상황에 따라 달라지며 이 사이트는 세무 조언을 제공하지 않습니다. 신고 전 국세청 홈택스나 세무전문가에게 확인하세요.</p>
<h2 class="group-title">📬 문의·정정</h2><p class="lead">오류 제보는 <a href="mailto:ingmaster83@gmail.com">ingmaster83@gmail.com</a> 으로 보내 주세요.</p>
"""
    write("/about/", layout("/about/", "데이터 설명 — 출처와 한계", "우아경비율 데이터 출처(국세청 고시 제2026-14호)와 계산 방법, 한계.", body, None, [("홈", "/"), ("데이터 설명", "/about/")]), "0.5")
def page_privacy():
    body = """
<div class="page-head"><h1>개인정보처리방침</h1></div>
<p class="lead">우아경비율(wooagyeongbi.wooahouse.com, 이하 “서비스”)은 회원가입·로그인을 요구하지 않으며 이용자의 개인정보를 직접 수집하지 않습니다. 계산기에 입력한 수입금액은 브라우저에서만 처리되고 서버로 전송되지 않습니다.</p>
<h3>자동 수집 정보</h3><p class="lead">서비스 개선을 위해 Google Analytics로 방문자 수·페이지뷰 등 익명 통계를 수집하며, Google AdSense와 쿠팡 파트너스는 맞춤 광고를 위해 쿠키를 사용할 수 있습니다. 쿠키는 브라우저 설정에서 비활성화할 수 있습니다. (<a href="https://policies.google.com/privacy">Google 개인정보처리방침</a>, <a href="https://policies.google.com/technologies/ads">Google 광고 정책</a>)</p>
<h3>쿠팡 파트너스</h3><p class="lead">일부 페이지에는 쿠팡 파트너스 활동의 일환으로 광고가 포함되어 있으며 이에 따른 수수료를 제공받을 수 있습니다.</p>
<h3>문의</h3><p class="lead"><a href="mailto:ingmaster83@gmail.com">ingmaster83@gmail.com</a></p>
<p class="note">최종 수정일: 2026년 10월 26일</p>
"""
    write("/privacy/", layout("/privacy/", "개인정보처리방침", "우아경비율 개인정보처리방침", body, None, [("홈", "/"), ("개인정보처리방침", "/privacy/")]), sitemap=False)

def make_og():
    f = ROOT / "assets" / "og-image.png"
    if f.exists(): return
    try: from PIL import Image, ImageDraw, ImageFont
    except Exception: return
    im = Image.new("RGB", (1200, 630), (180, 83, 9)); dr = ImageDraw.Draw(im)
    def font(sz):
        for n_ in ("malgunbd.ttf", "malgun.ttf", "NanumGothicBold.ttf"):
            try: return ImageFont.truetype(n_, sz)
            except Exception: pass
        return ImageFont.load_default()
    dr.rounded_rectangle((90, 90, 1110, 540), 40, fill=(255, 255, 255))
    dr.text((150, 150), "우아경비율", font=font(110), fill=(146, 64, 14))
    dr.text((150, 310), "업종별 단순경비율 · 기준경비율", font=font(54), fill=(31, 41, 55))
    dr.text((150, 390), "종합소득세 추정 · 2025년 귀속", font=font(54), fill=(31, 41, 55))
    dr.text((150, 480), "wooagyeongbi.wooahouse.com", font=font(34), fill=(107, 114, 128))
    im.save(f)

def main():
    t0 = time.time(); make_og()
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets", dirs_exist_ok=True)
    for nf in ROOT.glob("naver*.html"): shutil.copy(nf, OUT / nf.name)
    (OUT / "assets" / "rates.json").write_text(json.dumps([[d["c"], d["full"], d["s"], "" if d["x"] is None else d["x"], d["b"]] for d in D], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for d in D: page_code(d)
    for k in CATS: page_category(k)
    hub_category(); pages_rank(); page_freelancer(); pages_guide(); page_code_hub(); page_home(); page_about(); page_privacy()
    today = time.strftime("%Y-%m-%d")
    urls = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>" % (BASE, q(p), today, pr_) for p, pr_ in WRITTEN)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls, encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE, encoding="utf-8")
    (OUT / "CNAME").write_text("wooagyeongbi.wooahouse.com\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    nf = layout("/404.html", "페이지를 찾을 수 없습니다", "요청한 페이지를 찾을 수 없습니다.", '<div class="page-head"><h1>페이지를 찾을 수 없습니다</h1></div><div class="chips"><a class="chip" href="/">홈</a><a class="chip" href="/code/">업종 검색</a></div>', None, None, noindex=True)
    (OUT / "404.html").write_text(nf, encoding="utf-8")
    print("pages", len(WRITTEN), "elapsed", round(time.time() - t0), "s")

if __name__ == "__main__":
    main()
