from tests.routes.base import BaseTestCase
from mock import patch
from app.models import Shaker, Handshake, Outcome, Shaker, User, Match
from app import db, app
from app.helpers.message import MESSAGE
from app.constants import Handshake as HandshakeStatus

import mock
import json
import time
import app.bl.user as user_bl

class TestEventBluePrint(BaseTestCase):

    def setUp(self):
        # create match

        match = Match.find_match_by_id(1)
        if match is None:
            match = Match(
                id=1
            )
            db.session.add(match)
            db.session.commit()

        # create user
        user = User.find_user_with_id(88)
        if user is None:
            user = User(
                id=88
            )
            db.session.add(user)
            db.session.commit()

        user = User.find_user_with_id(99)
        if user is None:
            user = User(
                id=99
            )
            db.session.add(user)
            db.session.commit()


        user = User.find_user_with_id(33)
        if user is None:
            user = User(
                id=33
            )
            db.session.add(user)
            db.session.commit()

        user = User.find_user_with_id(22)
        if user is None:
            user = User(
                id=22
            )
            db.session.add(user)
            db.session.commit()

        user = User.find_user_with_id(66)
        if user is None:
            user = User(
                id=66
            )
            db.session.add(user)
            db.session.commit()

        # create outcome
        outcome = Outcome.find_outcome_by_id(88)
        if outcome is None:
            outcome = Outcome(
                id=88,
                match_id=1,
                hid=88
            )
            db.session.add(outcome)
            db.session.commit()
        else:
            outcome.result = -1
            db.session.commit()

    def clear_data_before_test(self):
        # delete master user
        user = User.find_user_with_id(1)
        if user is not None:
            db.session.delete(user)
            db.session.commit()

        handshakes = db.session.query(Handshake).filter(Handshake.outcome_id==88).all()
        for handshake in handshakes:
            db.session.delete(handshake)
            db.session.commit()

    def test_reiceive_init_event(self):
        self.clear_data_before_test()
        # -----
        handshake = Handshake(
				hs_type=3,
				chain_id=4,
				is_private=1,
				user_id=88,
				outcome_id=88,
				odds=1.2,
				amount=1,
				currency='ETH',
				side=1,
				remaining_amount=1,
				from_address='0x123',
                status=-1
        )
        db.session.add(handshake)
        db.session.commit()

        handshake_id = handshake.id

        with self.client:
            Uid = 1
            
            params = {
                "contract": "predictionHandshake",
                "eventName": "__init",
                "status": 1,
                "inputs": {
                    "offchain": "cryptosign_m{}".format(handshake_id),
                    "hid": 88
                }
            }

            response = self.client.post(
                                    '/event',
                                    data=json.dumps(params), 
                                    content_type='application/json',
                                    headers={
                                        "Uid": "{}".format(Uid),
                                        "Fcm-Token": "{}".format(123),
                                        "Payload": "{}".format(123),
                                    })

            data = json.loads(response.data.decode()) 
            self.assertTrue(data['status'] == 1)
            db.session.close()

            h = Handshake.find_handshake_by_id(handshake_id)
            self.assertEqual(h.status, 0)

    def test_reiceive_uninit_event(self):
        self.clear_data_before_test()
        # -----
        handshake = Handshake(
				hs_type=3,
				chain_id=4,
				is_private=1,
				user_id=99,
				outcome_id=88,
				odds=1.2,
				amount=1,
				currency='ETH',
				side=1,
				remaining_amount=1,
				from_address='0x123',
                status=0,
                bk_status=0
        )
        db.session.add(handshake)
        db.session.commit()

        with self.client:
            Uid = 1
            
            params = {
                "contract": "predictionHandshake",
                "eventName": "__uninit",
                "inputs": {
                    "offchain": "cryptosign_m{}".format(handshake.id),
                    "hid": 88
                }
                
            }

            response = self.client.post(
                                    '/event',
                                    data=json.dumps(params), 
                                    content_type='application/json',
                                    headers={
                                        "Uid": "{}".format(Uid),
                                        "Fcm-Token": "{}".format(123),
                                        "Payload": "{}".format(123),
                                    })

            data = json.loads(response.data.decode()) 
            self.assertTrue(data['status'] == 1)

            h = Handshake.find_handshake_by_id(handshake.id)
            self.assertEqual(h.status, 1)


    def test_reiceive_create_maket_event(self):
        self.clear_data_before_test()
        # -----
        outcome = Outcome.find_outcome_by_id(22)
        if outcome is not None:
            db.session.delete(outcome)
            db.session.commit()

        outcome = Outcome(
            id=22,
            match_id=1
        )
        db.session.add(outcome)
        db.session.commit()

        with self.client:
            Uid = 1
            
            params = {
                "contract": "predictionHandshake",
                "eventName": "__createMarket",
                "inputs": {
                    "offchain": "cryptosign_createMarket{}".format(22),
                    "hid": 88
                }
            }

            response = self.client.post(
                                    '/event',
                                    data=json.dumps(params), 
                                    content_type='application/json',
                                    headers={
                                        "Uid": "{}".format(Uid),
                                        "Fcm-Token": "{}".format(123),
                                        "Payload": "{}".format(123),
                                    })

            data = json.loads(response.data.decode()) 
            self.assertTrue(data['status'] == 1)

            outcome = Outcome.find_outcome_by_id(22)
            self.assertEqual(outcome.hid, 88)


    def test_reiceive_collect_event_for_shaker(self):
        self.clear_data_before_test()
        # -----
        handshake = Handshake(
				hs_type=3,
				chain_id=4,
				is_private=1,
				user_id=33,
				outcome_id=88,
				odds=1.2,
				amount=1,
				currency='ETH',
				side=2,
				remaining_amount=1,
				from_address='0x123',
                status=0
        )
        db.session.add(handshake)
        db.session.commit()

        # -----
        shaker = Shaker(
					shaker_id=33,
					amount=0.2,
					currency='ETH',
					odds=6,
					side=1,
					handshake_id=handshake.id,
					from_address='0x123',
					chain_id=4,
                    status=2
				)
        db.session.add(shaker)
        db.session.commit()


        outcome = Outcome.find_outcome_by_id(88)
        outcome.result = 1

        match = Match.find_match_by_id(outcome.match_id)
        match.date = time.time() - 18600
        db.session.commit()

        with self.client:
            Uid = 66
            params = {
                "contract": "predictionHandshake",
                "eventName": "__collect",
                "status": 1,
                "inputs": {
                    "offchain": "cryptosign_s{}".format(shaker.id),
                    "hid": 88
                }
            }

            response = self.client.post(
                                    '/event',
                                    data=json.dumps(params), 
                                    content_type='application/json',
                                    headers={
                                        "Uid": "{}".format(Uid),
                                        "Fcm-Token": "{}".format(123),
                                        "Payload": "{}".format(123),
                                    })

            data = json.loads(response.data.decode()) 
            self.assertTrue(data['status'] == 1)

            hs = Handshake.find_handshake_by_id(handshake.id)
            s = Shaker.find_shaker_by_id(shaker.id)
            self.assertEqual(hs.status, 6)
            self.assertEqual(s.status, 6)


    def test_reiceive_collect_event_for_maker(self):
        self.clear_data_before_test()
        # -----
        handshake = Handshake(
				hs_type=3,
				chain_id=4,
				is_private=1,
				user_id=22,
				outcome_id=88,
				odds=1.2,
				amount=1,
				currency='ETH',
				side=2,
				remaining_amount=1,
				from_address='0x123',
                status=0
        )
        db.session.add(handshake)
        db.session.commit()

        # -----
        shaker = Shaker(
					shaker_id=22,
					amount=0.2,
					currency='ETH',
					odds=6,
					side=1,
					handshake_id=handshake.id,
					from_address='0x123',
					chain_id=4,
                    status=2
				)
        db.session.add(shaker)
        db.session.commit()


        outcome = Outcome.find_outcome_by_id(88)
        outcome.result = 2

        match = Match.find_match_by_id(outcome.match_id)
        match.date = time.time() - 18600
        db.session.commit()

        with self.client:
            Uid = 22
            params = {
                "contract": "predictionHandshake",
                "eventName": "__collect",
                "status": 1,
                "inputs": {
                    "offchain": "cryptosign_m{}".format(handshake.id),
                    "hid": 88
                }
            }

            response = self.client.post(
                                    '/event',
                                    data=json.dumps(params), 
                                    content_type='application/json',
                                    headers={
                                        "Uid": "{}".format(Uid),
                                        "Fcm-Token": "{}".format(123),
                                        "Payload": "{}".format(123),
                                    })

            data = json.loads(response.data.decode()) 
            self.assertTrue(data['status'] == 1)

            hs = Handshake.find_handshake_by_id(handshake.id)
            s = Shaker.find_shaker_by_id(shaker.id)

            self.assertEqual(hs.status, 6)
            self.assertEqual(s.status, 6)

    def test_reiceive_shake_event(self):
        self.clear_data_before_test()
        # -----
        handshake = Handshake(
				hs_type=3,
				chain_id=4,
				is_private=1,
				user_id=66,
				outcome_id=88,
				odds=1.2,
				amount=1,
				currency='ETH',
				side=2,
				remaining_amount=1,
				from_address='0x123',
                status=0
        )
        db.session.add(handshake)
        db.session.commit()

        # -----
        shaker = Shaker(
					shaker_id=66,
					amount=0.2,
					currency='ETH',
					odds=6,
					side=1,
					handshake_id=handshake.id,
					from_address='0x123',
					chain_id=4,
                    status=-1
				)
        db.session.add(shaker)
        db.session.commit()

        shaker_id = shaker.id

        with self.client:
            Uid = 1
            
            params = {
                "contract": "predictionHandshake",
                "eventName": "__shake",
                "status": 1,
                "inputs": {
                    "offchain": "cryptosign_s{}".format(shaker_id),
                    "hid": 88
                }   
            }

            response = self.client.post(
                                    '/event',
                                    data=json.dumps(params), 
                                    content_type='application/json',
                                    headers={
                                        "Uid": "{}".format(Uid),
                                        "Fcm-Token": "{}".format(123),
                                        "Payload": "{}".format(123),
                                    })

            data = json.loads(response.data.decode()) 
            self.assertTrue(data['status'] == 1)
            db.session.close()

            s = Shaker.find_shaker_by_id(shaker_id)
            self.assertEqual(s.status, 2)

    def test_reiceive_report_event(self):
        self.clear_data_before_test()
        # -----
        handshake = Handshake(
				hs_type=3,
				chain_id=4,
				is_private=1,
				user_id=99,
				outcome_id=88,
				odds=1.2,
				amount=1,
				currency='ETH',
				side=1,
				remaining_amount=1,
				from_address='0x123',
                status=0
        )
        db.session.add(handshake)
        db.session.commit()

        with self.client:
            Uid = 1
            
            params = {
                "contract": "predictionHandshake",
                "eventName": "__report",
                "status": 1,
                "inputs": {
                    "offchain": "cryptosign_report1",
                    "hid": 88    
                }   
            }

            response = self.client.post(
                                    '/event',
                                    data=json.dumps(params), 
                                    content_type='application/json',
                                    headers={
                                        "Uid": "{}".format(Uid),
                                        "Fcm-Token": "{}".format(123),
                                        "Payload": "{}".format(123),
                                    })

            data = json.loads(response.data.decode()) 
            self.assertTrue(data['status'] == 1)

        hs = Handshake.find_handshake_by_id(handshake.id)
        self.assertEqual(hs.status, 0)

    
if __name__ == '__main__':
    unittest.main()