import os
import json
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# إعداد المسارات
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'news.db')
json_path = os.path.join(basedir, 'full_news.json')

# إعداد قاعدة البيانات
Base = declarative_base()
engine = create_engine(f"sqlite:///{db_path}")
Session = sessionmaker(bind=engine)
session = Session()

# نموذج الأخبار
class News(Base):
    __tablename__ = 'news'
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    link = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

# إنشاء الجدول
Base.metadata.create_all(engine)

# قراءة الأخبار من JSON وترحيلها
with open(json_path, 'r', encoding='utf-8') as f:
    news_items = json.load(f)

for item in news_items:
    news_id = str(item.get("id")) if item.get("id") else str(uuid.uuid4())
    news = News(
        id=news_id,
        title=item.get("title", "بدون عنوان"),
        content=item.get("content", ""),
        link=item.get("link", "")
    )
    session.add(news)

session.commit()
print("✅ تم ترحيل الأخبار إلى قاعدة البيانات الجديدة.")
