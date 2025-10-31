from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # إضافة الاستيراد هنا
from datetime import datetime, timedelta
from pathlib import Path
import json
import os
import subprocess
import math
import uuid
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, TopImage, Version
from pdf2image import convert_from_path
from werkzeug.utils import secure_filename

# Configure logging to write to a file named 'app.log'
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
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



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
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
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
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

    return render_template("index.html",
                           news_list=news_list,
                           top_images=top_images,
                           now=datetime.utcnow(),
                           timedelta=timedelta,
                           versions_basmat=versions_basmat,
                           versions_papers=versions_papers,
                           versions_marsad=versions_marsad)



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


@app.route('/news/<news_id>')
def news_detail(news_id):
    news = News.query.get(news_id)
    if not news:
        flash("❌ الخبر غير موجود.", "error")
        return redirect(url_for("news"))
    related_images = Gallery.query.filter_by(news_id=news.id).all()
    return render_template("news_detail.html", news=news, images=related_images)


@app.route('/add_news', methods=['GET', 'POST'])
def add_news():
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
    # جلب الأخبار من قاعدة البيانات
    news_list = News.query.all()
    # إضافة التمرير (pagination) بشكل صحيح
    page = request.args.get('page', 1, type=int)
    per_page = 5  # عدد العناصر في الصفحة
    #pagination = News.query.order_by(News.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    pagination = Gallery.query.order_by(Gallery.uploaded_at.desc()).paginate(page=page, per_page=per_page)
    images = pagination.items
    news_items = pagination.items
    news = News.query.order_by(News.created_at.desc()).all()

    #return render_template('add_news.html', pagination=pagination, news_items=news_items)  # إرسال التمرير إلى القالب
    return render_template("add_news.html", images=images, pagination=pagination, news=news, news_items=news_items)


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
    per_page = 9
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
        file = request.files.get('file')  # تأكد من أن الحقل 'file' هو الذي يتم رفعه
        file_path = None  # تحديد القيمة الافتراضية لـ file_path
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            #relative_path = os.path.join('pdfs', filename)  # يتم الحفظ داخل static/pdfs
            save_path = os.path.join(app.config['PDF_UPLOAD_FOLDER'], filename)
           # save_path = os.path.join(app.static_folder, relative_path)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            file.save(save_path)
        else:
            flash("❌ يجب رفع ملف PDF للإصدار.", "error")
            return redirect(url_for('add_version'))

        # رفع الصورة المصغرة
        thumbnail = request.files.get('thumbnail')
        thumbnail_path2 = None  # تحديد القيمة الافتراضية لـ thumbnail_path
        if thumbnail and allowed_file(thumbnail.filename):
            thumbnail_filename = secure_filename(thumbnail.filename)
            thumbnail_path2 =  thumbnail_filename
            thumbnail.save(thumbnail_path2)

        # إضافة الإصدار إلى قاعدة البيانات
        new_version = Version(
            title=title,
            file_path=os.path.join( filename),  # المسار الصحيح داخل مجلد pdfs
            thumbnail_path= thumbnail_path2 if thumbnail else None,
            category=category
        )
        db.session.add(new_version)
        db.session.commit()

        flash("✅ تم إضافة الإصدار بنجاح!", "success")
        return redirect(url_for('admin'))  # العودة إلى لوحة التحكم بعد إضافة الإصدار

    return render_template('add_version.html')


@app.context_processor
def inject_marquee_news():
    marquee_news = News.query.filter_by(is_custom=True).order_by(News.created_at.desc()).limit(5).all()
    return dict(news_marquee=[
        {"title": news.title, "url": f"/news/{news.id}"} for news in marquee_news
    ])


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

@app.errorhandler(413)
def request_entity_too_large(error):
    flash('❌ الملف الذي تحاول رفعه كبير جداً. يرجى اختيار ملف أصغر.', 'error')
    return redirect(request.referrer)  # إعادة التوجيه إلى الصفحة السابقة


if __name__ == '__main__':
    app.run(debug=True)
