# Cursor Auto-Continue Bot

A lightweight automation tool designed to maintain long-running, unsupervised development sessions with AI agents in Cursor. By automatically detecting and interacting with the agent's prompt, it reduces the need for manual oversight and keeps the development flow moving forward.

> **Note:** This tool is currently experimental and primarily tested on Windows with Cursor 2.0.64.

## Roadmap

- [ ] **Improved Process Management**: Enhance background process handling (specifically `sleep` behavior on Gemini 3 Pro).
- [ ] **Auto-Commit Integration**: Implement automatic git commits upon agent interaction to create checkpoints, allowing for easier rollbacks if the agent diverges.

## Features
*   **Visual Detection**: Scans for the microphone icon.
*   **Smart ROI**: Learns the icon location for faster subsequent scans.
*   **System Tray**: Background operation with menu control.
*   **Run on Startup**: Option to automatically start with Windows (via Tray menu).
*   **Notifications**: Optional system alerts.
*   **Polite Mode**: Respects your mouse usage.
*   **Logging**: Diagnostic logs in `bot.log`.

## Prerequisites (Host Machine)

Run this on your main OS (Windows/Mac/Linux).

1.  **Install Python**.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Linux Users*: You may also need `sudo apt-get install python3-tk python3-dev scrot`.

## Setup

1.  **Capture the Microphone**:
    *   Screenshot just the microphone icon from the chat bar.
    *   Save it as `microphone_icon.png`.

2.  **Calibration**:
    ```bash
    python auto_continue_bot.py --calibrate
    ```

## Usage

```bash
python auto_continue_bot.py
```

*   The bot starts in the **System Tray** in a **PAUSED** state (Red icon).
*   Right-click the icon and select **Resume** or press **F8** to start monitoring.

### Controls

*   **Tray Menu (Right-Click Icon)**:
    *   **Pause/Resume**: Toggle bot activity.
    *   **Run on Startup**: Toggle automatic startup (Windows only).
    *   **Quit**: Exit the application.
*   **F8**: Pause / Resume.
*   **F9**: Quit.

### Configuration

Settings are loaded from `config.json` or CLI arguments:
*   `--text "Your text"`: Custom text to type.
*   `--cooldown 15`: Seconds to wait between actions.
*   `--no-polite`: Disable user activity detection.
*   `--notify`: Enable system notifications.
*   `--background`: Suppress console window (used internally for startup).
