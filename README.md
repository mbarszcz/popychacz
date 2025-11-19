# Cursor Auto-Continue Bot

This script automates typing "continue" in the Cursor Chat when the agent stops.

## Logic
1.  It constantly scans the screen for the **Microphone icon**, which indicates the agent has finished generating and is waiting for input.
2.  When found, it saves your current mouse position.
3.  It clicks near the microphone (to focus the input box).
4.  It types `continue` and hits `ENTER`.
5.  It moves your mouse back to where it was.

## Prerequisites (Host Machine)

Run this on your main OS (Windows/Mac/Linux).

1.  **Install Python**.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Setup

1.  **Capture the Microphone**:
    *   Open Cursor. Ensure the chat input is empty and the agent is stopped.
    *   Find the small microphone icon (usually in the input bar).
    *   Use "Snipping Tool" to screenshot **just the icon**.
    *   Save it as `microphone_icon.png` in this folder.

2.  **Adjust Offset (Optional)**:
    *   Open `auto_continue_bot.py`.
    *   Look for `target_x = mic_location.x + 50`.
    *   If the click misses the text box, increase or decrease this number.

## Usage

```bash
python auto_continue_bot.py
```
