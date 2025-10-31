from flask import send_from_directory
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # إضافة الاستيراد هنا
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import subprocess
import math
import uuid
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from models import db, TopImage, Version, Announcement, AnnouncementImage, AnnouncementAttachment
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

# Configure logging to write to a file named 'app.log'
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

load_dotenv()  # Load environment variables from .env

CORS(app)
# make Flask trust IIS/ARR's X-Forwarded-* headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

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





def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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


class News(db.Model):
    id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    link = db.Column(db.String, default="")
    created_at = db.Column(db.DateTime, default=(lambda: datetime.now(timezone.utc)), nullable=False)
    is_custom = db.Column(db.Boolean, default=False, nullable=False)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class Gallery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=(lambda: datetime.now(timezone.utc)), nullable=False)
    news_id = db.Column(db.String, db.ForeignKey('news.id'), nullable=True)


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
        flash(f'حدث خطأ أثناء المعالجة: {e}', 'error')
        # You may want to handle this differently outside a request context


@app.route('/')
def index():
    # جلب الأخبار من قاعدة البيانات
    news_list = News.query.order_by(News.created_at.desc()).all()
    # عرض الأخبار في الصفحة الرئيسية
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
                           versions_marsad=versions_marsad)


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


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session:
        flash("❌ يجب تسجيل الدخول للوصول إلى لوحة التحكم.", "error")
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        link = request.form.get('link')
        image = request.files.get('image')
        gallery_title = request.form.get('gallery_title')
        gallery_description = request.form.get('gallery_description')

        try:
            new_news = News(
                id=str(uuid.uuid4()),
                title=title,
                content=content,
                link=link,
                is_custom=True
            )
            db.session.add(new_news)

            if image and allowed_file(image.filename):
                filename = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                image.save(filepath)
                new_image = Gallery(
                    filename=filename,
                    title=gallery_title,
                    description=gallery_description,
                    news_id=new_news.id
                )
                db.session.add(new_image)
            db.session.commit()
            flash("✅ تم إضافة الخبر (والصورة إن وجدت) بنجاح!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ خطأ أثناء الحفظ: {str(e)}", "error")
        return redirect(url_for('admin'))

    page = request.args.get('page', 1, type=int)
    per_page = 9
    pagination = Gallery.query.order_by(Gallery.uploaded_at.desc()).paginate(page=page, per_page=per_page)
    images = pagination.items
    news = News.query.order_by(News.created_at.desc()).all()
    return render_template("admin.html", user=user, images=images, pagination=pagination, news=news)


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
        base_query = base_query.filter(
            News.title.ilike(f'%{query}%') | News.content.ilike(f'%{query}%')
        )
    pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)
    news_items = pagination.items
    for item in news_items:
        item.gallery = Gallery.query.filter_by(news_id=item.id).all()
    return render_template("news.html", news_list=news_items, page=page, pages=pagination.pages, query=query)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/project_form')
def project_form():
    return render_template('project_form.html')

@app.route('/partners')
def partners():
    return render_template('partners.html')

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
    return render_template('announcement_detail.html', announcement=ann)

@app.route('/announcements_page')
def announcements_page():
    date_from_str = request.args.get('date_from', '').strip()
    date_to_str = request.args.get('date_to', '').strip()

    # 2. ابدأ ببناء الاستعلام الأساسي
    query = Announcement.query.order_by(Announcement.created_at.desc())

    # 3. إذا وُجد تاريخ بداية صالح، قم بإضافته كمرشح
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            # ابحث عن الإعلانات التي تاريخها >= date_from منتصف الليل
            query = query.filter(Announcement.created_at >= date_from)
        except ValueError:
            pass  # تجاهل التواريخ غير الصالحة

    # 4. إذا وُجد تاريخ نهاية صالح، أضفه كمرشح
    if date_to_str:
        try:
            # أضف 1 يوم حتى يشمل تاريخ النهاية بالكامل
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
            # ابحث عن الإعلانات التي تاريخها <= date_to + نهاية اليوم
            date_to_end = datetime(
                date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc
            )
            query = query.filter(Announcement.created_at <= date_to_end)
        except ValueError:
            pass

    # 5. احصل على النتائج بعد الفلترة
    announcements = query.all()

    return render_template('announcements.html', announcements=announcements)


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
        ann     = Announcement(title=title, content=content)
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
        ann.title   = request.form['title']
        ann.content = request.form['content']

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
    related_images = Gallery.query.filter_by(news_id=news.id).all()
    return render_template("news_detail.html", news=news, images=related_images)


@app.route('/add_news', methods=['GET', 'POST'])
def add_news():
    if request.method == 'POST':
        # 1) اجمع بيانات الخبر ومعلومات الصور
        title               = request.form.get('title')
        content             = request.form.get('content')
        link                = request.form.get('link')
        gallery_title       = request.form.get('gallery_title')
        gallery_description = request.form.get('gallery_description')

        # 2) أنشئ كائن الخبر أولاً
        new_news = News(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            link=link,
            is_custom=True
        )
        db.session.add(new_news)
        try:
            db.session.flush()  # لضمان حصول new_news.id

            # 3) رفع عدة صور وربطها بالخبر
            images = request.files.getlist('images')
            for img in images:
                if img and allowed_file(img.filename):
                    filename = f"{uuid.uuid4().hex}_{secure_filename(img.filename)}"
                    save_dir = app.config['UPLOAD_FOLDER']
                    os.makedirs(save_dir, exist_ok=True)
                    img.save(os.path.join(save_dir, filename))

                    new_image = Gallery(
                        filename=filename,
                        title=gallery_title,
                        description=gallery_description,
                        news_id=new_news.id
                    )
                    db.session.add(new_image)

            # 4) commit كل التغييرات دفعة واحدة
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


@app.route('/gallery')
def gallery():
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
    return render_template("gallery.html", images=images, pagination=pagination)

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
    marquee_news = News.query.filter_by(is_custom=True).order_by(News.created_at.desc()).limit(5).all()
    return dict(news_marquee=[
        {"title": news.title, "url": f"/news/{news.id}"} for news in marquee_news
    ])

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
    if request.method == "POST":
        image.title = request.form.get("title")
        image.description = request.form.get("description")
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
        news.title = request.form.get('title')
        news.content = request.form.get('content')
        news.link = request.form.get('link')
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
    title = request.form.get('title')
    description = request.form.get('description')
    if file and file.filename:
        filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        save_path = os.path.join('static', 'images', 'top_images', filename)
        file.save(save_path)
        new_image = TopImage(
            image=filename,
            title=title,
            description=description,
            news_title=request.form.get('news_title'),
            news_content=request.form.get('news_content')
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
                news_id=news_id
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
            News.title.ilike(f'%{query}%') | News.content.ilike(f'%{query}%')
        )
    pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)
    news_items = pagination.items
    for item in news_items:
        item.gallery = Gallery.query.filter_by(news_id=item.id).all()
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
    date_from_str = request.args.get('date_from', '').strip()
    date_to_str = request.args.get('date_to', '').strip()

    # 2. ابدأ ببناء الاستعلام الأساسي
    query = Announcement.query.order_by(Announcement.created_at.desc())

    # 3. إذا وُجد تاريخ بداية صالح، قم بإضافته كمرشح
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            # ابحث عن الإعلانات التي تاريخها >= date_from منتصف الليل
            query = query.filter(Announcement.created_at >= date_from)
        except ValueError:
            pass  # تجاهل التواريخ غير الصالحة

    # 4. إذا وُجد تاريخ نهاية صالح، أضفه كمرشح
    if date_to_str:
        try:
            # أضف 1 يوم حتى يشمل تاريخ النهاية بالكامل
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
            # ابحث عن الإعلانات التي تاريخها <= date_to + نهاية اليوم
            date_to_end = datetime(
                date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc
            )
            query = query.filter(Announcement.created_at <= date_to_end)
        except ValueError:
            pass

    # 5. احصل على النتائج بعد الفلترة
    announcements = query.all()

    return render_template('en/announcements.html', announcements=announcements)

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


if __name__ == '__main__':
    app.run(host="127.0.0.1", port=8000, debug=True, use_reloader=False)
  #  app.run(debug=True)









