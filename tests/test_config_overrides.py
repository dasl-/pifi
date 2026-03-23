#!/usr/bin/env python3
"""
Unit tests for Config.reload_overrides().

Verifies that config overrides from the database are correctly
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
        'screensavers': {
            'timeout': 120,
            'transitions': {'enabled': True, 'duration': 1.0, 'tick_sleep': 0.03},
            'configs': {
                'boids': {'num_boids': 15, 'tick_sleep': 0.05},
                'aurora': {'tick_sleep': 0.04},
            },
        },
    }

    def setUp(self):
        """Reset Config state before each test."""
        Config._Config__is_loaded = True
        Config._Config__config = copy.deepcopy(self.BASE_CONFIG)
        Config._Config__base_config = copy.deepcopy(self.BASE_CONFIG)
        Config._Config__applied_overrides = {}

    @patch('pifi.settingsdb.SettingsDb')
    def test_applies_overrides(self, MockSettingsDb):
        """Overrides from DB are applied to config."""
        overrides = {'screensavers': {'configs': {'boids': {'num_boids': 50}}}}
        MockSettingsDb.return_value.get.return_value = json.dumps(overrides)

        Config.reload_overrides(['screensaver_settings'])

        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 50)
        # Non-overridden keys should be preserved
        self.assertEqual(Config.get('screensavers.configs.boids.tick_sleep'), 0.05)

    @patch('pifi.settingsdb.SettingsDb')
    def test_reset_restores_defaults(self, MockSettingsDb):
        """After overrides are removed from DB, config reverts to defaults."""
        mock_db = MockSettingsDb.return_value

        # First call: apply overrides
        mock_db.get.return_value = json.dumps({'screensavers': {'configs': {'boids': {'num_boids': 50}}}})
        Config.reload_overrides(['screensaver_settings'])
        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 50)

        # Second call: overrides removed (reset)
        mock_db.get.return_value = json.dumps({})
        Config.reload_overrides(['screensaver_settings'])
        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 15)

    @patch('pifi.settingsdb.SettingsDb')
    def test_reset_restores_all_keys(self, MockSettingsDb):
        """Reset restores all keys in a section, not just overridden ones."""
        mock_db = MockSettingsDb.return_value

        # Override multiple keys
        mock_db.get.return_value = json.dumps({
            'screensavers': {'configs': {'boids': {'num_boids': 50, 'tick_sleep': 0.01}}}
        })
        Config.reload_overrides(['screensaver_settings'])
        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 50)
        self.assertEqual(Config.get('screensavers.configs.boids.tick_sleep'), 0.01)

        # Reset
        mock_db.get.return_value = None
        Config.reload_overrides(['screensaver_settings'])
        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 15)
        self.assertEqual(Config.get('screensavers.configs.boids.tick_sleep'), 0.05)

    @patch('pifi.settingsdb.SettingsDb')
    def test_independent_screensavers(self, MockSettingsDb):
        """Overriding one screensaver does not affect another."""
        mock_db = MockSettingsDb.return_value

        mock_db.get.return_value = json.dumps({'screensavers': {'configs': {'boids': {'num_boids': 50}}}})
        Config.reload_overrides(['screensaver_settings'])

        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 50)
        self.assertEqual(Config.get('screensavers.configs.aurora.tick_sleep'), 0.04)

    @patch('pifi.settingsdb.SettingsDb')
    def test_reset_one_keeps_other(self, MockSettingsDb):
        """Resetting one screensaver's overrides preserves another's."""
        mock_db = MockSettingsDb.return_value

        # Override both
        mock_db.get.return_value = json.dumps({
            'screensavers': {'configs': {
                'boids': {'num_boids': 50},
                'aurora': {'tick_sleep': 0.1},
            }}
        })
        Config.reload_overrides(['screensaver_settings'])
        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 50)
        self.assertEqual(Config.get('screensavers.configs.aurora.tick_sleep'), 0.1)

        # Reset only boids
        mock_db.get.return_value = json.dumps({
            'screensavers': {'configs': {
                'aurora': {'tick_sleep': 0.1},
            }}
        })
        Config.reload_overrides(['screensaver_settings'])
        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 15)
        self.assertEqual(Config.get('screensavers.configs.aurora.tick_sleep'), 0.1)

    @patch('pifi.settingsdb.SettingsDb')
    def test_override_new_screensaver_then_reset(self, MockSettingsDb):
        """Overriding a screensaver not in base config, then resetting, removes it."""
        mock_db = MockSettingsDb.return_value

        # Override a screensaver that has no base config
        mock_db.get.return_value = json.dumps({'screensavers': {'configs': {'newss': {'foo': 'bar'}}}})
        Config.reload_overrides(['screensaver_settings'])
        self.assertEqual(Config.get('screensavers.configs.newss.foo'), 'bar')

        # Reset
        mock_db.get.return_value = json.dumps({})
        Config.reload_overrides(['screensaver_settings'])
        self.assertIsNone(Config.get('screensavers.configs.newss.foo'))
        self.assertIsNone(Config.get('screensavers.configs.newss'))

    @patch('pifi.settingsdb.SettingsDb')
    def test_non_screensaver_config_untouched(self, MockSettingsDb):
        """Non-screensaver config sections are never modified by overrides."""
        mock_db = MockSettingsDb.return_value

        mock_db.get.return_value = json.dumps({'screensavers': {'configs': {'boids': {'num_boids': 50}}}})
        Config.reload_overrides(['screensaver_settings'])

        self.assertEqual(Config.get('leds.driver'), 'apa102')
        self.assertEqual(Config.get('leds.display_width'), 32)

    @patch('pifi.settingsdb.SettingsDb')
    def test_no_overrides_in_db(self, MockSettingsDb):
        """No overrides in DB leaves config unchanged."""
        mock_db = MockSettingsDb.return_value

        mock_db.get.return_value = None
        Config.reload_overrides(['screensaver_settings'])

        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 15)
        self.assertEqual(Config.get('screensavers.configs.aurora.tick_sleep'), 0.04)

    @patch('pifi.settingsdb.SettingsDb')
    def test_invalid_json_in_db(self, MockSettingsDb):
        """Invalid JSON in DB is handled gracefully without crashing."""
        mock_db = MockSettingsDb.return_value

        mock_db.get.return_value = 'not valid json{'
        Config.reload_overrides(['screensaver_settings'])

        # Config should remain unchanged
        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 15)

    @patch('pifi.settingsdb.SettingsDb')
    def test_non_dict_override_replaces_value(self, MockSettingsDb):
        """Non-dict override replaces the existing value."""
        mock_db = MockSettingsDb.return_value

        mock_db.get.return_value = json.dumps({'screensavers': {'configs': {'boids': 'a string'}}})
        Config.reload_overrides(['screensaver_settings'])

        self.assertEqual(Config.get('screensavers.configs.boids'), 'a string')


    @patch('pifi.settingsdb.SettingsDb')
    def test_multiple_db_keys(self, MockSettingsDb):
        """Overrides from multiple DB keys are all applied."""
        mock_db = MockSettingsDb.return_value

        def get_by_key(key):
            if key == 'key1':
                return json.dumps({'screensavers': {'configs': {'boids': {'num_boids': 50}}}})
            elif key == 'key2':
                return json.dumps({'screensavers': {'configs': {'aurora': {'tick_sleep': 0.1}}}})
            return None

        mock_db.get.side_effect = get_by_key
        Config.reload_overrides(['key1', 'key2'])

        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 50)
        self.assertEqual(Config.get('screensavers.configs.aurora.tick_sleep'), 0.1)

    @patch('pifi.settingsdb.SettingsDb')
    def test_partial_reload_preserves_other_keys(self, MockSettingsDb):
        """Reloading one DB key doesn't clobber overrides from another."""
        mock_db = MockSettingsDb.return_value

        # Load overrides from key1
        mock_db.get.return_value = json.dumps({'screensavers': {'configs': {'boids': {'num_boids': 50}}}})
        Config.reload_overrides(['key1'])
        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 50)

        # Load overrides from key2 — key1 overrides should persist
        mock_db.get.return_value = json.dumps({'screensavers': {'configs': {'aurora': {'tick_sleep': 0.1}}}})
        Config.reload_overrides(['key2'])
        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 50)
        self.assertEqual(Config.get('screensavers.configs.aurora.tick_sleep'), 0.1)

    @patch('pifi.settingsdb.SettingsDb')
    def test_partial_reload_reset_preserves_other_keys(self, MockSettingsDb):
        """Removing overrides from one DB key doesn't affect another's overrides."""
        mock_db = MockSettingsDb.return_value

        # Load overrides from both keys
        mock_db.get.return_value = json.dumps({'screensavers': {'configs': {'boids': {'num_boids': 50}}}})
        Config.reload_overrides(['key1'])
        mock_db.get.return_value = json.dumps({'screensavers': {'configs': {'aurora': {'tick_sleep': 0.1}}}})
        Config.reload_overrides(['key2'])

        # Remove key1 overrides
        mock_db.get.return_value = None
        Config.reload_overrides(['key1'])

        # key1 overrides gone, key2 overrides preserved
        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 15)
        self.assertEqual(Config.get('screensavers.configs.aurora.tick_sleep'), 0.1)

    @patch('pifi.settingsdb.SettingsDb')
    def test_skips_rebuild_when_unchanged(self, MockSettingsDb):
        """Config is not rebuilt when DB values haven't changed."""
        mock_db = MockSettingsDb.return_value

        mock_db.get.return_value = json.dumps({'screensavers': {'configs': {'boids': {'num_boids': 50}}}})
        Config.reload_overrides(['screensaver_settings'])
        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 50)

        # Mutate config directly to detect if rebuild happens
        Config._Config__config['screensavers']['configs']['boids']['num_boids'] = 999

        # Same DB value — should skip rebuild, keeping the mutation
        Config.reload_overrides(['screensaver_settings'])
        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 999)

    @patch('pifi.settingsdb.SettingsDb')
    def test_rebuilds_when_changed(self, MockSettingsDb):
        """Config is rebuilt when DB values change."""
        mock_db = MockSettingsDb.return_value

        mock_db.get.return_value = json.dumps({'screensavers': {'configs': {'boids': {'num_boids': 50}}}})
        Config.reload_overrides(['screensaver_settings'])
        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 50)

        # Mutate config directly
        Config._Config__config['screensavers']['configs']['boids']['num_boids'] = 999

        # Different DB value — should rebuild, overwriting the mutation
        mock_db.get.return_value = json.dumps({'screensavers': {'configs': {'boids': {'num_boids': 75}}}})
        Config.reload_overrides(['screensaver_settings'])
        self.assertEqual(Config.get('screensavers.configs.boids.num_boids'), 75)

    @patch('pifi.settingsdb.SettingsDb')
    def test_override_timeout_and_transitions(self, MockSettingsDb):
        """DB overrides can set timeout and transition settings."""
        mock_db = MockSettingsDb.return_value

        mock_db.get.return_value = json.dumps({
            'screensavers': {'timeout': 30, 'transitions': {'enabled': False}}
        })
        Config.reload_overrides(['screensaver_settings'])

        self.assertEqual(Config.get('screensavers.timeout'), 30)
        self.assertFalse(Config.get('screensavers.transitions.enabled'))
        # Non-overridden transition keys preserved
        self.assertEqual(Config.get('screensavers.transitions.duration'), 1.0)


if __name__ == '__main__':
    unittest.main()
