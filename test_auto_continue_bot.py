import sys
import os
import json
import threading
import time
from unittest.mock import MagicMock, patch, mock_open, Mock

# Mock pyautogui
mock_pyautogui = MagicMock()
class MockImageNotFoundException(Exception): pass
mock_pyautogui.ImageNotFoundException = MockImageNotFoundException
sys.modules['pyautogui'] = mock_pyautogui

# Mock pynput
mock_pynput = MagicMock()
mock_keyboard = MagicMock()
mock_key = MagicMock()
mock_keyboard.Key = MagicMock()
mock_keyboard.Key.f8 = MagicMock()
mock_keyboard.Key.f9 = MagicMock()
mock_keyboard.Listener = MagicMock()
mock_pynput.keyboard = mock_keyboard
sys.modules['pynput'] = mock_pynput
sys.modules['pynput.keyboard'] = mock_keyboard

# Mock pystray and PIL
mock_pystray = MagicMock()
mock_pil = MagicMock()
mock_image = MagicMock()
mock_image_draw = MagicMock()
mock_pil.Image = MagicMock()
mock_pil.ImageDraw = MagicMock()
mock_pil.ImageDraw.Draw = MagicMock()
mock_pil.UnidentifiedImageError = Exception
sys.modules['pystray'] = mock_pystray
sys.modules['PIL'] = mock_pil
sys.modules['PIL.Image'] = mock_pil.Image
sys.modules['PIL.ImageDraw'] = mock_pil.ImageDraw

# Mock plyer
mock_plyer = MagicMock()
mock_notification = MagicMock()
mock_plyer.notification = mock_notification
sys.modules['plyer'] = mock_plyer

# Mock winreg
mock_winreg = MagicMock()
sys.modules['winreg'] = mock_winreg

import unittest
import argparse

# Add current directory to path so we can import auto_continue_bot
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import auto_continue_bot

class TestAutoContinueBot(unittest.TestCase):

    def setUp(self):
        self.args = argparse.Namespace(
            text="Test Continue",
            cooldown=15.0,
            offset_x=-10,
            offset_y=-10,
            image="microphone_icon.png",
            dry_run=False,
            no_polite=True,
            calibrate=False,
            notify=True,
            once=False,
            background=False
        )
        # Reset global state
        auto_continue_bot.bot_paused = False
        auto_continue_bot.bot_running = True
        auto_continue_bot.last_known_mic_pos = None
        auto_continue_bot.tray_icon = MagicMock()
        
        # Reset mocks
        mock_pyautogui.reset_mock()
        mock_pyautogui.position.side_effect = None
        mock_pyautogui.position.return_value = (100, 100)
        mock_pyautogui.locateCenterOnScreen.side_effect = None
        mock_notification.reset_mock()
        
        mock_winreg.reset_mock()
        mock_winreg.OpenKey.side_effect = None
        mock_winreg.OpenKey.return_value = MagicMock()
        mock_winreg.QueryValueEx.return_value = ("command", 1)
        
        auto_continue_bot.WIN_REG_AVAILABLE = True
        # Ensure winreg is available in module namespace for tests
        auto_continue_bot.winreg = mock_winreg

    def test_resource_path_normal(self):
        with patch('os.path.abspath', return_value='/test'):
            with patch('os.path.join') as mock_join:
                mock_join.return_value = '/test/test.png'
                result = auto_continue_bot.resource_path("test.png")
                self.assertEqual(result, '/test/test.png')
    
    def test_resource_path_pyinstaller(self):
        # Mock sys._MEIPASS by setting it directly
        original_meipass = getattr(sys, '_MEIPASS', None)
        sys._MEIPASS = '/pyinstaller/path'
        try:
            with patch('os.path.join') as mock_join:
                mock_join.return_value = '/pyinstaller/path/test.png'
                result = auto_continue_bot.resource_path("test.png")
                self.assertEqual(result, '/pyinstaller/path/test.png')
        finally:
            if original_meipass is not None:
                sys._MEIPASS = original_meipass
            elif hasattr(sys, '_MEIPASS'):
                delattr(sys, '_MEIPASS')

    def test_is_run_on_startup_when_not_available(self):
        auto_continue_bot.WIN_REG_AVAILABLE = False
        self.assertFalse(auto_continue_bot.is_run_on_startup())

    def test_is_run_on_startup_when_enabled(self):
        auto_continue_bot.WIN_REG_AVAILABLE = True
        # Ensure winreg is available in the module namespace
        auto_continue_bot.winreg = mock_winreg
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = ("command", 1)
        
        result = auto_continue_bot.is_run_on_startup()
        self.assertTrue(result)
        mock_winreg.OpenKey.assert_called_once()
        mock_winreg.CloseKey.assert_called_once_with(mock_key)

    def test_is_run_on_startup_when_disabled(self):
        auto_continue_bot.WIN_REG_AVAILABLE = True
        # Ensure winreg is available in the module namespace
        auto_continue_bot.winreg = mock_winreg
        mock_winreg.OpenKey.side_effect = OSError("Not found")
        
        result = auto_continue_bot.is_run_on_startup()
        self.assertFalse(result)

    def test_toggle_run_on_startup_non_windows(self):
        auto_continue_bot.WIN_REG_AVAILABLE = False
        with patch('auto_continue_bot.logging') as mock_logging:
            auto_continue_bot.toggle_run_on_startup()
            mock_logging.warning.assert_called_once()

    def test_toggle_run_on_startup_enable(self):
        auto_continue_bot.WIN_REG_AVAILABLE = True
        # Ensure winreg is available in the module namespace
        auto_continue_bot.winreg = mock_winreg
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.QueryValueEx.side_effect = OSError("Not found")  # Not enabled
        
        # Mock sys.frozen attribute
        original_frozen = getattr(sys, 'frozen', False)
        sys.frozen = False
        try:
            with patch('sys.executable', '/usr/bin/python'):
                with patch('auto_continue_bot.__file__', '/path/to/bot.py'):
                    with patch('os.path.abspath', return_value='/path/to/bot.py'):
                        auto_continue_bot.toggle_run_on_startup()
                        mock_winreg.SetValueEx.assert_called_once()
        finally:
            if hasattr(sys, 'frozen'):
                sys.frozen = original_frozen

    def test_toggle_run_on_startup_disable(self):
        auto_continue_bot.WIN_REG_AVAILABLE = True
        # Ensure winreg is available in the module namespace
        auto_continue_bot.winreg = mock_winreg
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = ("command", 1)  # Enabled
        
        auto_continue_bot.toggle_run_on_startup()
        mock_winreg.DeleteValue.assert_called_once()

    def test_create_tray_icon_image_with_custom_icon(self):
        with patch('os.path.exists', return_value=True):
            with patch('auto_continue_bot.resource_path', return_value='icon.png'):
                mock_img = MagicMock()
                mock_pil.Image.open.return_value = mock_img
                result = auto_continue_bot.create_tray_icon_image(True)
                self.assertEqual(result, mock_img)

    def test_create_tray_icon_image_generated(self):
        with patch('os.path.exists', return_value=False):
            with patch('auto_continue_bot.resource_path', return_value='icon.png'):
                mock_new_img = MagicMock()
                mock_draw = MagicMock()
                mock_pil.Image.new.return_value = mock_new_img
                mock_pil.ImageDraw.Draw.return_value = mock_draw
                
                result = auto_continue_bot.create_tray_icon_image(True)
                mock_pil.Image.new.assert_called_once()
                mock_pil.ImageDraw.Draw.assert_called_once()

    def test_update_tray_icon(self):
        mock_icon = MagicMock()
        auto_continue_bot.tray_icon = mock_icon
        auto_continue_bot.bot_paused = True
        
        with patch('auto_continue_bot.create_tray_icon_image') as mock_create:
            mock_img = MagicMock()
            mock_create.return_value = mock_img
            auto_continue_bot.update_tray_icon()
            self.assertEqual(mock_icon.icon, mock_img)

    def test_send_notification_success(self):
        auto_continue_bot.send_notification("Test", "Message")
        mock_notification.notify.assert_called_once()

    def test_send_notification_failure(self):
        mock_notification.notify.side_effect = Exception("Failed")
        with patch('auto_continue_bot.logging') as mock_logging:
            auto_continue_bot.send_notification("Test", "Message")
            mock_logging.error.assert_called_once()

    def test_toggle_pause(self):
        auto_continue_bot.bot_paused = False
        with patch('auto_continue_bot.update_tray_icon') as mock_update:
            with patch('auto_continue_bot.logging'):
                auto_continue_bot.toggle_pause()
                self.assertTrue(auto_continue_bot.bot_paused)
                mock_update.assert_called_once()

    def test_quit_app(self):
        mock_icon = MagicMock()
        auto_continue_bot.tray_icon = mock_icon
        auto_continue_bot.bot_running = True
        
        with patch('auto_continue_bot.logging'):
            auto_continue_bot.quit_app()
            self.assertFalse(auto_continue_bot.bot_running)
            mock_icon.stop.assert_called_once()

    def test_load_config_exists(self):
        config_data = {"text": "Custom text", "cooldown": 20.0}
        with patch('os.path.exists', return_value=True):
            with patch('auto_continue_bot.resource_path', return_value='config.json'):
                with patch('builtins.open', mock_open(read_data=json.dumps(config_data))):
                    result = auto_continue_bot.load_config()
                    self.assertEqual(result, config_data)

    def test_load_config_not_exists(self):
        with patch('os.path.exists', return_value=False):
            result = auto_continue_bot.load_config()
            self.assertEqual(result, {})

    def test_save_config(self):
        config_data = {"text": "Test", "cooldown": 15.0}
        with patch('auto_continue_bot.resource_path', return_value='config.json'):
            m = mock_open()
            with patch('builtins.open', m):
                with patch('auto_continue_bot.logging'):
                    with patch('json.dump') as mock_dump:
                        auto_continue_bot.save_config(config_data)
                        m.assert_called_once_with('config.json', 'w')
                        mock_dump.assert_called_once_with(config_data, m(), indent=4)

    def test_parse_arguments_defaults(self):
        with patch('auto_continue_bot.load_config', return_value={}):
            with patch('sys.argv', ['auto_continue_bot.py']):
                args = auto_continue_bot.parse_arguments()
                self.assertEqual(args.text, auto_continue_bot.DEFAULT_TEXT)
                self.assertEqual(args.cooldown, 15.0)

    def test_parse_arguments_from_config(self):
        config = {"text": "Config text", "cooldown": 25.0, "offset_x": -100}
        with patch('auto_continue_bot.load_config', return_value=config):
            with patch('sys.argv', ['auto_continue_bot.py']):
                args = auto_continue_bot.parse_arguments()
                self.assertEqual(args.text, "Config text")
                self.assertEqual(args.cooldown, 25.0)
                self.assertEqual(args.offset_x, -100)

    def test_is_user_active_moving(self):
        mock_pyautogui.position.side_effect = [(100, 100), (110, 110)]
        with patch('time.sleep'):
            result = auto_continue_bot.is_user_active(check_duration=0.1, threshold=5)
            self.assertTrue(result)

    def test_is_user_active_stationary(self):
        mock_pyautogui.position.side_effect = [(100, 100), (101, 101)]
        with patch('time.sleep'):
            result = auto_continue_bot.is_user_active(check_duration=0.1, threshold=5)
            self.assertFalse(result)

    @patch('auto_continue_bot.time')
    def test_process_cycle_paused(self, mock_time):
        auto_continue_bot.bot_paused = True
        mock_time.sleep = MagicMock()
        
        result_time, acted = auto_continue_bot.process_cycle(self.args, "mic.png", 0)
        self.assertFalse(acted)
        mock_time.sleep.assert_called_once_with(1)

    @patch('auto_continue_bot.time')
    def test_process_cycle_cooldown_not_passed(self, mock_time):
        auto_continue_bot.bot_paused = False
        mock_time.time.return_value = 10.0
        last_action_time = 20.0  # Cooldown not passed
        
        result_time, acted = auto_continue_bot.process_cycle(self.args, "mic.png", last_action_time)
        self.assertFalse(acted)

    @patch('auto_continue_bot.time')
    def test_process_cycle_image_found(self, mock_time):
        auto_continue_bot.bot_paused = False
        mock_time.time.return_value = 200.0
        mock_location = MagicMock(x=100, y=100)
        mock_pyautogui.locateCenterOnScreen.return_value = mock_location
        mock_pyautogui.position.return_value = (50, 50)
        
        result_time, acted = auto_continue_bot.process_cycle(self.args, "mic.png", 0)
        self.assertTrue(acted)
        self.assertEqual(auto_continue_bot.last_known_mic_pos, mock_location)

    @patch('auto_continue_bot.time')
    def test_process_cycle_image_not_found(self, mock_time):
        auto_continue_bot.bot_paused = False
        mock_time.time.return_value = 200.0
        mock_pyautogui.locateCenterOnScreen.return_value = None
        
        result_time, acted = auto_continue_bot.process_cycle(self.args, "mic.png", 0)
        self.assertFalse(acted)

    @patch('auto_continue_bot.time')
    def test_process_cycle_polite_mode_active(self, mock_time):
        auto_continue_bot.bot_paused = False
        self.args.no_polite = False
        mock_time.time.return_value = 200.0
        mock_location = MagicMock(x=100, y=100)
        mock_pyautogui.locateCenterOnScreen.return_value = mock_location
        
        with patch('auto_continue_bot.is_user_active', return_value=True):
            result_time, acted = auto_continue_bot.process_cycle(self.args, "mic.png", 0)
            self.assertFalse(acted)

    @patch('auto_continue_bot.time')
    def test_process_cycle_dry_run(self, mock_time):
        auto_continue_bot.bot_paused = False
        self.args.dry_run = True
        mock_time.time.return_value = 200.0
        mock_location = MagicMock(x=100, y=100)
        mock_pyautogui.locateCenterOnScreen.return_value = mock_location
        mock_pyautogui.position.return_value = (50, 50)
        
        result_time, acted = auto_continue_bot.process_cycle(self.args, "mic.png", 0)
        self.assertTrue(acted)
        mock_pyautogui.moveTo.assert_called()
        mock_pyautogui.click.assert_not_called()

    def test_validate_image_valid(self):
        with patch('os.path.exists', return_value=True):
            mock_img = MagicMock()
            # Create a proper context manager mock
            mock_context_manager = MagicMock()
            mock_context_manager.__enter__ = MagicMock(return_value=mock_img)
            mock_context_manager.__exit__ = MagicMock(return_value=None)
            with patch('auto_continue_bot.Image.open', return_value=mock_context_manager):
                result = auto_continue_bot.validate_image("valid.png")
                self.assertTrue(result)
                mock_img.verify.assert_called_once()

    def test_validate_image_missing(self):
        with patch('os.path.exists', return_value=False):
            with patch('auto_continue_bot.logging'):
                result = auto_continue_bot.validate_image("missing.png")
                self.assertFalse(result)

    def test_validate_image_invalid(self):
        with patch('os.path.exists', return_value=True):
            mock_pil.Image.open.side_effect = IOError("Bad file")
            with patch('auto_continue_bot.logging'):
                result = auto_continue_bot.validate_image("corrupt.png")
                self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
