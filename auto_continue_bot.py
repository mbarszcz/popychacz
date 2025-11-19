import pyautogui
import time
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def main():
    print("=== Cursor Auto-Continue Bot (Microphone Detection) ===")
    print("1. Take a screenshot of the 'Microphone' icon (which appears when agent stops).")
    print("2. Save it as 'microphone_icon.png' in this folder.")
    print("3. Take a screenshot of the Chat Input box (empty).")
    print("4. Save it as 'chat_input.png' in this folder (optional, helps targeting).")
    
    # Debug Screen Info
    screen_size = pyautogui.size()
    print(f"Debug: Screen Resolution: {screen_size}")
    print("======================================================")
    
    mic_image = resource_path("microphone_icon.png")
    
    if not os.path.exists(mic_image):
        print(f"Error: Could not find '{mic_image}'")
        print("Please create the screenshot and try again.")
        input("Press Enter to exit...")
        return

    print("Press Ctrl+C to stop.")
    
    last_action_time = 0
    # Cooldown to prevent spamming "continue" immediately after sending it
    COOLDOWN_SECONDS = 15 

    try:
        print("Starting main loop...")
        while True:
            current_time = time.time()
            
            # Only check if cooldown has passed
            if current_time - last_action_time < COOLDOWN_SECONDS:
                print(f"Cooldown active. Waiting... ({int(COOLDOWN_SECONDS - (current_time - last_action_time))}s left)")
                time.sleep(1)
                continue

            print("Scanning for microphone icon...")
            # 1. Look for the Microphone icon (indicating agent is idle/ready)
            try:
                # grayscale=True makes it faster and more robust to minor color shifts
                mic_location = pyautogui.locateCenterOnScreen(mic_image, confidence=0.9, grayscale=True)
            except pyautogui.ImageNotFoundException:
                 print("Microphone icon not found (ImageNotFoundException).")
                 mic_location = None
            except Exception as e:
                print(f"Error searching for image: {e}")
                mic_location = None

            if mic_location:
                print(f"Microphone detected at {mic_location}. Agent is idle.")
                
                # Save current mouse position to restore later
                original_mouse_x, original_mouse_y = pyautogui.position()
                print(f"Saved mouse position: ({original_mouse_x}, {original_mouse_y})")
                
                # 2. Determine where to click. 
                # The input box is usually to the right of the microphone or below the chat history.
                # We can either search for the input box image, or assume an offset from the mic.
                # Usually, in Cursor, the microphone is INSIDE or right next to the input area.
                # Let's click slightly to the right of the microphone to focus the input.
                
                target_x = mic_location.x - 200  # Adjust this offset based on your UI scale
                target_y = mic_location.y - 50
                
                print(f"Clicking at target: ({target_x}, {target_y})")
                # Focus the chat input
                pyautogui.click(target_x, target_y)
                
                # Small delay to ensure focus
                time.sleep(0.2)
                
                # 3. Type "continue" and press Enter
                print("Typing 'continue'...")
                pyautogui.write("""Continue with the plan. Develop the rest of the requirements. Make improvements.  Make sure everything works.  Write tests. Run the tests. If you have confirmed there is absolutely nothing left to do, execute 'sleep 60000' command in the shell (not in the background) and wait for it. Only if you are certain. Otherwise, wait for further instructions.""", interval=0.01)
                print("Pressing Enter...")
                pyautogui.press('enter')
                
                print("Sent 'continue'.")
                last_action_time = time.time()
                
                # 4. Restore mouse position (attempt to minimize disruption)
                print(f"Restoring mouse to: ({original_mouse_x}, {original_mouse_y})")
                pyautogui.moveTo(original_mouse_x, original_mouse_y)
            else:
                print("Microphone not detected on this scan.")
                
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nBot stopped.")

if __name__ == "__main__":
    main()
