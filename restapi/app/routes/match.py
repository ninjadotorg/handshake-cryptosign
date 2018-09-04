import os
import json
import requests
import app.constants as CONST
import app.bl.match as match_bl
import app.bl.contract as contract_bl

from sqlalchemy import and_, or_, desc, func
from flask_jwt_extended import jwt_required, decode_token
from flask import g, Blueprint, request, current_app as app
from datetime import datetime
from app.helpers.response import response_ok, response_error
from app.helpers.decorators import login_required, admin_required
from app.helpers.utils import local_to_utc
from app.bl.match import is_validate_match_time
from app import db
from app.models import User, Match, Outcome, Task, Source, Category, Contract, Handshake, Shaker
from app.helpers.message import MESSAGE, CODE

match_routes = Blueprint('match', __name__)

@match_routes.route('/', methods=['GET'])
@login_required
def matches():
	try:
		response = []
		matches = []

		t = datetime.now().timetuple()
		seconds = local_to_utc(t)
		
		matches = db.session.query(Match).filter(Match.deleted == 0, Match.date > seconds, Match.id.in_(db.session.query(Outcome.match_id).filter(and_(Outcome.result == -1, Outcome.hid != None)).group_by(Outcome.match_id))).order_by(Match.index.desc(), Match.date.asc()).all()
		for match in matches:
			match_json = match.to_json()

			# Total User
			hs_count_user = db.session.query(Handshake.user_id.label("user_id"))\
			.filter(Outcome.match_id == match.id)\
			.filter(Handshake.outcome_id == Outcome.id)\
			.group_by(Handshake.user_id)

			s_count_user = db.session.query(Shaker.shaker_id.label("user_id"))\
			.filter(Outcome.match_id == match.id)\
			.filter(Handshake.outcome_id == Outcome.id)\
			.filter(Handshake.id == Shaker.handshake_id)\
			.group_by(Shaker.shaker_id)

			user_union = hs_count_user.union(s_count_user)
			total_user = db.session.query(func.count(user_union.subquery().columns.user_id).label("total")).scalar()

			# Total Amount
			hs_amount = db.session.query(func.sum((Handshake.amount * Handshake.odds)).label("total_amount_hs"))\
			.filter(Outcome.match_id == match.id)\
			.filter(Handshake.outcome_id == Outcome.id)

			s_amount = db.session.query(func.sum((Shaker.amount * Shaker.odds)).label("total_amount_s"))\
			.filter(Outcome.match_id == match.id)\
			.filter(Handshake.outcome_id == Outcome.id)\
			.filter(Handshake.id == Shaker.handshake_id)
			total_amount = db.session.query(hs_amount.label("total_amount_hs"), s_amount.label("total_amount_s")).first()
			
			match_json["total_users"] = total_user if total_user is not None else 0			
			match_json["total_bets"] = (total_amount.total_amount_hs if total_amount.total_amount_hs is not None else 0)  + (total_amount.total_amount_s if total_amount.total_amount_s is not None else 0)
			response.append(match_json)

		return response_ok(response)
	except Exception, ex:
		return response_error(ex.message)


@match_routes.route('/add', methods=['POST'])
@login_required
def add_match():
	try:
		uid = int(request.headers['Uid'])

		data = request.json
		if data is None:
			return response_error(MESSAGE.INVALID_DATA, CODE.INVALID_DATA)

		matches = []
		response_json = []

		contract = contract_bl.get_active_smart_contract()
		if contract is None:
			return response_error(MESSAGE.CONTRACT_EMPTY_VERSION, CODE.CONTRACT_EMPTY_VERSION)

		for item in data:
			source = None
			category = None

			if match_bl.is_validate_match_time(item) == False:				
				return response_error(MESSAGE.MATCH_INVALID_TIME, CODE.MATCH_INVALID_TIME)

			if "source_id" in item:
    			# TODO: check deleted and approved
				source = db.session.query(Source).filter(Source.id == int(item['source_id'])).first()
			else:
				if "source" in item and "name" in item["source"] and "url" in item["source"]:
					source = db.session.query(Source).filter(and_(Source.name==item["source"]["name"], Source.url==item["source"]["url"])).first()
					if source is not None:
						return response_error(MESSAGE.SOURCE_EXISTED_ALREADY, CODE.SOURCE_EXISTED_ALREADY)

					source = Source(
						name=item["source"]["name"],
						url=item["source"]["url"],
						created_user_id=uid
					)
					db.session.add(source)
					db.session.flush()

			if "category_id" in item:
				category = db.session.query(Category).filter(Category.id == int(item['category_id'])).first()
			else:
				if "category" in item and "name" in item["category"]:
					category = Category(
						name=item["category"]["name"],
						created_user_id=uid
					)
					db.session.add(category)
					db.session.flush()

			match = Match(
				homeTeamName=item['homeTeamName'],
				homeTeamCode=item['homeTeamCode'],
				homeTeamFlag=item['homeTeamFlag'],
				awayTeamName=item['awayTeamName'],
				awayTeamCode=item['awayTeamCode'],
				awayTeamFlag=item['awayTeamFlag'],
				name=item['name'],
				market_fee=int(item.get('market_fee', 0)),
				date=item['date'],
				reportTime=item['reportTime'],
				disputeTime=item['disputeTime'],
				created_user_id=uid,
				source_id=None if source is None else source.id,
				category_id=None if category is None else category.id
			)
			matches.append(match)
			db.session.add(match)
			db.session.flush()

			if 'outcomes' in item:
				for outcome_data in item['outcomes']:
					outcome = Outcome(
						name=outcome_data['name'],
						match_id=match.id,
						public=item.get('public', 0),
						contract_id=contract.id,
						modified_user_id=uid,
						created_user_id=uid
					)
					db.session.add(outcome)
					db.session.flush()
			match_json = match.to_json()
			match_json['contract'] = contract.to_json()
			match_json['source_name'] = None if source is None else source.name
			match_json['category_name'] = None if category is None else category.name
			response_json.append(match_json)

		db.session.commit()

		return response_ok(response_json)
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
			return response_error(MESSAGE.MATCH_NOT_FOUND, CODE.MATCH_NOT_FOUND)

	except Exception, ex:
		db.session.rollback()
		return response_error(ex.message)


@match_routes.route('/report/<int:match_id>', methods=['POST'])
@login_required
def report_match(match_id):
	"""
	"" report: report outcomes
	"" input:
	""		match_id
	"""
	try:
		uid = int(request.headers['Uid'])
		data = request.json
		response = []
		if data is None:
			return response_error(MESSAGE.INVALID_DATA, CODE.INVALID_DATA)

		match = Match.find_match_by_id(match_id)
		if match is not None:
			result = data['result']
			if result is None:
				return response_error(MESSAGE.MATCH_RESULT_EMPTY, CODE.MATCH_RESULT_EMPTY)
			
			if not match_bl.is_exceed_closing_time(match.id):
				return response_error(MESSAGE.MATCH_CANNOT_SET_RESULT, CODE.MATCH_CANNOT_SET_RESULT)

			for item in result:
				if 'side' not in item:
					return response_error(MESSAGE.OUTCOME_INVALID_RESULT, CODE.OUTCOME_INVALID_RESULT)
				
				if 'outcome_id' not in item:
					return response_error(MESSAGE.OUTCOME_INVALID, CODE.OUTCOME_INVALID)

				outcome = Outcome.find_outcome_by_id(item['outcome_id'])
				if outcome is not None and outcome.created_user_id == uid:
					message, code = match_bl.is_able_to_set_result_for_outcome(outcome)
					if message is not None and code is not None:
						return message, code

					outcome.result = CONST.RESULT_TYPE['PROCESSING']
					outcome_json = outcome.to_json()
					response.append(outcome_json)

				else:
					return response_error(MESSAGE.OUTCOME_INVALID, CODE.OUTCOME_INVALID)

			return response_ok(response)
		else:
			return response_error(MESSAGE.MATCH_NOT_FOUND, CODE.MATCH_NOT_FOUND)

	except Exception, ex:
		return response_error(ex.message)


@match_routes.route('/report', methods=['GET'])
@login_required
def match_need_user_report():
	try:
		uid = int(request.headers['Uid'])

		if request.headers['Uid'] is None:
			return response_error(MESSAGE.USER_INVALID, CODE.USER_INVALID)

		t = datetime.now().timetuple()
		seconds = local_to_utc(t)

		response = []
		contracts = contract_bl.all_contracts()

		# Get all matchs are PENDING (-1)
		matches = db.session.query(Match).filter(and_(Match.date < seconds, Match.reportTime >= seconds, Match.id.in_(db.session.query(Outcome.match_id).filter(and_(Outcome.result == CONST.RESULT_TYPE['PENDING'], Outcome.hid != None, Outcome.created_user_id == uid)).group_by(Outcome.match_id)))).all()

		# Filter all outcome of user
		for match in matches:
			match_json = match.to_json()
			arr_outcomes = []
			for outcome in match.outcomes:
				if outcome.created_user_id == uid and outcome.hid >= 0:
					outcome_json = contract_bl.filter_contract_id_in_contracts(outcome.to_json(), contracts)
					arr_outcomes.append(outcome_json)
			
			match_json["outcomes"] = arr_outcomes
			response.append(match_json)

		return response_ok(response)
	except Exception, ex:
		return response_error(ex.message)
