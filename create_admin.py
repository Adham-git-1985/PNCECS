from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()

    username = input("ادخل اسم المستخدم: ")
    password = input("ادخل كلمة المرور: ")

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        print("⚠️ المستخدم موجود مسبقًا.")
    else:
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        print(f"✅ تم إنشاء المستخدم '{username}' بنجاح.")
