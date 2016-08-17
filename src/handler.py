
import common.access

from tornado.web import HTTPError
from tornado.gen import coroutine

from common.access import scoped
import common.handler

from model.config import ConfigNotFound


class ConfigGetHandler(common.handler.AuthenticatedHandler):
    @coroutine
    @scoped()
    def get(self, app_id, version_name):

        gamespace_id = self.token.get(common.access.AccessToken.GAMESPACE)

        try:
            config = yield self.application.configs.get_config(
                gamespace_id,
                app_id,
                version_name,
                try_default=True)
        except ConfigNotFound:
            raise HTTPError(
                404,
                "Config was not found")
        else:
            self.write(config)
