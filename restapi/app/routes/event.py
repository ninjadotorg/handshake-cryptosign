import app.bl.handshake as handshake_bl
import app.bl.event as event_bl

from flask import Blueprint, request
from app import db

from app.helpers.response import response_ok, response_error
from app.models import Tx
from app.helpers.message import MESSAGE, CODE

event_routes = Blueprint('event', __name__)


@event_routes.route('/', methods=['POST'])
def event():
	try:
		data = request.json
		print 'event = {}'.format(data)
		if data is None:
			return response_error(MESSAGE.INVALID_DATA, CODE.INVALID_DATA)

		status = data.get('status', 1)
		tx_id = int(data['id'])

		handshakes = []
		shakers = []
		tx = Tx.find_tx_by_id(tx_id)
		event_name = ''
		if status == 1:
			event_name = data['eventName']
			inputs = data['inputs']
			handshakes, shakers = handshake_bl.save_handshake_for_event(event_name, inputs)

		elif status == 0:
			method = data.get('methodName', '')
			inputs = data['inputs']
			handshakes, shakers = handshake_bl.save_handshake_method_for_event(method, inputs)

		elif status == 2:
			method = data.get('methodName', '')
			handshakes, shakers = handshake_bl.save_failed_handshake_method_for_event(method, tx)

		if tx is not None:
			tx.status = status
			db.session.flush()

		db.session.commit()
		
		handshake_bl.update_handshakes_feed(handshakes, shakers)
		event_bl.run_bots_for_tx(tx)

		return response_ok()
	except Exception, ex:
		db.session.rollback()
		return response_error(ex.message)
