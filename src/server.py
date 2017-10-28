
from tornado.gen import coroutine

import admin as a
import handler

import common.access
import common.server
import common.sign
import common.environment
import common.discover
import common.database
import common.keyvalue

from model.builds import BuildsModel
from model.apps import BuildApplicationsModel

from common.options import options
import options as _opts


class ConfigServer(common.server.Server):
    def __init__(self):
        super(ConfigServer, self).__init__()

        db = common.database.Database(
            host=options.db_host,
            database=options.db_name,
            user=options.db_username,
            password=options.db_password)

        self.cache = common.keyvalue.KeyValueStorage(
            host=options.cache_host,
            port=options.cache_port,
            db=options.cache_db,
            max_connections=options.cache_max_connections)

        self.builds = BuildsModel(db)
        self.apps = BuildApplicationsModel(db, self.cache)

        self.env_service = common.environment.EnvironmentClient(self.cache)

    def get_models(self):
        return [self.builds, self.apps]

    def get_admin(self):
        return {
            "index": a.RootAdminController,
            "apps": a.ApplicationsController,
            "app": a.ApplicationController,
            "deploy_build": a.DeployBuildController,
            "app_settings": a.ApplicationSettingsController,
            "app_version": a.ApplicationVersionController
        }

    def get_internal_handler(self):
        return handler.InternalHandler(self)

    def get_metadata(self):
        return {
            "title": "Configuration",
            "description": "Configure your application dynamically",
            "icon": "cogs"
        }

    def get_handlers(self):
        return [
            (r"/config/(.*)/(.*)", handler.ConfigGetHandler)
        ]


if __name__ == "__main__":
    stt = common.server.init()
    common.access.AccessToken.init([common.access.public()])
    common.server.start(ConfigServer)
