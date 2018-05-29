from flask import Flask, g, redirect, request
from app.core import db, jwt, sg, s3, configure_app, wm, fcm, ipfs
from flask_cors import CORS
from models import User
from app.helpers.response import response_error
from app.routes import init_routes
import time

app = Flask(__name__)
# disable strict_slashes
app.url_map.strict_slashes = False
# config app
configure_app(app)

# Accept CORS
# CORS(app)
# init db
db.init_app(app)
# init jwt
jwt.init_app(app)
# init s3
s3.init_app(app)
# init sendgrid
sg.init_app(app)
# init watermark
wm.init_app(app)
# init fcm
fcm.init_app(app)
# init ipfs
ipfs.init_app(app)


@app.before_request
def before_request():
	rp = request.path
	if rp != '/' and rp.endswith('/'):
		return redirect(rp[:-1])

	g.BLOCKCHAIN_SERVER_ENDPOINT = app.config.get('BLOCKCHAIN_SERVER_ENDPOINT')
	g.AUTONOMOUS_SERVICE_ENDPOINT = app.config.get('AUTONOMOUS_SERVICE_ENDPOINT')
	g.PASSPHASE = app.config.get('PASSPHASE')
	g.AUTONOMOUS_WEB_PASSPHASE = app.config.get('AUTONOMOUS_WEB_PASSPHASE')
	g.SOLR_SERVICE = app.config.get('SOLR_SERVICE')

	g.start = time.time()


@app.after_request
def after_request(response):
	if 'start' in g:
		diff = time.time() - g.start
		print "Exec time: %s" % str(diff)
	return response


init_routes(app)


def jwt_error_handler(message):
	return response_error(message)


def needs_fresh_token_callback():
	return response_error('Only fresh tokens are allowed')


def revoked_token_callback():
	return response_error('Token has been revoked')


def expired_token_callback():
	return response_error('Token has expired', 401)


jwt.unauthorized_loader(jwt_error_handler)
jwt.invalid_token_loader(jwt_error_handler)
jwt.claims_verification_loader(jwt_error_handler)
jwt.token_in_blacklist_loader(jwt_error_handler)
jwt.user_loader_error_loader(jwt_error_handler)
jwt.claims_verification_failed_loader(jwt_error_handler)
jwt.expired_token_loader(expired_token_callback)
jwt.needs_fresh_token_loader(needs_fresh_token_callback)
jwt.revoked_token_loader(revoked_token_callback)


@app.errorhandler(Exception)
def error_handler(err):
	return response_error(err.message)

	# @app.errorhandler(404)
	# def error_handler400(err):
	#   return response_error(err.message);
	#
	# @app.errorhandler(500)
	# def error_handler500(err):
	#   return response_error(err.message);
	#
	# @app.error_handler_all(Exception)
	# def errorhandler(err):
	#   return response_error(err.message);
