# -*- coding: utf-8 -*-

from .. import server, utils


class Memcached(server.Server):

    binary = 'memcached'

    def init(self, **kwargs):
        self.binary = utils.find_binary(kwargs.get('memcached_bin', self.binary))
        assert 'ip' in kwargs, "memcached servers requires <ip> option"
        self.ip = kwargs['ip']
        assert 'port' in kwargs, "memcached server require <port> option"
        self.port = kwargs['port']
        self.command = [ self.binary, '-l', self.ip, '-p', self.port ]
