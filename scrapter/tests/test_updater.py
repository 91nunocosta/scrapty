from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch, call

import scrapy
import scrapter.updater
from scrapter.updates_register import Crawl, CrawlStatus
from scrapy.settings import Settings


class SpiderExample(scrapy.Spider):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SpiderExampleWithLast(scrapy.Spider):

    def __init__(self, last=None, *args, **kwargs):
        super().__init__(*args, **kwargs)



class TestUpdater(TestCase):

    def setUp(self):
        self.crawl_patcher = patch('scrapter.updater.CrawlerProcess')
        self.register_patcher = patch('scrapter.updater.MongoUpdatesRegister')
        self.load_spider_patcher = patch('scrapter.updater.SpiderLoader')
        self.crawl_mock = self.crawl_patcher.start()
        self.register_mock = self.register_patcher.start()
        self.load_spider_mock = self.load_spider_patcher.start()
        register = self.register_mock.return_value
        self.start = datetime(2018, 1, 1)
        end = datetime(2018, 2, 1)
        register.last.return_value = Crawl('spider',
                                           CrawlStatus.SUCCESS,
                                           self.start,
                                           end
                                           )

        spiders = ['spider1', 'spider2']
        settings = Settings({
            'MONGO_HOST': None,
            'MONGO_PORT': None,
            'MONGO_DB': None,
            'SPIDERS': spiders
        })
        self.updater = scrapter.updater.Updater(settings)
        self.assertListEqual(self.updater.spiders, spiders)

    def tearDown(self):
        self.crawl_patcher.stop()
        self.register_patcher.stop()
        self.load_spider_patcher.stop()
    
    def test_can_not_create_with_missing_settings(self):
        settings = Settings({
        })
        with self.assertRaises(scrapter.updater.MissingSetting):
            scrapter.updater.Updater(settings)

    def test_can_create(self):
        register = self.register_mock.return_value
        register.open_db.assert_called()
    
    def test_can_start(self):
        self.updater.run()
        crawl_process = self.crawl_mock.return_value
        crawl_process.crawl.assert_any_call('spider1')
        crawl_process.crawl.assert_any_call('spider2')
        crawl_process.start.assert_called()

    def test_can_register_successful_update(self):
        register = self.register_mock.return_value
        register.start = MagicMock(return_value='1')
        self.updater.run()
        register.start.assert_called_with(['spider1', 'spider2'])
        register.succeed.assert_called_with('1')

    def test_can_check_if_accepts_last(self):
        self.assertFalse(self.updater._accepts_last(SpiderExample))
        self.assertTrue(self.updater._accepts_last(SpiderExampleWithLast))

    def test_can_define_spider_args(self):
        spider_loader = self.load_spider_mock.return_value
        spider_loader.load.return_value = SpiderExampleWithLast
        self.assertDictEqual(self.updater._spider_args('spider'), {
            'last': self.start
        })

    def test_can_start_without_last_update(self):
        register = self.register_mock.return_value
        spider_loader = self.load_spider_mock.return_value
        crawl_process = self.crawl_mock.return_value
        start = datetime(2018, 1, 1)
        end = datetime(2018, 2, 1)
        register.last.return_value = None
        spider_loader.load.return_value = SpiderExampleWithLast
        self.updater.spiders = ['spider']
        self.updater.run()
        crawl_process.crawl.assert_called_with('spider')

    def test_can_continue_last_update(self):
        register = self.register_mock.return_value
        spider_loader = self.load_spider_mock.return_value
        crawl_process = self.crawl_mock.return_value
        start = datetime(2018, 1, 1)
        end = datetime(2018, 2, 1)
        register.last.return_value = Crawl(['spider'],
                                           CrawlStatus.SUCCESS,
                                           start,
                                           end
                                           )
        spider_loader.load.return_value = SpiderExampleWithLast
        self.updater.spiders = ['spider']
        self.updater.run()
        crawl_process.crawl.assert_called_with('spider', last=start)

    
    def test_can_continue_last_with_different_starts(self):
        register = self.register_mock.return_value
        spider_loader = self.load_spider_mock.return_value
        crawl_process = self.crawl_mock.return_value
        start = datetime(2018, 1, 1)
        end = datetime(2018, 2, 1)
        start2 = datetime(2018, 3, 1)
        end2 = datetime(2018, 4, 1)
        register.last.side_effect = [Crawl(['spider'],
                                           CrawlStatus.SUCCESS,
                                           start,
                                           end
                                           ),
                                     Crawl(['spider2'],
                                           CrawlStatus.SUCCESS,
                                           start2,
                                           end2
                                           )
                                    ]
        spider_loader.load.return_value = SpiderExampleWithLast
        self.updater.spiders = ['spider', 'spider2']
        self.updater.run()
        crawl_process.crawl.assert_has_calls([
            call('spider', last=start),
            call('spider2', last=start2)
        ])

    def test_can_check_if_failed(self):
        crawler_process = self.crawl_mock.return_value
        crawler_mock1 = MagicMock()
        crawler_mock2 = MagicMock()
        crawler_mock1.stats.get_value.return_value = 'finished'
        crawler_mock2.stats.get_value.return_value = 'finished'
        crawler_process.crawlers = [crawler_mock1, crawler_mock2]
        self.assertFalse(self.updater._failed(crawler_process))
        crawler_mock1.stats.get_value.return_value = 'failed'
        self.assertTrue(self.updater._failed(crawler_process))

    def test_can_fail(self):
        register = self.register_mock.return_value
        register.start.return_value = '2'
        self.updater._failed = MagicMock(return_value=True)
        self.updater.run()
        register.fail.assert_called_with('2')
