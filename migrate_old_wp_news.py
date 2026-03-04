import zipfile
from datetime import datetime
from app import app, db, News

ZIP_PATH = "web20_hind.zip"
SQL_NAME_INSIDE_ZIP = "web20_hind.sql"

START_DATE = datetime(2025, 10, 1)  # 01-10-2025

# مؤشرات أعمدة جدول ar_posts حسب الدامب
IDX_ID = 0
IDX_POST_DATE = 2
IDX_POST_CONTENT = 4
IDX_POST_TITLE = 5
IDX_POST_STATUS = 7
IDX_GUID = 18
IDX_POST_TYPE = 20


def _unescape_mysql(s: str) -> str:
    """يفك ترميزات MySQL الشائعة داخل النصوص."""
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
                out.append(nxt)  # يشمل \", \', \\
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _parse_values_block(values_text: str):
    """
    يحول:
      (..),(..),(..)
    إلى قائمة Rows
    """
    rows = []
    row = []
    field = []

    in_quote = False
    in_row = False

    i = 0
    while i < len(values_text):
        c = values_text[i]

        if not in_row:
            if c == "(":
                in_row = True
                row = []
                field = []
            i += 1
            continue

        # داخل row
        if in_quote:
            if c == "'":
                in_quote = False
            else:
                field.append(c)
            i += 1
            continue

        # خارج quote وداخل row
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


def _process_insert_statement(stmt: str):
    if "VALUES" not in stmt:
        return []

    values_part = stmt.split("VALUES", 1)[1].strip()

    # إزالة ; في النهاية
    if values_part.endswith(";"):
        values_part = values_part[:-1]

    return _parse_values_block(values_part)


def migrate():
    inserted = 0
    skipped = 0
    found_matching = 0

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        with zf.open(SQL_NAME_INSIDE_ZIP, "r") as f, app.app_context():
            buffer = ""
            collecting = False

            for raw in f:
                line = raw.decode("utf-8", errors="replace")

                if not collecting:
                    if line.startswith("INSERT INTO `ar_posts`"):
                        collecting = True
                        buffer = line
                        if ";" in line:
                            rows = _process_insert_statement(buffer)
                            collecting = False
                            buffer = ""

                            for r in rows:
                                if len(r) < 23:
                                    continue

                                post_type = (r[IDX_POST_TYPE] or "").strip()
                                post_status = (r[IDX_POST_STATUS] or "").strip()

                                if post_type != "post" or post_status != "publish":
                                    continue

                                try:
                                    post_date = datetime.strptime(r[IDX_POST_DATE], "%Y-%m-%d %H:%M:%S")
                                except Exception:
                                    continue

                                if post_date < START_DATE:
                                    continue

                                found_matching += 1

                                wp_id = str(r[IDX_ID])
                                new_id = f"wp-{wp_id}"  # ID ثابت لمنع التكرار عند إعادة التشغيل

                                if News.query.get(new_id):
                                    skipped += 1
                                    continue

                                title = (r[IDX_POST_TITLE] or "").strip()
                                content = r[IDX_POST_CONTENT] or ""
                                link = r[IDX_GUID] or ""

                                if not title:
                                    # إذا بدون عنوان، تجاهله
                                    skipped += 1
                                    continue

                                news = News(
                                    id=new_id,
                                    title=title,
                                    content=content,
                                    link=link,
                                    created_at=post_date,
                                    is_custom=True
                                )

                                db.session.add(news)
                                inserted += 1

                            db.session.commit()

                    continue

                # collecting
                buffer += line
                if ";" in line:
                    rows = _process_insert_statement(buffer)
                    collecting = False
                    buffer = ""

                    for r in rows:
                        if len(r) < 23:
                            continue

                        post_type = (r[IDX_POST_TYPE] or "").strip()
                        post_status = (r[IDX_POST_STATUS] or "").strip()

                        if post_type != "post" or post_status != "publish":
                            continue

                        try:
                            post_date = datetime.strptime(r[IDX_POST_DATE], "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            continue

                        if post_date < START_DATE:
                            continue

                        found_matching += 1

                        wp_id = str(r[IDX_ID])
                        new_id = f"wp-{wp_id}"

                        if News.query.get(new_id):
                            skipped += 1
                            continue

                        title = (r[IDX_POST_TITLE] or "").strip()
                        content = r[IDX_POST_CONTENT] or ""
                        link = r[IDX_GUID] or ""

                        if not title:
                            skipped += 1
                            continue

                        news = News(
                            id=new_id,
                            title=title,
                            content=content,
                            link=link,
                            created_at=post_date,
                            is_custom=True
                        )

                        db.session.add(news)
                        inserted += 1

                    db.session.commit()

    print("✅ انتهى النقل.")
    print(f"🔎 الأخبار المطابقة بعد 01-10-2025: {found_matching}")
    print(f"➕ تم إدخال: {inserted}")
    print(f"⏭️ تم تجاوز/موجود مسبقاً: {skipped}")


if __name__ == "__main__":
    migrate()