import os
import re
import csv
import shutil
import zipfile
from datetime import datetime
from html import unescape
from html.parser import HTMLParser

from app import app, db, News  # News.created_at موجودة في الموديل :contentReference[oaicite:2]{index=2}

ZIP_PATH = "web20_hind.zip"
SQL_FILE_INSIDE_ZIP = "web20_hind.sql"

DRY_RUN = False  # خلّيها False عشان يحفظ فعلياً

# أعمدة ar_posts بالترتيب القياسي في الدامب
IDX_ID = 0
IDX_POST_DATE = 2
IDX_POST_CONTENT = 4
IDX_POST_TITLE = 5
IDX_POST_STATUS = 7
IDX_POST_MODIFIED = 14
IDX_GUID = 18
IDX_POST_TYPE = 20


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

    # حذف تعليقات Gutenberg
    t = re.sub(r"<!--\s*/?wp:.*?-->", "", t, flags=re.I | re.S)

    # حذف shortcodes مثل [table id=.. /] [vc_row]...
    t = re.sub(r"\[/?[a-zA-Z][^\]]*\]", "", t)

    # أسطر قبل نزع HTML
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</p\s*>", "\n", t)
    t = re.sub(r"(?i)</div\s*>", "\n", t)
    t = re.sub(r"(?i)</li\s*>", "\n", t)

    t = strip_html(t)
    t = t.replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n\s*\n+", "\n\n", t)
    return t.strip()


_AR_DIACRITICS = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed]")
_PUNCT = re.compile(r"[\"'“”‘’`´\(\)\[\]\{\}\<\>\|،,؛;:!?\.\-–—_+/\\ـ]+")


def normalize_title_strong(s: str) -> str:
    if not s:
        return ""
    s = unescape(s).strip()
    s = s.replace("\u0640", "")  # tatweel
    s = _AR_DIACRITICS.sub("", s)
    s = _PUNCT.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def signature_from_content(s: str, n=120) -> str:
    t = clean_wp_text(s)
    t = normalize_title_strong(t)
    t = re.sub(r"\s+", " ", t).strip()
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


def iter_ar_posts_rows():
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        with zf.open(SQL_FILE_INSIDE_ZIP, "r") as f:
            collecting = False
            buffer = ""

            for raw in f:
                line = raw.decode("utf-8", errors="replace")

                if not collecting:
                    if line.startswith("INSERT INTO `ar_posts`"):
                        collecting = True
                        buffer = line
                        if ";" in line:
                            collecting = False
                            stmt = buffer
                            buffer = ""
                            yield from extract_rows_from_insert(stmt)
                    continue

                buffer += line
                if ";" in line:
                    collecting = False
                    stmt = buffer
                    buffer = ""
                    yield from extract_rows_from_insert(stmt)


def extract_rows_from_insert(stmt: str):
    if "VALUES" not in stmt:
        return
    values_part = stmt.split("VALUES", 1)[1].strip()
    if values_part.endswith(";"):
        values_part = values_part[:-1]
    for row in parse_values_block(values_part):
        yield row


def backup_db():
    db_path = os.path.join("instance", "news.db")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join("instance", f"news_before_wp_sync_{ts}.db")
    shutil.copy2(db_path, backup_path)
    print(f"🧾 Backup created: {backup_path}")


def build_indexes():
    id_map = {}       # wp_id -> (dt, guid, norm_title, content_sig)
    guid_map = {}     # guid -> (dt, wp_id)
    title_map = {}    # strong_title -> (dt, wp_id)
    sig_map = {}      # content_sig -> (dt, wp_id)

    cnt = 0
    for r in iter_ar_posts_rows():
        if len(r) < 23:
            continue

        post_type = (r[IDX_POST_TYPE] or "").strip()
        post_status = (r[IDX_POST_STATUS] or "").strip()
        if post_type != "post" or post_status != "publish":
            continue

        wp_id = str(r[IDX_ID])
        dt = parse_wp_datetime(r[IDX_POST_DATE]) or parse_wp_datetime(r[IDX_POST_MODIFIED])
        if not dt:
            continue

        title = r[IDX_POST_TITLE] or ""
        guid = (r[IDX_GUID] or "").strip()
        content = r[IDX_POST_CONTENT] or ""

        st = normalize_title_strong(title)
        sig = signature_from_content(content)

        id_map[wp_id] = (dt, guid, st, sig)
        if guid:
            guid_map[guid] = (dt, wp_id)

        # إذا العنوان تكرر نختار الأقدم (الأقرب لـ “تاريخ نشر أصلي” عادة)
        if st:
            if st not in title_map or dt < title_map[st][0]:
                title_map[st] = (dt, wp_id)

        if sig:
            if sig not in sig_map or dt < sig_map[sig][0]:
                sig_map[sig] = (dt, wp_id)

        cnt += 1

    print(f"✅ Indexed published WP posts: {cnt}")
    return id_map, guid_map, title_map, sig_map


def main():
    backup_db()

    id_map, guid_map, title_map, sig_map = build_indexes()

    report_rows = []
    updated = 0
    unmatched = 0

    with app.app_context():
        items = News.query.all()
        print(f"🔎 New DB News count: {len(items)}")

        for n in items:
            old_dt = n.created_at
            method = None
            wp_id = None
            new_dt = None

            # 1) wp-id
            if n.id and n.id.startswith("wp-"):
                wp_id_candidate = n.id[3:]
                info = id_map.get(wp_id_candidate)
                if info:
                    new_dt = info[0]
                    wp_id = wp_id_candidate
                    method = "id"

            # 2) guid via link
            if not new_dt and (n.link or "").strip():
                info = guid_map.get(n.link.strip())
                if info:
                    new_dt, wp_id = info[0], info[1]
                    method = "guid"

            # 3) strong title match
            if not new_dt:
                st = normalize_title_strong(n.title or "")
                info = title_map.get(st)
                if info:
                    new_dt, wp_id = info[0], info[1]
                    method = "title"

            # 4) content signature match
            if not new_dt:
                sig = signature_from_content(n.content or "")
                info = sig_map.get(sig)
                if info:
                    new_dt, wp_id = info[0], info[1]
                    method = "content"

            if not new_dt:
                unmatched += 1
                report_rows.append([n.id, n.title, old_dt, "", "UNMATCHED", "", ""])
                continue

            # إذا نفس اليوم لا تغيّر
            if old_dt and old_dt.date() == new_dt.date():
                report_rows.append([n.id, n.title, old_dt, new_dt, "SAME", method, wp_id])
                continue

            print(f"✏️ {n.title[:60]} | {old_dt} -> {new_dt} ({method}, wp:{wp_id})")

            if not DRY_RUN:
                n.created_at = new_dt
                updated += 1

            report_rows.append([n.id, n.title, old_dt, new_dt, "UPDATED", method, wp_id])

        if not DRY_RUN:
            db.session.commit()

    # report
    report_path = "wp_date_fix_report.csv"
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