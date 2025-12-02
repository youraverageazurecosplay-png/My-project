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

# Make pyautogui as fast as safely possible
pyautogui.PAUSE = 0.001  # smaller pause => faster clicks

# For update checks (launcher version)
VERSION = "1.6"
print(f"Running Gaming_Stuffs version {VERSION}")

# Base directory (put this file in /Users/ps/game_stuff)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "settings.json")

# ========= Global state for Spam tab =========
clicking = False
current_hotkey = '<f6>'
click_interval = 0.05
hotkey_listener = None

action_type = "key"
key_name = "enter"
mouse_button = "left"

capturing_key = False
capturing_mouse = False

# ========= Global state for Hold tab =========
holding = False
hold_hotkey = '<f7>'
hold_listener = None

hold_action_type = "key"
hold_key_name = "w"
hold_mouse_button = "left"

capturing_hold_key = False
capturing_hold_mouse = False

# ========= Global state for CPS Test tab =========
cps_test_running = False
cps_test_clicks = 0
cps_test_duration = 5
cps_result_var = None
cps_timer_var = None

# ========= Settings / Always on top / Theme / Auto update =========
always_on_top_var = None
theme_mode_var = None  # "system", "light", "dark"
auto_update_var = None  # bool: automatically check for updates on launch

# ========= Notepad state =========
notepad_text_widget = None  # will hold Text widget


# ========= Settings save/load =========
def load_settings():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings():
    try:
        # notebook might not be ready in some early/error paths; fall back gracefully
        try:
            selected_tab_index = notebook.index(notebook.select())
        except Exception:
            selected_tab_index = 0

        data = {
            "spam_hotkey": spam_hotkey_entry.get(),
            "spam_interval": interval_entry.get(),
            "spam_action_type": action_type_var.get(),
            "spam_key": key_entry.get(),
            "spam_mouse_button": mouse_button_var.get(),
            "hold_hotkey": hold_hotkey_entry.get(),
            "hold_action_type": hold_action_type_var.get(),
            "hold_key": hold_key_entry.get(),
            "hold_mouse_button": hold_mouse_button_var.get(),
            "cps_duration": cps_duration_spin.get(),
            "always_on_top": always_on_top_var.get(),
            "theme_mode": theme_mode_var.get(),
            "auto_update": auto_update_var.get(),
            "selected_tab": selected_tab_index,
        }
        if notepad_text_widget is not None:
            data["notepad_text"] = notepad_text_widget.get("1.0", "end-1c")
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ========= Theme helpers =========
def is_macos_dark():
    if platform.system() != "Darwin":
        return False
    try:
        cmd = 'defaults read -g AppleInterfaceStyle'
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, shell=True)
        out, _ = p.communicate()
        return bool(out)
    except Exception:
        return False


def _apply_widget_theme(widget, bg, fg, entry_bg, button_bg):
    cls = widget.__class__.__name__
    try:
        if cls in ("Frame", "LabelFrame"):
            widget.configure(bg=bg)
        elif cls == "Label":
            widget.configure(bg=bg, fg=fg)
        elif cls == "Button":
            widget.configure(
                bg=button_bg,
                fg=fg,
                activebackground=button_bg,
                activeforeground=fg,
                highlightbackground=bg,
            )
        elif cls in ("Entry", "Spinbox", "Text"):
            widget.configure(
                bg=entry_bg,
                fg=fg,
                insertbackground=fg,
                highlightbackground=bg,
            )
        elif cls == "Checkbutton":
            widget.configure(
                bg=bg,
                fg=fg,
                activebackground=bg,
                activeforeground=fg,
                selectcolor=bg,
            )
        elif cls == "Canvas":
            widget.configure(bg=bg, highlightbackground=bg)
    except tk.TclError:
        pass

    for child in widget.winfo_children():
        _apply_widget_theme(child, bg, fg, entry_bg, button_bg)


def apply_theme():
    mode = theme_mode_var.get()
    if mode == "system":
        dark = is_macos_dark()
    else:
        dark = (mode == "dark")

    if dark:
        bg = "#202124"
        fg = "#ffffff"
        entry_bg = "#303134"
        button_bg = "#555555"
    else:
        bg = "#f0f0f0"
        fg = "#000000"
        entry_bg = "#ffffff"
        button_bg = "#e0e0e0"

    root.configure(bg=bg)
    _apply_widget_theme(root, bg, fg, entry_bg, button_bg)

    style = ttk.Style()
    try:
        style.theme_use(style.theme_use())
    except tk.TclError:
        pass

    style.configure(
        "TCombobox",
        fieldbackground=entry_bg,
        background=entry_bg,
        foreground=fg,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", entry_bg)],
        foreground=[("readonly", fg)],
    )

    style.configure(
        "TNotebook",
        background=bg,
        tabmargins=0,
    )
    style.configure(
        "TNotebook.Tab",
        background=button_bg,
        foreground=fg,
    )


# ========= Mouse wheel scrolling =========
def _on_mousewheel(event, canvas):
    system = platform.system()
    if system == "Darwin":
        canvas.yview_scroll(int(-1 * event.delta), "units")
    else:
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ========= Spam logic ==========
def spam_action():
    global clicking, click_interval, action_type, key_name, mouse_button
    while clicking:
        if action_type == "key":
            pyautogui.press(key_name)
        else:
            pyautogui.click(button=mouse_button)
        time.sleep(click_interval)


def spam_hotkey_trigger():
    global clicking
    clicking = not clicking
    if clicking:
        threading.Thread(target=spam_action, daemon=True).start()
    update_status()


def start_spam_listener(hotkey_str):
    global hotkey_listener, current_hotkey

    if hotkey_listener is not None:
        try:
            hotkey_listener.stop()
        except Exception:
            pass
        hotkey_listener = None

    current_hotkey = hotkey_str

    try:
        hotkey_listener = keyboard.GlobalHotKeys({current_hotkey: spam_hotkey_trigger})
        t = threading.Thread(target=hotkey_listener.run, daemon=True)
        t.start()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to set spam hotkey '{current_hotkey}': {e}")
        return

    update_status()


def apply_spam_hotkey():
    raw = spam_hotkey_entry.get().strip().lower()
    if not raw:
        messagebox.showerror("Error", "Spam hotkey cannot be empty.")
        return
    if not raw.startswith('<'):
        hotkey_str = f'<{raw}>'
    else:
        hotkey_str = raw
    start_spam_listener(hotkey_str)
    save_settings()


def apply_interval():
    global click_interval
    try:
        value = float(interval_entry.get())
        if value <= 0:
            raise ValueError
        # Clamp to a safe minimum
        if value < 0.001:
            value = 0.001
        click_interval = value
        update_status()
        messagebox.showinfo("Interval", f"Interval set to {click_interval} seconds.")
        save_settings()
    except ValueError:
        messagebox.showerror("Error", "Please enter a positive number for the interval.")


def apply_spam_action():
    global action_type, key_name, mouse_button

    action_type = action_type_var.get()
    if action_type == "key":
        k = key_entry.get().strip().lower()
        if not k:
            messagebox.showerror("Error", "Key name cannot be empty.")
            return
        key_name = k
    else:
        mouse_button = mouse_button_var.get()

    update_status()
    messagebox.showinfo(
        "Spam Action",
        f"Spam action set to: {action_type} - "
        f"{key_name if action_type=='key' else mouse_button}",
    )
    save_settings()


def start_key_capture():
    global capturing_key
    capturing_key = True
    status_var.set("Status: [Spam] Press a key in the window to set spam key...")


def start_mouse_capture():
    global capturing_mouse
    capturing_mouse = True
    status_var.set("Status: [Spam] Click in the window to set spam mouse button...")


# ========= Hold logic ==========
def start_hold():
    global holding, hold_action_type, hold_key_name, hold_mouse_button
    if holding:
        return
    holding = True
    if hold_action_type == "key":
        pyautogui.keyDown(hold_key_name)
    else:
        pyautogui.mouseDown(button=hold_mouse_button)
    update_status()


def stop_hold():
    global holding, hold_action_type, hold_key_name, hold_mouse_button
    if not holding:
        return
    if hold_action_type == "key":
        pyautogui.keyUp(hold_key_name)
    else:
        pyautogui.mouseUp(button=hold_mouse_button)
    holding = False
    update_status()


def hold_hotkey_trigger():
    global holding
    if holding:
        stop_hold()
    else:
        start_hold()


def start_hold_listener(hotkey_str):
    global hold_listener, hold_hotkey

    if hold_listener is not None:
        try:
            hold_listener.stop()
        except Exception:
            pass
        hold_listener = None

    hold_hotkey = hotkey_str

    try
