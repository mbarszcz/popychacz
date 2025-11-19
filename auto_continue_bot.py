import time
import os
import sys
import argparse
import logging
import json
import threading
from logging.handlers import RotatingFileHandler

import pyautogui
from pynput import keyboard
import pystray
from PIL import Image, ImageDraw, UnidentifiedImageError
from plyer import notification

# Import winreg on Windows
if sys.platform == 'win32':
    import winreg
    WIN_REG_AVAILABLE = True
else:
    WIN_REG_AVAILABLE = False

# Configure logging with Rotation
LOG_FILE = "bot.log"
# Max 1MB per file, keep 3 backups
handler = RotatingFileHandler(LOG_FILE, maxBytes=1024*1024, backupCount=3, encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        handler
    ]
)

DEFAULT_TEXT = """Continue with the plan. Develop the rest of the requirements. Make improvements.  Make sure everything works.  Write tests. Run the tests. If you have confirmed there is absolutely nothing left to do, execute 'sleep 60000' command in the shell (not in the background) and wait for it. Only if you are certain. Otherwise, wait for further instructions."""
CONFIG_FILE = "config.json"
APP_NAME = "Cursor Auto-Continue Bot"
REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

# Global state for hotkeys and tray
bot_paused = True
bot_running = True
tray_icon = None
last_known_mic_pos = None

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def is_run_on_startup():
    """Check if the app is set to run on startup via Registry."""
    if not WIN_REG_AVAILABLE:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False

def toggle_run_on_startup(icon=None, item=None):
    """Toggle the Run on Startup registry key."""
    if not WIN_REG_AVAILABLE:
        logging.warning("Startup toggling only supported on Windows.")
        return

    currently_enabled = is_run_on_startup()
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE | winreg.KEY_WRITE)
        
        if currently_enabled:
            # Disable it
            try:
                winreg.DeleteValue(key, APP_NAME)
                logging.info("Startup: Disabled.")
                if icon:
                    send_notification("Cursor Auto-Continue", "Removed from startup.")
            except OSError as e:
                logging.error(f"Error removing registry key: {e}")
        else:
            # Enable it
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                cmd = f'"{exe_path}" --background'
            else:
                python_exe = sys.executable.replace("python.exe", "pythonw.exe")
                script_path = os.path.abspath(__file__)
                cmd = f'"{python_exe}" "{script_path}" --background'
            
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            logging.info(f"Startup: Enabled with command: {cmd}")
            if icon:
                send_notification("Cursor Auto-Continue", "Added to startup.")
        
        winreg.CloseKey(key)
        
    except Exception as e:
        logging.error(f"Registry error: {e}")

def create_tray_icon_image(paused):
    # Try to load a custom icon if it exists
    custom_icon_path = resource_path("icon.png")
    if os.path.exists(custom_icon_path):
        try:
            image = Image.open(custom_icon_path)
            return image
        except Exception:
            pass

    # Generate a simple icon
    width = 64
    height = 64
    color = 'red' if paused else 'green'
    
    image = Image.new('RGB', (width, height), (255, 255, 255))
    dc = ImageDraw.Draw(image)
    
    # Draw a circle
    dc.ellipse((8, 8, 56, 56), fill=color)
    
    return image

def update_tray_icon():
    global tray_icon, bot_paused
    if tray_icon:
        tray_icon.icon = create_tray_icon_image(bot_paused)

def send_notification(title, message):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name='Cursor Auto-Continue',
            timeout=3
        )
    except Exception as e:
        logging.error(f"Failed to send notification: {e}")

def toggle_pause(icon=None, item=None):
    global bot_paused
    bot_paused = not bot_paused
    state = "PAUSED" if bot_paused else "RESUMED"
    logging.info(f">>> Bot {state} by user <<<")
    update_tray_icon()

def quit_app(icon=None, item=None):
    global bot_running, tray_icon
    logging.info(">>> Quit signal received. Stopping... <<<")
    bot_running = False
    if tray_icon:
        tray_icon.stop()

def on_press(key):
    global bot_paused, bot_running
    try:
        if key == keyboard.Key.f8:
            toggle_pause()
        elif key == keyboard.Key.f9:
            quit_app()
            return False # Stop listener
    except AttributeError:
        pass

def start_hotkey_listener():
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    return listener

def load_config():
    """Load configuration from JSON file if it exists."""
    config_path = resource_path(CONFIG_FILE)
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading config file: {e}")
    return {}

def save_config(config_data):
    """Save configuration to JSON file."""
    config_path = resource_path(CONFIG_FILE)
    try:
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)
        logging.info(f"Configuration saved to {config_path}")
    except Exception as e:
        logging.error(f"Error saving config file: {e}")

def parse_arguments():
    # Load defaults from config file
    config = load_config()
    
    parser = argparse.ArgumentParser(description="Cursor Auto-Continue Bot")
    parser.add_argument("--text", type=str, default=config.get("text", DEFAULT_TEXT), help="Text to type into the chat")
    parser.add_argument("--cooldown", type=float, default=config.get("cooldown", 15.0), help="Cooldown in seconds between actions")
    parser.add_argument("--offset-x", type=int, default=config.get("offset_x", -200), help="X offset from microphone icon to click")
    parser.add_argument("--offset-y", type=int, default=config.get("offset_y", -50), help="Y offset from microphone icon to click")
    parser.add_argument("--image", type=str, default=config.get("image", "microphone_icon.png"), help="Path to the microphone icon image")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without clicking or typing")
    
    # Handle boolean flags correctly when loading from config
    no_polite_default = config.get("no_polite", False)
    parser.add_argument("--no-polite", action="store_true", default=no_polite_default, help="Disable polite mode (user activity detection)")
    
    notify_default = config.get("notify", False)
    parser.add_argument("--notify", action="store_true", default=notify_default, help="Send system notification when action is taken")
    
    parser.add_argument("--calibrate", action="store_true", help="Run interactive calibration wizard to find offsets")
    parser.add_argument("--once", action="store_true", help="Run once and exit immediately after action (or if image not found)")
    parser.add_argument("--background", action="store_true", help="Running in background mode (suppress some outputs/console logic if needed)")
    
    # Allow overriding config with explicit flags
    return parser.parse_args()

def is_user_active(check_duration=0.5, threshold=5):
    """
    Checks if the user is moving the mouse.
    Returns True if mouse moved more than threshold pixels in check_duration.
    """
    x1, y1 = pyautogui.position()
    time.sleep(check_duration)
    x2, y2 = pyautogui.position()
    
    distance = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
    return distance > threshold

def run_calibration():
    print("=== Calibration Wizard ===")
    print("This tool will help you calculate the correct X and Y offsets.")
    print("You will need to move your mouse to specific locations and press Enter.")
    print("")
    
    input("1. Move your mouse over the center of the 'Microphone' icon. Then press Enter here...")
    mic_x, mic_y = pyautogui.position()
    print(f"   Recorded Microphone Position: ({mic_x}, {mic_y})")
    
    print("")
    input("2. Move your mouse to where you want the bot to CLICK (e.g., the chat input box). Then press Enter here...")
    target_x, target_y = pyautogui.position()
    print(f"   Recorded Target Position: ({target_x}, {target_y})")
    
    offset_x = target_x - mic_x
    offset_y = target_y - mic_y
    
    print("")
    print("=== Results ===")
    print(f"Calculated Offsets: X={offset_x}, Y={offset_y}")
    print("")
    
    save_choice = input("Do you want to save these offsets to config.json? (y/n): ").lower()
    if save_choice == 'y':
        config = load_config()
        config['offset_x'] = offset_x
        config['offset_y'] = offset_y
        save_config(config)
        print("Saved! You can now run the bot without specifying offsets.")
    else:
        print("Use these arguments when running the bot:")
        print(f"   python auto_continue_bot.py --offset-x {offset_x} --offset-y {offset_y}")
    print("======================")

def process_cycle(args, mic_image, last_action_time):
    """
    Runs one cycle of scanning and action.
    Returns (updated_last_action_time, action_taken_bool)
    """
    global bot_paused, last_known_mic_pos
    
    if bot_paused:
        time.sleep(1)
        return last_action_time, False

    current_time = time.time()
    
    # Only check if cooldown has passed
    if current_time - last_action_time < args.cooldown:
        return last_action_time, False

    mic_location = None
    
    # 1. Try Region of Interest (ROI) if we have a last known location
    if last_known_mic_pos:
        try:
            # Define region around last pos: (left, top, width, height)
            roi_size = 200
            left = max(0, int(last_known_mic_pos.x - roi_size/2))
            top = max(0, int(last_known_mic_pos.y - roi_size/2))
            
            mic_location = pyautogui.locateCenterOnScreen(mic_image, region=(left, top, roi_size, roi_size), confidence=0.95, grayscale=False)
            if mic_location:
                pass
        except Exception:
            pass

    # 2. Fallback to Full Screen if not found in ROI
    if not mic_location:
        try:
            mic_location = pyautogui.locateCenterOnScreen(mic_image, confidence=0.95, grayscale=False)
        except pyautogui.ImageNotFoundException:
                pass
        except Exception as e:
            if "ImageNotFoundException" in str(type(e)):
                    pass
            else:
                logging.error(f"Error searching for image: {e}")

    if mic_location:
        logging.info(f"Microphone detected at {mic_location}. Agent is idle.")
        last_known_mic_pos = mic_location 
        
        # Polite mode check
        if not args.no_polite:
            logging.info("Checking for user activity...")
            if is_user_active():
                logging.warning("User activity detected (mouse moving). Skipping this cycle to be polite.")
                return last_action_time, False
        
        try:
            # Save current mouse position to restore later
            original_mouse_x, original_mouse_y = pyautogui.position()
            logging.info(f"Saved mouse position: ({original_mouse_x}, {original_mouse_y})")
            
            target_x = mic_location.x + args.offset_x
            target_y = mic_location.y + args.offset_y
            
            logging.info(f"Target coordinates: ({target_x}, {target_y})")
            
            if args.dry_run:
                logging.info("[DRY RUN] Moving to target...")
                pyautogui.moveTo(target_x, target_y)
                time.sleep(1)
                logging.info("[DRY RUN] Would click and type here.")
                pyautogui.moveRel(10, 0)
                pyautogui.moveRel(-20, 0)
                pyautogui.moveRel(10, 0)
            else:
                logging.info(f"Clicking at target...")
                # Focus the chat input
                pyautogui.click(target_x, target_y)
                
                # Small delay to ensure focus
                time.sleep(0.3)
                
                # Type text and press Enter
                logging.info("Typing text...")
                pyautogui.write(args.text, interval=0.02)
                logging.info("Pressing Enter...")
                pyautogui.press('enter')
                
                logging.info("Sent 'continue'.")
                last_action_time = time.time()
                
                if args.notify:
                    send_notification("Cursor Auto-Continue", "Sent 'continue' command.")

            # Restore mouse position
            logging.info(f"Restoring mouse to: ({original_mouse_x}, {original_mouse_y})")
            pyautogui.moveTo(original_mouse_x, original_mouse_y)
            
            return (last_action_time if args.dry_run else time.time()), True
            
        except Exception as e:
            logging.error(f"Error performing action: {e}")
            return last_action_time, False
    else:
        pass
        
    return last_action_time, False

def bot_loop(args, mic_image):
    """Thread function for the main bot logic"""
    global bot_running
    last_action_time = 0
    logging.info("Starting background bot thread...")
    
    while bot_running:
        try:
            last_action_time, action_taken = process_cycle(args, mic_image, last_action_time)
            
            if args.once:
                if action_taken:
                    logging.info("Action taken. Exiting (--once mode).")
                    quit_app()
                    break
            
            time.sleep(2)
        except Exception as e:
            logging.error(f"Error in bot loop: {e}")
            time.sleep(5) 

def validate_image(image_path):
    """Ensure image file exists and is readable."""
    if not os.path.exists(image_path):
        logging.error(f"Image file not found: {image_path}")
        return False
    try:
        with Image.open(image_path) as img:
            img.verify() # Verify it's a valid image
        return True
    except (IOError, SyntaxError, UnidentifiedImageError) as e:
        logging.error(f"Invalid image file '{image_path}': {e}")
        return False

def main():
    global tray_icon
    args = parse_arguments()

    if args.calibrate:
        run_calibration()
        return
    
    logging.info("=== Cursor Auto-Continue Bot ===")
    
    logging.info(f"Configuration: Cooldown={args.cooldown}s, Notifications={args.notify}, Once={args.once}, Background={args.background}")
    if args.dry_run:
        logging.info("Mode: DRY RUN (No clicks/typing)")
    
    mic_image = resource_path(args.image)
    if not validate_image(mic_image):
        print(f"Error: Invalid or missing image file: {mic_image}")
        return

    if args.once:
        logging.info("Mode: ONCE (Will exit after first successful action)")
    else:
        logging.info("Hotkeys: [F8] Pause/Resume | [F9] Quit")
    
    logging.info(f"Logging to {os.path.abspath(LOG_FILE)}")
    
    # Start Hotkey Listener
    listener = start_hotkey_listener()

    # Start Bot Thread
    bot_thread = threading.Thread(target=bot_loop, args=(args, mic_image), daemon=True)
    bot_thread.start()

    # Start Tray Icon (blocks main thread)
    try:
        def get_startup_checked(item):
            return is_run_on_startup()

        menu = pystray.Menu(
            pystray.MenuItem("Cursor Auto-Bot", None, enabled=False),
            pystray.MenuItem("Pause/Resume", toggle_pause),
            pystray.MenuItem("Run on Startup", toggle_run_on_startup, checked=get_startup_checked),
            pystray.MenuItem("Quit", quit_app)
        )
        
        tray_icon = pystray.Icon("CursorBot", create_tray_icon_image(bot_paused), "Cursor Auto-Bot", menu)
        
        if not args.once:
            logging.info("System tray icon started. Check your taskbar.")
            if bot_paused:
                logging.info("Bot started in PAUSED state. Right-click tray icon or press F8 to resume.")
            
        tray_icon.run() 
        
    except Exception as e:
        logging.error(f"Failed to start system tray: {e}")
    finally:
        # Cleanup
        global bot_running
        bot_running = False
        if listener.is_alive():
            listener.stop()
        logging.info("Bot stopped.")

if __name__ == "__main__":
    main()
