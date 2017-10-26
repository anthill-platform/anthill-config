
from tornado.gen import coroutine, Return
from common.database import DatabaseError
from common.model import Model
from common.validate import validate


class ConfigBuildError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return str(self.code) + ": " + str(self.message)


class NoSuchBuildError(Exception):
    pass


class ConfigBuildAdapter(object):
    def __init__(self, data):
        self.build_id = str(data.get("build_id"))
        self.url = data.get("build_url")
        self.application_name = data.get("application_name")
        self.date = data.get("build_date")
        self.comment = data.get("build_comment")
        self.author = data.get("build_author")


class BuildsModel(Model):
    def __init__(self, db):
        self.db = db

    def get_setup_db(self):
        return self.db

    def get_setup_tables(self):
        return ["config_builds"]

    @coroutine
    @validate(gamespace_id="int", application_name="str_name", build_comment="str", build_author="int")
    def create_build(self, gamespace_id, application_name, build_comment, build_author):
        try:
            build_id = yield self.db.insert(
                """
                INSERT INTO `config_builds`
                (`gamespace_id`, `application_name`, `build_comment`, `build_author`) 
                VALUES (%s, %s, %s, %s);
                """, gamespace_id, application_name, build_comment, build_author)
        except DatabaseError as e:
            raise ConfigBuildError(500, e.args[1])

        raise Return(build_id)

    @coroutine
    @validate(gamespace_id="int", build_id="int", application_name="str_name", build_url="str")
    def update_build_url(self, gamespace_id, build_id, application_name, build_url):
        try:
            updated = yield self.db.execute(
                """
                UPDATE `config_builds`
                SET `build_url`=%s
                WHERE `gamespace_id`=%s AND `application_name`=%s AND `build_id`=%s
                LIMIT 1;
                """, build_url, gamespace_id, application_name, build_id)
        except DatabaseError as e:
            raise ConfigBuildError(500, e.args[1])

        raise Return(bool(updated))

    @coroutine
    @validate(gamespace_id="int", build_id="int")
    def get_build(self, gamespace_id, build_id):
        try:
            build = yield self.db.get(
                """
                SELECT * 
                FROM `config_builds`
                WHERE `gamespace_id`=%s AND `build_id`=%s
                LIMIT 1;
                """, gamespace_id, build_id)
        except DatabaseError as e:
            raise ConfigBuildError(500, e.args[1])

        if not build:
            raise NoSuchBuildError()

        raise Return(ConfigBuildAdapter(build))

    @coroutine
    @validate(gamespace_id="int", build_id="int")
    def delete_build(self, gamespace_id, build_id):
        try:
            deleted = yield self.db.execute(
                """
                DELETE 
                FROM `config_builds`
                WHERE `gamespace_id`=%s AND `build_id`=%s
                LIMIT 1;
                """, gamespace_id, build_id)
        except DatabaseError as e:
            raise ConfigBuildError(500, e.args[1])

        raise Return(bool(deleted))

    @coroutine
    @validate(gamespace_id="int", application_name="str_name", limit="int", offset="int")
    def list_builds(self, gamespace_id, application_name, limit=20, offset=0):
        try:
            builds = yield self.db.query(
                """
                SELECT * 
                FROM `config_builds`
                WHERE `gamespace_id`=%s AND `application_name`=%s AND `build_url` IS NOT NULL
                ORDER BY `build_id` DESC
                LIMIT %s, %s;
                """, gamespace_id, application_name, offset, limit)
        except DatabaseError as e:
            raise ConfigBuildError(500, e.args[1])

        raise Return(map(ConfigBuildAdapter, builds))

    @coroutine
    @validate(gamespace_id="int", application_name="str_name", limit="int", offset="int")
    def list_builds_pages(self, gamespace_id, application_name, limit=20, offset=0):
        try:
            with (yield self.db.acquire()) as db:
                builds = yield db.query(
                    """
                    SELECT SQL_CALC_FOUND_ROWS * 
                    FROM `config_builds`
                    WHERE `gamespace_id`=%s AND `application_name`=%s AND `build_url` IS NOT NULL
                    ORDER BY `build_id` DESC
                    LIMIT %s, %s;
                    """, gamespace_id, application_name, offset, limit)

                count_result = yield db.get(
                    """
                        SELECT FOUND_ROWS() AS count;
                    """)
                count_result = count_result["count"]

        except DatabaseError as e:
            raise ConfigBuildError(500, e.args[1])

        raise Return((count_result, map(ConfigBuildAdapter, builds)))
