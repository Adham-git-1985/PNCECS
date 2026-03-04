import os
import re
import csv
import shutil
import zipfile
from datetime import datetime
from html import unescape
from html.parser import HTMLParser

from app import app, db, News

ZIP_PATH = "web20_hind.zip"
SQL_FILE_INSIDE_ZIP = "web20_hind.sql"

DRY_RUN = False  # خلّيها False للتطبيق الفعلي

# WordPress ar_posts columns (23)
IDX_ID = 0
IDX_POST_DATE = 2
IDX_POST_DATE_GMT = 3
IDX_POST_CONTENT = 4
IDX_POST_TITLE = 5
IDX_POST_STATUS = 7
IDX_POST_MODIFIED = 14
IDX_GUID = 18
IDX_POST_TYPE = 20

_AR_DIACRITICS = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed]")
_PUNCT = re.compile(r"[\"'“”‘’`´\(\)\[\]\{\}\<\>\|،,؛;:!?\.\-–—_+/\\ـ]+")


class _Stripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, d):
        if d:
            self.parts.append(d)
    def get_data(self):
        return "".join(self.parts)

def strip_html(s: str) -> str:
    p = _Stripper()
    p.feed(s or "")
    return p.get_data()

def clean_wp_text(s: str) -> str:
    if not s:
        return ""
    t = unescape(s)
    t = re.sub(r"<!--\s*/?wp:.*?-->", "", t, flags=re.I | re.S)   # Gutenberg comments
    t = re.sub(r"\[/?[a-zA-Z][^\]]*\]", "", t)                  # shortcodes
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</p\s*>", "\n", t)
    t = re.sub(r"(?i)</div\s*>", "\n", t)
    t = strip_html(t)
    t = t.replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n\s*\n+", "\n\n", t)
    return t.strip()

def normalize_strong(s: str) -> str:
    if not s:
        return ""
    s = unescape(s).strip()
    s = s.replace("\u0640", "")  # tatweel
    s = _AR_DIACRITICS.sub("", s)
    s = _PUNCT.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def signature_from_content(s: str, n=140) -> str:
    t = clean_wp_text(s)
    t = normalize_strong(t)
    return t[:n]

def parse_wp_datetime(x):
    if not x:
        return None
    x = str(x).strip()
    if x.startswith("0000-00-00"):
        return None
    try:
        return datetime.strptime(x, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def backup_db():
    db_path = os.path.join("instance", "news.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"لم أجد قاعدة البيانات: {db_path}")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join("instance", f"news_before_wp_sync_{ts}.db")
    shutil.copy2(db_path, backup_path)
    print(f"🧾 Backup created: {backup_path}")

def _unescape_mysql(s: str) -> str:
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt == "r":
                out.append("\r")
            elif nxt == "t":
                out.append("\t")
            elif nxt == "0":
                out.append("\x00")
            else:
                out.append(nxt)
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)

def parse_values_block(values_text: str):
    rows = []
    row = []
    field = []
    in_quote = False
    in_row = False
    i = 0
    L = len(values_text)

    while i < L:
        c = values_text[i]

        if not in_row:
            if c == "(":
                in_row = True
                row = []
                field = []
            i += 1
            continue

        if in_quote:
            if c == "\\" and i + 1 < L:
                field.append(c)
                field.append(values_text[i + 1])
                i += 2
                continue
            if c == "'":
                in_quote = False
                i += 1
                continue
            field.append(c)
            i += 1
            continue

        if c == "'":
            in_quote = True
            i += 1
            continue

        if c == ",":
            raw = "".join(field).strip()
            if raw == "NULL":
                row.append(None)
            else:
                row.append(_unescape_mysql(raw))
            field = []
            i += 1
            continue

        if c == ")":
            raw = "".join(field).strip()
            if raw == "NULL":
                row.append(None)
            else:
                row.append(_unescape_mysql(raw))
            rows.append(row)
            in_row = False
            field = []
            row = []
            i += 1
            continue

        field.append(c)
        i += 1

    return rows

def iter_ar_posts_insert_statements():
    """
    يجمع INSERT كاملة لجدول ar_posts.
    المهم: يعتبر ; نهاية INSERT فقط إذا كانت خارج '...'
    """
    needle = "INSERT INTO `ar_posts`"
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        with zf.open(SQL_FILE_INSIDE_ZIP, "r") as f:
            in_stmt = False
            in_quote = False
            esc = False
            buf = []

            for raw in f:
                line = raw.decode("utf-8", errors="replace")

                # لو لسّا مش داخل INSERT نبحث عن بدايتها
                if not in_stmt:
                    pos = line.find(needle)
                    if pos == -1:
                        continue
                    line = line[pos:]
                    in_stmt = True
                    in_quote = False
                    esc = False
                    buf = []

                buf.append(line)

                # نفحص انتهاء الجملة على مستوى الأحرف
                for j, ch in enumerate(line):
                    if esc:
                        esc = False
                        continue
                    if ch == "\\":
                        esc = True
                        continue
                    if ch == "'":
                        in_quote = not in_quote
                        continue
                    if ch == ";" and not in_quote:
                        stmt = "".join(buf)
                        # قصّ كل شيء بعد أول ; (خارج النص) واحفظها كجملة واحدة
                        cut = stmt.find(";")
                        yield stmt[:cut+1]
                        in_stmt = False
                        in_quote = False
                        esc = False
                        buf = []
                        # قد يوجد INSERT آخر في نفس السطر (نادر) — نتجاهله لتبسيط التنفيذ
                        break

def build_wp_indexes():
    id_map = {}
    guid_map = {}
    title_map = {}  # title_norm -> list of candidates
    sig_map = {}

    count = 0
    for stmt in iter_ar_posts_insert_statements():
        if "VALUES" not in stmt:
            continue
        values = stmt.split("VALUES", 1)[1].strip()
        if values.endswith(";"):
            values = values[:-1]

        rows = parse_values_block(values)
        for r in rows:
            if len(r) < 23:
                continue

            post_type = (r[IDX_POST_TYPE] or "").strip()
            post_status = (r[IDX_POST_STATUS] or "").strip()
            if post_type != "post" or post_status != "publish":
                continue

            wp_id = str(r[IDX_ID])
            dt = parse_wp_datetime(r[IDX_POST_DATE]) or parse_wp_datetime(r[IDX_POST_MODIFIED]) or parse_wp_datetime(r[IDX_POST_DATE_GMT])
            if not dt:
                continue

            title = r[IDX_POST_TITLE] or ""
            guid = (r[IDX_GUID] or "").strip()
            content = r[IDX_POST_CONTENT] or ""

            st = normalize_strong(title)
            sig = signature_from_content(content)

            id_map[wp_id] = (dt, guid, st, sig)
            if guid:
                guid_map[guid] = (dt, wp_id)

            if st:
                title_map.setdefault(st, []).append((dt, wp_id, guid, sig))
            if sig:
                # خذ الأقدم لنفس التوقيع
                if sig not in sig_map or dt < sig_map[sig][0]:
                    sig_map[sig] = (dt, wp_id)

            count += 1

    print(f"✅ WP indexed posts (publish/post): {count}")
    return id_map, guid_map, title_map, sig_map

def pick_by_title_and_content(cands, news_content):
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0][0], cands[0][1]  # dt, wp_id

    nsig = signature_from_content(news_content or "")
    for (dt, wp_id, guid, sig) in cands:
        if sig and nsig and sig == nsig:
            return dt, wp_id

    # إذا تعدد ولم نجد توقيع مطابق: خذ الأقدم (أقرب للنشر الأصلي)
    cands_sorted = sorted(cands, key=lambda x: x[0])
    return cands_sorted[0][0], cands_sorted[0][1]

def main():
    backup_db()
    id_map, guid_map, title_map, sig_map = build_wp_indexes()

    report_rows = []
    updated = 0
    unmatched = 0

    with app.app_context():
        items = News.query.all()
        print(f"🔎 New DB news count: {len(items)}")

        for n in items:
            old_dt = n.created_at
            method = ""
            wp_id = ""
            new_dt = None

            # 1) wp-id
            if n.id and n.id.startswith("wp-"):
                cand = id_map.get(n.id[3:])
                if cand:
                    new_dt, wp_id = cand[0], n.id[3:]
                    method = "id"

            # 2) guid/link
            if not new_dt and (n.link or "").strip():
                cand = guid_map.get(n.link.strip())
                if cand:
                    new_dt, wp_id = cand[0], cand[1]
                    method = "guid"

            # 3) strong title (+ disambiguate by content signature)
            if not new_dt:
                st = normalize_strong(n.title or "")
                cands = title_map.get(st)
                picked = pick_by_title_and_content(cands, n.content)
                if picked:
                    new_dt, wp_id = picked[0], picked[1]
                    method = "title"

            # 4) content signature
            if not new_dt:
                nsig = signature_from_content(n.content or "")
                cand = sig_map.get(nsig)
                if cand:
                    new_dt, wp_id = cand[0], cand[1]
                    method = "content"

            if not new_dt:
                unmatched += 1
                report_rows.append([n.id, n.title, old_dt, "", "UNMATCHED", "", ""])
                continue

            if old_dt and old_dt.date() == new_dt.date():
                report_rows.append([n.id, n.title, old_dt, new_dt, "SAME", method, wp_id])
                continue

            print(f"✏️ { (n.title or '')[:60] } | {old_dt} -> {new_dt} ({method}, wp:{wp_id})")

            if not DRY_RUN:
                n.created_at = new_dt
                updated += 1

            report_rows.append([n.id, n.title, old_dt, new_dt, "UPDATED", method, wp_id])

        if not DRY_RUN:
            db.session.commit()

    report_path = "wp_date_fix_report_v4.csv"
    with open(report_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["news_id", "title", "old_created_at", "new_created_at", "status", "match_method", "wp_id"])
        w.writerows(report_rows)

    print("\n✅ Done.")
    print(f"➕ Updated: {updated}")
    print(f"❌ Unmatched: {unmatched}")
    print(f"📄 Report: {report_path}")
    if DRY_RUN:
        print("⚠️ DRY_RUN=True (لم يتم الحفظ). غيّرها إلى False وأعد التشغيل.")

if __name__ == "__main__":
    main()