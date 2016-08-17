
import ujson

from tornado.gen import coroutine, Return
from common.database import DatabaseError
from common.model import Model

from config import DEFAULT


class SchemeAdapter(object):
    def __init__(self, data):
        self.scheme_id = data.get("scheme_id")
        self.app_id = data.get("application_name")
        self.app_version = data.get("application_version")
        self.payload = data.get("payload")


class SchemeNotFound(Exception):
    pass


class SchemeError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class SchemesModel(Model):

    def __init__(self, db):
        self.db = db

    def get_setup_db(self):
        return self.db

    @coroutine
    def setup_table_schemes(self):
        pass

    def get_setup_tables(self):
        return ["schemes"]

    @coroutine
    def delete_scheme(self, gamespace_id, application_name, application_version):
        try:
            result = yield self.db.execute(
                """
                    DELETE FROM `schemes`
                    WHERE `application_name`=%s AND `application_version`=%s AND `gamespace_id`=%s;
                """, application_name, application_version, gamespace_id)
        except DatabaseError as e:
            raise SchemeError("Failed to delete configuration: " + e.args[1])

        raise Return(result)

    @coroutine
    def get_scheme(self, gamespace_id, application_name, application_version, try_default=False):
        try:
            scheme = yield self.db.get(
                """
                    SELECT `payload`
                    FROM `schemes`
                    WHERE `application_name`=%s AND `application_version`=%s AND `gamespace_id`=%s;
                """, application_name, application_version, gamespace_id)
        except DatabaseError as e:
            raise SchemeError("Failed to get configuration: " + e.args[1])

        if scheme is None:
            if try_default and application_version != DEFAULT:
                config = yield self.get_scheme(gamespace_id, application_name, DEFAULT, try_default=False)
                raise Return(config)
            else:
                raise SchemeNotFound()

        raise Return(scheme["payload"])

    @coroutine
    def set_scheme(self, gamespace_id, application_name, application_version, content):
        try:
            yield self.get_scheme(
                gamespace_id,
                application_name,
                application_version)

        except SchemeNotFound:

            try:
                yield self.db.insert(
                    """
                        INSERT INTO `schemes`
                        (`gamespace_id`, `application_name`, `application_version`, `payload`)
                        VALUES (%s, %s, %s, %s);
                    """, gamespace_id, application_name, application_version, ujson.dumps(content))
            except DatabaseError as e:
                raise SchemeError("Failed to create configuration: " + e.args[1])

        else:
            try:
                yield self.db.execute(
                    """
                        UPDATE `schemes`
                        SET `payload`=%s
                        WHERE `application_name`=%s AND `application_version`=%s AND `gamespace_id`=%s;
                    """, ujson.dumps(content), application_name, application_version, gamespace_id)

            except DatabaseError as e:
                raise SchemeError("Failed to update configuration: " + e.args[1])
