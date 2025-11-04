from flask import send_from_directory
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask import has_request_context
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload
from flask_migrate import Migrate  # إضافة الاستيراد هنا
from datetime import datetime, timedelta, timezone
from pathlib import Path
from flask import g
import json
import os
import subprocess
import math
import uuid
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from models import db, TopImage, Version, Announcement, AnnouncementImage, AnnouncementAttachment, News, Gallery, User
from models import Category
from pdf2image import convert_from_path
from werkzeug.utils import secure_filename
import time
from flask_mail import Mail, Message
import traceback
from flask import jsonify
from markupsafe import Markup
# ====== routes for reports explorer ======
import os, re, glob
from openai import OpenAI, RateLimitError, APIError, APITimeoutError, AuthenticationError, BadRequestError
from flask_cors import CORS
from dotenv import load_dotenv
from flask import Response, request
from urllib.parse import urljoin
import html
import zipfile

from flask import send_file, request
import io, json



# Configure logging to write to a file named 'app.log'
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

TRANSLATIONS = {
    "ar": {
        # عامة / رأس الصفحة
        "site_name": "اللجنة الوطنية الفلسطينية للتربية والثقافة والعلوم",
        "home": "الرئيسية",
        "about": "نبذة عن اللجنة",
        "news": "الأخبار",
        "announcements": "الإعلانات",
        "gallery": "معرض الصور",
        "contact": "اتصل بنا",
        "search": "بحث",
        "language": "اللغة",
        "arabic": "عربي",
        "english": "English",
        "partners": "الشركاء",
        "achievement_reports": "تقارير الإنجاز",
        "project_form": "نموذج المشاريع",
        "about": "نبذة عن اللجنة",

        # عناصر الواجهة
        "latest_news": "آخر الأخبار",
        "read_more": "اقرأ المزيد",
        "view_all": "عرض الكل",
        "no_results": "لا توجد نتائج",
        "loading": "جاري التحميل...",
        "more": "المزيد",

        # paginate
        "prev": "السابق",
        "next": "التالي",
        "page": "صفحة",

        # نموذج عام
        "title": "العنوان",
        "content": "المحتوى",
        "link": "الرابط",
        "image": "الصورة",
        "save": "حفظ",
        "cancel": "إلغاء",
        "edit": "تعديل",
        "delete": "حذف",
        "confirm_delete": "هل أنت متأكد من الحذف؟",
        "upload": "رفع",
        "optional": "اختياري",
        "required": "مطلوب",

        # الأخبار
        "news_list": "قائمة الأخبار",
        "news_details": "تفاصيل الخبر",
        "created_at": "تاريخ الإضافة",

        # الإعلانات
        "announcements_header": "الإعلانات",
        "announcement_details": "تفاصيل الإعلان",

        # المعرض
        "gallery_header": "معرض الصور",
        "image_title": "عنوان الصورة",
        "image_description": "وصف الصورة",

        # الدخول/لوحة التحكم
        "login": "تسجيل الدخول",
        "logout": "تسجيل الخروج",
        "username": "اسم المستخدم",
        "password": "كلمة المرور",
        "admin_panel": "لوحة التحكم",

        # رسائل قصيرة
        "saved_success": "تم الحفظ بنجاح",
        "deleted_success": "تم الحذف بنجاح",
        "error_generic": "حدث خطأ غير متوقع",

        # شركاؤنا
        "partners_title": "شركاؤنا",
        "partners_intro": "نفتخر بشراكاتنا مع المؤسسات المحلية والدولية التي تدعم رسالتنا التعليمية والثقافية.",
        "strategic_partners": "الشركاء الاستراتيجيون",
        "local_partners": "الشركاء المحليون",
        "international_partners": "الشركاء الدوليون",
    },
    "en": {
        # Global / Header
        "site_name": "Palestinian National Commission for Education, Culture and Science",
        "home": "Home",
        "about": "About",
        "news": "News",
        "announcements": "Announcements",
        "gallery": "Gallery",
        "contact": "Contact",
        "search": "Search",
        "language": "Language",
        "arabic": "عربي",
        "english": "English",
        "partners": "Partners",
        "achievement_reports": "Achievement Reports",
        "project_form": "Project Form",
        "about": "About PNCECS",

        # UI
        "latest_news": "Latest News",
        "read_more": "Read more",
        "view_all": "View all",
        "no_results": "No results found",
        "loading": "Loading...",
        "more": "More",

        # paginate
        "prev": "Previous",
        "next": "Next",
        "page": "Page",

        # Forms
        "title": "Title",
        "content": "Content",
        "link": "Link",
        "image": "Image",
        "save": "Save",
        "cancel": "Cancel",
        "edit": "Edit",
        "delete": "Delete",
        "confirm_delete": "Are you sure you want to delete?",
        "upload": "Upload",
        "optional": "Optional",
        "required": "Required",

        # News
        "news_list": "News List",
        "news_details": "News Details",
        "created_at": "Created at",

        # Announcements
        "announcements_header": "Announcements",
        "announcement_details": "Announcement Details",

        # Gallery
        "gallery_header": "Photo Gallery",
        "image_title": "Image Title",
        "image_description": "Image Description",

        # Auth/Admin
        "login": "Login",
        "logout": "Logout",
        "username": "Username",
        "password": "Password",
        "admin_panel": "Admin Panel",

        # Messages
        "saved_success": "Saved successfully",
        "deleted_success": "Deleted successfully",
        "error_generic": "Unexpected error occurred",

        # Partners
        "partners_title": "Our Partners",
        "partners_intro": "We are proud of our partnerships with local and international institutions supporting our educational and cultural mission.",
        "strategic_partners": "Strategic Partners",
        "local_partners": "Local Partners",
        "international_partners": "International Partners",
    }
}




app = Flask(__name__)

load_dotenv()  # Load environment variables from .env

CORS(app)
# make Flask trust IIS/ARR's X-Forwarded-* headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

from flask import g, session, redirect, request, url_for


# إعداد البريد
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'pncecs.info@gmail.com'
app.config['MAIL_PASSWORD'] = 'wwxx mzyh uwti ponm'
app.config['MAIL_DEFAULT_SENDER'] = 'pncecs.info@gmail.com'

# تهيئة mail وربطه بالتطبيق
mail = Mail(app)

basedir = Path(__file__).resolve().parent
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_secret')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'instance', 'news.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db)  # تهيئة Migrate بعد تهيئة db

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images', 'gallery') # للمجلد الخاص بالصور
app.config['PDF_UPLOAD_FOLDER'] = os.path.join('static')  # للمجلد الخاص بالـ PDF
app.config['TOP_IMAGES_FOLDER'] = str(basedir / 'static' / 'images' / 'top_images')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB
# تأكد من أنك قد قمت بتحديد المسار لمجلد الصور المصغرة
app.config['THUMBNAIL_FOLDER'] = os.path.join('static', 'images', 'thumbnails')
#logging.info('adham line 38: '+ os.path.join('static', 'images', 'thumbnails'))



# تأكد من أن مجلد الصور المصغرة موجود
os.makedirs(app.config['THUMBNAIL_FOLDER'], exist_ok=True)
#os.makedirs(app.config['PDF_UPLOAD_FOLDER'], exist_ok=True)  # هذا سيجعل المجلد موجودًا إذا لم يكن موجودًا

from openai import OpenAI, RateLimitError, APIError, APITimeoutError, AuthenticationError, BadRequestError


def full_url(path: str) -> str:
    return urljoin(request.url_root, path.lstrip('/'))

def iso_date(dt: datetime | None) -> str:
    if not dt:
        return datetime.utcnow().strftime("%Y-%m-%d")
    # لو عندك تواريخ timezone-aware خليك تستخدم dt.date().isoformat()
    return dt.date().isoformat()

def news_lastmod(n):
    return getattr(n, "updated_at", None) or getattr(n, "created_at", None)

def ann_lastmod(a):
    return getattr(a, "updated_at", None) or getattr(a, "created_at", None)

def gal_lastmod(g):
    return getattr(g, "uploaded_at", None)

@app.context_processor
def inject_theme():
    # القيم الممكنة: 'light' / 'dark' / 'auto'
    theme = request.cookies.get('theme', 'auto')
    return dict(theme=theme)

@app.route("/robots.txt")
def robots_txt():
    sitemap_url = urljoin(request.url_root, "sitemap.xml")
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {sitemap_url}",
        ""
    ]
    return Response("\n".join(lines), mimetype="text/plain")

@app.route("/sitemap.xml")
def sitemap_xml():
    # ====== اجمع الروابط ======
    urls = []

    # صفحات ثابتة (عدّل حسب موقعك)
    static_pairs = [
        ("/", "/en/"),                         # الرئيسية
        ("/about", "/en/about"),               # نبذة
        ("/contact", "/en/contact"),           # تواصل
        ("/gallery", "/en/gallery"),           # المعرض
        ("/news", "/en/news"),                 # قائمة الأخبار
        ("/announcements", "/en/announcements")# الإعلانات (لو عندك)
    ]
    today = datetime.utcnow()
    for ar, en in static_pairs:
        urls.append({
            "loc": full_url(ar),
            "lastmod": iso_date(today),
            "changefreq": "weekly",
            "priority": "0.8",
            "alternates": [
                {"hreflang": "ar", "href": full_url(ar)},
                {"hreflang": "en", "href": full_url(en)},
            ]
        })
        # خيار: أضف نسخة EN كعنصر مستقل (ليس لازماً، لأننا نوفر alternates)
        # نكتفي بعنصر واحد لكل زوج.

    # الأخبار (تفاصيل الخبر AR/EN)
    try:
        news_list = News.query.order_by(News.created_at.desc()).all()
        for n in news_list:
            ar_path = url_for("news_detail", id=n.id)                   # تأكد من اسم المسار
            en_path = "/en" + ar_path                                   # لو عندك مسارات موازية
            urls.append({
                "loc": full_url(ar_path),
                "lastmod": iso_date(news_lastmod(n)),
                "changefreq": "weekly",
                "priority": "0.9",
                "alternates": [
                    {"hreflang": "ar", "href": full_url(ar_path)},
                    {"hreflang": "en", "href": full_url(en_path)},
                ]
            })
    except Exception:
        pass

    # الإعلانات (إن وُجدت)
    try:
        anns = Announcement.query.order_by(Announcement.created_at.desc()).all()
        for a in anns:
            ar_path = url_for("announcement_detail", id=a.id)
            en_path = "/en" + ar_path
            urls.append({
                "loc": full_url(ar_path),
                "lastmod": iso_date(ann_lastmod(a)),
                "changefreq": "weekly",
                "priority": "0.7",
                "alternates": [
                    {"hreflang": "ar", "href": full_url(ar_path)},
                    {"hreflang": "en", "href": full_url(en_path)},
                ]
            })
    except Exception:
        pass

    # المعرض (صورة لكل عنصر + صُوَر)
    try:
        images = Gallery.query.order_by(Gallery.uploaded_at.desc()).all()
        for g in images:
            # صفحة عرض الصورة (لو عندك صفحة تفصيلية للصور؛ إن لم توجد استخدم صفحة المعرض العامة مع هاشر أو بارامتر)
            ar_path = url_for("gallery")  # أو url_for("image_detail", id=g.id) إن وُجد
            en_path = "/en" + ar_path

            #img_url = full_url(url_for("static", filename=f"images/gallery/{g.filename}"))
            #title = g.title_en if (session.get('lang') == 'en' and g.title_en) else (g.title or "")

            img_url = url_for("static", filename=f"images/gallery/{g.filename}", _external=True)
            title = (g.title_en if (session.get("lang") == "en" and g.title_en) else g.title) or "Image"

            urls.append({
                "loc": full_url(ar_path),
                "lastmod": iso_date(gal_lastmod(g)),
                "changefreq": "weekly",
                "priority": "0.6",
                "alternates": [
                    {"hreflang": "ar", "href": full_url(ar_path)},
                    {"hreflang": "en", "href": full_url(en_path)},
                ],
                "images": [
                    {
                        "image_loc": img_url,
                        "image_title": title or "Image"
                    }
                ]
            })
    except Exception:
        pass

    # ====== ابنِ XML ======
    # namespaces: xhtml للروابط البديلة، والصور
    NS_XHTML = "http://www.w3.org/1999/xhtml"
    NS_IMAGE = "http://www.google.com/schemas/sitemap-image/1.1"
    # رأس الملف
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        f'xmlns:xhtml="{NS_XHTML}" xmlns:image="{NS_IMAGE}">'
    ]

    def esc(s: str) -> str:
        return html.escape(s or "", quote=True)

    for u in urls:
        parts.append("<url>")
        parts.append(f"<loc>{esc(u['loc'])}</loc>")
        if u.get("lastmod"):
            parts.append(f"<lastmod>{esc(u['lastmod'])}</lastmod>")
        if u.get("changefreq"):
            parts.append(f"<changefreq>{esc(u['changefreq'])}</changefreq>")
        if u.get("priority"):
            parts.append(f"<priority>{esc(u['priority'])}</priority>")

        # alternates (hreflang)
        for alt in u.get("alternates", []):
            parts.append(
                f'<xhtml:link rel="alternate" hreflang="{esc(alt["hreflang"])}" href="{esc(alt["href"])}" />'
            )

        # images
        for img in u.get("images", []):
            parts.append("<image:image>")
            parts.append(f"<image:loc>{esc(img['image_loc'])}</image:loc>")
            if img.get("image_title"):
                parts.append(f"<image:title>{esc(img['image_title'])}</image:title>")
            parts.append("</image:image>")

        parts.append("</url>")

    parts.append("</urlset>")
    xml = "\n".join(parts)
    resp = Response(xml, mimetype="application/xml")
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


def build_announcements_list():
    lang = session.get('lang', 'ar')
    try:
        anns = Announcement.query.order_by(Announcement.created_at.desc()).limit(8).all()
    except Exception:
        anns = []
    out = []
    for a in anns:
        # يختار العنوان حسب اللغة، مع سقوط تلقائي للعربي
        title = a.title_en if (lang == 'en' and getattr(a, 'title_en', None)) else a.title
        out.append({"id": a.id, "title": title})
    return out

def upgrade():
    with op.batch_alter_table('gallery') as batch_op:
        batch_op.add_column(sa.Column('title_en', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('description_en', sa.Text(), nullable=True))

def downgrade():
    with op.batch_alter_table('gallery') as batch_op:
        batch_op.drop_column('description_en')
        batch_op.drop_column('title_en')


@app.context_processor
def inject_i18n_helpers():
    lang = session.get('lang', 'ar')

    def t(key, **kwargs):
        # ترجمة المفتاح مع سقوط تلقائي للعربي إن لم يُوجد
        text = TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS["ar"].get(key, key))
        return text.format(**kwargs) if kwargs else text

    def pick(ar_val, en_val):
        # اختيار قيمة بحسب اللغة مع سقوط للعربي إن لم تتوفر الإنجليزية
        return (en_val if (lang == 'en' and en_val) else ar_val)

    def l(obj, base_field):
        """
        يعيد الحقل بحسب اللغة: base_field / base_field_en
        مثال: l(news, 'title') -> news.title_en أو news.title
        """
        ar_val = getattr(obj, base_field, None)
        en_val = getattr(obj, f"{base_field}_en", None)
        return pick(ar_val, en_val)

    return dict(lang=lang, t=t, pick=pick, l=l)

# مسار لتبديل اللغة (يحفظها في الجلسة ويعيد التوجيه للمكان السابق)
@app.route("/set-lang/<code>")
def set_lang(code):
    code = code.lower()
    if code not in ("ar", "en"):
        code = "ar"
    session['lang'] = code
    next_url = request.args.get("next") or request.referrer or url_for("index")
    return redirect(next_url)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def auto_translate_to_en(text: str | None) -> str | None:
    """استبدل هذه الدالة بتكامل Google/DeepL في الإنتاج."""
    if not text:
        return text
    # TODO: تكامل مترجم سحابي. مؤقتًا نعيد None ليبقى الحقل فارغًا إن لم تُفعّل الترجمة.
    return None

#for reports page filtering
def _slugify(s):
    return re.sub(r'[^a-zA-Z0-9_-]+', '-', s).strip('-')


# تحميل إعدادات config
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
except Exception as e:
    print(f"⚠️ فشل تحميل ملف config.json: {e}")
    config = {}





# إنشاء قاعدة البيانات ومستخدم admin
with app.app_context():
    try:
        db.create_all()

        admin_username = config.get("admin_username", "admin")
        admin_password = config.get("admin_password", "admin123")

        if not User.query.filter_by(username=admin_username).first():
            hashed_password = generate_password_hash(admin_password)
            new_user = User(username=admin_username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
    except Exception as e:
        msg = f'حدث خطأ أثناء المعالجة: {e}'
        if has_request_context():
            flash(msg, 'error')
        else:
            # أثناء CLI (migrate/upgrade) لا يوجد request context: استخدم اللّوغر بدل الفلاش
            app.logger.error(msg)
        # You may want to handle this differently outside a request context
    try:
        db.session.execute("ALTER TABLE news ADD COLUMN title_en TEXT")
    except Exception as _e:
        pass
    try:
        db.session.execute("ALTER TABLE news ADD COLUMN content_en TEXT")
    except Exception as _e:
        pass
    try:
        db.session.commit()
    except Exception as _e:
        db.session.rollback()

# ضبط اللغة في g.lang قبل كل طلب + مسار لتغيير اللغة
@app.before_request
def _set_lang():
    session.setdefault('lang', 'ar')
    g.lang = session.get('lang', 'ar')

@app.route('/set_lang/<lang>')
def set_lang_route(lang):
    if lang not in ('ar', 'en'):
        lang = 'ar'
    session['lang'] = lang
    # العودة للصفحة السابقة أو الرئيسية
    return redirect(request.referrer or url_for('index'))

def _apply_locale_to_top_images(items, lang):
    """يستبدل حقول العربية بالإنجليزية مؤقتًا في الذاكرة فقط."""
    if not items:
        return
    for it in items:
        if lang == 'en':
            if getattr(it, 'title_en', None):
                it.title = it.title_en
            if getattr(it, 'description_en', None):
                it.description = it.description_en
            if getattr(it, 'news_title_en', None):
                it.news_title = it.news_title_en
            if getattr(it, 'news_content_en', None):
                it.news_content = it.news_content_en



def _apply_locale_to_news(records, lang):
    """يعدّل النسخ المؤقتة من الكائنات لعرض الإنجليزية عند توافرها دون حفظ في القاعدة."""
    if lang != 'en':
        return records
    for n in records:
        # في حال توفرت ترجمة إنجليزية، نعرضها مؤقتًا
        if getattr(n, 'title_en', None):
            try:
                object.__setattr__(n, 'title', n.title_en)
            except Exception:
                n.title = n.title_en
        if getattr(n, 'content_en', None):
            try:
                object.__setattr__(n, 'content', n.content_en)
            except Exception:
                n.content = n.content_en
    return records

@app.route('/')
def index():
    session.setdefault('lang', 'ar')
    # جلب الأخبار من قاعدة البيانات
    try:
        top_images = TopImage.query.order_by(TopImage.created_at.desc()).all()
    except Exception:
        top_images = []  # أمان إضافي لو حصلت مشكلة بالجدول

    news_list = News.query.order_by(News.created_at.desc()).limit(10).all()

    # طبّق اللغة مؤقتًا قبل التمرير للقالب
    _apply_locale_to_top_images(top_images, g.lang)
    _apply_locale_to_news(news_list, g.lang)

    # عرض الأخبار في الصفحة الرئيسية
    with db.session.no_autoflush:
        for item in news_list:
            item.gallery = Gallery.query.filter_by(news_id=item.id).all()

    # جلب الصور العلوية
    top_images = TopImage.query.all()
    # جلب الإصدارات من قاعدة البيانات
    versions_basmat = Version.query.filter_by(category='مجلة بصمات').all()
    versions_papers = Version.query.filter_by(category='أوراق ودراسات').all()
    versions_marsad = Version.query.filter_by(category='مرصد الانتهاكات').all()
    # استدعاء UTC كائن timezone-aware
    now = datetime.utcnow()
    #now = datetime.now(timezone.utc)


    return render_template("index.html",
                           news_list=news_list,
                           top_images=top_images,
                           now=now,
                           timedelta=timedelta,
                           versions_basmat=versions_basmat,
                           versions_papers=versions_papers,
                           versions_marsad=versions_marsad, announcements_list=build_announcements_list())


@app.template_filter('nl2br')
def nl2br(s):
    return Markup(s.replace('\n', '<br>\n'))

# صفحة لوحة التحكم
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash("✅ تم تسجيل الدخول بنجاح!", "success")
            return redirect(url_for('admin'))
        else:
            flash("❌ فشل في تسجيل الدخول. تحقق من بياناتك.", "error")
    return render_template('login.html')


from sqlalchemy import func
from sqlalchemy.orm import joinedload
# تأكد من استيراد Category و Gallery و News و User و بقية المستلزمات أعلى الملف

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session:
        flash("❌ يجب تسجيل الدخول للوصول إلى لوحة التحكم.", "error")
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])

    if request.method == 'POST':
        # --- الحقول النصية للأخبار ---
        title = request.form.get('title')
        content = request.form.get('content')
        link = request.form.get('link')

        # --- ملف الصورة + حقول المعرض ---
        image = request.files.get('image')
        gallery_title = request.form.get('gallery_title')
        gallery_description = request.form.get('gallery_description')

        # --- الحقول الإنجليزية (خبر + معرض) ---
        title_en = request.form.get('title_en') or None
        content_en = request.form.get('content_en') or None
        gallery_title_en = request.form.get('gallery_title_en') or None
        gallery_description_en = request.form.get('gallery_description_en') or None

        # --- التصنيف (اختياري) ---
        category_id_raw = request.form.get('category_id') or None
        category_id = int(category_id_raw) if category_id_raw else None

        try:
            # إنشاء الخبر
            new_news = News(
                id=str(uuid.uuid4()),
                title=title,
                content=content,
                link=link,
                is_custom=True
            )
            # EN fallback
            new_news.title_en = title_en or title
            new_news.content_en = content_en or content
            db.session.add(new_news)

            # رفع الصورة وإنشاء سجل المعرض (اختياري)
            if image and allowed_file(image.filename):
                filename = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                image.save(filepath)

                new_image = Gallery(
                    filename=filename,
                    title=gallery_title,
                    description=gallery_description,
                    title_en=gallery_title_en,
                    description_en=gallery_description_en,
                    news_id=new_news.id,
                    uploaded_at=datetime.utcnow(),   # كما هو عندك
                    category_id=category_id          # <-- التصنيف
                )
                db.session.add(new_image)

            db.session.commit()
            flash("✅ تم إضافة الخبر (والصورة إن وجدت) بنجاح!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ خطأ أثناء الحفظ: {str(e)}", "error")

        return redirect(url_for('admin'))

    # --- GET: عرض لوحة التحكم ---
    page = request.args.get('page', 1, type=int)
    per_page = 9

    # تحميل الصور مع التصنيف لتقليل استعلامات إضافية
    pagination = (Gallery.query
                  .options(joinedload(Gallery.category))
                  .order_by(Gallery.uploaded_at.desc())
                  .paginate(page=page, per_page=per_page))

    images = pagination.items
    news = News.query.order_by(News.created_at.desc()).all()

    # تمرير قائمة التصنيفات لنموذج الإضافة
    categories = (Category.query
                  .order_by(func.lower(func.coalesce(Category.name_en, Category.name)))
                  .all())

    return render_template(
        "admin.html",
        user=user,
        images=images,
        pagination=pagination,
        news=news,
        categories=categories   # <-- مهم: لعرض قائمة التصنيفات في الفورم
    )

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("✅ تم تسجيل الخروج.", "success")
    return redirect(url_for('login'))


@app.route('/news')
def news():
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 6
    base_query = News.query.order_by(News.created_at.desc())
    if query:
        # لو اللغة إنجليزي نبحث في الحقول الإنجليزية، وإلا العربية
        if g.lang == 'en':
            base_query = base_query.filter(
                (News.title_en.ilike(f'%{query}%')) | (News.content_en.ilike(f'%{query}%'))
            )
        else:
            base_query = base_query.filter(
                (News.title.ilike(f'%{query}%')) | (News.content.ilike(f'%{query}%'))
            )
    pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)
    news_items = pagination.items
    for item in news_items:
        item.gallery = Gallery.query.filter_by(news_id=item.id).all()
    # طبّق اللغة على السجلات قبل الإرسال للقالب دون تعديل دائم
    _apply_locale_to_news(pagination.items, g.lang)
    return render_template("news.html", news_list=news_items, page=page, pages=pagination.pages, query=query)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/project_form')
def project_form():
    return render_template('project_form.html')

@app.route("/partners")
def partners():
    session.setdefault('lang', 'ar')

    # أمثلة بيانات (حتى لو بدون قاعدة بيانات)
    partners_strategic = [
        {"logo": "unesco.png", "name": "منظمة اليونسكو", "name_en": "UNESCO"},
        {"logo": "iseesco.png", "name": "الإيسيسكو", "name_en": "ICESCO"},
    ]
    partners_local = [
        {"logo": "paltel.png", "name": "شركة بالتل", "name_en": "Paltel"},
        {"logo": "jawwal.png", "name": "شركة جوال", "name_en": "Jawwal"},
    ]
    partners_international = [
        {"logo": "arableague.png", "name": "جامعة الدول العربية", "name_en": "League of Arab States"},
    ]

    return render_template(
        "partners.html",
        partners_strategic=partners_strategic,
        partners_local=partners_local,
        partners_international=partners_international
    )


@app.route('/reports')
def reports_explorer():
    # 1) scan static/pdfs/reports for pdf files
    root = os.path.join(app.static_folder, 'pdfs', 'reports')
    files = sorted(glob.glob(os.path.join(root, '*.pdf')))

    reports = []
    for f in files:
        rel = os.path.relpath(f, app.static_folder).replace('\\', '/')
        name = os.path.splitext(os.path.basename(f))[0]
        # derive year/category heuristically from filename e.g. "2025_Q2-Strategy.pdf"
        year = None
        m = re.search(r'(20\d{2})', name)
        if m:
            year = m.group(1)

        # simple category by prefix if it exists (e.g., "Finance_", "Culture_")
        parts = re.split(r'[-_]', name, maxsplit=1)
        category = parts[0] if len(parts) > 1 and not parts[0].isdigit() else None

        reports.append({
            "id": _slugify(name),
            "title": name.replace('_', ' '),
            "file_path": rel,   # static-relative path
            "year": year,
            "category": category
        })

    # Build filters
    years = sorted({r["year"] for r in reports if r["year"]}, reverse=True)
    categories = sorted({r["category"] for r in reports if r["category"]})

    return render_template('report_explorer.html',
                           reports=reports,
                           years=years,
                           categories=categories)


@app.route('/announcement/<int:id>')
def announcement_detail(id):
    ann = Announcement.query.get_or_404(id)
    if g.lang == 'en':
        if ann.title_en:   ann.title   = ann.title_en
        if ann.content_en: ann.content = ann.content_en
    images = AnnouncementImage.query.filter_by(announcement_id=ann.id).all()
    atts   = AnnouncementAttachment.query.filter_by(announcement_id=ann.id).all()
    return render_template("announcement_detail.html",
                           announcement=ann,
                           images=images, attachments=atts)

@app.route('/announcements_page')
def announcements_page():
    date_from_str = request.args.get('date_from', '').strip()
    date_to_str   = request.args.get('date_to', '').strip()

    # 2) الاستعلام الأساسي
    query = Announcement.query.order_by(Announcement.created_at.desc())

    # 3) فلترة بتاريخ البداية (00:00:00)
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            query = query.filter(Announcement.created_at >= date_from)
        except ValueError:
            pass  # تجاهل التواريخ غير الصالحة

    # 4) فلترة بتاريخ النهاية (23:59:59)
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
            date_to_end = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)
            query = query.filter(Announcement.created_at <= date_to_end)
        except ValueError:
            pass

    # 5) النتائج
    announcements = query.all()

    #  إضافة صغيرة فقط: طبّق اللغة على نفس الكائنات (لا نحولها لقواميس)
    if g.get('lang') == 'en':
        for a in announcements:
            if getattr(a, 'title_en', None):
                a.title = a.title_en
            if getattr(a, 'content_en', None):
                a.content = a.content_en

    # تمرير قيم التواريخ للقالب (اختياري لعرضها في الحقول)
    return render_template(
        'announcements.html',
        announcements=announcements,
        date_from=date_from_str,
        date_to=date_to_str
    )



# قائمة الإعلانات في لوحة التحكم
@app.route('/admin/announcements')
def admin_announcements():
    anns = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('admin_announcements.html', announcements=anns)


# إضافة إعلان جديد
@app.route('/admin/announcements/add', methods=['GET', 'POST'])
def add_announcement():
    if request.method == 'POST':
        # 1) أنشئ الإعلان أولاً
        title   = request.form['title']
        content = request.form['content']
        title_en = request.form.get('title_en') or None
        content_en = request.form.get('content_en') or None
        ann     = Announcement(title=title, content=content, title_en= title_en, content_en=content_en)
        ann.title_en = title_en or ann.title
        ann.content_en = content_en or ann.content
        db.session.add(ann)
        db.session.flush()  # لضمان وجود ann.id قبل حفظ الملفات

        # 2) رفع المرفقات (PDF)
        files = request.files.getlist('attachments')
        for f in files:
            if f and f.filename.lower().endswith('.pdf'):
                orig = secure_filename(f.filename)
                fn = f"{int(time.time())}_{orig}"
                save_path = os.path.join(app.static_folder, 'pdfs/announcements', fn)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                f.save(save_path)
                pdf_rel = f"pdfs/announcements/{fn}"
                att = AnnouncementAttachment(
                    filename=pdf_rel,
                    mimetype='application/pdf',
                    announcement=ann
                )
                db.session.add(att)

        # 2.1) رفع الصور
        images = request.files.getlist('images')
        for img in images:
            if img and allowed_file(img.filename):
                filename = f"{uuid.uuid4().hex}_{secure_filename(img.filename)}"
                save_dir = os.path.join(app.static_folder, 'images/announcements')
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, filename)
                img.save(save_path)
                rel_path = f"images/announcements/{filename}"  # استخدم "/" دوماً
                image_record = AnnouncementImage(
                    filename=rel_path,
                    announcement=ann
                )
                db.session.add(image_record)

        # 3) أخيرًا: ثبّت كل التغييرات
        db.session.commit()
        flash('✅ تم إضافة الإعلان!', 'success')
        return redirect(url_for('admin_announcements'))

    return render_template('admin_announcement_form.html', announcement=None)



# تعديل إعلان موجود
@app.route('/admin/announcements/edit/<int:id>', methods=['GET','POST'])
def edit_announcement(id):
    ann = Announcement.query.get_or_404(id)


    if request.method == 'POST':
        # 1) حذف الصور المُعلّمة
        delete_imgs = request.form.getlist('delete_images')
        for img_id in delete_imgs:
            img = AnnouncementImage.query.get(int(img_id))
            if img:
                # احذف الملف من القرص
                path = os.path.join(app.static_folder, img.filename)
                if os.path.exists(path):
                    os.remove(path)
                db.session.delete(img)

        # 2) حذف المرفقات المُعلّمة
        delete_atts = request.form.getlist('delete_attachments')
        for att_id in delete_atts:
            att = AnnouncementAttachment.query.get(int(att_id))
            if att:
                path = os.path.join(app.static_folder, att.filename)
                if os.path.exists(path):
                    os.remove(path)
                db.session.delete(att)

        # 3) تعديل العنوان والمحتوى

        title_en = request.form.get('title_en') or None
        content_en = request.form.get('content_en') or None

        ann.title = request.form.get('title', ann.title)
        ann.content = request.form.get('content', ann.content)

        if title_en is not None:   ann.title_en = title_en
        if content_en is not None: ann.content_en = content_en

        # 4) رفع صور جديدة (كما في السابق)
        new_images = request.files.getlist('images')
        for img in new_images:
            if img and allowed_file(img.filename):
                orig = secure_filename(img.filename)
                fn = f"{int(time.time())}_{orig}"
                save_dir = os.path.join(app.static_folder, 'images/announcements')
                os.makedirs(save_dir, exist_ok=True)
                img.save(os.path.join(save_dir, fn))
                image_record = AnnouncementImage(
                    filename=f"images/announcements/{fn}",
                    announcement=ann
                )
                db.session.add(image_record)

        # 5) رفع مرفقات PDF جديدة
        new_atts = request.files.getlist('attachments')
        for f in new_atts:
            if f and f.filename.lower().endswith('.pdf'):
                orig = secure_filename(f.filename)
                fn = f"{int(time.time())}_{orig}"
                save_dir = os.path.join(app.static_folder, 'pdfs/announcements')
                os.makedirs(save_dir, exist_ok=True)
                f.save(os.path.join(save_dir, fn))
                att_record = AnnouncementAttachment(
                    filename=f"pdfs/announcements/{fn}",
                    mimetype='application/pdf',
                    announcement=ann
                )
                db.session.add(att_record)

        # 6) وأخيرًا: الحفظ
        db.session.commit()
        flash('✅ تم تعديل الإعلان بنجاح!', 'success')
        return redirect(url_for('admin_announcements'))

    return render_template('admin_announcement_form.html', announcement=ann)

# حذف إعلان
@app.route('/admin/announcements/delete/<int:id>', methods=['POST'])
def delete_announcement(id):
    ann = Announcement.query.get_or_404(id)
    db.session.delete(ann)
    db.session.commit()
    flash('✅ تم حذف الإعلان!', 'success')
    return redirect(url_for('admin_announcements'))


@app.route('/news/<news_id>')
def news_detail(news_id):
    #news = News.query.get(news_id)
    news = db.session.get(News, news_id)  # ← صلحنا هنا
    if not news:
        flash("❌ الخبر غير موجود.", "error")
        return redirect(url_for("news"))
    # عرض النسخة الإنجليزية مؤقتًا إن وُجدت
    _apply_locale_to_news([news], g.lang)
    related_images = Gallery.query.filter_by(news_id=news.id).all()
    return render_template("news_detail.html", news=news, images=related_images)


@app.route('/add_news', methods=['GET', 'POST'])
def add_news():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        link = request.form.get('link')
        gallery_title = request.form.get('gallery_title')
        gallery_description = request.form.get('gallery_description')

        title_en = request.form.get('title_en') or None
        content_en = request.form.get('content_en') or None

        new_news = News(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            link=link,
            is_custom=True
        )

        # استخدم المدخل الإنجليزي إن وُجد، وإلا انسخ العربي
        new_news.title_en = title_en or title
        new_news.content_en = content_en or content

        db.session.add(new_news)

        try:
            db.session.flush()  # لضمان new_news.id

            images = request.files.getlist('images')
            for img in images:
                if img and allowed_file(img.filename):
                    filename = f"{uuid.uuid4().hex}_{secure_filename(img.filename)}"
                    save_dir = app.config['UPLOAD_FOLDER']
                    os.makedirs(save_dir, exist_ok=True)
                    img.save(os.path.join(save_dir, filename))

                    db.session.add(Gallery(
                        filename=filename,
                        title=gallery_title,
                        description=gallery_description,
                        news_id=new_news.id,
                        uploaded_at=datetime.utcnow()
                    ))

            db.session.commit()
            flash("✅ تم إضافة الخبر مع صوره بنجاح!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ خطأ أثناء الحفظ: {e}", "error")

        return redirect(url_for('admin'))

    # GET: إعداد البيانات لعرض النموذج
    page = request.args.get('page', 1, type=int)
    per_page = 5  # <-- غيّر هذا الرقم لعدد الأخبار الذي تريده
    news_pagination = News.query.order_by(News.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)
    news_items = news_pagination.items

    # صورة المعرض نتركها كما هي
    gallery_pagination = Gallery.query \
        .order_by(Gallery.uploaded_at.desc()) \
        .paginate(page=page, per_page=9, error_out=False)
    images = gallery_pagination.items

    return render_template(
        "add_news.html",
        news_items=news_items,
        news_pagination=news_pagination,
        images=images,
        gallery_pagination=gallery_pagination
    )



@app.route('/update_news')
def update_news():
    try:
        subprocess.run(["python", "scrape_partial_update.py"], check=True)
        flash("✅ تم تحديث الأخبار بنجاح!", "success")
    except subprocess.CalledProcessError as e:
        flash(f"❌ خطأ أثناء التحديث: {e}", "error")
    except Exception as e:
        flash(f'حدث خطأ أثناء المعالجة: {e}', 'error')
    return redirect(url_for("news"))


@app.route("/gallery")
def gallery():
    lang = session.get('lang', 'ar')
    q = (request.args.get('q') or "").strip()
    sort = request.args.get('sort', 'newest')
    cat_slug = request.args.get('category', None)
    page = request.args.get('page', 1, type=int)
    per_page = 18

    # Base query + eager load to avoid N+1
    query = Gallery.query.options(joinedload(Gallery.category))

    # --- Filter: search ---
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Gallery.title.ilike(like),
            Gallery.description.ilike(like),
            Gallery.title_en.ilike(like),
            Gallery.description_en.ilike(like),
        ))

    # --- Filter: category (by slug) ---
    if cat_slug:
        # join فقط مرة عند الحاجة
        query = query.join(Category, isouter=True).filter(Category.slug == cat_slug)

    # --- Sort ---
    # نستخدم coalesce حسب لغة الجلسة: لو العنوان المطلوب فاضي، نfallback للثاني
    if sort in ("az", "za"):
        order_col = func.lower(func.coalesce(
            Gallery.title_en if lang == "en" else Gallery.title,
            Gallery.title if lang == "en" else Gallery.title_en,
            ""
        ))
    else:
        order_col = None

    if sort == "newest":
        query = query.order_by(Gallery.uploaded_at.desc(), Gallery.id.desc())
    elif sort == "oldest":
        query = query.order_by(Gallery.uploaded_at.asc(), Gallery.id.asc())
    elif sort == "az":
        query = query.order_by(order_col.asc(), Gallery.id.asc())
    elif sort == "za":
        query = query.order_by(order_col.desc(), Gallery.id.desc())
    else:
        query = query.order_by(Gallery.uploaded_at.desc(), Gallery.id.desc())

    # --- Pagination ---
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    images = pagination.items

    # Categories list for chips
    categories = Category.query.order_by(func.lower(func.coalesce(Category.name_en, Category.name))).all()

    return render_template(
        "gallery.html",
        images=images,
        pagination=pagination,
        categories=categories
    )

@app.route('/add_version', methods=['GET', 'POST'])
def add_version():
    if 'user_id' not in session:
        flash("❌ يجب تسجيل الدخول للوصول إلى لوحة التحكم.", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['version_title']
        category = request.form['category']

        # رفع ملف PDF
        file = request.files.get('file')
        if not file or not allowed_file(file.filename):
            flash("❌ يجب رفع ملف PDF صالح.", "error")
            return redirect(url_for('add_version'))

        filename = secure_filename(file.filename)
        #pdf_relative_path = os.path.join('pdfs', filename)
        pdf_relative_path = os.path.join('pdfs', filename).replace("\\", "/")
        pdf_full_path = os.path.join(app.static_folder, pdf_relative_path)
        os.makedirs(os.path.dirname(pdf_full_path), exist_ok=True)
        file.save(pdf_full_path)

        # رفع الصورة المصغّرة
        thumbnail = request.files.get('thumbnail')
        thumbnail_path2 = None
        if thumbnail and allowed_file(thumbnail.filename):
            thumbnail_filename = secure_filename(file.filename)
            #thumbnail_relative_path = os.path.join('pdfs', thumbnail_filename)
            thumbnail_relative_path = os.path.join('pdfs', thumbnail_filename).replace("\\", "/")
            thumbnail_full_path = os.path.join(app.static_folder, thumbnail_relative_path)
            os.makedirs(os.path.dirname(thumbnail_full_path), exist_ok=True)
            try:
                thumbnail.save(thumbnail_full_path)
                thumbnail_path2 = thumbnail_relative_path
            except PermissionError:
                flash("⚠️ لا يمكن حفظ الصورة المصغّرة، تحقق من الصلاحيات أو من أن الملف مفتوح في برنامج آخر.", "error")
                return redirect(url_for('add_version'))

        # إضافة إلى قاعدة البيانات
        new_version = Version(
            title=title,
            file_path=pdf_relative_path,
            thumbnail_path=thumbnail_path2,
            category=category
        )
        db.session.add(new_version)
        db.session.commit()

        flash("✅ تم إضافة الإصدار بنجاح!", "success")
        return redirect(url_for('admin'))

    return render_template('add_version.html')


@app.route('/admin/versions')
def admin_versions():
    versions = db.session.execute(db.select(Version).order_by(Version.created_at.desc())).scalars().all()
    return render_template('admin_versions.html', versions=versions)


@app.route('/admin/versions/delete/<int:id>')
def delete_version(id):
    version = db.get_or_404(Version, id)
    # حذف الملف من النظام
    file_path = os.path.join(app.static_folder, version.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    # حذف الصورة المصغرة
    if version.thumbnail_path:
        thumb_path = os.path.join(app.static_folder, version.thumbnail_path)
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
    db.session.delete(version)
    db.session.commit()
    flash('تم حذف الإصدار بنجاح')
    return redirect(url_for('admin_versions'))

@app.route('/send_feedback', methods=['POST'])
def send_feedback():
    feedback_type = request.form.get('type')
    email = request.form.get('email', 'لم يتم إدخال بريد')
    message = request.form.get('message')

    full_message = f"""
    نوع الرسالة: {feedback_type}
    البريد الإلكتروني: {email}

    المحتوى:
    {message}
    """

    try:
        msg = Message(subject=f"📝 {feedback_type} - رأي من الموقع",
                      recipients=['pncecs.info@gmail.com'],
                      body=full_message)
        mail.send(msg)
        flash("✅ تم إرسال رسالتك بنجاح، شكرًا لمساهمتك!", "success")
    except Exception as e:
        flash("❌ حدث خطأ أثناء إرسال الرسالة. حاول لاحقًا.", "danger")
        print("SMTP Error:", e)
        traceback.print_exc()

    return redirect(request.referrer or url_for('index'))



@app.context_processor
def inject_marquee_news():
    # اللغة الحالية (افتراضي عربي)
    lang = session.get('lang', 'ar')

    # آخر 5 أخبار مضافة يدويًا لتظهر في الماركيه
    marquee_news = News.query.filter_by(is_custom=True)\
                             .order_by(News.created_at.desc())\
                             .limit(6).all()

    items = []
    for n in marquee_news:
        # لو عندك حقل title_en سيُستخدم عند اختيار الإنجليزية، وإلا يسقط للعربية
        title = getattr(n, 'title_en', None) if lang == 'en' else n.title
        items.append({
            "title": title or n.title,
            "url": f"/news/{n.id}"
        })

    return dict(news_marquee=items)


@app.context_processor
def inject_announcements():
    ann = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return dict(announcements_list=ann)


@app.route('/delete_image/<int:image_id>', methods=['POST'])
def delete_image(image_id):
    if "user_id" not in session:
        flash("❌ لا تملك صلاحية لحذف الصور.", "error")
        return redirect(url_for("login"))
    image = Gallery.query.get_or_404(image_id)
    try:
        db.session.delete(image)
        db.session.commit()
        flash("✅ تم حذف الصورة بنجاح", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ حدث خطأ أثناء الحذف: {e}", "error")
    return redirect(url_for("gallery"))


@app.route('/edit_image/<int:image_id>', methods=['GET', 'POST'])
def edit_image(image_id):
    if "user_id" not in session:
        flash("❌ لا تملك صلاحية لتعديل الصور.", "error")
        return redirect(url_for("login"))
    image = Gallery.query.get_or_404(image_id)

    if request.method == "GET":
        categories = Category.query.order_by(func.lower(func.coalesce(Category.name_en, Category.name))).all()
        return render_template("edit_image.html", image=image, categories=categories)

    if request.method == "POST":
        image.title = request.form.get("title")
        image.description = request.form.get("description")
        image.title_en = request.form.get("title_en")
        image.description_en = request.form.get("description_en")
        category_id = request.form.get("category_id") or None
        image.category_id = int(category_id) if category_id else None
        new_image = request.files.get("new_image")

        if new_image and new_image.filename:
            filename = f"{uuid.uuid4().hex}_{secure_filename(new_image.filename)}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
            new_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                new_image.save(new_path)
                image.filename = filename
            except Exception as e:
                flash(f"❌ خطأ أثناء رفع الصورة الجديدة: {e}", "error")
        try:
            db.session.commit()
            flash("✅ تم تعديل الصورة بنجاح", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ حدث خطأ أثناء التعديل: {e}", "error")
        return redirect(url_for("gallery"))
    return render_template("edit_image.html", image=image)


@app.route('/edit_news/<news_id>', methods=['GET', 'POST'])
def edit_news(news_id):
    if 'user_id' not in session:
        flash("❌ لا تملك صلاحية للتعديل.", "error")
        return redirect(url_for('login'))
    news = News.query.get_or_404(news_id)
    if request.method == 'POST':
        #news.title = request.form.get('title')
        news.title = request.form.get('title', news.title)
        #news.content = request.form.get('content')
        news.content = request.form.get('content', news.content)
        news.link = request.form.get('link')

        title_en = request.form.get('title_en') or None
        content_en = request.form.get('content_en') or None

        # تحديث الإنجليزي إن أُدخل
        if title_en is not None:
            news.title_en = title_en
        if content_en is not None:
            news.content_en = content_en

        try:
            db.session.commit()
            flash("✅ تم تعديل الخبر بنجاح", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ حدث خطأ أثناء التعديل: {e}", "error")
        return redirect(url_for('admin'))
    return render_template('edit_news.html', news=news)


@app.route('/delete_news/<news_id>', methods=['POST'])
def delete_news(news_id):
    if 'user_id' not in session:
        flash("❌ لا تملك صلاحية للحذف.", "error")
        return redirect(url_for('login'))
    news = News.query.get_or_404(news_id)
    try:
        # حذف الصور المرتبطة بهذا الخبر
        related_images = Gallery.query.filter_by(news_id=news.id).all()
        for image in related_images:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
            if os.path.exists(image_path):
                os.remove(image_path)
            db.session.delete(image)
        db.session.delete(news)
        db.session.commit()
        flash("✅ تم حذف الخبر والصور المرتبطة به بنجاح", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ حدث خطأ أثناء الحذف: {e}", "error")
    return redirect(url_for('admin'))


# إدارة الصور العلوية
@app.route('/add_top_image', methods=['POST'])
def add_top_image():
    if 'user_id' not in session:
        flash("الرجاء تسجيل الدخول أولاً", "error")
        return redirect(url_for('login'))
    file = request.files.get('image')
    title = request.form.get('title', '').strip()[:200]
    description = request.form.get('description', '').strip()
    news_title = request.form.get('news_title', '').strip()
    news_content = request.form.get('news_content', '').strip()
    news_id = request.form.get('news_id') or None
    title_en = request.form.get('title_en')
    description_en = request.form.get('description_en')
    caption_en = request.form.get('caption_en')
    if file and file.filename:
        filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        save_path = os.path.join('static', 'images', 'top_images', filename)
        file.save(save_path)
        new_image = TopImage(
            image=filename,
            title=title,
            description=description,
            news_title=news_title,
            news_content=news_content,
            news_id=news_id,
            title_en=title_en,
            description_en=description_en,
            caption_en = caption_en
        )
        db.session.add(new_image)
        db.session.commit()
        flash("✅ تم إضافة الصورة بنجاح", "success")
    else:
        flash("❌ يرجى اختيار صورة", "error")
    return redirect(url_for('admin_top_images'))


@app.route('/delete_top_image/<int:image_id>', methods=['POST'])
def delete_top_image(image_id):
    if 'user_id' not in session:
        flash("الرجاء تسجيل الدخول أولاً", "error")
        return redirect(url_for('login'))

    image = TopImage.query.get_or_404(image_id)
    image_path = os.path.join(app.config['TOP_IMAGES_FOLDER'], image.image)

    try:
        db.session.delete(image)
        db.session.commit()

        # حذف الملف من المجلد إن وجد
        if os.path.exists(image_path):
            os.remove(image_path)

        flash("✅ تم حذف الصورة", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ حدث خطأ أثناء الحذف: {e}", "error")

    return redirect(url_for('admin_top_images'))



@app.route('/edit_top_image/<int:image_id>', methods=['GET', 'POST'])
def edit_top_image(image_id):
    if 'user_id' not in session:
        flash("الرجاء تسجيل الدخول أولاً", "error")
        return redirect(url_for('login'))

    image = TopImage.query.get_or_404(image_id)

    if request.method == 'POST':
        image.title = request.form.get('title', '').strip()
        image.description = request.form.get('description', '').strip()
        image.news_title = request.form.get('news_title', '').strip()
        image.news_content = request.form.get('news_content', '').strip()
        image.description_en = request.form.get('description_en', '').strip()
        image.title_en = request.form.get('title_en', '').strip()
        image.caption_en = request.form.get('caption_en', '').strip()
        image.news_id = request.form.get('news_id') or None

        new_image = request.files.get('new_image')
        if new_image and allowed_file(new_image.filename):
            try:
                filename = f"{uuid.uuid4().hex}_{secure_filename(new_image.filename)}"
                new_path = os.path.join(app.config['TOP_IMAGES_FOLDER'], filename)
                old_path = os.path.join(app.config['TOP_IMAGES_FOLDER'], image.image)

                os.makedirs(app.config['TOP_IMAGES_FOLDER'], exist_ok=True)
                new_image.save(new_path)

                if os.path.exists(old_path):
                    os.remove(old_path)

                image.image = filename
            except Exception as e:
                flash(f"❌ خطأ أثناء رفع الصورة الجديدة: {e}", "error")
                return redirect(url_for('edit_top_image', image_id=image.id))

        try:
            db.session.commit()
            flash("✅ تم تحديث معلومات الصورة بنجاح", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ حدث خطأ أثناء الحفظ: {e}", "error")

        return redirect(url_for('admin_top_images'))

    news_list = News.query.order_by(News.created_at.desc()).all()
    return render_template('edit_top_image.html', image=image, news_list=news_list)




@app.route('/admin_top_images', methods=['GET', 'POST'])
def admin_top_images():
    if 'user_id' not in session:
        flash("الرجاء تسجيل الدخول أولاً", "error")
        return redirect(url_for('login'))

    # ✅ عند إرسال POST: إضافة صورة جديدة
    if request.method == 'POST':
        file = request.files.get('image')
        title = request.form.get('title', '').strip()[:200]
        description = request.form.get('description', '').strip()
        news_title = request.form.get('news_title', '').strip()
        news_content = request.form.get('news_content', '').strip()
        news_id = request.form.get('news_id') or None
        title_en = request.form.get('title_en')
        caption_en = request.form.get('caption_en')

        if not file or not allowed_file(file.filename):
            flash("❌ يرجى اختيار صورة صالحة.", "error")
            return redirect(url_for('admin_top_images'))

        try:
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            os.makedirs(app.config['TOP_IMAGES_FOLDER'], exist_ok=True)
            file.save(os.path.join(app.config['TOP_IMAGES_FOLDER'], filename))

            new_image = TopImage(
                image=filename,
                title=title,
                description=description,
                news_title=news_title,
                news_content=news_content,
                news_id=news_id,
                title_en = title_en,
                caption_en = caption_en,
            )

            db.session.add(new_image)
            db.session.commit()
            flash("✅ تم إضافة الصورة العلوية بنجاح!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ خطأ أثناء إضافة الصورة: {e}", "error")

    # ✅ فلترة حسب البحث والترتيب
    query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort_by', 'created_at_desc')

    base_query = TopImage.query
    if query:
        base_query = base_query.filter(
            TopImage.title.ilike(f"%{query}%") |
            TopImage.description.ilike(f"%{query}%") |
            TopImage.news_title.ilike(f"%{query}%")
        )

    if sort_by == 'created_at_asc':
        base_query = base_query.order_by(TopImage.created_at.asc())
    elif sort_by == 'title_asc':
        base_query = base_query.order_by(TopImage.title.asc())
    elif sort_by == 'title_desc':
        base_query = base_query.order_by(TopImage.title.desc())
    else:
        base_query = base_query.order_by(TopImage.created_at.desc())

    top_images = base_query.all()
    news = News.query.order_by(News.created_at.desc()).all()

    return render_template('admin_top_images.html', top_images=top_images, news=news)

#english
@app.route('/en/')
def index_en():
    news_list = News.query.order_by(News.created_at.desc()).all()
    _apply_locale_to_news(news_list, 'en')
    top_images = TopImage.query.all()
    versions_basmat  = Version.query.filter_by(category='مجلة بصمات').all()
    versions_papers  = Version.query.filter_by(category='أوراق ودراسات').all()
    versions_marsad  = Version.query.filter_by(category='مرصد الانتهاكات').all()
    now = datetime.utcnow()
    #now = datetime.now(timezone.utc)
    return render_template("en/index.html",
                           news_list=news_list,
                           top_images=top_images,
                           now=now,
                           timedelta=timedelta,
                           versions_basmat=versions_basmat,
                           versions_papers=versions_papers,
                           versions_marsad=versions_marsad)


@app.route('/en/about')
def about_en():
    return render_template('en/about.html')


@app.route('/en/project_form')
def project_form_en():
    return render_template('en/project_form.html')

@app.route('/en/news')
def news_en():
    page = request.args.get('page', 1, type=int)
    per_page = 6
    query = request.args.get('q', '').strip()
    base_query = News.query.order_by(News.created_at.desc())
    if query:
        base_query = base_query.filter(
            (News.title_en.ilike(f'%{query}%')) | (News.content_en.ilike(f'%{query}%'))
        )
    pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)
    news_items = pagination.items
    for item in news_items:
        item.gallery = Gallery.query.filter_by(news_id=item.id).all()
    _apply_locale_to_news(news_items, 'en')
    return render_template("en/news.html", news_list=news_items, page=page, pages=pagination.pages, query=query)

@app.route('/en/news/<news_id>')
def news_detail_en(news_id):
    news = db.session.get(News, news_id)
    if not news:
        flash("❌ News not found.", "error")
        return redirect(url_for("news_en"))
    images = Gallery.query.filter_by(news_id=news.id).all()
    return render_template("en/news_detail.html", news=news, images=images)

@app.route('/en/partners')
def partners_en():
    return render_template('en/partners.html')

@app.route('/en/reports')
def reports_explorer_en():
    # 1) scan static/pdfs/reports for pdf files
    root = os.path.join(app.static_folder, 'pdfs', 'reports')
    files = sorted(glob.glob(os.path.join(root, '*.pdf')))

    reports = []
    for f in files:
        rel = os.path.relpath(f, app.static_folder).replace('\\', '/')
        name = os.path.splitext(os.path.basename(f))[0]
        # derive year/category heuristically from filename e.g. "2025_Q2-Strategy.pdf"
        year = None
        m = re.search(r'(20\d{2})', name)
        if m:
            year = m.group(1)

        # simple category by prefix if it exists (e.g., "Finance_", "Culture_")
        parts = re.split(r'[-_]', name, maxsplit=1)
        category = parts[0] if len(parts) > 1 and not parts[0].isdigit() else None

        reports.append({
            "id": _slugify(name),
            "title": name.replace('_', ' '),
            "file_path": rel,   # static-relative path
            "year": year,
            "category": category
        })

    # Build filters
    years = sorted({r["year"] for r in reports if r["year"]}, reverse=True)
    categories = sorted({r["category"] for r in reports if r["category"]})

    return render_template('en/report_explorer.html',
                           reports=reports,
                           years=years,
                           categories=categories)

@app.route('/en/announcement/<int:id>')
def announcement_detail_en(id):
    ann = Announcement.query.get_or_404(id)
    return render_template('en/announcement_detail.html', announcement=ann)

@app.route('/en/announcements_page')
def announcements_page_en():
    # مدخلات البحث/التاريخ/التصفح
    q             = request.args.get('q', '').strip()
    date_from_str = request.args.get('date_from', '').strip()
    date_to_str   = request.args.get('date_to', '').strip()
    page          = request.args.get('page', 1, type=int)
    per           = 10

    # الاستعلام الأساسي (أحدث إعلان أولاً)
    base = Announcement.query.order_by(Announcement.created_at.desc())

    # فلترة بتاريخ البداية (يوم كامل يبدأ 00:00:00)
    if date_from_str:
        try:
            d = datetime.strptime(date_from_str, '%Y-%m-%d')
            date_from = datetime(d.year, d.month, d.day, 0, 0, 0)
            base = base.filter(Announcement.created_at >= date_from)
        except ValueError:
            pass  # تجاهل تاريخ غير صالح

    # فلترة بتاريخ النهاية (يوم كامل ينتهي 23:59:59)
    if date_to_str:
        try:
            d = datetime.strptime(date_to_str, '%Y-%m-%d')
            date_to_end = datetime(d.year, d.month, d.day, 23, 59, 59)
            base = base.filter(Announcement.created_at <= date_to_end)
        except ValueError:
            pass

    # البحث في الحقول الإنجليزية فقط لمسار /en
    if q:
        base = base.filter(
            (Announcement.title_en.ilike(f'%{q}%')) |
            (Announcement.content_en.ilike(f'%{q}%'))
        )

    # التصفح
    pagination = base.paginate(page=page, per_page=per, error_out=False)
    items = pagination.items

    # طبّق اللغة: اعرض النسخة الإنجليزية إن وُجدت
    for a in items:
        if a.title_en:
            a.title = a.title_en
        if a.content_en:
            a.content = a.content_en

    # مرّر نفس البارامترات للقالب (للمحافظة على الحقول)
    return render_template(
        'en/announcements.html',
        announcements=items,
        page=page,
        pages=pagination.pages,
        query=q,
        date_from=date_from_str,
        date_to=date_to_str
    )

@app.route('/en/gallery')
def gallery_en():
    query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort_by', '')
    page = request.args.get('page', 1, type=int)
    per_page = 50
    base_query = Gallery.query
    if query:
        base_query = base_query.filter(
            Gallery.title.ilike(f'%{query}%') | Gallery.description.ilike(f'%{query}%')
        )
    if sort_by == 'uploaded_at_asc':
        base_query = base_query.order_by(Gallery.uploaded_at.asc())
    elif sort_by == 'title_asc':
        base_query = base_query.order_by(Gallery.title.asc())
    elif sort_by == 'title_desc':
        base_query = base_query.order_by(Gallery.title.desc())
    else:
        base_query = base_query.order_by(Gallery.uploaded_at.desc())
    pagination = base_query.paginate(page=page, per_page=per_page)
    images = pagination.items
    return render_template("en/gallery.html", images=images, pagination=pagination)


@app.route("/cultural_forum")
def cultural_forum():
    import json
    lang = session.get("lang", "ar")
    with open("cultural_forum_data.json", "r", encoding="utf-8") as f:
        posts = json.load(f)
    posts = sorted(posts, key=lambda x: x.get("date", ""), reverse=True)
    return render_template("cultural_forum.html", posts=posts, lang=lang)







@app.route("/download_cultural_forum_images")
def download_cultural_forum_images():
    folder = os.path.join(app.static_folder, "images", "cultural_forum")
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, _, files in os.walk(folder):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path, os.path.relpath(file_path, folder))

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name="cultural_forum_images.zip",
        mimetype="application/zip"
    )




OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    client = None  # Will return 500 on /api/chat if missing
else:
    # تقدر تضيف timeout افتراضي (اختياري): OpenAI(api_key=..., timeout=30)
    client = OpenAI(api_key=OPENAI_API_KEY)

@app.post("/api/chat")
def api_chat():
    if client is None:
        return jsonify({"error": "Server is not configured with OPENAI_API_KEY"}), 500

    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()
    history  = data.get("history") or []  # [{user:"..", assistant:".."}, ...]

    if not user_msg:
        return jsonify({"error": "empty message"}), 400

    # حوّل الهيستوري إلى رسائل للنموذج
    msgs = [{"role": "system", "content": "أنت مساعد ودود وعملي."}]
    for turn in history[-10:]:
        if turn.get("user"):
            msgs.append({"role": "user", "content": turn["user"]})
        if turn.get("assistant"):
            msgs.append({"role": "assistant", "content": turn["assistant"]})
    msgs.append({"role": "user", "content": user_msg})

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=msgs,
            temperature=0.4,
            max_tokens=500,
        )
        answer = completion.choices[0].message.content.strip()
        return jsonify({"answer": answer})

    # --------- معالجة دقيقة للأخطاء ---------
    except RateLimitError as e:
        # 429 قد تكون "insufficient_quota" (نفاد الرصيد) أو rate limit (طلبات كثيرة)
        code = None
        retry_after = None
        try:
            # مكتبة 1.x تُرجِع response مع JSON على شكل {"error": {... "code": "insufficient_quota"}}
            details = e.response.json()
            code = (details.get("error") or {}).get("code")
        except Exception:
            pass
        try:
            retry_after = e.response.headers.get("retry-after")
        except Exception:
            pass

        if code == "insufficient_quota":
            # رصيد/حصة غير كافية: لا تفيد إعادة المحاولة
            return jsonify({
                "error": "insufficient_quota",
                "user_message": "نفد الرصيد أو تجاوزت الحصة. رجاءً تحقق من الفوترة والحد الشهري في لوحة OpenAI."
            }), 429
        else:
            # Rate limit عابر: أعطِ تلميحًا للانتظار
            return jsonify({
                "error": "rate_limited",
                "user_message": f"طلبات كثيرة بسرعة. جرّب بعد قليل."
                                  + (f" انتظر {retry_after} ثانية." if retry_after else "")
            }), 429

    except AuthenticationError:
        return jsonify({
            "error": "bad_api_key",
            "user_message": "مفتاح API غير صالح أو صلاحيات غير كافية."
        }), 401

    except BadRequestError as e:
        # أخطاء المعطيات (model/parameters)
        return jsonify({
            "error": "bad_request",
            "user_message": "طلب غير صالح. راجع المعطيات المُرسَلة إلى واجهة OpenAI.",
            "details": str(e)
        }), 400

    except APITimeoutError:
        return jsonify({
            "error": "timeout",
            "user_message": "انتهت مهلة الاتصال بخدمة OpenAI. حاول مجددًا."
        }), 504

    except APIError as e:
        # أخطاء خادم OpenAI العامة (5xx)
        return jsonify({
            "error": "openai_server_error",
            "user_message": "حصل خطأ داخلي في خدمة OpenAI.",
            "details": str(e)
        }), 502

    except Exception as e:
        # مسك أي شيء غير متوقع
        print("OpenAI error:", e)
        return jsonify({"error": "llm_error"}), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    flash('❌ الملف الذي تحاول رفعه كبير جداً. يرجى اختيار ملف أصغر.', 'error')
    return redirect(request.referrer)  # إعادة التوجيه إلى الصفحة السابقة

@app.get("/health")
def health():
    return jsonify({"status":"ok"}), 200

#announcement_english
@app.route("/admin/tools/fill_en_ann", methods=["POST"])
def admin_fill_en_ann():
    if 'user_id' not in session:
        flash("❌ لا تملك صلاحية.", "error"); return redirect(url_for("login"))
    try:
        db.session.execute(text("""
            UPDATE announcement
            SET title_en   = COALESCE(title_en,   title),
                content_en = COALESCE(content_en, content)
        """))
        db.session.commit()
        flash("✅ تمت تعبئة الإنجليزية للإعلانات.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ خطأ: {e}", "error")
    return redirect(url_for("announcements_page"))


@app.route("/admin/tools/fill_en_once", methods=["POST"])
def admin_fill_en_once():
    if 'user_id' not in session:
        flash("❌ لا تملك صلاحية تنفيذ هذه العملية.", "error")
        return redirect(url_for("login"))
    try:
        db.session.execute(text("""
            UPDATE news
            SET title_en   = COALESCE(title_en,   title),
                content_en = COALESCE(content_en, content)
        """))
        db.session.commit()
        flash("✅ تمت تعبئة الحقول الإنجليزية للأخبار القديمة.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ خطأ: {e}", "error")
    return redirect(url_for("news"))

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, Category=Category, Gallery=Gallery)

#if __name__ == '__main__':
 #   app.run(debug=False, host='0.0.0.0', port=8000)
  #  app.run(debug=True)

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8000)


#app.config.update(
#    DEBUG=False,
#    TESTING=False,
#    TEMPLATES_AUTO_RELOAD=False
#)
