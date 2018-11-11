from datetime import datetime, timedelta
from unittest import TestCase

import mongomock
import pymongo

from scrapter.mongo_updates_register import MissingConfigurationParameter, \
    MongoUpdatesRegister
from scrapter.updates_register import Crawl, CrawlStatus

class TestMongoUpdatesRegister(TestCase):

    @mongomock.patch(servers=(('mongodb', 27017),))
    def test_can_open_db(self):
        db_config = {
            'MONGO_HOST': 'mongodb',
            'MONGO_PORT': 27017,
            'MONGO_DB': 'db'
        }
        register = MongoUpdatesRegister(db_config)
        register.open_db()
        self.assertIsNotNone(register.database)
        self.assertEqual(register.database.name, 'db')
        self.assertEqual(register.database.client.host, 'mongodb')
        self.assertEqual(register.database.client.port, 27017)

    @mongomock.patch(servers=(('mongodb', 27017),))
    def test_cant_open_db_with_missing_configs(self):
        db_config = {
            'MONGO_HOST': 'mongodb',
            'MONGO_PORT': 27017,
        }
        register = MongoUpdatesRegister(db_config)
        with self.assertRaises(MissingConfigurationParameter) as cm:
            register.open_db()
        self.assertTrue('MONGO_DB' in str(cm.exception))
        db_config = {
            'MONGO_HOST': 'mongodb',
            'MONGO_DB': 'db',
        }
        register = MongoUpdatesRegister(db_config)
        with self.assertRaises(MissingConfigurationParameter) as cm:
            register.open_db()
        self.assertTrue('MONGO_PORT' in str(cm.exception))
        db_config = {
            'MONGO_PORT': 27017,
            'MONGO_DB': 'db'
        }
        register = MongoUpdatesRegister(db_config)
        with self.assertRaises(MissingConfigurationParameter) as cm:
            register.open_db()
        self.assertTrue('MONGO_HOST' in str(cm.exception))

    @mongomock.patch(servers=(('mongodb', 27017),))
    def test_can_start(self):
        db_config = {
            'MONGO_HOST': 'mongodb',
            'MONGO_PORT': 27017,
            'MONGO_DB': 'db'
        }
        register = MongoUpdatesRegister(db_config)
        register.open_db()
        start_date = datetime.now()
        register.start('spider1')
        registers = list(register.database['updates'].find())
        self.assertEqual(len(registers), 1)
        register = registers[0]
        self.assertListEqual(register['spiders'], ['spider1'])
        self.assertEqual(register['status'], str(CrawlStatus.STARTED))
        self.assertAlmostEqual(register['start'], start_date, delta=timedelta(seconds=1))
