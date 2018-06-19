#!/usr/bin/python
# -*- coding: utf-8 -*-
import hashlib
import os
import sys
import time
import requests
import app.constants as CONST
import math

from decimal import *
from flask import g
from app import db, fcm, sg, firebase
from sqlalchemy import and_, or_, func, text
from app.constants import Handshake as HandshakeStatus, CRYPTOSIGN_OFFCHAIN_PREFIX
from app.models import Handshake, User, Shaker, Outcome
from app.helpers.utils import parse_date_to_int, is_valid_email, parse_shakers_array
from app.helpers.bc_exception import BcException
from app.tasks import update_feed, add_shuriken
from datetime import datetime
from app.helpers.message import MESSAGE
from datetime import datetime
from sqlalchemy import literal

getcontext().prec = 18


def save_status_all_bet_which_user_win(user_id, outcome):
	handshakes = []
	shakers = []
	if outcome.result == CONST.RESULT_TYPE['DRAW'] or outcome.result == CONST.RESULT_TYPE['PENDING']:
		print 'outcome result is {}'.format(outcome.result)
		return

	handshakes = db.session.query(Handshake).filter(and_(Handshake.user_id==user_id, Handshake.outcome_id==outcome.id, Handshake.side==outcome.result)).all()
	print 'handshakes {}'.format(handshakes)
	shakers = db.session.query(Shaker).filter(and_(Shaker.shaker_id==user_id, Shaker.side==outcome.result, Shaker.handshake_id.in_(db.session.query(Handshake.id).filter(Handshake.outcome_id==outcome.id)))).all()
	print 'shakers {}'.format(shakers)

	for handshake in handshakes:
		handshake.status = HandshakeStatus['STATUS_DONE']
		handshake.bk_status = HandshakeStatus['STATUS_DONE']
		db.session.commit()

		update_feed.delay(handshake.id)

	for shaker in shakers:
		shaker.status = HandshakeStatus['STATUS_DONE']
		shaker.bk_status = HandshakeStatus['STATUS_DONE']
		db.session.commit()

		handshake = Handshake.find_handshake_by_id(shaker.handshake_id)
		update_feed.delay(handshake.id, shaker.id)

def save_collect_state_for_maker(handshake):
	if handshake is not None:
		outcome = Outcome.find_outcome_by_id(handshake.outcome_id)
		if outcome is not None:
			if handshake.side == outcome.result:
				handshake.status = HandshakeStatus['STATUS_DONE']
				handshake.bk_status = HandshakeStatus['STATUS_DONE']
				db.session.commit()

				save_status_all_bet_which_user_win(handshake.user_id, outcome)

def save_collect_state_for_shaker(shaker):
	if shaker is not None:
		handshake = Handshake.find_handshake_by_id(shaker.handshake_id)
		outcome = Outcome.find_outcome_by_id(handshake.outcome_id)

		if outcome is not None:
			if shaker.side == outcome.result:
				shaker.status = HandshakeStatus['STATUS_DONE']
				shaker.bk_status = HandshakeStatus['STATUS_DONE']

				handshake.status = HandshakeStatus['STATUS_DONE']
				handshake.bk_status = HandshakeStatus['STATUS_DONE']

				db.session.commit()
				save_status_all_bet_which_user_win(shaker.shaker_id, outcome)

def update_feed_result_for_outcome(outcome):
	print 'update_feed_result_for_outcome --> {}, {}'.format(outcome.id, outcome.result)

	handshakes = db.session.query(Handshake).filter(Handshake.outcome_id==outcome.id).all()
	shakers = db.session.query(Shaker).filter(Shaker.handshake_id.in_(db.session.query(Handshake.id).filter(Handshake.outcome_id==outcome.id))).all()

	for handshake in handshakes:
		print '--> {}'.format(handshake)
		update_feed.delay(handshake.id)

	for shaker in shakers:
		print '--> {}'.format(shaker)
		update_feed.delay(handshake.id, shaker.id)

	return handshakes, shakers


def save_handshake_for_event(event_name, offchain, outcome=None):
	if 'report' in offchain:
		if outcome is None:
			print 'outcome is None'
			return

		# report1: mean that support win
		# report2: mean that against win
		# report0: mean that no one win
		result = offchain.replace('report', '')
		print 'result {}'.format(result)
		if len(result) > -1:
			result = int(result)
			outcome.result = result

			# TOOD: recheck why flush not work here??
			db.session.commit()
			update_feed_result_for_outcome(outcome)

	elif 's' in offchain: # shaker
		offchain = offchain.replace('s', '')
		shaker = Shaker.find_shaker_by_id(int(offchain))
		print 'shaker = {}'.format(shaker)
		if shaker is not None:
			if '__shake' in event_name:
				print '__shake'
				shaker.status = HandshakeStatus['STATUS_SHAKER_SHAKED']
				shaker.bk_status = HandshakeStatus['STATUS_SHAKER_SHAKED']

				# TOOD: recheck why flush not work here??
				db.session.commit()

				handshake = Handshake.find_handshake_by_id(shaker.handshake_id)
				update_feed.delay(handshake.id, shaker.id)
				add_shuriken(shaker.shaker_id)

			elif '__collect' in event_name:
				print '__collect'
				# update status of shaker and handshake to done
				# find all bets belongs to this outcome which user join
				# update all statuses (shaker and handshake) of them to done
				save_collect_state_for_shaker(shaker)

	else: # maker
		offchain = offchain.replace('m', '')
		handshake = Handshake.find_handshake_by_id(int(offchain))
		print 'handshake = {}, offchain = {}'.format(handshake, offchain)
		if handshake is not None:
			if '__init' in event_name:
				print '__init'
				handshake.status = HandshakeStatus['STATUS_INITED']
				handshake.bk_status = HandshakeStatus['STATUS_INITED']

				# TOOD: recheck why flush not work here??
				db.session.commit()

				update_feed.delay(handshake.id)
				add_shuriken(handshake.user_id)

			elif '__uninit' in event_name:
				print '__uninit'
				handshake.status = HandshakeStatus['STATUS_MAKER_UNINITED']
				handshake.bk_status = HandshakeStatus['STATUS_MAKER_UNINITED']

				# TOOD: recheck why flush not work here??
				db.session.commit()

				update_feed.delay(handshake.id)

			elif '__collect' in event_name:
				print '__collect'
				# update status of shaker and handshake to done
				# find all bets belongs to this outcome which user join
				# update all statuses (shaker and handshake) of them to done
				save_collect_state_for_maker(handshake)

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
		for handshake in handshakes:
			print "{} - {}".format(handshake[0], handshake[1])
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

	if shaker.status == HandshakeStatus['STATUS_SHAKER_ROLLBACK']:
		raise Exception(MESSAGE.SHAKER_ROLLBACK_ALREADY)

	shaker.status = HandshakeStatus['STATUS_SHAKER_ROLLBACK']
	handshake = db.session.query(Handshake).filter(and_(Handshake.id==shaker.handshake_id, Handshake.status==HandshakeStatus['STATUS_INITED'])).first()
	if handshake is None:
		raise Exception(MESSAGE.HANDSHAKE_NOT_FOUND)

	handshake.remaining_amount += ((shaker.odds * shaker.amount) - shaker.amount)
	db.session.flush()

	update_feed.delay(handshake.id, shaker.id)