import logging
from importlib import import_module

LOGGER = logging.getLogger(__name__)

SETTINGS = "iamksm_bot.config.settings_file"


class Settings:
    def __init__(self):
        module = import_module(SETTINGS)
        for setting in dir(module):
            if setting.isupper():
                setting_value = getattr(module, setting)
                setattr(self, setting, setting_value)


settings = Settings()
