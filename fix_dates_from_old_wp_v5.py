import os
import re
import csv
import shutil
import zipfile
from datetime import datetime
from html import unescape
from html.parser import HTMLParser

from app import app, db, News  # created_at موجود في News :contentReference[oaicite:3]{index=3}

ZIP_PATH = "web20_hind.zip"
SQL_FILE_INSIDE_ZIP = "web20_hind.sql"

DRY_RUN = False  # خلّيها False للتطبيق الفعلي

# WordPress ar_posts columns (الترتيب القياسي)
IDX_ID = 0
IDX_POST_DATE = 2
IDX_POST_DATE_GMT = 3
IDX_POST_CONTENT = 4
IDX_POST_TITLE = 5
IDX_POST_STATUS = 7
IDX_POST_MODIFIED = 14
IDX_GUID = 18
IDX_POST_TYPE = 20


# ----------------- تنظيف/تطبيع للمطابقة -----------------
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
    t = re.sub(r"<!--\s*/?wp:.*?-->", "", t, flags=re.I | re.S)  # Gutenberg
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


def signature_from_content(s: str, n=160) -> str:
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


# ----------------- Backup -----------------
def backup_db():
    db_path = os.path.join("instance", "news.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"لم أجد قاعدة البيانات: {db_path}")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join("instance", f"news_before_wp_date_fix_{ts}.db")
    shutil.copy2(db_path, backup_path)
    print(f"🧾 Backup created: {backup_path}")


# ----------------- Parser صحيح لـ INSERT (بدون قص غلط عند ;) -----------------
def iter_ar_posts_insert_statements():
    """
    يجمع INSERT كاملة لجدول ar_posts.
    يعتبر ; نهاية INSERT فقط إذا كانت خارج النص بين '...'
    """
    needle = "INSERT INTO `ar_posts`"
    in_stmt = False
    in_quote = False
    esc = False
    buf = []

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        with zf.open(SQL_FILE_INSIDE_ZIP, "r") as f:
            for raw in f:
                line = raw.decode("utf-8", errors="replace")
                i = 0

                while i < len(line):
                    if not in_stmt:
                        pos = line.find(needle, i)
                        if pos == -1:
                            break
                        in_stmt = True
                        in_quote = False
                        esc = False
                        buf = []
                        # ابدأ من pos
                        seg = line[pos:]
                        buf.append(seg)
                        # افحص seg حرف حرف
                        j = 0
                        while j < len(seg):
                            ch = seg[j]
                            if esc:
                                esc = False
                            elif ch == "\\":
                                esc = True
                            elif ch == "'":
                                in_quote = not in_quote
                            elif ch == ";" and not in_quote:
                                stmt = "".join(buf)
                                # قص عند نفس ; التي وجدناها (آخرها)
                                cut_len = len(stmt) - (len(seg) - j - 1)
                                yield stmt[:cut_len]
                                in_stmt = False
                                in_quote = False
                                esc = False
                                buf = []
                                # تابع البحث بعد نهاية الجملة ضمن نفس السطر
                                i = pos + j + 1
                                break
                            j += 1
                        else:
                            i = len(line)
                        continue

                    # داخل INSERT: أكمل تجميع
                    seg = line[i:]
                    buf.append(seg)
                    j = 0
                    while j < len(seg):
                        ch = seg[j]
                        if esc:
                            esc = False
                        elif ch == "\\":
                            esc = True
                        elif ch == "'":
                            in_quote = not in_quote
                        elif ch == ";" and not in_quote:
                            stmt = "".join(buf)
                            cut_len = len(stmt) - (len(seg) - j - 1)
                            yield stmt[:cut_len]
                            in_stmt = False
                            in_quote = False
                            esc = False
                            buf = []
                            i = i + j + 1
                            break
                        j += 1
                    else:
                        i = len(line)


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
                out.append(nxt)  # يشمل \', \", \\
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
            row.append(None if raw == "NULL" else _unescape_mysql(raw))
            field = []
            i += 1
            continue

        if c == ")":
            raw = "".join(field).strip()
            row.append(None if raw == "NULL" else _unescape_mysql(raw))
            rows.append(row)
            in_row = False
            field = []
            row = []
            i += 1
            continue

        field.append(c)
        i += 1

    return rows


# ----------------- بناء فهارس ووردبريس -----------------
def build_wp_indexes():
    guid_map = {}     # guid -> (dt, wp_id)
    title_map = {}    # norm_title -> list[(dt, wp_id, sig)]
    sig_map = {}      # sig -> (dt, wp_id)

    total = 0

    for stmt in iter_ar_posts_insert_statements():
        if "VALUES" not in stmt:
            continue
        values = stmt.split("VALUES", 1)[1].strip()
        if values.endswith(";"):
            values = values[:-1]

        for r in parse_values_block(values):
            if len(r) < 23:
                continue

            post_type = (r[IDX_POST_TYPE] or "").strip()
            post_status = (r[IDX_POST_STATUS] or "").strip()
            if post_type != "post" or post_status != "publish":
                continue

            wp_id = str(r[IDX_ID])

            dt = (
                parse_wp_datetime(r[IDX_POST_DATE])
                or parse_wp_datetime(r[IDX_POST_MODIFIED])
                or parse_wp_datetime(r[IDX_POST_DATE_GMT])
            )
            if not dt:
                continue

            title = r[IDX_POST_TITLE] or ""
            content = r[IDX_POST_CONTENT] or ""
            guid = (r[IDX_GUID] or "").strip()

            nt = normalize_strong(title)
            sig = signature_from_content(content)

            if guid:
                guid_map[guid] = (dt, wp_id)

            if nt:
                title_map.setdefault(nt, []).append((dt, wp_id, sig))

            if sig:
                # خذ الأقدم لنفس التوقيع
                if sig not in sig_map or dt < sig_map[sig][0]:
                    sig_map[sig] = (dt, wp_id)

            total += 1

    print(f"✅ WP indexed published posts: {total}")
    return guid_map, title_map, sig_map


def pick_from_title_candidates(cands, news_content):
    if not cands:
        return None
    if len(cands) == 1:
        dt, wp_id, _ = cands[0]
        return dt, wp_id

    nsig = signature_from_content(news_content or "")
    for (dt, wp_id, sig) in cands:
        if sig and nsig and sig == nsig:
            return dt, wp_id

    # إذا تعدد ولم نميز: خذ الأقدم
    cands_sorted = sorted(cands, key=lambda x: x[0])
    dt, wp_id, _ = cands_sorted[0]
    return dt, wp_id


# ----------------- التنفيذ -----------------
def main():
    backup_db()
    guid_map, title_map, sig_map = build_wp_indexes()

    updated = 0
    unmatched = 0
    report_rows = []

    with app.app_context():
        items = News.query.all()
        print(f"🔎 New DB news count: {len(items)}")

        for n in items:
            old_dt = n.created_at
            new_dt = None
            wp_id = ""
            method = ""

            # 1) guid via link (إذا عندك link)
            link = (n.link or "").strip()
            if link and link in guid_map:
                new_dt, wp_id = guid_map[link]
                method = "guid"

            # 2) title match
            if not new_dt:
                nt = normalize_strong(n.title or "")
                cands = title_map.get(nt)
                picked = pick_from_title_candidates(cands, n.content or "")
                if picked:
                    new_dt, wp_id = picked
                    method = "title"

            # 3) content signature
            if not new_dt:
                nsig = signature_from_content(n.content or "")
                if nsig and nsig in sig_map:
                    new_dt, wp_id = sig_map[nsig]
                    method = "content"

            if not new_dt:
                unmatched += 1
                report_rows.append([n.id, n.title, old_dt, "", "UNMATCHED", "", ""])
                continue

            # إذا نفس اليوم، اعتبرها SAME
            if old_dt and old_dt.date() == new_dt.date():
                report_rows.append([n.id, n.title, old_dt, new_dt, "SAME", method, wp_id])
                continue

            # تحديث
            if not DRY_RUN:
                n.created_at = new_dt
                updated += 1

            report_rows.append([n.id, n.title, old_dt, new_dt, "UPDATED", method, wp_id])

        if not DRY_RUN:
            db.session.commit()

    report_path = "wp_date_fix_report_v5.csv"
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