import json
import app.constants as CONST

from flask import Blueprint, request, current_app as app
from app.helpers.response import response_ok, response_error
from app.helpers.decorators import login_required
from app.helpers.utils import parse_date_string_to_timestamp
from app import db
from app.models import User, Match, Outcome
from app.helpers.message import MESSAGE

match_routes = Blueprint('match', __name__)

@match_routes.route('/', methods=['GET'])
@login_required
def matches():
	try:
		matches = Match.query.all()
		data = []
		for match in matches:
			data.append(match.to_json())

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
		for item in data:
			match = Match(
				homeTeamName=item['homeTeamName'],
				homeTeamCode=item['homeTeamCode'],
				homeTeamFlag=item['homeTeamFlag'],
				awayTeamName=item['awayTeamName'],
				awayTeamCode=item['awayTeamCode'],
				awayTeamFlag=item['awayTeamFlag'],
				date=parse_date_string_to_timestamp(item['date'])
			)
			matches.append(match)

		db.session.add_all(matches)
		db.session.commit()

		return response_ok()
	except Exception, ex:
		db.session.rollback()
		return response_error(ex.message)


@match_routes.route('/remove/<int:id>', methods=['POST'])
@login_required
def remove(id):
	try:
		match = Match.find_match_by_id(id)
		if match is not None:
			db.session.delete(match)
			db.session.commit()
			return response_ok("{} has been deleted!".format(match.id))
		else:
			return response_error(MESSAGE.MATCH_NOT_FOUND)

	except Exception, ex:
		db.session.rollback()
		return response_error(ex.message)


@match_routes.route('/report/<int:match_id>', methods=['POST'])
@login_required
def report(match_id):
	try:
		data = request.json
		if data is None:
			raise Exception(MESSAGE.INVALID_DATA)

		match = Match.find_match_by_id(match_id)
		if match is not None:
			homeScore = data['homeScore']
			awayScore = data['awayScore']
			result = data['result']

			match.homeScore = homeScore
			match.awayScore = awayScore
			for outcome in result:
				outcome = Outcome.find_outcome_by_id(outcome['outcome_id'])
				if outcome is not None:
					pass
					# TODO: call nodejs
				else:
					return response_error(MESSAGE.INVALID_OUTCOME)

			return response_ok()
		else:
			return response_error(MESSAGE.MATCH_NOT_FOUND)

	except Exception, ex:
		db.session.rollback()
		return response_error(ex.message)
