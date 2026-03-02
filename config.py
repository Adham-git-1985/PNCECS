import os
import secrets


class BaseConfig:
    """
    الإعدادات الأساسية المشتركة بين جميع البيئات
    """
    # مفتاح التشفير – يُفضَّل تمريره من متغير بيئة وليس ثابتًا في الكود
    SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))

    # الإعدادات العامة
    DEBUG = False
    TESTING = False
    TEMPLATES_AUTO_RELOAD = False

    # إعدادات قاعدة البيانات (كمثال، يمكن تعديلها لاحقاً)
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProductionConfig(BaseConfig):
    """
    إعدادات بيئة الإنتاج (Production)
    """
    DEBUG = False
    TEMPLATES_AUTO_RELOAD = False

    # في حال استخدام PostgreSQL في الإنتاج:
    # DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///instance/news.db")


class DevelopmentConfig(BaseConfig):
    """
    إعدادات بيئة التطوير (Development)
    """
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True

    # قاعدة بيانات SQLite أثناء التطوير
    # DATABASE_URL = "sqlite:///instance/dev.db"