# -*- coding: utf-8 -*-

import os
import signal
import sys
from wsgiref.simple_server import make_server

from . import server


class Mock(server.GenericServer):

    def init(self, **kwargs):
        kwargs['command'] = 'true'
        super(Mock, self).init(**kwargs)

    def start(self):
        pid = os.fork()
        if pid:
            self.pid = pid
        else:
            self.setup_signals()
            self.open_log()
            self.run()

    def run():
        raise Exception("should be implemented")

    def setup_signals(self):
        self.runner.reset_signals()

        def handle(signal, frame):
            sys.exit(0)
        signal.signal(signal.SIGTERM, handle)

    def open_log(self):
        if self.stdout is not None:
            self.stdout = open(self.basepath(self.stdout), 'w')
            os.dup2(self.stdout.fileno(), sys.stdout.fileno())
        if self.stderr is not None:
            self.stderr = open(self.basepath(self.stderr), 'w')
            os.dup2(self.stderr.fileno(), sys.stderr.fileno())


class HttpMock(Mock):

    application = None
    ip = ''
    port = None

    def init(self, **kwargs):
        super(HttpMock, self).init(**kwargs)
        assert self.application is not None, "application attribute should be defined"
        assert self.port is not None, "port attribute should be defined"
        self.port = int(self.port)
        self.address = (self.ip, self.port)

    def run(self):
        httpd = make_server(self.ip, self.port, self.application)
        httpd.serve_forever()
