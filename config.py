# config.py
class BaseConfig:
    SECRET_KEY = '0000'
    DEBUG = False
    TESTING = False
    TEMPLATES_AUTO_RELOAD = False

class ProductionConfig(BaseConfig):
    pass

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True

# app.py
from config import ProductionConfig, DevelopmentConfig
import os

env = os.getenv("FLASK_ENV", "production").lower()
app.config.from_object(DevelopmentConfig if env == "development" else ProductionConfig)

if __name__ == "__main__":
    # للاستخدام المحلي فقط أثناء التطوير:
    app.run()  # بدون debug=True
