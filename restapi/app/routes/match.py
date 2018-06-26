import os
import json
import requests
import app.constants as CONST
import app.bl.match as match_bl

from flask import g, Blueprint, request, current_app as app
from app.helpers.response import response_ok, response_error
from app.helpers.decorators import login_required, admin_required
from app.bl.match import is_validate_match_time
from app import db
from app.models import User, Match, Outcome, Task
from app.helpers.message import MESSAGE
from flask_jwt_extended import jwt_required

match_routes = Blueprint('match', __name__)

@match_routes.route('/', methods=['GET'])
@login_required
def matches():
	try:
		matches = Match.query.all()
		data = []

		for match in matches:
			#  find best odds which match against
			match_json = match.to_json()

			arr_outcomes = []
			for outcome in match.outcomes:
				if outcome.result == -1 and outcome.hid is not None:
					outcome_json = outcome.to_json()
					odds, amount = match_bl.find_best_odds_which_match_support_side(outcome.id)
					outcome_json["market_odds"] = odds
					outcome_json["market_amount"] = amount
					arr_outcomes.append(outcome_json)
			
			if len(arr_outcomes) > 0:
				match_json["outcomes"] = arr_outcomes
				data.append(match_json)

		return response_ok(data)
	except Exception, ex:
		return response_error(ex.message)


@match_routes.route('/add', methods=['POST'])
@login_required
def add():
	try:
		data = request.json
		if data is None:
			raise Exception(MESSAGE.INVALID_DATA)

		matches = []
		response_json = []
		for item in data:

			if match_bl.is_validate_match_time(item) == False:				
				raise Exception(MESSAGE.INVALID_DATA)

			match = Match(
				homeTeamName=item['homeTeamName'],
				homeTeamCode=item['homeTeamCode'],
				homeTeamFlag=item['homeTeamFlag'],
				awayTeamName=item['awayTeamName'],
				awayTeamCode=item['awayTeamCode'],
				awayTeamFlag=item['awayTeamFlag'],
				name=item['name'],
				public=item.get('public', 0),
				source=item['source'],
				market_fee=int(item['market_fee']),
				date=item['date'],
				reportTime=item['reportTime'],
				disputeTime=item['disputeTime']
			)
			matches.append(match)
			db.session.add(match)
			db.session.flush()

			if 'outcomes' in item:
				for outcome_data in item['outcomes']:
					outcome = Outcome(
						name=outcome_data['name'],
						match_id=match.id
					)
					db.session.add(outcome)
					db.session.flush()

			response_json.append(match.to_json())

		db.session.commit()

		return response_ok(response_json)
	except Exception, ex:
		db.session.rollback()
		return response_error(ex.message)


@match_routes.route('/create_market', methods=['POST'])
@admin_required
def create_market():
	try:
		fixtures_path = os.path.abspath(os.path.dirname(__file__)) + '/fixtures.json'
		data = {}
		with open(fixtures_path, 'r') as f:
			data = json.load(f)

		matches = []
		if 'fixtures' in data:
			fixtures = data['fixtures']
			for item in fixtures:
				if len(item['homeTeamName']) > 0 and len(item['awayTeamName']) > 0:
					match = Match(
								homeTeamName=item['homeTeamName'],
								awayTeamName=item['awayTeamName'],
								name='{} vs {}'.format(item['homeTeamName'], item['awayTeamName']),
								source='football-data.org',
								market_fee=0,
								date=item['date'],
								reportTime=item['reportTime'],
								disputeTime=item['disputeTime']
							)
					matches.append(match)
					db.session.add(match)
					db.session.flush()
					
					outcome = Outcome(
						name='{} wins'.format(item['homeTeamName']),
						match_id=match.id
					)
					db.session.add(outcome)
					db.session.flush()

					# add Task
					task = Task(
						task_type=CONST.TASK_TYPE['REAL_BET'],
						data=json.dumps(outcome.to_json()),
						action=CONST.TASK_ACTION['CREATE_MARKET'],
						status=-1
					)
					db.session.add(task)
					db.session.flush()

		db.session.commit()
		return response_ok()
	except Exception, ex:
		db.session.rollback()
		return response_error(ex.message)


@match_routes.route('/remove/<int:id>', methods=['POST'])
@login_required
@admin_required
def remove(id):
	try:
		match = Match.find_match_by_id(id)
		if match is not None:
			db.session.delete(match)
			db.session.commit()
			return response_ok(message="{} has been deleted!".format(match.id))
		else:
			return response_error(MESSAGE.MATCH_NOT_FOUND)

	except Exception, ex:
		db.session.rollback()
		return response_error(ex.message)

@match_routes.route('/report/<int:match_id>', methods=['POST'])
@login_required
@jwt_required
def report(match_id):
	try:
		data = request.json
		if data is None:
			raise Exception(MESSAGE.INVALID_DATA)

		match = Match.find_match_by_id(match_id)
		if match is not None:
			result = data['result']
			if result is None:
				return response_error(MESSAGE.MATCH_RESULT_EMPTY)
			
			if result['side'] is None:
				return response_error(MESSAGE.OUTCOME_INVALID_RESULT)
				
			if result['outcome_id'] is None:
				return response_error(MESSAGE.OUTCOME_INVALID)

			outcome = Outcome.find_outcome_by_id(result['outcome_id'])
			if outcome is not None:
				if outcome.result != -1:
					return response_error(MESSAGE.OUTCOME_HAS_RESULT)

				elif match_bl.is_exceed_report_time(outcome.match_id):
					return response_error(MESSAGE.MATCH_CANNOT_SET_RESULT)

			else:
				return response_error(MESSAGE.OUTCOME_INVALID)

			dataReport = {}
			dataReport['hid'] = outcome.hid
			dataReport['outcome_result'] = result['side']
			requests.post(g.BLOCKCHAIN_SERVER_ENDPOINT + '/cryptosign/report',
							json=dataReport,
							headers={"Content-Type": "application/json"})

			return response_ok()
		else:
			return response_error(MESSAGE.MATCH_NOT_FOUND)

	except Exception, ex:
		db.session.rollback()
		return response_error(ex.message)
