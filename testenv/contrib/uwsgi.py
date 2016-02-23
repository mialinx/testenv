# -*- coding: utf-8 -*-

import os
import os.path
import subprocess

from .. import server, utils

class Uwsgi(server.Server):

    binary = 'uwsgi'

    default_config = {
        'threats': 2,
    }

    def init(self, **kwargs):
        assert 'config' in kwargs and type(kwargs['config']) == dict, \
            "uwsgi server requires <config> section"
        assert os.path.exists(kwargs['config']['wsgi-file']), \
            "uwsgi server requires wsgi-file"
        self.configfile = os.path.join(self.basedir, 'uwsgi.ini')
        self.pidfile = os.path.join(self.basedir, 'uwsgi.pid')
        self.config = utils.merge(
            self.default_config,
            {
                'chdir': os.path.dirname(os.path.abspath(kwargs['config']['wsgi-file'])),
            },
            kwargs['config'],
        )

    def prepare(self):
        os.makedirs(self.basedir)
        utils.write_ini(self.configfile, { 'uwsgi' : self.config })

    def start(self):
        super(Uwsgi, self).start()
        pass

    def stop(self):
        pass

