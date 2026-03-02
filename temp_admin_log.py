with app.app_context():
    if not User.query.filter_by(username="admin").first():
        from werkzeug.security import generate_password_hash
        admin_user = User(id=1, username="admin", password=generate_password_hash("1234"))
        db.session.add(admin_user)
        db.session.commit()
