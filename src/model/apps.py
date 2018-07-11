
from tornado.gen import coroutine, Return
from common.database import DatabaseError
from common.model import Model
from common.validate import validate
from common.internal import Internal, InternalError
from common.jsonrpc import JsonRPCError
from common.login import LoginClient, LoginClientError
from common import cached

from builds import ConfigBuildAdapter

import ujson


class ConfigApplicationError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return str(self.code) + ": " + str(self.message)


class NoSuchApplicationError(Exception):
    pass


class NoSuchApplicationVersionError(Exception):
    pass


class NoSuchConfigurationError(Exception):
    pass


class ConfigApplicationVersionAdapter(object):
    def __init__(self, data):
        self.application_name = data.get("application_name")
        self.application_version = data.get("application_version")
        self.build = str(data.get("build_id"))


class ConfigApplicationAdapter(object):
    def __init__(self, data):
        self.application_name = data.get("application_name")
        self.deployment_method = data.get("deployment_method")
        self.deployment_data = data.get("deployment_data")

        d = data.get("default_build")
        self.default_build = str(d) if d else None


class BuildApplicationsModel(Model):
    def __init__(self, db, cache):
        self.db = db
        self.cache = cache
        self.internal = Internal()

    def get_setup_db(self):
        return self.db

    def get_setup_tables(self):
        return ["config_applications", "config_application_versions"]

    @coroutine
    @validate(gamespace_name="str", gamespace_id="int", application_name="str_name", application_version="str")
    def get_version_configuration(self, application_name, application_version, gamespace_name=None, gamespace_id=None):

        if gamespace_name:

            login_client = LoginClient(self.cache)

            try:
                gamespace_info = yield login_client.find_gamespace(gamespace_name)
            except LoginClientError as e:
                raise ConfigApplicationError(e.code, e.message)

            gamespace_id = gamespace_info.gamespace_id

        if not gamespace_id:
            raise ConfigApplicationError(400, "Either 'gamespace_name' or 'gamespace_id' should be defined.")

        try:
            # look for per-version configuration first
            # if failed, fallback to per-app configuration
            # if even that is failed, we have a 404 here
            build = yield self.db.get(
                """
                SELECT * 
                FROM `config_builds` AS b
                WHERE b.`gamespace_id`=%s AND b.`application_name`=%s AND b.`build_id` = COALESCE(
                    (
                        SELECT `build_id` 
                        FROM `config_application_versions` AS v
                        WHERE v.`gamespace_id` = b.`gamespace_id` AND v.`application_name` = b.`application_name`
                            AND v.`application_version`=%s
                        LIMIT 1
                    ),
                    (
                        SELECT `default_build`
                        FROM `config_applications` AS a
                        WHERE a.`gamespace_id`= b.`gamespace_id` AND a.`application_name` = b.`application_name`
                        LIMIT 1
                    )
                )
                LIMIT 1;
                """, gamespace_id, application_name, application_version)
        except DatabaseError as e:
            raise ConfigApplicationError(500, e.args[1])

        if not build:
            raise NoSuchConfigurationError()

        raise Return(ConfigBuildAdapter(build))

    @coroutine
    @validate(gamespace_id="int", application_name="str_name", deployment_method="str_name",
              deployment_data="json_dict")
    def update_application_settings(self, gamespace_id, application_name, deployment_method, deployment_data):
        try:
            yield self.db.execute(
                """
                INSERT INTO `config_applications`
                (`gamespace_id`, `application_name`, `deployment_method`, `deployment_data`) 
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY 
                UPDATE `deployment_method`=VALUES(`deployment_method`), `deployment_data`=VALUES(`deployment_data`);
                """, gamespace_id, application_name, deployment_method, ujson.dumps(deployment_data))
        except DatabaseError as e:
            raise ConfigApplicationError(500, e.args[1])

    @coroutine
    @validate(gamespace_id="int", application_name="str_name")
    def delete_application_settings(self, gamespace_id, application_name):
        try:
            deleted = yield self.db.execute(
                """
                DELETE 
                FROM `config_applications`
                WHERE `gamespace_id`=%s AND `application_name`=%s
                LIMIT 1;
                """, gamespace_id, application_name)
        except DatabaseError as e:
            raise ConfigApplicationError(500, e.args[1])

        raise Return(bool(deleted))

    @coroutine
    @validate(gamespace_id="int", application_name="str_name")
    def get_application(self, gamespace_id, application_name):
        try:
            app = yield self.db.get(
                """
                SELECT * 
                FROM `config_applications`
                WHERE `gamespace_id`=%s AND `application_name`=%s
                LIMIT 1;
                """, gamespace_id, application_name)
        except DatabaseError as e:
            raise ConfigApplicationError(500, e.args[1])

        if not app:
            raise NoSuchApplicationError()

        raise Return(ConfigApplicationAdapter(app))

    @coroutine
    @validate(gamespace_id="int", application_name="str_name", default_build="int")
    def update_default_build(self, gamespace_id, application_name, default_build):
        try:
            updated = yield self.db.execute(
                """
                UPDATE `config_applications`
                SET `default_build`=%s
                WHERE `gamespace_id`=%s AND `application_name`=%s
                LIMIT 1;
                """, default_build, gamespace_id, application_name)
        except DatabaseError as e:
            raise ConfigApplicationError(500, e.args[1])

        raise Return(bool(updated))

    @coroutine
    @validate(gamespace_id="int", application_name="str_name")
    def unset_default_build(self, gamespace_id, application_name):
        try:
            updated = yield self.db.execute(
                """
                UPDATE `config_applications`
                SET `default_build`=NULL
                WHERE `gamespace_id`=%s AND `application_name`=%s
                LIMIT 1;
                """, gamespace_id, application_name)
        except DatabaseError as e:
            raise ConfigApplicationError(500, e.args[1])

        raise Return(bool(updated))

    @coroutine
    @validate(gamespace_id="int", application_name="str_name", application_version="str", build_id="int")
    def update_application_version(self, gamespace_id, application_name, application_version, build_id):
        try:
            yield self.db.execute(
                """
                INSERT INTO `config_application_versions`
                (`gamespace_id`, `application_name`, `application_version`, `build_id`) 
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY 
                UPDATE `build_id`=VALUES(`build_id`);
                """, gamespace_id, application_name, application_version, build_id)
        except DatabaseError as e:
            raise ConfigApplicationError(500, e.args[1])

    @coroutine
    @validate(gamespace_id="int", application_name="str_name", application_version="str")
    def delete_application_version(self, gamespace_id, application_name, application_version):
        try:
            deleted = yield self.db.execute(
                """
                DELETE 
                FROM `config_application_versions`
                WHERE `gamespace_id`=%s AND `application_name`=%s AND `application_version`=%s
                LIMIT 1;
                """, gamespace_id, application_name, application_version)
        except DatabaseError as e:
            raise ConfigApplicationError(500, e.args[1])

        raise Return(bool(deleted))

    @coroutine
    @validate(gamespace_id="int", application_name="str_name", application_version="str")
    def get_application_version(self, gamespace_id, application_name, application_version):
        try:
            app = yield self.db.get(
                """
                SELECT * 
                FROM `config_application_versions`
                WHERE `gamespace_id`=%s AND `application_name`=%s AND `application_version`=%s
                LIMIT 1;
                """, gamespace_id, application_name, application_version)
        except DatabaseError as e:
            raise ConfigApplicationError(500, e.args[1])

        if not app:
            raise NoSuchApplicationVersionError()

        raise Return(ConfigApplicationVersionAdapter(app))

    @coroutine
    @validate(gamespace_id="int", application_name="str_name")
    def list_application_versions(self, gamespace_id, application_name):
        try:
            v = yield self.db.query(
                """
                SELECT * 
                FROM `config_application_versions`
                WHERE `gamespace_id`=%s AND `application_name`=%s
                ORDER BY `application_version` DESC;
                """, gamespace_id, application_name)
        except DatabaseError as e:
            raise ConfigApplicationError(500, e.args[1])

        raise Return(map(ConfigApplicationVersionAdapter, v))
