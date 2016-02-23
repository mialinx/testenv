#! -*- codign: utf-8 -*-

import argparse
import contextlib
import os.path
import pprint
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import yaml
from . import utils

"""
Main code, runner
"""

class Runner(object):

    BASEDIR_TEMP = 'TEMP'

    signals = [
        signal.SIGINT,
        signal.SIGQUIT,
        signal.SIGTERM,
    ]

    def __init__(self):
        self.args = ()       # comman line args
        self.config = {}     # parsed config
        self.environ = {}    # generated vars
        self.servers = {}    # server instances
        self.basedir = None  # dir with temporary env
        self.confdir = None  # dir with config
        self.exit_code = 0

    def parse_params(self):
        parser = argparse.ArgumentParser(description='Process some integers.')
        parser.add_argument('--config', dest='config', type=str, help='testenv config (.yml)', required=True)
        parser.add_argument('command', nargs=argparse.REMAINDER)
        args = parser.parse_args()
        args.config = os.path.abspath(args.config)
        if not os.path.isfile(args.config):
            raise Exception("not a file: " + args.config)
        self.confdir = os.path.dirname(args.config)
        self.args = args

    def read_config(self):
        with contextlib.closing(open(self.args.config, "r")) as fh:
            self.config = yaml.load(fh)
        self.config.setdefault('basedir', 'tenv')
        self.config.setdefault('basedir_cleanup', False)
        self.config.setdefault('servers', {})
        self.config.setdefault('log', None)
        assert type(self.config['servers']) == dict, "servers section should be a dict"
        for name, sconf in self.config['servers'].iteritems():
            assert 'type' in sconf, name + " should have type attribute"

    def parametrize_config(self):
        environ = self.environ
        environ['confdir'] = self.confdir
        environ['basedir'] = self.basedir
        def handle(s, trail):
            def one(match):
                groups = match.groups()
                name = groups[0]
                if name in environ:
                    return environ[name]
                if len(groups) == 1:
                    return name
                kind = groups[1]
                if kind == 'addr':
                    ip = utils.free_ip()
                    port = utils.free_port(ip)
                    environ[name] = '{0}:{1}'.format(ip, port)
                elif kind == 'port':
                    ip_name = name[:-5] + '_ip'
                    ip = environ.setdefault(ip_name, utils.free_ip())
                    environ[name] = utils.free_port(ip)
                elif kind == 'ip':
                    environ[name] = utils.free_ip()
                elif kind == 'dir':
                    environ[name] = os.path.join(self.basedir, name)
                    os.makedirs(environ[name])
                elif kind == 'sock':
                    environ[name] = os.path.join(self.basedir, name + '.sock')
                else:
                    raise ValueError("unexpected pattern {0} in {1}".format(match.group(0), '/'.join(trail)))
                return environ[name]
            s = re.sub(r'\$(\w+_(\w+))\$', one, s)
            s = re.sub(r'\$(\w+)\$', one, s)
            return s
        self.config = utils.walk(self.config, handle)
        self.environ.update(self.config.get('extra', {}))

    def stop_by_signal(self, signup, frame):
        pprint.pprint("signal handler")
        raise Exception("signaled with " + str(signup))

    def setup_signals(self):
        for s in self.signals:
            signal.signal(s, self.stop_by_signal)

    def reset_signals(self):
        for s in self.signals:
            signal.signal(s, signal.SIG_DFL)

    def open_log(self):
        self.orig_stderr = os.fdopen(os.dup(sys.stderr.fileno()))
        self.orig_stdout = os.fdopen(os.dup(sys.stdout.fileno()))
        if self.config['log'] is not None:
            log = open(self.config['log'], 'w', buffering=1)
            os.dup2(log.fileno(), sys.stderr.fileno())
            os.dup2(log.fileno(), sys.stdout.fileno())

    def create_basedir(self):
        basedir = self.config['basedir']
        if basedir == self.BASEDIR_TEMP:
            self.basedir = tempfile.mkdtemp()
        else:
            self.basedir = os.path.join(self.confdir, basedir)
            if os.path.exists(self.basedir):
                shutil.rmtree(self.basedir)
            os.makedirs(self.basedir)

    def create_servers(self):
        for name, sconf in self.config['servers'].iteritems():
            stype = sconf['type']
            if '.' not in stype:
                stype = 'testenv.contrib.' + stype
            sclass = utils.load_class(stype)
            self.servers[name] = sclass(self, name, sconf)

    def start_servers(self):
        # TODO: ordered, parallel
        for name, s in self.servers.iteritems():
            pprint.pprint('preparing ' + name)
            s.prepare()
            pprint.pprint('starting ' + name)
            s.start()
            pprint.pprint('waiting ' + name)
            s.wait_ready()
            pprint.pprint('filling ' + name)
            s.fill()

    def run_command(self):
        if len(self.args.command) > 0:
            cmd = self.args.command
        else:
            cmd = ['env']
        #self.exit_code = subprocess.call(cmd, stdout=self.orig_stdout, stderr=self.orig_stderr)
        p = subprocess.Popen(cmd, stdout=self.orig_stdout, stderr=self.orig_stderr, env=self.environ)
        p.wait()
        self.exit_code = p.returncode

    def stop_servers(self):
        for s in self.servers.itervalues():
            import time
            pprint.pprint([s.name, time.time(), s.is_running()])
            if s.is_running():
                s.stop()
                pprint.pprint([s.name, time.time()])


    def cleanup(self):
        if self.config['basedir_cleanup'] or self.config['basedir'] == self.BASEDIR_TEMP:
            shutil.rmtree(self.basedir)

    def run(self):
        assert os.name == 'posix', "testenv support only unix now"
        self.parse_params()
        sys.path.append(self.confdir)
        self.read_config()
        self.setup_signals()
        self.open_log()
        try:
            self.create_basedir()
            self.parametrize_config()
            pprint.pprint('creating servers')
            self.create_servers()
            pprint.pprint('starting servers')
            self.start_servers()
            pprint.pprint('run command')
            self.run_command()
        finally:
            pprint.pprint('stoping servers')
            self.stop_servers()
            self.cleanup()

        sys.exit(self.exit_code)

