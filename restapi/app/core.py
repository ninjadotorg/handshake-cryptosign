import os

from app.extensions.ipfs import IPFS
from app.extensions.sg import SendGrid
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy

from app.extensions.s3 import AWSS3
from app.extensions.water_mark import WaterMark
from app.extensions.fcm import FirebaseCloudMessage

db = SQLAlchemy()
jwt = JWTManager()
s3 = AWSS3()
sg = SendGrid()
wm = WaterMark()
fcm = FirebaseCloudMessage()
ipfs = IPFS()


# configure app from env + silent local settings.cfg
def configure_app(app):
	
	base_dir = os.path.abspath(os.path.dirname(__file__))
	if not os.path.exists(base_dir + "/settings.py"):
		os.rename(base_dir + "/settings-default.py", base_dir + "/settings.py")	

	if not os.path.exists(base_dir + "/settings.cfg"):
		os.rename(base_dir + "/settings-default.cfg", base_dir + "/settings.cfg")	
	
	config = {
		"development": "app.settings.DevelopmentConfig",
		"testing": "app.settings.TestingConfig",
		"staging": "app.settings.StagingConfig",
		"production": "app.settings.ProductionConfig",
		"default": "app.settings.DevelopmentConfig"
	}	
	config_name = os.getenv('PYTHON_ENV', 'default')
	app.config.from_object(config[config_name])  # object-based default configuration
	app.config.from_pyfile(os.path.dirname(os.path.realpath(__file__)) + '/settings.cfg', silent=True)  # instance-folders configuration
