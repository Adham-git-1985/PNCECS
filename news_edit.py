
@app.route('/edit_news/<string:news_id>', methods=['GET', 'POST'])
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


@app.route('/delete_news/<string:news_id>', methods=['POST'])
def delete_news(news_id):
    if 'user_id' not in session:
        flash("❌ لا تملك صلاحية للحذف.", "error")
        return redirect(url_for('login'))

    news = News.query.get_or_404(news_id)
    try:
        db.session.delete(news)
        db.session.commit()
        flash("✅ تم حذف الخبر بنجاح", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ حدث خطأ أثناء الحذف: {e}", "error")

    return redirect(url_for('admin'))
