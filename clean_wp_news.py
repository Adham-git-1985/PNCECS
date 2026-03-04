import os
import re
import shutil
from datetime import datetime
from html import unescape
from html.parser import HTMLParser

from app import app, db, News


# ✅ يعدّل فقط الأخبار التي تم إدخالها من الووردبريس (IDs مثل wp-123)
WP_ID_PREFIX = "wp-"

# ✅ يعمل نسخة احتياطية قبل التنظيف
BACKUP_DIR = "instance"


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, d):
        if d:
            self.parts.append(d)

    def get_data(self):
        return "".join(self.parts)


def strip_html(html: str) -> str:
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def clean_wp_content(text: str) -> str:
    if not text:
        return ""

    # فك ترميز HTML entities مثل &nbsp; &amp;
    t = unescape(text)

    # إزالة تعليقات Gutenberg مثل:
    # <!-- wp:paragraph -->  <!-- /wp:paragraph -->
    t = re.sub(r"<!--\s*/?wp:.*?-->", "", t, flags=re.IGNORECASE | re.DOTALL)

    # إزالة shortcodes مثل [vc_row] ... [/vc_row] أو [gallery ids="..."]
    # (نزيل الوسوم نفسها، وأحياناً يبقى نص داخلي جيد)
    t = re.sub(r"\[/?[a-zA-Z][^\]]*\]", "", t)

    # تحويل بعض وسوم HTML لأسطر قبل نزع HTML
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</p\s*>", "\n", t)
    t = re.sub(r"(?i)</div\s*>", "\n", t)
    t = re.sub(r"(?i)</h[1-6]\s*>", "\n", t)
    t = re.sub(r"(?i)</li\s*>", "\n", t)

    # نزع بقية HTML
    t = strip_html(t)

    # تنظيف مسافات
    t = t.replace("\xa0", " ")  # nbsp
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n\s*\n+", "\n\n", t)  # أقصى شيء سطرين فراغ
    t = t.strip()

    return t


def backup_db():
    # يعتمد على مسار قاعدة البيانات في مشروعك (instance/news.db)
    db_path = os.path.join("instance", "news.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"لم أجد قاعدة البيانات هنا: {db_path}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"news_before_cleanup_{ts}.db")
    shutil.copy2(db_path, backup_path)
    print(f"🧾 تم عمل نسخة احتياطية: {backup_path}")
    return backup_path


def main():
    backup_db()

    updated = 0
    skipped = 0

    with app.app_context():
        # تنظيف فقط الأخبار المستوردة من ووردبريس
        items = News.query.filter(News.id.like(f"{WP_ID_PREFIX}%")).all()

        print(f"🔎 عدد أخبار ووردبريس التي سيتم فحصها: {len(items)}")

        for n in items:
            old_title = n.title or ""
            old_content = n.content or ""

            new_title = old_title.strip()
            new_content = clean_wp_content(old_content)

            # إذا ما تغير شيء، نتجاوز
            if new_title == old_title and new_content == old_content:
                skipped += 1
                continue

            n.title = new_title
            n.content = new_content
            updated += 1

        db.session.commit()

    print("✅ انتهى التنظيف.")
    print(f"✏️ تم تعديل: {updated}")
    print(f"⏭️ لم يتغير شيء: {skipped}")


if __name__ == "__main__":
    main()