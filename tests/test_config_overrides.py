#!/usr/bin/env python3
"""
Unit tests for Config.reload_screensaver_overrides().

Verifies that screensaver config overrides from the database are correctly
applied to and removed from the in-memory config.
"""

import copy
import json
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pifi.config import Config


class TestReloadScreensaverOverrides(unittest.TestCase):

    BASE_CONFIG = {
        'leds': {'driver': 'apa102', 'display_width': 32, 'display_height': 16},
        'boids': {'num_boids': 15, 'tick_sleep': 0.05, 'max_ticks': 3000},
        'aurora': {'tick_sleep': 0.04, 'max_ticks': 3000},
    }

    def setUp(self):
        """Reset Config state before each test."""
        Config._Config__is_loaded = True
        Config._Config__config = copy.deepcopy(self.BASE_CONFIG)
        Config._Config__base_config = copy.deepcopy(self.BASE_CONFIG)
        Config._Config__previously_overridden = set()

    @patch('pifi.settingsdb.SettingsDb')
    def test_applies_overrides(self, MockSettingsDb):
        """Overrides from DB are applied to config."""
        overrides = {'boids': {'num_boids': 50}}
        MockSettingsDb.return_value.get.return_value = json.dumps(overrides)
        MockSettingsDb.SCREENSAVER_CONFIGS = 'screensaver_configs'

        Config.reload_screensaver_overrides()

        self.assertEqual(Config.get('boids.num_boids'), 50)
        # Non-overridden keys should be preserved
        self.assertEqual(Config.get('boids.tick_sleep'), 0.05)

    @patch('pifi.settingsdb.SettingsDb')
    def test_reset_restores_defaults(self, MockSettingsDb):
        """After overrides are removed from DB, config reverts to defaults."""
        MockSettingsDb.SCREENSAVER_CONFIGS = 'screensaver_configs'
        mock_db = MockSettingsDb.return_value

        # First call: apply overrides
        mock_db.get.return_value = json.dumps({'boids': {'num_boids': 50}})
        Config.reload_screensaver_overrides()
        self.assertEqual(Config.get('boids.num_boids'), 50)

        # Second call: overrides removed (reset)
        mock_db.get.return_value = json.dumps({})
        Config.reload_screensaver_overrides()
        self.assertEqual(Config.get('boids.num_boids'), 15)

    @patch('pifi.settingsdb.SettingsDb')
    def test_reset_restores_all_keys(self, MockSettingsDb):
        """Reset restores all keys in a section, not just overridden ones."""
        MockSettingsDb.SCREENSAVER_CONFIGS = 'screensaver_configs'
        mock_db = MockSettingsDb.return_value

        # Override multiple keys
        mock_db.get.return_value = json.dumps({
            'boids': {'num_boids': 50, 'tick_sleep': 0.01, 'max_ticks': 100}
        })
        Config.reload_screensaver_overrides()
        self.assertEqual(Config.get('boids.num_boids'), 50)
        self.assertEqual(Config.get('boids.tick_sleep'), 0.01)
        self.assertEqual(Config.get('boids.max_ticks'), 100)

        # Reset
        mock_db.get.return_value = None
        Config.reload_screensaver_overrides()
        self.assertEqual(Config.get('boids.num_boids'), 15)
        self.assertEqual(Config.get('boids.tick_sleep'), 0.05)
        self.assertEqual(Config.get('boids.max_ticks'), 3000)

    @patch('pifi.settingsdb.SettingsDb')
    def test_independent_screensavers(self, MockSettingsDb):
        """Overriding one screensaver does not affect another."""
        MockSettingsDb.SCREENSAVER_CONFIGS = 'screensaver_configs'
        mock_db = MockSettingsDb.return_value

        mock_db.get.return_value = json.dumps({'boids': {'num_boids': 50}})
        Config.reload_screensaver_overrides()

        self.assertEqual(Config.get('boids.num_boids'), 50)
        self.assertEqual(Config.get('aurora.tick_sleep'), 0.04)

    @patch('pifi.settingsdb.SettingsDb')
    def test_reset_one_keeps_other(self, MockSettingsDb):
        """Resetting one screensaver's overrides preserves another's."""
        MockSettingsDb.SCREENSAVER_CONFIGS = 'screensaver_configs'
        mock_db = MockSettingsDb.return_value

        # Override both
        mock_db.get.return_value = json.dumps({
            'boids': {'num_boids': 50},
            'aurora': {'tick_sleep': 0.1},
        })
        Config.reload_screensaver_overrides()
        self.assertEqual(Config.get('boids.num_boids'), 50)
        self.assertEqual(Config.get('aurora.tick_sleep'), 0.1)

        # Reset only boids
        mock_db.get.return_value = json.dumps({
            'aurora': {'tick_sleep': 0.1},
        })
        Config.reload_screensaver_overrides()
        self.assertEqual(Config.get('boids.num_boids'), 15)
        self.assertEqual(Config.get('aurora.tick_sleep'), 0.1)

    @patch('pifi.settingsdb.SettingsDb')
    def test_override_new_screensaver_then_reset(self, MockSettingsDb):
        """Overriding a screensaver not in base config, then resetting, removes it."""
        MockSettingsDb.SCREENSAVER_CONFIGS = 'screensaver_configs'
        mock_db = MockSettingsDb.return_value

        # Override a screensaver that has no base config
        mock_db.get.return_value = json.dumps({'newss': {'foo': 'bar'}})
        Config.reload_screensaver_overrides()
        self.assertEqual(Config.get('newss.foo'), 'bar')

        # Reset
        mock_db.get.return_value = json.dumps({})
        Config.reload_screensaver_overrides()
        self.assertIsNone(Config.get('newss.foo'))
        self.assertIsNone(Config.get('newss'))

    @patch('pifi.settingsdb.SettingsDb')
    def test_non_screensaver_config_untouched(self, MockSettingsDb):
        """Non-screensaver config sections are never modified by overrides."""
        MockSettingsDb.SCREENSAVER_CONFIGS = 'screensaver_configs'
        mock_db = MockSettingsDb.return_value

        mock_db.get.return_value = json.dumps({'boids': {'num_boids': 50}})
        Config.reload_screensaver_overrides()

        self.assertEqual(Config.get('leds.driver'), 'apa102')
        self.assertEqual(Config.get('leds.display_width'), 32)

    @patch('pifi.settingsdb.SettingsDb')
    def test_no_overrides_in_db(self, MockSettingsDb):
        """No overrides in DB leaves config unchanged."""
        MockSettingsDb.SCREENSAVER_CONFIGS = 'screensaver_configs'
        mock_db = MockSettingsDb.return_value

        mock_db.get.return_value = None
        Config.reload_screensaver_overrides()

        self.assertEqual(Config.get('boids.num_boids'), 15)
        self.assertEqual(Config.get('aurora.tick_sleep'), 0.04)

    @patch('pifi.settingsdb.SettingsDb')
    def test_invalid_json_in_db(self, MockSettingsDb):
        """Invalid JSON in DB is handled gracefully without crashing."""
        MockSettingsDb.SCREENSAVER_CONFIGS = 'screensaver_configs'
        mock_db = MockSettingsDb.return_value

        mock_db.get.return_value = 'not valid json{'
        Config.reload_screensaver_overrides()

        # Config should remain unchanged
        self.assertEqual(Config.get('boids.num_boids'), 15)

    @patch('pifi.settingsdb.SettingsDb')
    def test_non_dict_override_ignored(self, MockSettingsDb):
        """Non-dict override values are ignored."""
        MockSettingsDb.SCREENSAVER_CONFIGS = 'screensaver_configs'
        mock_db = MockSettingsDb.return_value

        mock_db.get.return_value = json.dumps({'boids': 'not a dict'})
        Config.reload_screensaver_overrides()

        self.assertEqual(Config.get('boids.num_boids'), 15)


if __name__ == '__main__':
    unittest.main()
