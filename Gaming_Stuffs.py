import threading
import time
import json
import os
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

import pyautogui
from pynput import keyboard
import requests

# ----------------- VERSION / CONFIG -----------------

VERSION = "1.2"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "settings.json")

# GitHub URLs (same as before, just update if your repo path changes)
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/youraverageazurecosplay-png/My-project/main/version.txt"
REMOTE_SCRIPT_URL = "https://raw.githubusercontent.com/youraverageazurecosplay-png/My-project/main/Gaming_Stuffs.py"


# ----------------- GLOBAL STATE -----------------

clicking = False
holding = False

hotkey_listener = None
hold_listener = None

current_spam_hotkey = "<f6>"
current_hold_hotkey = "<f7>"

spam_interval = 0.05

spam_action_type = "key"
spam_key = "return"
spam_button = "left"

hold_action_type = "key"
hold_key = "w"
hold_button = "left"

cps_clicks = 0
cps_running = False
cps_duration = 5

always_on_top = False

theme_mode = "system"  # "system", "light", "dark"
selected_tab_name = "Spam"

auto_update_on_launch = False  # NEW: setting to auto-check on startup


# ----------------- SETTINGS LOAD/SAVE -----------------

def default_settings():
    return {
        "spam_hotkey": current_spam_hotkey,
        "hold_hotkey": current_hold_hotkey,
        "spam_interval": spam_interval,
        "spam_action_type": spam_action_type,
        "spam_key": spam_key,
        "spam_button": spam_button,
        "hold_action_type": hold_action_type,
        "hold_key": hold_key,
        "hold_button": hold_button,
        "cps_duration": cps_duration,
        "always_on_top": always_on_top,
        "theme_mode": theme_mode,
        "selected_tab": selected_tab_name,
        "auto_update_on_launch": auto_update_on_launch,  # NEW
    }


def load_settings():
    global current_spam_hotkey, current_hold_hotkey
    global spam_interval, spam_action_type, spam_key, spam_button
    global hold_action_type, hold_key, hold_button
    global cps_duration, always_on_top, theme_mode, selected_tab_name
    global auto_update_on_launch

    if not os.path.exists(CONFIG_PATH):
        return

    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
    except Exception:
        return

    current_spam_hotkey = data.get("spam_hotkey", current_spam_hotkey)
    current_hold_hotkey = data.get("hold_hotkey", current_hold_hotkey)
    spam_interval = data.get("spam_interval", spam_interval)
    spam_action_type = data.get("spam_action_type", spam_action_type)
    spam_key = data.get("spam_key", spam_key)
    spam_button = data.get("spam_button", spam_button)
    hold_action_type = data.get("hold_action_type", hold_action_type)
    hold_key = data.get("hold_key", hold_key)
    hold_button = data.get("hold_button", hold_button)
    cps_duration = data.get("cps_duration", cps_duration)
    always_on_top = data.get("always_on_top", always_on_top)
    theme_mode = data.get("theme_mode", theme_mode)
    selected_tab_name = data.get("selected_tab", selected_tab_name)
    auto_update_on_launch = data.get("auto_update_on_launch", auto_update_on_launch)


def save_settings():
    data = default_settings()
    data["spam_hotkey"] = current_spam_hotkey
    data["hold_hotkey"] = current_hold_hotkey
    data["spam_interval"] = spam_interval
    data["spam_action_type"] = spam_action_type
    data["spam_key"] = spam_key
    data["spam_button"] = spam_button
    data["hold_action_type"] = hold_action_type
    data["hold_key"] = hold_key
    data["hold_button"] = hold_button
    data["cps_duration"] = cps_duration
    data["always_on_top"] = always_on_top
    data["theme_mode"] = theme_mode
    data["selected_tab"] = selected_tab_name
    data["auto_update_on_launch"] = auto_update_on_launch
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ----------------- THEME UTILS -----------------

def is_system_dark_mode():
    if platform.system() != "Darwin":
        return False
    try:
        out = subprocess.check_output(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
        return out.lower() == "dark"
    except Exception:
        return False


def apply_theme():
    if theme_mode == "system":
        dark = is_system_dark_mode()
    elif theme_mode == "dark":
        dark = True
    else:
        dark = False

    if dark:
        bg = "#202020"
        fg = "#ffffff"
        btn_bg = "#404040"
        btn_fg = "#ffffff"
        entry_bg = "#303030"
        entry_fg = "#ffffff"
    else:
        bg = "#f0f0f0"
        fg = "#000000"
        btn_bg = "#ffffff"
        btn_fg = "#000000"
        entry_bg = "#ffffff"
        entry_fg = "#000000"

    root.configure(bg=bg)

    style = ttk.Style()
    style.theme_use("default")

    style.configure("TNotebook", background=bg, borderwidth=0)
    style.configure("TNotebook.Tab", background=btn_bg, foreground=fg)
    style.map("TNotebook.Tab",
              background=[("selected", bg)],
              foreground=[("selected", fg)])

    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("TButton", background=btn_bg, foreground=btn_fg)
    style.map("TButton",
              background=[("active", btn_bg)],
              foreground=[("active", btn_fg)])

    style.configure("TCheckbutton", background=bg, foreground=fg)

    def recolor_widgets(widget):
        for child in widget.winfo_children():
            if isinstance(child, tk.Button):
                child.configure(bg=btn_bg, fg=btn_fg, activebackground=btn_bg, activeforeground=btn_fg)
            elif isinstance(child, tk.Label):
                child.configure(bg=bg, fg=fg)
            elif isinstance(child, tk.Entry):
                child.configure(bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
            elif isinstance(child, tk.Text):
                child.configure(bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
            elif isinstance(child, tk.Checkbutton):
                child.configure(bg=bg, fg=fg, selectcolor=bg)
            elif isinstance(child, tk.Frame):
                child.configure(bg=bg)
            recolor_widgets(child)

    recolor_widgets(root)

    root.attributes("-topmost", always_on_top)


# ----------------- SPAM LOGIC -----------------

def spam_loop():
    while clicking:
        if spam_action_type == "key":
            pyautogui.press(spam_key)
        else:
            pyautogui.click(button=spam_button)
        time.sleep(spam_interval)


def toggle_spam():
    global clicking
    clicking = not clicking
    if clicking:
        threading.Thread(target=spam_loop, daemon=True).start()
        spam_status_var.set("Spamming: ON")
    else:
        spam_status_var.set("Spamming: OFF")


def on_spam_hotkey_press(key):
    try:
        k = key.char
    except AttributeError:
        k = str(key).lower()
    if k == current_spam_hotkey:
        toggle_spam()


def start_spam_listener():
    global hotkey_listener
    if hotkey_listener is not None:
        try:
            hotkey_listener.stop()
        except Exception:
            pass

    def on_press(key):
        try:
            name = key.char
        except AttributeError:
            name = str(key).lower()
        normalized = f"<{name}>"
        if normalized == current_spam_hotkey:
            toggle_spam()

    hotkey_listener = keyboard.Listener(on_press=on_press)
    hotkey_listener.daemon = True
    hotkey_listener.start()


# ----------------- HOLD LOGIC -----------------

def hold_loop():
    while holding:
        if hold_action_type == "key":
            pyautogui.keyDown(hold_key)
            time.sleep(0.05)
            pyautogui.keyUp(hold_key)
        else:
            pyautogui.mouseDown(button=hold_button)
            time.sleep(0.05)
            pyautogui.mouseUp(button=hold_button)
        time.sleep(0.05)


def toggle_hold():
    global holding
    holding = not holding
    if holding:
        threading.Thread(target=hold_loop, daemon=True).start()
        hold_status_var.set("Holding: ON")
    else:
        hold_status_var.set("Holding: OFF")


def start_hold_listener():
    global hold_listener
    if hold_listener is not None:
        try:
            hold_listener.stop()
        except Exception:
            pass

    def on_press(key):
        try:
            name = key.char
        except AttributeError:
            name = str(key).lower()
        normalized = f"<{name}>"
        if normalized == current_hold_hotkey:
            toggle_hold()

    hold_listener = keyboard.Listener(on_press=on_press)
    hold_listener.daemon = True
    hold_listener.start()


# ----------------- CPS TEST -----------------

def cps_click():
    global cps_clicks
    if cps_running:
        cps_clicks += 1
        cps_label_var.set(f"Clicks: {cps_clicks}")


def start_cps_test():
    global cps_clicks, cps_running
    if cps_running:
        return
    cps_clicks = 0
    cps_running = True
    cps_label_var.set("Clicks: 0")
    cps_result_var.set("")

    def run():
        global cps_running
        time.sleep(cps_duration)
        cps_running = False
        cps = cps_clicks / cps_duration if cps_duration > 0 else 0
        cps_result_var.set(f"CPS: {cps:.2f}")

    threading.Thread(target=run, daemon=True).start()


# ----------------- UPDATE / RESTART LOGIC -----------------

def download_new_version():
    try:
        vr = requests.get(REMOTE_VERSION_URL, timeout=5)
        if vr.status_code != 200:
            return None
        remote_version = vr.text.strip()
    except Exception:
        return None

    if remote_version <= VERSION:
        return None

    try:
        sr = requests.get(REMOTE_SCRIPT_URL, timeout=10)
        if sr.status_code != 200:
            return None
        new_path = os.path.join(BASE_DIR, "Gaming_Stuffs_new.py")
        with open(new_path, "w", encoding="utf-8") as f:
            f.write(sr.text)
        return new_path
    except Exception:
        return None


def restart_into(path):
    # Relaunch this script as the new file, then exit current process.[web:37][web:39]
    try:
        python_exe = "python3"
        subprocess.Popen([python_exe, path], cwd=os.path.dirname(path))
    except Exception:
        return
    os._exit(0)


def check_for_updates_manual():
    messagebox.showinfo("Update", f"Running on version {VERSION}")
    new_path = download_new_version()
    if new_path is None:
        messagebox.showinfo("Update", "You are already on the latest version or update failed.")
        return

    ans = messagebox.askyesno("Update available", "A new version is available. Download and restart now?")
    if not ans:
        return

    messagebox.showinfo("Update", "Downloading and restarting into new version...")
    restart_into(new_path)


def auto_update_on_start():
    # Called at launch if setting is enabled. Silent if no update or error.
    new_path = download_new_version()
    if new_path is None:
        return
    # Auto‑restart into the new file as soon as it is downloaded.
    restart_into(new_path)


# ----------------- GUI -----------------

root = tk.Tk()
root.title(f"game stuffs v{VERSION}")
root.geometry("650x500")

load_settings()

print(f"Running on version {VERSION}")

root.attributes("-topmost", always_on_top)

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

spam_frame = ttk.Frame(notebook)
hold_frame = ttk.Frame(notebook)
cps_frame = ttk.Frame(notebook)
settings_frame = ttk.Frame(notebook)

notebook.add(spam_frame, text="Spam")
notebook.add(hold_frame, text="Hold")
notebook.add(cps_frame, text="CPS Test")
notebook.add(settings_frame, text="Settings")

# ----- Spam tab -----
spam_status_var = tk.StringVar(value="Spamming: OFF")

tk.Label(spam_frame, text="Spam hotkey (e.g. <f6>):").pack(anchor="w", padx=10, pady=4)
spam_hotkey_entry = tk.Entry(spam_frame)
spam_hotkey_entry.pack(anchor="w", padx=10)
spam_hotkey_entry.insert(0, current_spam_hotkey)

def apply_spam_hotkey():
    global current_spam_hotkey
    val = spam_hotkey_entry.get().strip()
    if not val:
        return
    if not val.startswith("<"):
        val = f"<{val}>"
    current_spam_hotkey = val.lower()
    save_settings()
    start_spam_listener()

tk.Button(spam_frame, text="Apply Spam Hotkey", command=apply_spam_hotkey).pack(anchor="w", padx=10, pady=4)

tk.Label(spam_frame, text="Interval (seconds):").pack(anchor="w", padx=10, pady=4)
spam_interval_entry = tk.Entry(spam_frame)
spam_interval_entry.pack(anchor="w", padx=10)
spam_interval_entry.insert(0, str(spam_interval))

def apply_spam_interval():
    global spam_interval
    try:
        v = float(spam_interval_entry.get().strip())
        if v <= 0:
            raise ValueError
        spam_interval = v
        save_settings()
    except Exception:
        messagebox.showerror("Error", "Invalid interval value.")

tk.Button(spam_frame, text="Apply Interval", command=apply_spam_interval).pack(anchor="w", padx=10, pady=4)

tk.Label(spam_frame, textvariable=spam_status_var).pack(anchor="w", padx=10, pady=4)
tk.Button(spam_frame, text="Toggle Spam Now", command=toggle_spam).pack(anchor="w", padx=10, pady=4)

# ----- Hold tab -----
hold_status_var = tk.StringVar(value="Holding: OFF")

tk.Label(hold_frame, text="Hold hotkey (e.g. <f7>):").pack(anchor="w", padx=10, pady=4)
hold_hotkey_entry = tk.Entry(hold_frame)
hold_hotkey_entry.pack(anchor="w", padx=10)
hold_hotkey_entry.insert(0, current_hold_hotkey)

def apply_hold_hotkey():
    global current_hold_hotkey
    val = hold_hotkey_entry.get().strip()
    if not val:
        return
    if not val.startswith("<"):
        val = f"<{val}>"
    current_hold_hotkey = val.lower()
    save_settings()
    start_hold_listener()

tk.Button(hold_frame, text="Apply Hold Hotkey", command=apply_hold_hotkey).pack(anchor="w", padx=10, pady=4)

tk.Label(hold_frame, textvariable=hold_status_var).pack(anchor="w", padx=10, pady=4)
tk.Button(hold_frame, text="Toggle Hold Now", command=toggle_hold).pack(anchor="w", padx=10, pady=4)

# ----- CPS tab -----
cps_label_var = tk.StringVar(value="Clicks: 0")
cps_result_var = tk.StringVar(value="")

tk.Label(cps_frame, text="Click as fast as you can in the box below.").pack(anchor="w", padx=10, pady=4)

cps_button = tk.Button(cps_frame, text="Click here!", command=cps_click)
cps_button.pack(pady=10)

tk.Label(cps_frame, textvariable=cps_label_var).pack(anchor="w", padx=10, pady=4)
tk.Label(cps_frame, textvariable=cps_result_var).pack(anchor="w", padx=10, pady=4)

tk.Label(cps_frame, text="Test duration (seconds):").pack(anchor="w", padx=10, pady=4)
cps_duration_entry = tk.Entry(cps_frame)
cps_duration_entry.pack(anchor="w", padx=10)
cps_duration_entry.insert(0, str(cps_duration))

def apply_cps_duration():
    global cps_duration
    try:
        v = float(cps_duration_entry.get().strip())
        if v <= 0:
            raise ValueError
        cps_duration = v
        save_settings()
    except Exception:
        messagebox.showerror("Error", "Invalid duration.")

tk.Button(cps_frame, text="Apply Duration", command=apply_cps_duration).pack(anchor="w", padx=10, pady=4)
tk.Button(cps_frame, text="Start CPS Test", command=start_cps_test).pack(anchor="w", padx=10, pady=4)

# ----- Settings tab -----

theme_var = tk.StringVar(value=theme_mode)
tk.Label(settings_frame, text="Theme:").pack(anchor="w", padx=10, pady=4)
theme_frame_inner = tk.Frame(settings_frame)
theme_frame_inner.pack(anchor="w", padx=10)

def set_theme(mode):
    global theme_mode
    theme_mode = mode
    save_settings()
    apply_theme()

tk.Radiobutton(theme_frame_inner, text="System", variable=theme_var, value="system",
               command=lambda: set_theme("system")).pack(side="left")
tk.Radiobutton(theme_frame_inner, text="Light", variable=theme_var, value="light",
               command=lambda: set_theme("light")).pack(side="left")
tk.Radiobutton(theme_frame_inner, text="Dark", variable=theme_var, value="dark",
               command=lambda: set_theme("dark")).pack(side="left")

always_on_top_var = tk.BooleanVar(value=always_on_top)

def toggle_always_on_top():
    global always_on_top
    always_on_top = always_on_top_var.get()
    root.attributes("-topmost", always_on_top)
    save_settings()

tk.Checkbutton(settings_frame, text="Always on top",
               variable=always_on_top_var,
               command=toggle_always_on_top).pack(anchor="w", padx=10, pady=4)

# NEW: Auto‑update on launch option
auto_update_var = tk.BooleanVar(value=auto_update_on_launch)

def toggle_auto_update_launch():
    global auto_update_on_launch
    auto_update_on_launch = auto_update_var.get()
    save_settings()

tk.Checkbutton(
    settings_frame,
    text="Auto‑check for updates on launch",
    variable=auto_update_var,
    command=toggle_auto_update_launch
).pack(anchor="w", padx=10, pady=4)

tk.Button(settings_frame, text="Check for updates now", command=check_for_updates_manual).pack(anchor="w", padx=10, pady=6)

def quit_app():
    root.destroy()

tk.Button(settings_frame, text="Quit", command=quit_app).pack(anchor="w", padx=10, pady=8)


# ----------------- TAB PERSISTENCE -----------------

def on_tab_change(event):
    global selected_tab_name
    tab = event.widget.tab(event.widget.select(), "text")
    selected_tab_name = tab
    save_settings()

notebook.bind("<<NotebookTabChanged>>", on_tab_change)

# Restore last tab
for i in range(notebook.index("end")):
    if notebook.tab(i, "text") == selected_tab_name:
        notebook.select(i)
        break

# Apply initial theme
apply_theme()

# Start hotkey listeners
start_spam_listener()
start_hold_listener()

# Auto‑update on launch if enabled
if auto_update_on_launch:
    threading.Thread(target=auto_update_on_start, daemon=True).start()

def on_close():
    global clicking, holding
    clicking = False
    holding = False
    if hotkey_listener is not None:
        try:
            hotkey_listener.stop()
        except Exception:
            pass
    if hold_listener is not None:
        try:
            hold_listener.stop()
        except Exception:
            pass
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

root.mainloop()
