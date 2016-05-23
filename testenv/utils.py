# -*- coding: utf-8 -*-

import contextlib
import getpass
import os
import signal
import socket
import subprocess
import time

import yaml


user = getpass.getuser()

promised_ports = {}

proto_aliases = {
    'tcp': socket.SOCK_STREAM,
    'udp': socket.SOCK_DGRAM,
}


def free_port(ip, proto='tcp'):
    for port in range(64000, 32768, -1):
        if port in promised_ports:
            continue
        stype = proto_aliases[proto]
        s = socket.socket(socket.AF_INET, stype)
        try:
            s.bind((ip, port))
        except:
            continue
        else:
            promised_ports[port] = 1
            s.close()
        return str(port)


def free_ip():
    return '127.0.0.1'


def walk(node, code, trail=[]):
    if isinstance(node, dict):
        for k, v in node.iteritems():
            node[k] = walk(v, code, trail + [k])
    elif isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            node[i] = walk(v, code, trail + [str(i)])
    elif isinstance(node, basestring):
        node = code(node, trail)
    return node


def merge(*args):
    # args = ( {dict1}, {dict2}, {dict3} )
    def handle(res, node):
        assert type(node) == dict, "merge args should be a dicts"
        for k, v in node.iteritems():
            if k not in res:
                res[k] = v
            else:
                if isinstance(v, dict):
                    res[k] = merge(res[k], v)
                elif isinstance(v, (list, tuple)):
                    res[k] += v
                elif isinstance(v, (basestring, int)):
                    res[k] = v
        return res
    return reduce(handle, args, {})


def load_class(name):
    components = name.split('.')
    mod = __import__('.'.join(components[:-1]))
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def write_ini(path, ini):
    assert type(ini) == dict, "ini should be a dict"
    with contextlib.closing(open(path, "w")) as fh:
        def line(k, v):
            fh.write(str(k) + (v is None and "" or (" = " + str(v))) + "\n")
        for k, v in ini.iteritems():
            if isinstance(v, dict):
                fh.write("[" + str(k) + "]\n")
                for k, v in v.iteritems():
                    line(k, v)
            else:
                line(k, v)


def write_yaml(path, cfg):
    with contextlib.closing(open(path, "w")) as fh:
        fh.write(yaml.dump(cfg))


# process controll funcs, may be move to separate module ?

def find_binary(binary):
    if os.path.isfile(binary):
        return binary
    path = os.environ.get('PATH', os.getcwd())
    for p in path.split(':'):
        full = os.path.join(p, binary)
        if os.path.isfile(full):
            return full
    return None


def spawn_process(binary, args):
    pid = os.fork()
    if not pid:
        os.execvp(binary, args)
    else:
        return pid


def wait_for(cb, sleeptime=0.1, maxtime=5):
    sleeptotal = 0
    while (maxtime > 0 and sleeptotal <= maxtime) or (maxtime == sleeptotal == 0):
        res = cb()
        if res:
            return res
        time.sleep(sleeptime)
        sleeptotal += sleeptime
    return None


def wait_for_pid(pidfile, sleeptime=0.1, maxtime=5):
    sleeptotal = 0
    while (maxtime > 0 and sleeptotal <= maxtime) or (maxtime == sleeptotal == 0):
        try:
            with contextlib.closing(open(pidfile, "r")) as fh:
                return int(fh.readline().strip())
        except IOError:
            pass
        time.sleep(sleeptime)
        sleeptotal += sleeptime
    return None


def is_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def stop_with_signal(pid, as_group=False, is_child=False, term=signal.SIGTERM, maxtime=5, sleeptime=0.1):
    sleeptotal = 0
    kpid = as_group and -pid or pid
    while (maxtime > 0 and sleeptotal <= maxtime) or (maxtime == sleeptotal == 0):
        if is_child:
            os.waitpid(pid, os.P_NOWAIT)
        if not is_running(pid):
            return True
        os.kill(kpid, term)
        time.sleep(sleeptime)
        sleeptotal += sleeptime
    if not is_running(pid):
        return True
    os.kill(kpid, signal.SIGKILL)
    return False


def wait_for_socket(addr, maxtime=5, sleeptime=0.1, timeout=0.01):
    sleeptotal = 0
    if isinstance(addr, tuple) or isinstance(addr, list):
        family = socket.AF_INET
        addr = (addr[0], int(addr[1]))
    else:
        family = socket.AF_UNIX
    s = socket.socket(family, socket.SOCK_STREAM)
    s.settimeout(timeout)
    while (maxtime > 0 and sleeptotal <= maxtime) or (maxtime == sleeptotal == 0):
        try:
            s.connect(addr)
            s.close()
            return True
        except socket.error:
            pass
        time.sleep(sleeptime)
        sleeptotal += sleeptime
    return False


def wait_for_proc(p, name=None):
    if name is None:
        name = 'proc-' + str(p.pid)
    exitcode = p.wait()
    if exitcode != 0:
        raise subprocess.CalledProcessError(exitcode, name)
