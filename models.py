from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class Gallery(db.Model):
    __tablename__ = "gallery"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)

    title_en = db.Column(db.String(255))         # إنجليزي
    description_en = db.Column(db.Text)

    # استخدم datetime.utcnow لتفادي الحاجة إلى timezone ولاختصار التعارض بين naive/aware
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    news_id = db.Column(db.String, db.ForeignKey('news.id'), nullable=True)

    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), index=True)  # FK + index
    category = db.relationship("Category", back_populates="images")

class Category(db.Model):
    __tablename__ = "category"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, index=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    name_en = db.Column(db.String(120))
    images = db.relationship("Gallery", back_populates="category")


# فهارس اختيارية للبحث (تحسّن الأداء لما يكبر الجدول)
db.Index("ix_gallery_title", Gallery.title)
db.Index("ix_gallery_title_en", Gallery.title_en)
db.Index("ix_gallery_desc", Gallery.description)
db.Index("ix_gallery_desc_en", Gallery.description_en)


class News(db.Model):
    __tablename__ = 'news'

    id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_custom = db.Column(db.Boolean, default=False, nullable=False)

    # حقول اللغة الإنجليزية
    title_en = db.Column(db.String(200))
    content_en = db.Column(db.Text)

    # علاقة عكسية مع TopImage (لأن TopImage.news_id موجودة بالفعل)
    top_images = db.relationship('TopImage', backref='news', lazy=True)


class TopImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    news_title = db.Column(db.String(200), nullable=True)
    news_content = db.Column(db.Text, nullable=True)
    news_id = db.Column(db.String, db.ForeignKey('news.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    description_en = db.Column(db.Text)
    news_title_en = db.Column(db.Text)
    news_content_en = db.Column(db.Text)
    title_en = db.Column(db.String(255), nullable=True)
    caption_en = db.Column(db.String(255), nullable=True)


class Version(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)  # عنوان الإصدار
    file_path = db.Column(db.String(255), nullable=False)  # رابط الـ PDF
    thumbnail_path = db.Column(db.String(255), nullable=True)  # رابط الصورة المصغرة
    category = db.Column(db.String(50), nullable=False)  # فئة الإصدار (مجلة بصمات / أوراق ودراسات / مرصد الانتهاكات)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    images = db.relationship('AnnouncementImage', backref='announcement', cascade='all, delete-orphan')
    attachments = db.relationship('AnnouncementAttachment', backref='announcement', cascade='all, delete-orphan')
    title_en = db.Column(db.Text)
    content_en = db.Column(db.Text)


class AnnouncementImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcement.id'), nullable=False)


class AnnouncementAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    mimetype = db.Column(db.String(50))
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcement.id'), nullable=False)

    def __repr__(self):
        return f'<AnnouncementAttachment {self.filename}>'
