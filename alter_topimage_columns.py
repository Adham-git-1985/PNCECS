from flask import Flask
from models import db
import os
from sqlalchemy import text

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'instance', 'news.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    with db.engine.connect() as connection:
        try:
            connection.execute(text("ALTER TABLE top_image ADD COLUMN news_title TEXT"))
            print("✅ تم إضافة عمود news_title بنجاح")
        except Exception as e:
            print(f"⚠️ خطأ عند إضافة news_title: {e}")

        try:
            connection.execute(text("ALTER TABLE top_image ADD COLUMN news_content TEXT"))
            print("✅ تم إضافة عمود news_content بنجاح")
        except Exception as e:
            print(f"⚠️ خطأ عند إضافة news_content: {e}")