#!/usr/bin/python
# -*- coding: utf-8 -*-
import hashlib
import os
import sys
import time
import requests
import app.constants as CONST
import math
import app.bl.match as match_bl

from decimal import *
from flask import g
from app import db, fcm, sg, firebase
from sqlalchemy import and_, or_, func, text
from app.constants import Handshake as HandshakeStatus, CRYPTOSIGN_OFFCHAIN_PREFIX
from app.models import Handshake, User, Shaker, Outcome
from app.helpers.bc_exception import BcException
from app.tasks import update_feed
from app.helpers.message import MESSAGE
from datetime import datetime

getcontext().prec = 18


def save_status_all_bet_which_user_win(user_id, outcome):
	handshakes = []
	shakers = []
	if outcome.result == CONST.RESULT_TYPE['DRAW'] or outcome.result == CONST.RESULT_TYPE['PENDING']:
		print 'outcome result is {}'.format(outcome.result)
		return None, None

	handshakes = db.session.query(Handshake).filter(or_(Handshake.status==HandshakeStatus['STATUS_INITED'], Handshake.status==HandshakeStatus['STATUS_COLLECT_PENDING']), and_(Handshake.user_id==user_id, Handshake.outcome_id==outcome.id, Handshake.side==outcome.result)).all()
	print 'handshakes {}'.format(handshakes)
	shakers = db.session.query(Shaker).filter(or_(Shaker.status==HandshakeStatus['STATUS_SHAKER_SHAKED'], Shaker.status==HandshakeStatus['STATUS_COLLECT_PENDING']), and_(Shaker.shaker_id==user_id, Shaker.side==outcome.result, Shaker.handshake_id.in_(db.session.query(Handshake.id).filter(Handshake.outcome_id==outcome.id)))).all()
	print 'shakers {}'.format(shakers)

	for handshake in handshakes:
		handshake.status = HandshakeStatus['STATUS_DONE']
		handshake.bk_status = HandshakeStatus['STATUS_DONE']
		db.session.merge(handshake)

	for shaker in shakers:
		shaker.status = HandshakeStatus['STATUS_DONE']
		shaker.bk_status = HandshakeStatus['STATUS_DONE']
		db.session.merge(shaker)
		

	db.session.flush()
	return handshakes, shakers

def save_collect_state_for_maker(handshake):
	if handshake is not None:
		outcome = Outcome.find_outcome_by_id(handshake.outcome_id)
		if outcome is not None:
			if handshake.side == outcome.result:
				shaker = Shaker.find_shaker_by_handshake_id(handshake.id)
				shaker.status = HandshakeStatus['STATUS_DONE']
				shaker.bk_status = HandshakeStatus['STATUS_DONE']

				db.session.merge(shaker)
				db.session.flush()
				handshakes, shakers = save_status_all_bet_which_user_win(handshake.user_id, outcome)
				
				if shakers is None:
					shakers = []	
				shakers.append(shaker)
				return handshakes, shakers

def save_collect_state_for_shaker(shaker):
	if shaker is not None:
		handshake = Handshake.find_handshake_by_id(shaker.handshake_id)
		outcome = Outcome.find_outcome_by_id(handshake.outcome_id)

		if outcome is not None:
			if shaker.side == outcome.result:
				handshake.status = HandshakeStatus['STATUS_DONE']
				handshake.bk_status = HandshakeStatus['STATUS_DONE']

				db.session.merge(handshake)
				db.session.flush()
				handshakes, shakers = save_status_all_bet_which_user_win(shaker.shaker_id, outcome)
				
				if handshakes is None:
					handshakes = []
				handshakes.append(handshake)
				return handshakes, shakers

	return None, None

def data_need_set_result_for_outcome(outcome):
	print 'data_need_set_result_for_outcome --> {}, {}'.format(outcome.id, outcome.result)

	handshakes = db.session.query(Handshake).filter(Handshake.outcome_id==outcome.id).all()
	shakers = db.session.query(Shaker).filter(Shaker.handshake_id.in_(db.session.query(Handshake.id).filter(Handshake.outcome_id==outcome.id))).all()
	return handshakes, shakers


def parse_inputs(inputs):
	offchain = ''
	hid = ''

	if 'offchain' in inputs:
		offchain = inputs['offchain']

	if 'hid' in inputs:
		hid = inputs['hid']

	return offchain, hid


def save_handshake_method_for_event(method, inputs):
	offchain = inputs['offchain']
	if method == 'init' or method == 'initTestDrive':
		offchain = offchain.replace(CONST.CRYPTOSIGN_OFFCHAIN_PREFIX, '')
		offchain = int(offchain.replace('m', ''))
		handshake = Handshake.find_handshake_by_id(offchain)
		if handshake is not None:
			handshake.status = HandshakeStatus['STATUS_INIT_FAILED']
			db.session.flush()

			if 'maker' in inputs: # free-bet
				user = User.find_user_with_id(handshake.user_id)
				if user is not None and user.free_bet == 1:
					user.free_bet = 0
					db.session.flush()

			arr = []
			arr.append(handshake)
			return arr, None

	elif method == 'shake' or method == 'shakeTestDrive':
		offchain = offchain.replace(CONST.CRYPTOSIGN_OFFCHAIN_PREFIX, '')
		offchain = int(offchain.replace('s', ''))
		shaker = Shaker.find_shaker_by_id(offchain)
		if shaker is not None:
			shaker.status = HandshakeStatus['STATUS_SHAKE_FAILED']
			db.session.flush()

			if 'taker' in inputs: # free-bet
				user = User.find_user_with_id(shaker.shaker_id)
				if user is not None and user.free_bet == 1:
					user.free_bet = 0
					db.session.flush()

			arr = []
			arr.append(shaker)
			return None, arr

	elif method == 'uninit' or method == 'uninitTestDrive':
		offchain = offchain.replace(CONST.CRYPTOSIGN_OFFCHAIN_PREFIX, '')
		offchain = int(offchain.replace('m', ''))
		handshake = Handshake.find_handshake_by_id(offchain)
		if handshake is not None:
			handshake.status = HandshakeStatus['STATUS_MAKER_UNINIT_FAILED']
			db.session.flush()

			arr = []
			arr.append(handshake)
			return arr, None

	return None, None


def save_handshake_for_event(event_name, inputs):
	offchain, hid = parse_inputs(inputs)
	offchain = offchain.replace(CONST.CRYPTOSIGN_OFFCHAIN_PREFIX, '')

	if '__createMarket' in event_name:
		offchain = int(offchain.replace('createMarket', ''))
		outcome = Outcome.find_outcome_by_id(offchain)
		if outcome is not None:
			outcome.hid = hid
			db.session.flush()

		return None, None

	elif '__report' in event_name:
		print '__report'
		# report1: mean that support win
		# report2: mean that against win
		# report0: mean that no one win
		result = offchain.replace('report', '')
		print 'result {}'.format(result)
		outcome = Outcome.find_outcome_by_hid(hid)
		if len(result) > -1:
			result = int(result)
			outcome.result = result

			db.session.flush()
			return data_need_set_result_for_outcome(outcome)

		return None, None

	elif '__shake' in event_name:
		print '__shake'
		offchain = offchain.replace('s', '')
		shaker = Shaker.find_shaker_by_id(int(offchain))
		if shaker is not None:
			print 'shaker = {}'.format(shaker)
			shaker.status = HandshakeStatus['STATUS_SHAKER_SHAKED']
			shaker.bk_status = HandshakeStatus['STATUS_SHAKER_SHAKED']

			db.session.flush()

			arr = []
			arr.append(shaker)
			return None, arr

		return None, None

	elif '__collect' in event_name:
		print '__collect'

		if 's' in offchain:
			offchain = offchain.replace('s', '')
			shaker = Shaker.find_shaker_by_id(int(offchain))
			if shaker is not None:
				# update status of shaker and handshake to done
				# find all bets belongs to this outcome which user join
				# update all statuses (shaker and handshake) of them to done
				return save_collect_state_for_shaker(shaker)

		elif 'm' in offchain:
			offchain = offchain.replace('m', '')
			handshake = Handshake.find_handshake_by_id(int(offchain))
			if handshake is not None:
				# update status of shaker and handshake to done
				# find all bets belongs to this outcome which user join
				# update all statuses (shaker and handshake) of them to done
				return save_collect_state_for_maker(handshake)

		return None, None

	elif '__init' in event_name:
		print '__init'

		offchain = offchain.replace('m', '')
		handshake = Handshake.find_handshake_by_id(int(offchain))
		if handshake is not None:
			handshake.status = HandshakeStatus['STATUS_INITED']
			handshake.bk_status = HandshakeStatus['STATUS_INITED']

			db.session.flush()

			arr = []
			arr.append(handshake)
			return arr, None

		return None, None

	elif '__uninit' in event_name:
		print '__uninit'
		offchain = offchain.replace('m', '')
		handshake = Handshake.find_handshake_by_id(int(offchain))
		if handshake is not None:
			handshake.status = HandshakeStatus['STATUS_MAKER_UNINITED']
			handshake.bk_status = HandshakeStatus['STATUS_MAKER_UNINITED']

			db.session.flush()

			arr = []
			arr.append(handshake)
			return arr, None

		return None, None


def find_all_matched_handshakes(side, odds, outcome_id, amount):
	outcome = db.session.query(Outcome).filter(and_(Outcome.result==CONST.RESULT_TYPE['PENDING'], Outcome.id==outcome_id)).first()
	if outcome is not None:
		win_value = amount*odds
		if win_value - amount > 0:
			# calculate matched odds
			v = odds/(odds-1)
			v = float(Decimal(str(v)).quantize(Decimal('.1'), rounding=ROUND_HALF_DOWN))

			print 'matched odds --> {}'.format(v)
			query = text('''SELECT * FROM handshake where outcome_id = {} and odds <= {} and remaining_amount > 0 and status = {} and side != {} ORDER BY odds ASC;'''.format(outcome_id, v, CONST.Handshake['STATUS_INITED'], side))
			print query
			handshakes = []
			result_db = db.engine.execute(query)
			for row in result_db:
				handshake = Handshake(
					id=row['id'],
					hs_type=row['hs_type'],
					extra_data=row['extra_data'],
					description=row['description'],
					chain_id=row['chain_id'],
					is_private=row['is_private'],
					user_id=row['user_id'],
					outcome_id=row['outcome_id'],
					odds=row['odds'],
					amount=row['amount'],
					currency=row['currency'],
					side=row['side'],
					remaining_amount=row['remaining_amount'],
					from_address=row['from_address'],
					shake_count=row['shake_count'],
					view_count=row['view_count'],
					date_created=row['date_created'],
					date_modified=row['date_modified']
				)
				handshakes.append(handshake)
			return handshakes
	return []


def find_all_joined_handshakes(side, outcome_id):
	outcome = db.session.query(Outcome).filter(and_(Outcome.result==CONST.RESULT_TYPE['PENDING'], Outcome.id==outcome_id)).first()
	if outcome is not None:
		handshakes = db.session.query(Handshake).filter(and_(Handshake.side!=side, Handshake.outcome_id==outcome_id, Handshake.remaining_amount>0, Handshake.status==CONST.Handshake['STATUS_INITED'])).order_by(Handshake.odds.desc()).all()
		return handshakes
	return []


def find_available_support_handshakes(outcome_id):
	outcome = db.session.query(Outcome).filter(and_(Outcome.result==CONST.RESULT_TYPE['PENDING'], Outcome.id==outcome_id)).first()
	if outcome is not None:
		handshakes = db.session.query(Handshake.odds, func.sum(Handshake.remaining_amount).label('amount')).filter(and_(Handshake.side==CONST.SIDE_TYPE['SUPPORT'], Handshake.outcome_id==outcome_id, Handshake.remaining_amount>0, Handshake.status==CONST.Handshake['STATUS_INITED'])).group_by(Handshake.odds).order_by(Handshake.odds.desc()).all()
		return handshakes
	return []


def find_available_against_handshakes(outcome_id):
	outcome = db.session.query(Outcome).filter(and_(Outcome.result==CONST.RESULT_TYPE['PENDING'], Outcome.id==outcome_id)).first()
	if outcome is not None:
		handshakes = db.session.query(Handshake.odds, func.sum(Handshake.remaining_amount).label('amount')).filter(and_(Handshake.side==CONST.SIDE_TYPE['AGAINST'], Handshake.outcome_id==outcome_id, Handshake.remaining_amount>0, Handshake.status==CONST.Handshake['STATUS_INITED'])).group_by(Handshake.odds).order_by(Handshake.odds.desc()).all()
		return handshakes
	return []


def rollback_shake_state(shaker):
	if shaker is None:
		raise Exception(MESSAGE.SHAKER_NOT_FOUND)

	shaker.status = HandshakeStatus['STATUS_SHAKER_ROLLBACK']
	handshake = db.session.query(Handshake).filter(and_(Handshake.id==shaker.handshake_id, Handshake.status==HandshakeStatus['STATUS_INITED'])).first()
	if handshake is None:
		raise Exception(MESSAGE.HANDSHAKE_NOT_FOUND)

	handshake.remaining_amount += ((shaker.odds * shaker.amount) - shaker.amount)
	db.session.flush()

	return shaker


def is_init_pending_status(handshake):
	if handshake.status == HandshakeStatus['STATUS_PENDING'] and handshake.bk_status == HandshakeStatus['STATUS_PENDING']:
		return True	
	return False


def update_handshakes_feed(handshakes, shakers):
	# update feed
	if handshakes is not None:
		for handshake in handshakes:
			update_feed.delay(handshake.id)

	if shakers is not None:
		for shaker in shakers:
			update_feed.delay(shaker.handshake_id)


def can_withdraw(handshake, shaker=None):
	outcome = None
	result = None

	if shaker is None:
		if handshake is not None:
			if handshake.status == HandshakeStatus['STATUS_INITED']:
				outcome = Outcome.find_outcome_by_id(handshake.outcome_id)
				result = handshake.side
			else:
				return MESSAGE.CANNOT_WITHDRAW
		else:
			return MESSAGE.CANNOT_WITHDRAW
	else:
		if shaker.status == HandshakeStatus['STATUS_SHAKER_SHAKED']:
			handshake = Handshake.find_handshake_by_id(shaker.handshake_id)
			outcome = Outcome.find_outcome_by_id(handshake.outcome_id)	
			result = shaker.side
		else:
			return MESSAGE.CANNOT_WITHDRAW

	if outcome is not None:
		if outcome.result != result:
			return MESSAGE.HANDSHAKE_NOT_THE_SAME_RESULT

		if match_bl.is_exceed_dispute_time(outcome.match_id) == False:
			return MESSAGE.HANDSHAKE_WITHDRAW_AFTER_DISPUTE
	else:
		return MESSAGE.OUTCOME_INVALID

	return ''

def can_uninit(handshake):
	if handshake is None:
		return False
	
	n = time.mktime(datetime.now().timetuple())
	if len(handshake.shakers.all()) == 0:
		ds = time.mktime(handshake.date_created.timetuple()) 
		if n - ds > 300: #5 minutes
			return True

	else:
		for sk in handshake.shakers.all():
			if sk.status == HandshakeStatus['STATUS_SHAKER_SHAKED']:
				return False
			else:
				ds = time.mktime(sk.date_created.timetuple()) 
				if n - ds < 300:
					return False

		return True

	return False
