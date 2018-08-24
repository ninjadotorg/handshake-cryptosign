from flask import Blueprint, request, g, current_app as app
from app.helpers.response import response_ok, response_error
from app.helpers.decorators import login_required, admin_required
from app import db
from app.models import User, Outcome, Match, Task
from app.helpers.message import MESSAGE, CODE
from sqlalchemy import or_, and_, text, func, desc

import re
import json
import app.constants as CONST
import app.bl.outcome as outcome_bl
import app.bl.contract as contract_bl

outcome_routes = Blueprint('outcome', __name__)


@outcome_routes.route('/', methods=['GET'])
@login_required
def outcomes():
	try:
		outcomes = Outcome.query.order_by(desc(Outcome.index)).all()
		data = []
		for outcome in outcomes:
			data.append(outcome.to_json())

		return response_ok(data)
	except Exception, ex:
		return response_error(ex.message)


@outcome_routes.route('/add/<int:match_id>', methods=['POST'])
@login_required
def add(match_id):
	"""
	""	Add outcome to match
	"" 	Inputs:
	""		match_id
	""	Outputs:
	""		match json with contract address for frontend
	"""
	try:
		uid = int(request.headers['Uid'])

		data = request.json
		if data is None:
			return response_error(MESSAGE.INVALID_DATA, CODE.INVALID_DATA)

		match = Match.find_match_by_id(match_id)
		if match is None:
			return response_error(MESSAGE.MATCH_NOT_FOUND, CODE.MATCH_NOT_FOUND)

		contract = contract_bl.get_active_smart_contract()
		if contract is None:
			return response_error(MESSAGE.CONTRACT_EMPTY_VERSION, CODE.CONTRACT_EMPTY_VERSION)

		outcomes = []
		response_json = []
		for item in data:
			outcome = Outcome(
				name=item['name'],
				public=item['public'],
				match_id=match_id,
				modified_user_id=uid,
				created_user_id=uid,
				contract_id=contract.id
			)
			db.session.add(outcome)
			db.session.flush()
			
			outcomes.append(outcome)
			outcome_json = outcome.to_json()
			outcome_json["contract"] = contract.to_json()

			response_json.append(outcome_json)

		db.session.add_all(outcomes)
		db.session.commit()

		return response_ok(response_json)

	except Exception, ex:
		db.session.rollback()
		return response_error(ex.message)


@outcome_routes.route('/remove/<int:outcome_id>', methods=['POST'])
@login_required
def remove(outcome_id):
	try:
		uid = int(request.headers['Uid'])
		outcome = db.session.query(Outcome).filter(and_(Outcome.id==outcome_id, Outcome.created_user_id==uid)).first()
		if outcome is not None:
			db.session.delete(outcome)
			db.session.commit()
			return response_ok("{} has been deleted!".format(outcome.id))
		else:
			return response_error(MESSAGE.OUTCOME_INVALID, CODE.OUTCOME_INVALID)

	except Exception, ex:
		db.session.rollback()
		return response_error(ex.message)


@outcome_routes.route('/generate-link', methods=['POST'])
@login_required
def generate_link():
	try:
		uid = int(request.headers['Uid'])
		data = request.json
		if data is None:
			return response_error(MESSAGE.INVALID_DATA, CODE.INVALID_DATA)

		outcome_id = data['outcome_id']
		outcome = db.session.query(Outcome).filter(and_(Outcome.id==outcome_id, Outcome.created_user_id==uid)).first()
		if outcome is not None:
			slug = re.sub('[^\w]+', '-', outcome.name.lower())
			response = {
				'slug': 'discover/{}?match={}&outcome={}&ref={}&is_private={}'.format(slug, outcome.match_id, outcome.id, uid, 0 if outcome.public else 1),
				'slug_short': '?match={}&outcome={}&ref={}&is_private={}'.format(outcome.match_id, outcome.id, uid, 0 if outcome.public else 1)
			}
			return response_ok(response)
			
		else:
			return response_error(MESSAGE.OUTCOME_INVALID, CODE.OUTCOME_INVALID)

	except Exception, ex:
		db.session.rollback()
		return response_error(ex.message)
