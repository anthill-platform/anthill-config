
import ujson

from tornado.gen import coroutine, Return
from common.database import DatabaseError
from common.model import Model


DEFAULT = "def"


class ConfigAdapter(object):
    def __init__(self, data):
        self.config_id = data.get("configuration_id")
        self.app_id = data.get("application_name")
        self.app_version = data.get("application_version")


class ConfigNotFound(Exception):
    pass


class DefaultConfigurationApplied(Exception):
    def __init__(self, config):
        self.config = config


class ConfigError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class ConfigsModel(Model):
    def __init__(self, db):
        self.db = db

    def get_setup_db(self):
        return self.db

    @coroutine
    def setup_table_configurations(self):
        pass

    def get_setup_tables(self):
        return ["configurations"]

    @coroutine
    def delete_config(self, gamespace_id, application_name, application_version):

        try:
            result = yield self.db.execute(
                """
                    DELETE FROM `configurations`
                    WHERE `application_name`=%s AND `application_version`=%s AND `gamespace_id`=%s;
                """, application_name, application_version, gamespace_id)
        except DatabaseError as e:
            raise ConfigError("Failed to delete configuration: " + e.args[1])

        raise Return(result)

    @coroutine
    def get_config(self, gamespace_id, application_name, application_version, try_default=False):

        try:
            config = yield self.db.get(
                """
                    SELECT `payload`
                    FROM `configurations`
                    WHERE `application_name`=%s AND `application_version`=%s AND `gamespace_id`=%s;
                """, application_name, application_version, gamespace_id)
        except DatabaseError as e:
            raise ConfigError("Failed to get configuration: " + e.args[1])

        if config is None:
            if try_default and application_version != DEFAULT:
                config = yield self.get_config(gamespace_id, application_name, DEFAULT, try_default=False)
                raise Return(config)
            else:
                raise ConfigNotFound()

        raise Return(config["payload"])

    @coroutine
    def set_config(self, gamespace_id, application_name, application_version, content):

        try:
            yield self.get_config(
                gamespace_id,
                application_name,
                application_version)

        except ConfigNotFound:

            try:
                yield self.db.insert(
                    """
                        INSERT INTO `configurations`
                        (`gamespace_id`, `application_name`, `application_version`, `payload`)
                        VALUES (%s, %s, %s, %s);
                    """, gamespace_id, application_name, application_version, ujson.dumps(content))
            except DatabaseError as e:
                raise ConfigError("Failed to create configuration: " + e.args[1])

        else:
            try:
                yield self.db.execute(
                    """
                        UPDATE `configurations`
                        SET `payload`=%s
                        WHERE `application_name`=%s AND `application_version`=%s AND `gamespace_id`=%s;
                    """, ujson.dumps(content), application_name, application_version, gamespace_id)

            except DatabaseError as e:
                raise ConfigError("Failed to update configuration: " + e.args[1])
