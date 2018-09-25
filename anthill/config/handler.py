
from anthill.common import access, handler

from tornado.web import HTTPError

from anthill.common.access import scoped
from anthill.common.validate import validate
from anthill.common.internal import InternalError

from . model.apps import NoSuchConfigurationError, ConfigApplicationError


class ConfigGetHandler(handler.AuthenticatedHandler):
    async def get(self, app_name, app_version):

        gamespace_name = self.get_argument("gamespace")

        try:
            build = await self.application.apps.get_version_configuration(
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

    @validate(app_name="str", app_version="str", gamespace="int")
    async def get_configuration(self, app_name, app_version, gamespace):

        try:
            build = await self.application.apps.get_version_configuration(
                app_name,
                app_version,
                gamespace_id=gamespace)
        except NoSuchConfigurationError:
            raise InternalError(404, "Config was not found")
        else:
            return build.dump()
