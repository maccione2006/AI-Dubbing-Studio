import os
from pathlib import Path
import unittest
from unittest.mock import patch

from ai_dubbing_studio.config import Settings


class SettingsTests(unittest.TestCase):
    def test_settings_from_env(self):
        with patch.dict(
            os.environ,
            {
                "APP_NAME": "Test Studio",
                "ENVIRONMENT": "staging",
                "DATA_DIR": "custom_data",
                "DEBUG": "true",
                "USE_VEGAS_INTEGRATION": "1",
            },
            clear=True,
        ):
            settings = Settings.from_env()

        self.assertEqual(settings.app_name, "Test Studio")
        self.assertEqual(settings.environment, "staging")
        self.assertEqual(settings.data_dir, Path("custom_data"))
        self.assertTrue(settings.debug)
        self.assertTrue(settings.use_vegas_integration)


if __name__ == "__main__":
    unittest.main()
