from copy import deepcopy

from mock import patch, call
from unittest import TestCase
import pymongo
from pymongo.read_preferences import Primary
from mongo_pool import MongoPool


class MongoPoolTestCase(TestCase):
    def setUp(self):
        self.config = [{'label1': {'host': '127.0.0.1',
                                   'port': 27017,
                                   'dbpath': 'db1'}},
                       {'label3': {'host': '127.0.0.1',
                                   'port': 27018,
                                   'dbpath': 'dbp'}},
                       {'label4': {'host': '127.0.0.1',
                                   'port': 27019,
                                   'dbpath': 'dbpat'}},
                       {'label5': {'host': '127.0.0.1',
                                   'port': 27020,
                                   'dbpath': 'dbpattern\d*'}},
                       {'label6': {'host': '127.0.0.1',
                                   'port': 27021,
                                   'dbpath': ['arraydb1', 'arraydb\dxyz']}}]

        self.call_arguments = {'host': '127.0.0.1',
                               'port': 27017,
                               'w': 1,
                               'j': False,
                               'read_preference': Primary(),
                               'socketTimeoutMS': None,
                               'replicaSet':None}

    def test_default_connection_classes(self):
        """
        Ensure that if no custom classes are provided, the default one are used
        (MongoClient, MongoReplicaSetClient).
        """
        pool = MongoPool(self.config)
        self.assertIs(pool._connection_class, pymongo.MongoClient,
                      "Does not use MongoClient by default.")

    @patch('mongo_pool.mongo_pool.pymongo.MongoClient')
    def test_uses_passed_connection_class(self, mock_connection):
        """
        Ensure passed custom connection classes are used.
        """
        kwarguments = {'connection_class': mock_connection}
        pool = MongoPool(self.config, **kwarguments)
        self.assertIs(pool._connection_class, mock_connection,
                      "Does not use passed connection class")

    def test_raises_exception_for_invalid_host(self):
        config = [{'label': {'port': 27017, 'dbpath': '.*'}}]
        # Expect exception to be raised when no host is provided
        with self.assertRaises(TypeError):
            MongoPool(config)

        # Expect exception to be raised when host is neither a string,
        # nor a list
        config[0]['label']['host'] = 1
        with self.assertRaises(TypeError):
            MongoPool(config)

        # Expect validation to pass when host is a string
        config[0]['label']['host'] = '127.0.0.1'
        try:
            MongoPool(config)
        except TypeError:
            self.fail('MongoPool._validate_config raised Type Error while '
                      'valid config was provided')

        # Expect validation to pass when host is a list
        config[0]['label']['host'] = ['127.0.0.1']
        try:
            MongoPool(config)
        except TypeError:
            self.fail('MongoPool._validate_config raised Type Error while '
                      'valid config was provided')

    def test_raises_exception_for_invalid_port(self):
        config = [{'label': {'host': '127.0.0.1', 'dbpath': '.*'}}]
        with self.assertRaises(TypeError):
            MongoPool(config)
        config[0]['label']['port'] = 'a'
        with self.assertRaises(TypeError):
            MongoPool(config)
        config[0]['label']['port'] = 27017
        try:
            MongoPool(config)
        except TypeError:
            self.fail('MongoPool._validate_config raised Type Error while '
                      'valid config was provided')

    def test_raises_exception_for_invalid_dbpath(self):
        config = [{'label': {'host': '127.0.0.1', 'port': 27017}}]
        with self.assertRaises(TypeError):
            MongoPool(config)
        config[0]['label']['dbpath'] = 1
        with self.assertRaises(TypeError):
            MongoPool(config)
        config[0]['label']['dbpath'] = '.*'
        try:
            MongoPool(config)
        except TypeError:
            self.fail('MongoPool._validate_config raised Type Error while '
                      'valid config was provided')
        config[0]['label']['dbpath'] = ['db1', 'db2']
        try:
            MongoPool(config)
        except TypeError:
            self.fail('MongoPool._validate_config raised Type Error while '
                      'valid config was provided')

    def test_rasies_exception_for_invalid_read_preference(self):
        config = [{'label': {'host': '127.0.0.1', 'port': 27017,
                             'dbpath': '.*'}}]
        config[0]['label']['read_preference'] = 1
        with self.assertRaises(TypeError):
            MongoPool(config)
        config[0]['label']['read_preference'] = 'primary'
        try:
            MongoPool(config)
        except TypeError:
            self.fail('MongoPool._validate_config raised Type Error while '
                      'valid config was provided')

    def test_rasies_exception_for_invalid_replica_set(self):
        config = [{'label': {'host': '127.0.0.1', 'port': 27017,
                             'dbpath': '.*'}}]
        config[0]['label']['replicaSet'] = 1
        with self.assertRaises(TypeError):
            MongoPool(config)
        config[0]['label']['replicaSet'] = 'replicaa'
        try:
            MongoPool(config)
        except TypeError:
            self.fail('MongoPool._validate_config raised Type Error while '
                      'valid config was provided')

    @patch('mongo_pool.mongo_pool.pymongo.MongoClient')
    def test_creates_simple_client(self, mock_MongoClient):
        """
        Ensure that a MongoClient is created when replicaSet is not specified
        in the configurations and the correct database is returned
        """
        pool = MongoPool(self.config)
        mock = mock_MongoClient()
        pool.db1
        mock_MongoClient.assert_called_with(**self.call_arguments)
        mock.__getitem__.assert_called_once_with('db1')

    @patch('mongo_pool.mongo_pool.pymongo.MongoClient')
    def test_creates_replica_set_client(self, mock_MongoClient):
        """
        Ensure that a MongoClient is created when replicaSet is specified
        in the configurations and the correct database is returned.
        """
        replica_set_name = 'replicaa'
        replica_set_config = [
            {'label1': {'host': ['127.0.0.1', '127.0.1.1'],
                        'port': 27017,
                        'dbpath': 'db1',
                        'replicaSet': replica_set_name}
            }]
        call_args = deepcopy(self.call_arguments)
        call_args['replicaSet'] = replica_set_name

        pool = MongoPool(self.config)
        mock = mock_MongoClient()
        pool.db1
        mock_MongoClient.assert_called_with(**self.call_arguments)
        mock.__getitem__.assert_called_once_with('db1')

    def test_exception_is_raised_when_the_database_is_not_configured(self):
        """
        Ensure that an exception is raised while trying to access a database
        which doesn't match any pattern of the configured clusters
        """
        pool = MongoPool(self.config)
        with self.assertRaisesRegexp(Exception, "No such database .*"):
            pool.inexistentdb

    @patch('mongo_pool.mongo_pool.pymongo.MongoClient')
    def test_matches_dbpaths_correctly(self, mock_MongoClient):
        """
        Ensure that dbpaths are matched in the order specified in the
        given order and a Client connecting to the first match is returned
        """
        pool = MongoPool(self.config)
        pool.dbp
        pool.dbpattern123
        pool.dbpat

        self.call_arguments['port'] = 27018
        calls = [call(**self.call_arguments)]
        self.call_arguments['port'] = 27020
        calls.append(call(**self.call_arguments))
        self.call_arguments['port'] = 27019
        calls.append(call(**self.call_arguments))

        self.assertEqual(mock_MongoClient.call_args_list, calls,
                         "Didn't retrieve the databases in the correct order")

    @patch('mongo_pool.mongo_pool.pymongo.MongoClient')
    def test_matches_dbpaths_in_array(self, mock_MongoClient):
        """
        Ensure that the correct database is returned when specifying dbpaths
        as arrays
        """
        pool = MongoPool(self.config)
        pool.arraydb9xyz
        self.call_arguments['port'] = 27021

        mock_MongoClient.assert_called_with(**self.call_arguments)

    @patch('mongo_pool.mongo_pool.pymongo.MongoClient')
    def test_uses_set_timeout(self, mock_MongoClient):
        """
        Ensure that Clients are created with the correct timeout after
        set_timeout method is called
        """
        pool = MongoPool(self.config)
        new_timeout = 5
        pool.set_timeout(new_timeout)

        pool.db1
        self.call_arguments['socketTimeoutMS'] = new_timeout

        mock_MongoClient.assert_called_with(**self.call_arguments)

    @patch('mongo_pool.mongo_pool.pymongo.MongoClient')
    def test_recreates_clients_after_set_timeout(self, mock_MongoClient):
        """
        Ensure that all created Clients are dropped and new ones are created
        after a set_timeout call to ensure the correct timeout value is used
        """
        pool = MongoPool(self.config)
        new_timeout = 5
        pool.db1
        mock_MongoClient.reset_mock()
        pool.set_timeout(new_timeout)

        pool.db1
        self.call_arguments['socketTimeoutMS'] = new_timeout
        mock_MongoClient.assert_called_once_with(**self.call_arguments)

    def test_get_cluster_inexistent(self):
        """
        Ensure that raises an exception when it is required to
        return a connection to a cluster that is not present in the config
        """
        pool = MongoPool(self.config)
        with self.assertRaises(AttributeError):
            pool.get_cluster('_doesntexist')

    @patch('mongo_pool.mongo_pool.pymongo.MongoClient')
    def test_get_cluster_existent(self, ReconnectingConnection_mock):
        """
        Ensures that get_cluster returns the correct connection to a cluster
        """
        pool = MongoPool(self.config)
        pool.get_cluster('label1')

        ReconnectingConnection_mock.assert_called_once_with(**self.call_arguments)
        pool.db1
        # Test that is the same connection used for databases in mongoi dbpath
        ReconnectingConnection_mock.assert_called_once_with(**self.call_arguments)

    @patch('mongo_pool.mongo_pool.pymongo.MongoClient')
    def test_that_connections_are_saved(self, mock_MongoClient):
        pool = MongoPool(self.config)
        pool.dbpattern1
        mock_MongoClient.reset_mock()
        pool.dbpattern2

        self.assertFalse(mock_MongoClient.called, "New connections are "
                         "created for each database access")
