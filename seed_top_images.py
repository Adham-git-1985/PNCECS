from models import db, TopImage
from flask import Flask
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'instance', 'news.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

    # أضف صور موجودة فعلاً في المجلد static/images/top_images/
    images = [
        {"image": "top1.jpg", "title": "الصورة الأولى"},
        {"image": "top2.jpg", "title": "الصورة الثانية"},
        {"image": "top3.jpg", "title": "الصورة الثالثة"}
    ]

    for img in images:
        entry = TopImage(**img)
        db.session.add(entry)

    db.session.commit()
    print("✅ تم إدخال الصور بنجاح في جدول TopImage.")
