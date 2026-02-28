from pifi.logger import Logger
import pifi.database

"""
This differs from the json configuration (see: Config) in that these settings are modifiable at runtime.
They are stored in a DB and re-read during program execution. They may be modified from a UI. Whereas
the json configuration is written manually and require a program restart to take effect, because they are
only read at program startup.
"""
class SettingsDb:

    # game of life screensaver
    SCREENSAVER_SETTING = 'is_screensaver_enabled'

    # Which screensavers are enabled (JSON array)
    ENABLED_SCREENSAVERS = 'enabled_screensavers'

    # Flag to trigger screensaver restart (checked and cleared by queue)
    RESTART_SCREENSAVER = 'restart_screensaver'

    # Screensaver config overrides (JSON object: {screensaver_id: {key: value, ...}, ...})
    SCREENSAVER_CONFIGS = 'screensaver_configs'

    SETTING_YOUTUBE_API_KEY = 'youtube_api_key'

    # Global LED brightness (0-100 percentage)
    BRIGHTNESS = 'brightness'

    def __init__(self):
        self.__cursor = pifi.database.Database().get_cursor()
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    def construct(self):
        self.__cursor.execute("DROP TABLE IF EXISTS settings")
        self.__cursor.execute("""
            CREATE TABLE settings (
                key VARCHAR(200) PRIMARY KEY,
                value VARCHAR(200),
                create_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                update_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

    def set(self, key, value):
        self.__cursor.execute(
            ("INSERT INTO settings (key, value, update_date) VALUES(?, ?, datetime()) ON CONFLICT(key) DO " +
                "UPDATE SET value=excluded.value, update_date=excluded.update_date"),
            [key, value]
        )
        return self.__cursor.rowcount == 1

    def get(self, key, default = None):
        self.__cursor.execute(
            "SELECT value FROM settings WHERE key = ?", [key]
        )
        res = self.__cursor.fetchone()
        if res is None:
            return default
        return res['value']

    # This may return None if the row doesn't exist.
    def get_row(self, key):
        self.__cursor.execute(
            "SELECT * FROM settings WHERE key = ?", [key]
        )
        return self.__cursor.fetchone()

    def is_enabled(self, key, default = False):
        res = self.get(key, default)
        if res is True or res == '1':
            return True
        else:
            return False
