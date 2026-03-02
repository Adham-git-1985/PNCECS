import sqlite3
import os

# تحديد موقع القاعدة
db_path = os.path.join("instance", "news.db")

# الاتصال بقاعدة البيانات
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# إضافة العمود is_custom إذا لم يكن موجودًا
try:
    cursor.execute("ALTER TABLE news ADD COLUMN is_custom BOOLEAN DEFAULT 0 NOT NULL")
    print("✅ تم إضافة العمود is_custom إلى جدول news.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ️ العمود is_custom موجود مسبقًا.")
    else:
        print("❌ خطأ:", e)

conn.commit()
conn.close()
