"""
database unittests
"""

import mock
import unittest
import posixpath
import json

from cloudant.database import CouchDatabase, CloudantDatabase
from cloudant.errors import CloudantException


class CouchDBTest(unittest.TestCase):
    def setUp(self):
        self.mock_session = mock.Mock()
        self.mock_session.get = mock.Mock()
        self.mock_session.post = mock.Mock()
        self.mock_session.put = mock.Mock()
        self.mock_session.delete = mock.Mock()

        self.account = mock.Mock()
        self.account._cloudant_url = "https://bob.cloudant.com"
        self.account._r_session = self.mock_session

        self.username = "bob"
        self.db_name = "testdb"

        self.db_url = posixpath.join(self.account._cloudant_url, self.db_name)
        self.c = CouchDatabase(self.account, self.db_name)

        self.db_info = {
            "update_seq": "1-g1AAAADfeJzLYWBg",
            "db_name": self.db_name,
            "sizes": {
                "file": 1528585,
                "external": 5643,
                "active": None
            },
            "purge_seq": 0,
            "other": {
                "data_size": 5643
            },
            "doc_del_count": 2,
            "doc_count": 13,
            "disk_size": 1528585,
            "disk_format_version": 6,
            "compact_running": False,
            "instance_start_time": "0"
        }

        self.ddocs = {
            "rows": [
                {
                    "id": "_design/test",
                    "key": "_design/test",
                    "value": {
                        "rev": "1-4e6d6671b0ba9ba994a0f5e7e8de1d9d"
                    },
                    "doc": {
                        "_id": "_design/test",
                        "_rev": "1-4e6d6671b0ba9ba994a0f5e7e8de1d9d",
                        "views": {
                            "test": {
                                "map": "function (doc) {emit(doc._id, 1);}"
                            }
                        }
                    }
                }
            ]
        }

        self.all_docs = {
            "total_rows": 13,
            "offset": 0,
            "rows": [
                {
                    "id": "snipe",
                    "key": "snipe",
                    "value": {
                        "rev": "1-4b2fb3b7d6a226b13951612d6ca15a6b"
                    }
                },
                {
                    "id": "zebra",
                    "key": "zebra",
                    "value": {
                        "rev": "1-750dac460a6cc41e6999f8943b8e603e"
                    }
                }
            ]
        }

    def test_create(self):
        mock_resp = mock.Mock()
        mock_resp.status_code = 201
        self.mock_session.put = mock.Mock()
        self.mock_session.put.return_value = mock_resp

        self.c.create()

        self.failUnless(self.mock_session.put.called)

    def test_delete(self):
        mock_resp = mock.Mock()
        mock_resp.status_code = 200
        self.mock_session.delete = mock.Mock()
        self.mock_session.delete.return_value = mock_resp

        self.c.delete()

        self.failUnless(self.mock_session.delete.called)

    def test_db_info(self):
        mock_resp = mock.Mock()
        mock_resp.status_code = 200
        mock_resp.json = mock.Mock(return_value=self.db_info)
        self.mock_session.get = mock.Mock(return_value=mock_resp)

        exists_resp = self.c.exists()
        meta_resp = self.c.metadata()
        count_resp = self.c.doc_count()

        self.failUnless(self.mock_session.get.called)
        self.assertEqual(self.mock_session.get.call_count, 3)
        self.assertEqual(exists_resp, True)
        self.assertEqual(meta_resp, self.db_info)
        self.assertEqual(count_resp, self.db_info["doc_count"])

    def test_ddocs(self):
        mock_resp = mock.Mock()
        mock_resp.raise_for_status = mock.Mock(return_value=False)
        mock_resp.json = mock.Mock(return_value=self.ddocs)
        self.mock_session.get = mock.Mock(return_value=mock_resp)

        ddocs = self.c.design_documents()
        ddoc_list = self.c.list_design_documents()

        self.failUnless(self.mock_session.get.called)
        self.assertEqual(self.mock_session.get.call_count, 2)
        self.assertEqual(ddocs[0]["id"], "_design/test")
        self.assertEqual(ddoc_list[0], "_design/test")

    def test_all_docs(self):
        mock_resp = mock.Mock()
        mock_resp.json = mock.Mock(return_value=self.all_docs)
        self.mock_session.get = mock.Mock(return_value=mock_resp)

        all_docs = self.c.all_docs()
        keys = self.c.keys(remote=True)

        self.failUnless(self.mock_session.get.called)
        self.assertDictContainsSubset({"id": "snipe"}, all_docs["rows"][0])
        self.assertDictContainsSubset({"id": "zebra"}, all_docs["rows"][1])
        self.assertListEqual(keys, ["snipe", "zebra"])

    def test_bulk_docs(self):
        mock_resp = mock.Mock()
        mock_resp.raise_for_status = mock.Mock(return_value=False)
        self.mock_session.post = mock.Mock(return_value=mock_resp)

        self.c.bulk_docs(['a', 'b', 'c'])

        self.mock_session.post.assert_called_once_with(
            posixpath.join(self.db_url, '_all_docs'),
            data=json.dumps({'keys': ['a', 'b', 'c']})
        )

    def test_bulk_insert(self):
        mock_resp = mock.Mock()
        mock_resp.raise_for_status = mock.Mock(return_value=False)
        self.mock_session.post = mock.Mock(return_value=mock_resp)

        docs = [
            {
                '_id': 'somedoc',
                'foo': 'bar'
            },
            {
                '_id': 'anotherdoc',
                '_rev': '1-ahsdjkasdgf',
                'hello': 'world'
            }
        ]

        self.c.bulk_insert(docs)

        self.mock_session.post.assert_called_once_with(
            posixpath.join(self.db_url, '_bulk_docs'),
            data=json.dumps({'docs': docs}),
            headers={'Content-Type': 'application/json'}
        )

    def test_db_updates(self):
        updates_feed = """
            {"dbname": "somedb3", "type": "created", "account": "bob", "seq": "3-g1AAAABteJzLYWBgYMxgTmFQSElKzi9KdUhJMtHLTc1NzTcwMNdLzskvTUnMK9HLSy3JAapkSmTIY2H4DwRZGcyJzLlAIfa0tKQUQ2NTIkzIAgD_wSJc"}
            {"dbname": "somedb2", "type": "updated", "account": "bob", "seq": "4-g1AAAABteJzLYWBgYMxgTmFQSElKzi9KdUhJMtHLTc1NzTcwMNdLzskvTUnMK9HLSy3JAapkSmTIY2H4DwRZGcyJLLlAIfa0tKQUQ2NTIkzIAgAAASJd"}
            {"dbname": "somedb1", "type": "deleted", "account": "bob", "seq": "9-g1AAAABteJzLYWBgYMxgTmFQSElKzi9KdUhJMtHLTc1NzTcwMNdLzskvTUnMK9HLSy3JAapkSmTIY2H4DwRZGcyJnLlAIfa0tKQUQ2NTIkzIAgAA9iJi"}
            {"dbname": "somedb2", "type": "created", "account": "bob", "seq": "11-g1AAAABteJzLYWBgYMxgTmFQSElKzi9KdUhJMtHLTc1NzTcwMNdLzskvTUnMK9HLSy3JAapkSmTIY2H4DwRZGcyJ3LlAIfa0tKQUQ2NTIkzIAgABWCJk"}
            {"dbname": "somedb1", "type": "updated", "account": "bob", "seq": "12-g1AAAABteJzLYWBgYMxgTmFQSElKzi9KdUhJMtHLTc1NzTcwMNdLzskvTUnMK9HLSy3JAapkSmTIY2H4DwRZGcyJPLlAIfa0tKQUQ2NTIkzIAgABiSJl"}
        """
        with mock.patch('cloudant.database.Feed') as mock_feed:
            feed = (x.strip() for x in updates_feed.split('\n'))
            mock_feed.__iter__ = mock.MagicMock()
            mock_feed.return_value = feed

            updates = [u for u in self.c.db_updates()]

            self.assertEqual(len(updates), 5)


class CloudantDBTest(unittest.TestCase):
    """
    Tests for additional Cloudant database features
    """
    def setUp(self):
        self.mock_session = mock.Mock()
        self.mock_session.get = mock.Mock()
        self.mock_session.post = mock.Mock()
        self.mock_session.put = mock.Mock()
        self.mock_session.delete = mock.Mock()

        self.account = mock.Mock()
        self.account._cloudant_url = "https://bob.cloudant.com"
        self.account._r_session = self.mock_session

        self.username = "bob"
        self.db_name = "testdb"
        self.cl = CloudantDatabase(self.account, self.db_name)

        self.sec_doc = {
            "_id": "_security",
            "cloudant": {
                "someapikey": [
                    "_reader"
                ],
                "nobody": [],
                "bob": [
                    "_writer",
                    "_admin",
                    "_replicator",
                    "_reader"
                ]
            }
        }

        self.shards = {
            "shards": {
                "00000000-3fffffff": [
                    "dbcore@db1.cluster.cloudant.net",
                    "dbcore@db4.cluster.cloudant.net",
                    "dbcore@db3.cluster.cloudant.net"
                ],
                "40000000-7fffffff": [
                    "dbcore@db1.cluster.cloudant.net",
                    "dbcore@db4.cluster.cloudant.net",
                    "dbcore@db6.cluster.cloudant.net"
                ],
                "80000000-bfffffff": [
                    "dbcore@db7.cluster.cloudant.net",
                    "dbcore@db4.cluster.cloudant.net",
                    "dbcore@db3.cluster.cloudant.net"
                ],
                "c0000000-ffffffff": [
                    "dbcore@db1.cluster.cloudant.net",
                    "dbcore@db4.cluster.cloudant.net",
                    "dbcore@db3.cluster.cloudant.net"
                ]
            }
        }

    def test_security_doc(self):
        mock_resp = mock.Mock()
        mock_resp.json = mock.Mock(return_value=self.sec_doc)
        self.mock_session.get = mock.Mock(return_value=mock_resp)

        security_doc = self.cl.security_document()

        self.failUnless(self.mock_session.get.called)
        self.assertDictEqual(security_doc, self.sec_doc)

    def test_shared_dbs(self):
        # share database
        mock_sec_doc = mock.Mock()
        mock_sec_doc.json.return_value = self.sec_doc
        self.mock_session.get.return_value = mock_sec_doc
        self.mock_session.put.return_value = mock_sec_doc

        shared_resp = self.cl.share_database(
            'someotheruser',
            reader=True,
            writer=True
        )

        self.failUnless(self.mock_session.get.called)
        self.failUnless(self.mock_session.put.called)
        self.assertIn('someotheruser', shared_resp['cloudant'])

        # unshare database
        unshared_resp = self.cl.unshare_database('someotheruser')
        self.assertNotIn('someotheruser', unshared_resp['cloudant'])

    def test_shards(self):
        mock_resp = mock.Mock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = mock.Mock()
        mock_resp.json = mock.Mock(return_value=self.shards)
        self.mock_session.get.return_value = mock_resp

        r = self.cl.shards()

        self.failUnless(self.mock_session.get.called)
        self.assertEqual(r, self.shards)

    def test_missing_revs(self):
        doc_id = 'somedocument'
        ret_val = {
            "missed_revs": {doc_id: ['rev1']}
        }
        mock_resp = mock.Mock()
        mock_resp.status_code = 201
        mock_resp.raise_for_status = mock.Mock()
        mock_resp.json = mock.Mock(return_value=ret_val)
        self.mock_session.post.return_value = mock_resp

        missed_revs = self.cl.missing_revisions(doc_id, 'rev1', 'rev2', 'rev3')

        expected_data = {doc_id: ['rev1', 'rev2', 'rev3']}
        expected_url = posixpath.join(
            self.account._cloudant_url,
            self.db_name,
            '_missing_revs'
        )
        self.failUnless(self.mock_session.post.called)
        self.mock_session.post.assert_called_once_with(
            expected_url,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(expected_data)
        )
        self.assertEqual(missed_revs, ret_val["missed_revs"][doc_id])

    def test_revs_diff(self):
        doc_id = 'somedocument'
        ret_val = {
            doc_id: {
                "missing": ['rev1', 'rev3'],
                "possible_ancestors": ['rev2']
            }
        }
        mock_resp = mock.Mock()
        mock_resp.status_code = 201
        mock_resp.raise_for_status = mock.Mock()
        mock_resp.json = mock.Mock(return_value=ret_val)
        self.mock_session.post.return_value = mock_resp

        revs_diff = self.cl.revisions_diff(doc_id, 'rev1', 'rev2', 'rev3')

        expected_data = {doc_id: ['rev1', 'rev2', 'rev3']}
        expected_url = posixpath.join(
            self.account._cloudant_url,
            self.db_name,
            '_revs_diff'
        )
        self.failUnless(self.mock_session.post.called)
        self.mock_session.post.assert_called_once_with(
            expected_url,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(expected_data)
        )
        self.assertEqual(revs_diff, ret_val)

    def test_revs_limit(self):
        limit = 500
        expected_url = posixpath.join(
            self.account._cloudant_url,
            self.db_name,
            '_revs_limit'
        )

        # set rev limit
        mock_put = mock.Mock()
        mock_put.status_code = 201
        mock_put.raise_for_status = mock.Mock()
        mock_put.json = mock.Mock(return_value='{"ok": true}')
        self.mock_session.put.return_value = mock_put

        set_limit = self.cl.set_revision_limit(limit)

        self.failUnless(self.mock_session.put.called)
        self.mock_session.put.assert_called_once_with(
            expected_url,
            data=limit
        )
        self.assertEqual(set_limit, '{"ok": true}')

        # get rev limit
        mock_get = mock.Mock()
        mock_get.status_code = 200
        mock_get.raise_for_status = mock.Mock()
        mock_get.text = limit
        self.mock_session.get.return_value = mock_get

        get_limit = self.cl.get_revision_limit()

        self.failUnless(self.mock_session.put.called)
        self.mock_session.get.assert_called_once_with(expected_url)
        self.assertEqual(get_limit, limit)

    def test_get_revs_limit_bad_resp(self):
        mock_get = mock.Mock()
        mock_get.status_code = 200
        mock_get.raise_for_status = mock.Mock()
        mock_get.text = 'bloop'
        self.mock_session.get.return_value = mock_get

        with self.assertRaises(CloudantException):
            resp = self.cl.get_revision_limit()
            self.failUnless(self.mock_session.get.called)
            self.assertEqual(resp.status_code, 400)

    def test_view_cleanup(self):
        expected_url = posixpath.join(
            self.account._cloudant_url,
            self.db_name,
            '_view_cleanup'
        )

        mock_post = mock.Mock()
        mock_post.status_code = 201
        mock_post.raise_for_status = mock.Mock()
        mock_post.json = mock.Mock(return_value='{"ok": true}')
        self.mock_session.post.return_value = mock_post

        cleanup = self.cl.view_cleanup()

        self.failUnless(self.mock_session.post.called)
        self.mock_session.post.assert_called_once_with(expected_url)
        self.assertEqual(cleanup, '{"ok": true}')

if __name__ == '__main__':
    unittest.main()
