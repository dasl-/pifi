from pifi.logger import Logger
import pifi.database

"""
This differs from the json settings in that these settings are modifiable at runtime. They are stored in a DB
and re-read during program execution. They may be modified from a UI. Whereas the json settings are written
manually and require a program restart to take effect, because they are only read at program startup.
"""
class SettingsDb:

    # game of life screensaver
    SCREENSAVER_SETTING = 'is_screensaver_enabled'

    __cursor = None
    __logger = None

    def __init__(self):
        self.__cursor = pifi.database.Database().get_cursor()
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    def construct(self):
        self.__cursor.execute("DROP TABLE IF EXISTS settings")
        self.__cursor.execute("""
            CREATE TABLE settings (
                key VARCHAR(200) PRIMARY KEY,
                value VARCHAR(200),
                create_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )

    def set(self, key, value):
        self.__cursor.execute(
            "INSERT INTO settings (key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            [key, value]
        )
        return self.__cursor.lastrowid

    def get(self, key, default = None):
        self.__cursor.execute(
            "SELECT value FROM settings WHERE key = ?", [key]
        )
        res = self.__cursor.fetchone()
        if res is None:
            return default
        return res['value']

    def isEnabled(self, key, default = False):
        res = self.get(key, default)
        if res is True or res == '1':
            return True
        else:
            return False