import logging
from pathlib import Path
from configparser import ConfigParser

class Config(object):
    def __init__(self, path=None):
        self.path = path or Path("./config.cfg")

        self.parser = ConfigParser()
        self.parser.read(self.path)
        self.reload()

    def reload(self):
        self.errlogLevel = self.parser.get(
            "nest",
            "errorlogLevel",
            fallback="info"
        )

        self.translogLevel = self.parser.get(
            "nest",
            "transactionlogLevel",
            fallback="info"
        )

        fs_auth_user = self.parser.get("nest", "FS_AUTH_USER", fallback="foo")
        fs_auth_pass = self.parser.get("nest", "FS_AUTH_PASS", fallback="bar")
        self.fastspring_auth = (fs_auth_user, fs_auth_pass)

        mc_auth_user = self.parser.get("nest", "MC_AUTH_USER", fallback="foo")
        mc_auth_token = self.parser.get("nest", "MC_AUTH_TOKEN", fallback="bar")
        self.mailchimp_auth = (mc_auth_user, mc_auth_token)

        self.postgres_connection_info = {}
        for key in ["host", "port", "user", "pass", "database"]:
            value = self.parser.get("nest:postgres", key, fallback=None)
            if key is "port":
                value = self.parser.getint("nest:postgres", key, fallback=None)
            if value:
                self.postgres_connection_info.update({key:value})

        self.redis_connection_info = {}
        for key in ["host", "port", "db"]:
            value = self.parser.get("nest:redis", key, fallback=None)
            if key is "port":
                value = self.parser.getint("nest:redis", key, fallback=None)
            if value:
                self.redis_connection_info.update({key:value})

        self.redis_node_list = []
        for section in self.parser.sections():
            node_info = {}
            if "redis" in section:
                for key in ["host", "port", "db"]:
                    value = self.parser.get(section, key, fallback=None)
                    if key is "port":
                        value = self.parser.getint(section, key, fallback=None)
                    if value:
                        node_info.update({key:value})
            if len(node_info) > 0:
                self.redis_node_list.append(node_info)
