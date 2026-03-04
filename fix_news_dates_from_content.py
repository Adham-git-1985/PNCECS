import os
import re
import shutil
from datetime import datetime

from app import app, db, News  # News.created_at موجود في app.py


# ✅ إذا بدك أول تجربة بدون تعديل فعلي
DRY_RUN = False

# ✅ نطاق سنوات منطقي لتجنب التقاط أرقام غلط
MIN_YEAR = 1995
MAX_YEAR = 2035

# يلتقط: 2023/10/20 أو 2023-10-20 (حتى لو بعدها - أو نص)
DATE_RE = re.compile(r"\b(19\d{2}|20\d{2})[/-](\d{1,2})[/-](\d{1,2})\b")


def backup_db():
    db_path = os.path.join("instance", "news.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"لم أجد قاعدة البيانات: {db_path}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join("instance", f"news_before_date_fix_{ts}.db")
    shutil.copy2(db_path, backup_path)
    print(f"🧾 تم عمل نسخة احتياطية: {backup_path}")


def extract_original_date(content: str):
    """
    نأخذ التاريخ الأصلي من بداية الخبر غالباً.
    - نبحث أولاً في أول 600 حرف (عادة فيه: الدولة - اليوم - 2023/10/20 -)
    - إذا لم نجد، نبحث في أول 3000 حرف.
    """
    if not content:
        return None

    for text in (content[:600], content[:3000]):
        m = DATE_RE.search(text)
        if not m:
            continue

        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))

        if not (MIN_YEAR <= y <= MAX_YEAR):
            continue

        try:
            return datetime(y, mo, d, 0, 0, 0)
        except ValueError:
            return None

    return None


def main():
    backup_db()

    updated = 0
    skipped_no_date = 0
    skipped_same = 0

    with app.app_context():
        all_news = News.query.all()

        print(f"🔎 عدد الأخبار التي سيتم فحصها: {len(all_news)}")

        for n in all_news:
            original_dt = extract_original_date(n.content or "")
            if not original_dt:
                skipped_no_date += 1
                continue

            current = n.created_at
            # إذا التاريخ أصلاً مطابق (نقارن يوم/شهر/سنة فقط)
            if current and current.date() == original_dt.date():
                skipped_same += 1
                continue

            print(f"✏️ تعديل: {n.title[:60]} ... | {current.date() if current else None} -> {original_dt.date()}")

            if not DRY_RUN:
                n.created_at = original_dt
                updated += 1

        if not DRY_RUN:
            db.session.commit()

    print("\n✅ انتهى.")
    print(f"➕ تم تعديل تواريخ: {updated}")
    print(f"⏭️ بدون تاريخ أصلي داخل النص: {skipped_no_date}")
    print(f"⏭️ تاريخ مطابق أصلاً: {skipped_same}")
    if DRY_RUN:
        print("⚠️ DRY_RUN=True يعني لم يتم الحفظ فعلياً. غيّرها لـ False ثم أعد التشغيل.")


if __name__ == "__main__":
    main()