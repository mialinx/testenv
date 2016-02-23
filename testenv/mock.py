# -*- coding: utf-8 -*-

import os
import sys
import signal

from . import server
from wsgiref.simple_server import make_server

class HttpMock(server.Server):

    application = None
    ip = ''
    port = None

    def init(self, **kwargs):
        kwargs['command'] = 'true'
        super(HttpMock, self).init(**kwargs)
        assert self.application is not None, "application attribute should be defined"
        assert self.port is not None, "port attribute should be defined"
        self.port = int(self.port)
        self.address = (self.ip, self.port)

    def start(self):
        pid = os.fork()
        if pid:
            self.pid = pid
        else:
            self.setup_signals()
            httpd = make_server(self.ip, self.port, self.application)
            httpd.serve_forever()

    def setup_signals(self):
        self.runner.reset_signals()
        def handle(signal, frame):
            sys.exit(0)
        signal.signal(signal.SIGTERM, handle)

