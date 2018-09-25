
from . import admin
from . import handler as h
from . import options as _opts

from anthill.common import access, server, database, keyvalue
from anthill.common.options import options

from . model.builds import BuildsModel
from . model.apps import BuildApplicationsModel


class ConfigServer(server.Server):
    def __init__(self):
        super(ConfigServer, self).__init__()

        db = database.Database(
            host=options.db_host,
            database=options.db_name,
            user=options.db_username,
            password=options.db_password)

        self.cache = keyvalue.KeyValueStorage(
            host=options.cache_host,
            port=options.cache_port,
            db=options.cache_db,
            max_connections=options.cache_max_connections)

        self.builds = BuildsModel(db)
        self.apps = BuildApplicationsModel(db, self.cache)

    def get_models(self):
        return [self.builds, self.apps]

    def get_admin(self):
        return {
            "index": admin.RootAdminController,
            "apps": admin.ApplicationsController,
            "app": admin.ApplicationController,
            "deploy_build": admin.DeployBuildController,
            "app_settings": admin.ApplicationSettingsController,
            "app_version": admin.ApplicationVersionController
        }

    def get_internal_handler(self):
        return h.InternalHandler(self)

    def get_metadata(self):
        return {
            "title": "Configuration",
            "description": "Configure your application dynamically",
            "icon": "cogs"
        }

    def get_handlers(self):
        return [
            (r"/config/(.*)/(.*)", h.ConfigGetHandler)
        ]


if __name__ == "__main__":
    stt = server.init()
    access.AccessToken.init([access.public()])
    server.start(ConfigServer)
