import json
from app import db, News, app
from datetime import datetime
import uuid

# تحميل البيانات من ملف JSON
with open('full_news.json', 'r', encoding='utf-8') as f:
    news_list = json.load(f)

with app.app_context():
    for item in news_list:
        news = News(
            id=str(uuid.uuid4()),  # أو str(item['id']) إذا كنت تريده مطابقًا
            title=item['title'],
            content=item['content'],
            link=item.get('link', ''),
            created_at=datetime.utcnow(),
            is_custom=True
        )
        db.session.add(news)
    db.session.commit()

print("✅ تم إدخال جميع الأخبار بنجاح.")
