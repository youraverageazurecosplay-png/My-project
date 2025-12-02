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

    try:
        hold_listener = keyboard.GlobalHotKeys({hold_hotkey: hold_hotkey_trigger})
        t = threading.Thread(target=hold_listener.run, daemon=True)
        t.start()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to set hold hotkey '{hold_hotkey}': {e}")
        return

    update_status()


def apply_hold_hotkey():
    raw = hold_hotkey_entry.get().strip().lower()
    if not raw:
        messagebox.showerror("Error", "Hold hotkey cannot be empty.")
        return
    if not raw.startswith('<'):
        hotkey_str = f'<{raw}>'
    else:
        hotkey_str = raw
    start_hold_listener(hotkey_str)
    save_settings()


def apply_hold_action():
    global hold_action_type, hold_key_name, hold_mouse_button

    hold_action_type = hold_action_type_var.get()
    if hold_action_type == "key":
        k = hold_key_entry.get().strip().lower()
        if not k:
            messagebox.showerror("Error", "Hold key name cannot be empty.")
            return
        hold_key_name = k
    else:
        hold_mouse_button = hold_mouse_button_var.get()

    update_status()
    messagebox.showinfo(
        "Hold Action",
        f"Hold action set to: {hold_action_type} - "
        f"{hold_key_name if hold_action_type=='key' else hold_mouse_button}",
    )
    save_settings()


def start_hold_key_capture():
    global capturing_hold_key
    capturing_hold_key = True
    status_var.set("Status: [Hold] Press a key in the window to set hold key...")


def start_hold_mouse_capture():
    global capturing_hold_mouse
    capturing_hold_mouse = True
    status_var.set("Status: [Hold] Click in the window to set hold mouse button...")


# ========= Shared capture handlers ==========
def on_key_press(event):
    global capturing_key, key_name, capturing_hold_key, hold_key_name

    if capturing_key:
        ks = event.keysym
        mapping = {
            "Return": "enter",
            "Escape": "esc",
            "Space": "space",
            "BackSpace": "backspace",
        }
        kn = mapping.get(ks, ks.lower())
        key_name = kn
        key_entry.delete(0, tk.END)
        key_entry.insert(0, key_name)
        capturing_key = False
        update_status()
        save_settings()
    elif capturing_hold_key:
        ks = event.keysym
        mapping = {
            "Return": "enter",
            "Escape": "esc",
            "Space": "space",
            "BackSpace": "backspace",
        }
        kn = mapping.get(ks, ks.lower())
        hold_key_name = kn
        hold_key_entry.delete(0, tk.END)
        hold_key_entry.insert(0, hold_key_name)
        capturing_hold_key = False
        update_status()
        save_settings()


def on_mouse_click(event):
    global capturing_mouse, mouse_button, capturing_hold_mouse, hold_mouse_button

    if capturing_mouse:
        if event.num == 1:
            mouse_button = "left"
        elif event.num == 2:
            mouse_button = "middle"
        elif event.num == 3:
            mouse_button = "right"
        mouse_button_var.set(mouse_button)
        capturing_mouse = False
        update_status()
        save_settings()
    elif capturing_hold_mouse:
        if event.num == 1:
            hold_mouse_button = "left"
        elif event.num == 2:
            hold_mouse_button = "middle"
        elif event.num == 3:
            hold_mouse_button = "right"
        hold_mouse_button_var.set(hold_mouse_button)
        capturing_hold_mouse = False
        update_status()
        save_settings()


# ========= CPS Test logic ==========
def set_cps_duration():
    global cps_test_duration
    try:
        cps_test_duration = int(cps_duration_spin.get())
        if cps_test_duration <= 0:
            cps_test_duration = 1
            cps_duration_spin.delete(0, "end")
            cps_duration_spin.insert(0, "1")
    except ValueError:
        cps_test_duration = 5
        cps_duration_spin.delete(0, "end")
        cps_duration_spin.insert(0, "5")
    save_settings()


def cps_button_click():
    global cps_test_clicks
    if cps_test_running:
        cps_test_clicks += 1


def start_cps_test():
    global cps_test_running, cps_test_clicks
    if cps_test_running:
        return
    set_cps_duration()
    cps_test_running = True
    cps_test_clicks = 0
    cps_button.config(text="Click!", command=cps_button_click)
    countdown_cps(cps_test_duration)


def countdown_cps(remaining):
    global cps_test_running, cps_test_clicks
    if not cps_test_running:
        return
    cps_timer_var.set(f"Time left: {remaining}")
    if remaining <= 0:
        cps_test_running = False
        cps_button.config(text="Start CPS Test", command=start_cps_test)
        cps_timer_var.set("Time left: 0")
        cps = cps_test_clicks / cps_test_duration if cps_test_duration > 0 else 0
        cps_result_var.set(f"Result: {cps_test_clicks} clicks, {cps:.1f} CPS")
    else:
        root.after(1000, lambda: countdown_cps(remaining - 1))


# ========= Settings helpers ==========
def apply_always_on_top():
    if always_on_top_var.get():
        root.attributes("-topmost", True)
    else:
        root.attributes("-topmost", False)
    save_settings()


def apply_auto_update():
    save_settings()


# ========= Games launchers ==========
def open_forsaken_practice():
    try:
        subprocess.Popen(
            ["python3", os.path.join(BASE_DIR, "ForsakenPractice.py")],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open ForsakenPractice.py:\n{e}")


def open_roblox():
    try:
        subprocess.Popen(
            ["/usr/bin/open", "-a", "/Users/ps/Applications/Roblox.app"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open Roblox:\n{e}")


def open_minecraft():
    try:
        subprocess.Popen(
            ["/usr/bin/open", "-a", "/Applications/Minecraft.app"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open Minecraft:\n{e}")


def open_rng_game():
    try:
        subprocess.Popen(
            ["python3", os.path.join(BASE_DIR, "rng_game.py")],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open RNG game:\n{e}")


# ========= Update checker (update launcher + games) ==========
def check_for_updates():
    import requests

    base_raw = "https://raw.githubusercontent.com/youraverageazurecosplay-png/My-project/main"
    remote_version_url = f"{base_raw}/version.txt"

    files_to_update = [
        "Gaming_Stuffs.py",
        "rng_game.py",
        "ForsakenPractice.py",
    ]

    try:
        resp = requests.get(remote_version_url, timeout=3)
        if resp.status_code != 200:
            messagebox.showinfo("Update", "No update info available.")
            return

        remote_version = resp.text.strip()
        if remote_version <= VERSION:
            messagebox.showinfo("Update", "You are already on the latest version.")
            return

        if not messagebox.askyesno(
            "Update",
            f"New version {remote_version} available.\n"
            f"Update main tools and games from GitHub?"
        ):
            return

        for filename in files_to_update:
            file_url = f"{base_raw}/{filename}"
            code = requests.get(file_url, timeout=5)
            if code.status_code != 200:
                messagebox.showerror("Update", f"Failed to download {filename}.")
                return

            local_path = os.path.join(BASE_DIR, filename)
            tmp_path = local_path + ".tmp"

            with open(tmp_path, "wb") as f:
                f.write(code.content)

            os.replace(tmp_path, local_path)

        messagebox.showinfo(
            "Update",
            "Update installed.\nClose and re-open the launcher to use the new version."
        )
    except Exception as e:
        messagebox.showinfo("Update", f"Could not check for updates:\n{e}")


# ========= Status text ==========
def update_status():
    spam_state = "RUNNING" if clicking else "STOPPED"
    hold_state = "HOLDING" if holding else "RELEASED"
    status_var.set(
        f"[Spam] {spam_state} (Hotkey: {current_hotkey}, Interval: {click_interval}s, "
        f"Action: {action_type}-"
        f"{key_name if action_type=='key' else mouse_button}) | "
        f"[Hold] {hold_state} (Hotkey: {hold_hotkey}, "
        f"Action: {hold_action_type}-"
        f"{hold_key_name if hold_action_type=='key' else hold_mouse_button})"
    )


# ========= GUI setup ==========
root = tk.Tk()
root.title("game stuffs")
root.geometry("400x470")
root.resizable(False, False)

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

# ----- Spam tab -----
spam_frame_outer = tk.Frame(notebook)
notebook.add(spam_frame_outer, text="Spam")

spam_container = tk.Frame(spam_frame_outer)
spam_container.pack(fill="both", expand=True)

spam_canvas = tk.Canvas(spam_container)
spam_canvas.pack(side="left", fill="both", expand=True)

spam_scrollbar = ttk.Scrollbar(spam_container, orient="vertical", command=spam_canvas.yview)
spam_scrollbar.pack(side="right", fill="y")

spam_canvas.configure(yscrollcommand=spam_scrollbar.set)

spam_inner = tk.Frame(spam_canvas)
spam_window = spam_canvas.create_window((0, 0), window=spam_inner, anchor="nw")


def on_spam_inner_configure(event):
    spam_canvas.configure(scrollregion=spam_canvas.bbox("all"))


def on_spam_canvas_configure(event):
    spam_canvas.itemconfig(spam_window, width=event.width)


spam_inner.bind("<Configure>", on_spam_inner_configure)
spam_canvas.bind("<Configure>", on_spam_canvas_configure)

spam_inner.bind("<Key>", on_key_press)
spam_inner.bind("<Button-1>", on_mouse_click)
spam_inner.bind("<Button-2>", on_mouse_click)
spam_inner.bind("<Button-3>", on_mouse_click)
spam_inner.focus_set()

spam_canvas.bind_all("<MouseWheel>", lambda e: _on_mousewheel(e, spam_canvas))

spam_hotkey_label = tk.Label(spam_inner, text="Spam toggle hotkey (e.g. f6):")
spam_hotkey_label.pack(pady=(8, 0))

spam_hotkey_entry = tk.Entry(spam_inner)
spam_hotkey_entry.insert(0, "f6")
spam_hotkey_entry.pack(pady=3)

spam_hotkey_button = tk.Button(spam_inner, text="Apply Spam Hotkey", command=apply_spam_hotkey)
spam_hotkey_button.pack(pady=3)

interval_label = tk.Label(spam_inner, text="Spam interval (seconds):")
interval_label.pack(pady=(5, 0))

interval_entry = tk.Entry(spam_inner)
interval_entry.insert(0, "0.01")  # faster default
interval_entry.pack(pady=3)

interval_button = tk.Button(spam_inner, text="Apply Interval", command=apply_interval)
interval_button.pack(pady=3)

action_type_label = tk.Label(spam_inner, text="Spam action type:")
action_type_label.pack(pady=(6, 0))

action_type_var = tk.StringVar(value="key")
action_type_combo = ttk.Combobox(
    spam_inner,
    textvariable=action_type_var,
    values=["key", "mouse"],
    state="readonly",
    width=10,
)
action_type_combo.pack(pady=3)

key_label = tk.Label(spam_inner, text="Spam key (e.g. enter, space, f1):")
key_label.pack(pady=(4, 0))

key_entry = tk.Entry(spam_inner)
key_entry.insert(0, "enter")
key_entry.pack(pady=3)

pick_key_button = tk.Button(spam_inner, text="Pick spam key by pressing it", command=start_key_capture)
pick_key_button.pack(pady=3)

mouse_label = tk.Label(spam_inner, text="Spam mouse button:")
mouse_label.pack(pady=(4, 0))

mouse_button_var = tk.StringVar(value="left")
mouse_combo = ttk.Combobox(
    spam_inner,
    textvariable=mouse_button_var,
    values=["left", "right", "middle"],
    state="readonly",
    width=10,
)
mouse_combo.pack(pady=3)

pick_mouse_button = tk.Button(spam_inner, text="Pick spam mouse by clicking", command=start_mouse_capture)
pick_mouse_button.pack(pady=3)

spam_action_button = tk.Button(spam_inner, text="Apply Spam Action", command=apply_spam_action)
spam_action_button.pack(pady=4)


def manual_spam_toggle():
    spam_hotkey_trigger()


spam_toggle_button = tk.Button(spam_inner, text="Spam Start/Stop (manual)", command=manual_spam_toggle)
spam_toggle_button.pack(pady=5)

# ----- Hold tab -----
hold_frame_outer = tk.Frame(notebook)
notebook.add(hold_frame_outer, text="Hold")

hold_container = tk.Frame(hold_frame_outer)
hold_container.pack(fill="both", expand=True)

hold_canvas = tk.Canvas(hold_container)
hold_canvas.pack(side="left", fill="both", expand=True)

hold_scrollbar = ttk.Scrollbar(hold_container, orient="vertical", command=hold_canvas.yview)
hold_scrollbar.pack(side="right", fill="y")

hold_canvas.configure(yscrollcommand=hold_scrollbar.set)

hold_inner = tk.Frame(hold_canvas)
hold_window = hold_canvas.create_window((0, 0), window=hold_inner, anchor="nw")


def on_hold_inner_configure(event):
    hold_canvas.configure(scrollregion=hold_canvas.bbox("all"))


def on_hold_canvas_configure(event):
    hold_canvas.itemconfig(hold_window, width=event.width)


hold_inner.bind("<Configure>", on_hold_inner_configure)
hold_canvas.bind("<Configure>", on_hold_canvas_configure)

hold_inner.bind("<Key>", on_key_press)
hold_inner.bind("<Button-1>", on_mouse_click)
hold_inner.bind("<Button-2>", on_mouse_click)
hold_inner.bind("<Button-3>", on_mouse_click)

hold_canvas.bind_all("<MouseWheel>", lambda e: _on_mousewheel(e, hold_canvas))

hold_hotkey_label = tk.Label(hold_inner, text="Hold toggle hotkey (e.g. f7):")
hold_hotkey_label.pack(pady=(8, 0))

hold_hotkey_entry = tk.Entry(hold_inner)
hold_hotkey_entry.insert(0, "f7")
hold_hotkey_entry.pack(pady=3)

hold_hotkey_button = tk.Button(hold_inner, text="Apply Hold Hotkey", command=apply_hold_hotkey)
hold_hotkey_button.pack(pady=3)

hold_action_type_label = tk.Label(hold_inner, text="Hold action type:")
hold_action_type_label.pack(pady=(6, 0))

hold_action_type_var = tk.StringVar(value="key")
hold_action_type_combo = ttk.Combobox(
    hold_inner,
    textvariable=hold_action_type_var,
    values=["key", "mouse"],
    state="readonly",
    width=10,
)
hold_action_type_combo.pack(pady=3)

hold_key_label = tk.Label(hold_inner, text="Hold key (e.g. w, enter):")
hold_key_label.pack(pady=(4, 0))

hold_key_entry = tk.Entry(hold_inner)
hold_key_entry.insert(0, "w")
hold_key_entry.pack(pady=3)

pick_hold_key_button = tk.Button(hold_inner, text="Pick hold key by pressing it", command=start_hold_key_capture)
pick_hold_key_button.pack(pady=3)

hold_mouse_label = tk.Label(hold_inner, text="Hold mouse button:")
hold_mouse_label.pack(pady=(4, 0))

hold_mouse_button_var = tk.StringVar(value="left")
hold_mouse_combo = ttk.Combobox(
    hold_inner,
    textvariable=hold_mouse_button_var,
    values=["left", "right", "middle"],
    state="readonly",
    width=10,
)
hold_mouse_combo.pack(pady=3)

pick_hold_mouse_button = tk.Button(hold_inner, text="Pick hold mouse by clicking", command=start_hold_mouse_capture)
pick_hold_mouse_button.pack(pady=3)

hold_action_button = tk.Button(hold_inner, text="Apply Hold Action", command=apply_hold_action)
hold_action_button.pack(pady=4)


def manual_hold_toggle():
    if holding:
        stop_hold()
    else:
        start_hold()


hold_toggle_button = tk.Button(hold_inner, text="Hold Start/Stop (manual)", command=manual_hold_toggle)
hold_toggle_button.pack(pady=5)

# ----- CPS Test tab -----
cps_frame = tk.Frame(notebook)
notebook.add(cps_frame, text="CPS Test")

cps_info = tk.Label(cps_frame, text="Click the button as fast as you can during the test.")
cps_info.pack(pady=(10, 5))

cps_duration_label = tk.Label(cps_frame, text="Test length (seconds):")
cps_duration_label.pack()

cps_duration_spin = tk.Spinbox(cps_frame, from_=1, to=30, width=5, command=lambda: set_cps_duration())
cps_duration_spin.delete(0, "end")
cps_duration_spin.insert(0, "5")
cps_duration_spin.pack(pady=3)

cps_button = tk.Button(cps_frame, text="Start CPS Test", width=20, command=lambda: start_cps_test())
cps_button.pack(pady=8)

cps_result_var = tk.StringVar(value="Result: 0 clicks, 0.0 CPS")
cps_result_label = tk.Label(cps_frame, textvariable=cps_result_var)
cps_result_label.pack(pady=4)

cps_timer_var = tk.StringVar(value="Time left: 0")
cps_timer_label = tk.Label(cps_frame, textvariable=cps_timer_var)
cps_timer_label.pack(pady=4)

# ----- Notepad tab -----
notepad_frame = tk.Frame(notebook)
notebook.add(notepad_frame, text="Notepad")

notepad_label = tk.Label(notepad_frame, text="Simple notepad for random notes:")
notepad_label.pack(pady=(10, 5))

notepad_text_widget = tk.Text(notepad_frame, wrap="word", height=12)
notepad_text_widget.pack(fill="both", expand=True, padx=8, pady=4)


def clear_notepad():
    notepad_text_widget.delete("1.0", tk.END)
    save_settings()


clear_notepad_button = tk.Button(notepad_frame, text="Clear notepad", command=clear_notepad)
clear_notepad_button.pack(pady=4)

# ----- Games tab -----
games_frame = tk.Frame(notebook)
notebook.add(games_frame, text="Games")

games_info = tk.Label(
    games_frame,
    text="Game launchers and offline practice.",
)
games_info.pack(pady=(10, 5))

open_forsaken_button = tk.Button(
    games_frame,
    text="Open Forsaken Generator Practice",
    command=open_forsaken_practice,
    width=30,
)
open_forsaken_button.pack(pady=4)

roblox_button = tk.Button(
    games_frame,
    text="Open Roblox",
    command=open_roblox,
    width=30,
)
roblox_button.pack(pady=4)

minecraft_button = tk.Button(
    games_frame,
    text="Open Minecraft Launcher",
    command=open_minecraft,
    width=30,
)
minecraft_button.pack(pady=4)

rng_game_button = tk.Button(
    games_frame,
    text="Open RNG Game",
    command=open_rng_game,
    width=30,
)
rng_game_button.pack(pady=4)

# ----- Settings tab -----
settings_frame = tk.Frame(notebook)
notebook.add(settings_frame, text="Settings")

always_on_top_var = tk.BooleanVar(value=False)
auto_update_var = tk.BooleanVar(value=False)

always_check = tk.Checkbutton(
    settings_frame,
    text="Always on top (keep window above others)",
    variable=always_on_top_var,
    command=apply_always_on_top,
)
always_check.pack(pady=(10, 4), anchor="w", padx=10)

auto_update_check = tk.Checkbutton(
    settings_frame,
    text="Automatically check for updates on launch",
    variable=auto_update_var,
    command=apply_auto_update,
)
auto_update_check.pack(pady=(0, 10), anchor="w", padx=10)

theme_mode_var = tk.StringVar(value="system")

theme_label = tk.Label(settings_frame, text="Theme:")
theme_label.pack(pady=(5, 0), anchor="w", padx=10)

theme_combo = ttk.Combobox(
    settings_frame,
    textvariable=theme_mode_var,
    values=["system", "light", "dark"],
    state="readonly",
    width=10,
)
theme_combo.pack(pady=3, anchor="w", padx=10)


def on_theme_change(event=None):
    apply_theme()
    save_settings()


theme_combo.bind("<<ComboboxSelected>>", on_theme_change)

update_button = tk.Button(settings_frame, text="Check for updates now", command=check_for_updates)
update_button.pack(pady=4, anchor="w", padx=10)

# ----- Status label + Quit button -----
status_var = tk.StringVar()
update_status()
status_label = tk.Label(root, textvariable=status_var, anchor="w", justify="left")
status_label.pack(fill="x", pady=2)


def on_close():
    global clicking, hotkey_listener, holding, hold_listener
    clicking = False
    if hotkey_listener is not None:
        try:
            hotkey_listener.stop()
        except Exception:
            pass
    stop_hold()
    if hold_listener is not None:
        try:
            hold_listener.stop()
        except Exception:
            pass
    save_settings()
    root.destroy()


quit_button = tk.Button(root, text="Quit", command=on_close)
quit_button.pack(pady=4)

# ----- Load settings and init -----
settings = load_settings()

# Restore Spam
if "spam_hotkey" in settings:
    spam_hotkey_entry.delete(0, "end")
    spam_hotkey_entry.insert(0, settings["spam_hotkey"])
if "spam_interval" in settings:
    interval_entry.delete(0, "end")
    interval_entry.insert(0, settings["spam_interval"])
if "spam_action_type" in settings:
    action_type_var.set(settings["spam_action_type"])
if "spam_key" in settings:
    key_entry.delete(0, "end")
    key_entry.insert(0, settings["spam_key"])
if "spam_mouse_button" in settings:
    mouse_button_var.set(settings["spam_mouse_button"])

# Restore Hold
if "hold_hotkey" in settings:
    hold_hotkey_entry.delete(0, "end")
    hold_hotkey_entry.insert(0, settings["hold_hotkey"])
if "hold_action_type" in settings:
    hold_action_type_var.set(settings["hold_action_type"])
if "hold_key" in settings:
    hold_key_entry.delete(0, "end")
    hold_key_entry.insert(0, settings["hold_key"])
if "hold_mouse_button" in settings:
    hold_mouse_button_var.set(settings["hold_mouse_button"])

# Restore CPS
if "cps_duration" in settings:
    cps_duration_spin.delete(0, "end")
    cps_duration_spin.insert(0, settings["cps_duration"])

# Restore theme
if "theme_mode" in settings:
    theme_mode_var.set(settings["theme_mode"])
else:
    theme_mode_var.set("system")

# Restore Always on top
if "always_on_top" in settings:
    always_on_top_var.set(settings["always_on_top"])
    apply_always_on_top()

# Restore auto update
if "auto_update" in settings:
    auto_update_var.set(settings["auto_update"])

# Restore notepad text
if "notepad_text" in settings and notepad_text_widget is not None:
    notepad_text_widget.delete("1.0", tk.END)
    notepad_text_widget.insert("1.0", settings["notepad_text"])

# Apply theme after widgets exist
apply_theme()

# Restore selected tab
if "selected_tab" in settings:
    try:
        notebook.select(settings["selected_tab"])
    except Exception:
        pass


def _hotkey_from_entry(entry, default_str):
    raw = entry.get().strip().lower()
    if not raw:
        return default_str
    if not raw.startswith("<"):
        return f"<{raw}>"
    return raw


start_spam_listener(_hotkey_from_entry(spam_hotkey_entry, "<f6>"))
start_hold_listener(_hotkey_from_entry(hold_hotkey_entry, "<f7>"))
update_status()

root.protocol("WM_DELETE_WINDOW", on_close)

# Auto-check for updates on launch if enabled
if auto_update_var.get():
    root.after(2000, check_for_updates)

root.mainloop()
