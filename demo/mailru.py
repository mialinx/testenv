from testenv import mock, server

import json
import textwrap

from werkzeug.wrappers import Response, Request
from werkzeug.utils import parse_cookie


USERS = { v: i + 1 for i, v in enumerate([
    'gmr_social0@mail.ru',
    'gmr_social1@mail.ru',
    'gmr_social2@mail.ru',
    'gmr_social3@mail.ru',
    'gmr_social4@mail.ru',
    'gmr_social5@mail.ru',
]) }


class SWA(mock.HttpMock):

    def application(self, environ, start_response):
        request = Request(environ)
        cookies = parse_cookie(request.headers.get('Cookies', ''))
        mpop = cookies.get('Mpop', '').split(':')
        email = len(mpop) and mpop[-1] or None
        if email and email in USERS:
            uid = USERS[email]
            data = {
                'Status': 'Ok',
                'Email': email,
                'UserId': uid,
                'ProfileFields': {
                    'FirstName': 'User',
                    'LastName':  '#' + str(uid),
                    'NickName':  'User#' + str(uid),
                }
            }
        else:
            data = { 'Status': 'NoAuth' }
        return Response(json.dumps(data), mimetype='application/json')(environ, start_response)


class Souz(mock.HttpMock):

    def application(self, environ, start_response):
        request = Request(environ)
        cookies = parse_cookie(request.headers.get('Cookies', ''))
        emails = request.args.get('mru_logins','').split(',')
        resp = '''
            <?xml version="1.0" encoding='utf-8'?>
            <anketa>
            <mru_logins>
        '''
        for email in emails:
            if email and email in USERS:
                uid = USERS[email]
                resp += '''
                <mru_login value="{email}">
                    <field name="mru_id" value="{uid}" />
                    <field name="first_name" value="{first_name}" />
                    <field name="last_name" value="{last_name}" />
                    <field name="nick_name" value="{nick_name}" />
                </mru_login>
                '''.format(
                    uid=uid, email=email,
                    first_name='User',
                    last_name='#'+str(uid),
                    nick_name='User#'+str(uid)
                )
        resp += '''
            </mru_logins>
            </anketa>
        '''
        resp = textwrap.dedent(resp).strip()
        return Response(resp, mimetype='text/xml')(environ, start_response)



#class Sociald(server.Server):
#
#    default_config = {}
#    command = '{sociald_bin} --config={configfile} --instance_config={configfile} --interactive'
#
#    def init(self, **kwargs):
#        super(Sociald, self).init(**kwargs)
#        assert 'config' in kwargs and type(kwargs['config']) == dict,
#            "config section missed"
#        assert 'command_tpl' in kwargs, "command_tpl is missed"
#        self.config = utils.merge_config(self.default_config, kwargs['config'])
#        self.configfile = os.path.join(self.basedir, 'sociald.conf')
#        self.command = self.command.format(**(self.__dict__))
#
#    def prepare(self):
#        super(Sociald, self).prepare()
#        utils.write_ini(self.configfile, self.config)
#
#
#class WSD(server.Server):
#    pass
