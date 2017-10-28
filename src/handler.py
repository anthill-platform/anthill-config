
import common.access

from tornado.web import HTTPError
from tornado.gen import coroutine, Return

from common.access import scoped
from common.validate import validate
from common.internal import InternalError

import common.handler

from model.apps import NoSuchConfigurationError, ConfigApplicationError


class ConfigGetHandler(common.handler.AuthenticatedHandler):
    @coroutine
    def get(self, app_name, app_version):

        gamespace_name = self.get_argument("gamespace")

        try:
            build = yield self.application.apps.get_version_configuration(
                app_name,
                app_version,
                gamespace_name=gamespace_name)
        except NoSuchConfigurationError:
            raise HTTPError(404, "Config was not found")
        else:
            self.dumps(build.dump())


class InternalHandler(object):
    def __init__(self, application):
        self.application = application

    @coroutine
    @validate(app_name="str", app_version="str", gamespace="int")
    def get_configuration(self, app_name, app_version, gamespace):

        try:
            build = yield self.application.apps.get_version_configuration(
                app_name,
                app_version,
                gamespace_id=gamespace)
        except NoSuchConfigurationError:
            raise InternalError(404, "Config was not found")
        else:
            raise Return(build.dump())
