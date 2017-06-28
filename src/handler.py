
import common.access

from tornado.web import HTTPError
from tornado.gen import coroutine, Return

from common.access import scoped
from common.validate import validate
from common.internal import InternalError

import common.handler

from model.config import ConfigNotFound


class ConfigGetHandler(common.handler.AuthenticatedHandler):
    @coroutine
    def get(self, app_name, app_version):
        try:
            config = yield self.application.configs.get_config(
                app_name,
                app_version,
                try_default=True)
        except ConfigNotFound:
            raise HTTPError(404, "Config was not found")
        else:
            self.dumps(config)


class InternalHandler(object):
    def __init__(self, application):
        self.application = application

    @coroutine
    @validate(app_name="str", app_version="str")
    def get_configuration(self, app_name, app_version):
        try:
            config = yield self.application.configs.get_config(
                app_name,
                app_version,
                try_default=True)
        except ConfigNotFound:
            raise InternalError(404, "Config was not found")

        raise Return(config)
