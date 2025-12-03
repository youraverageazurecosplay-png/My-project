import random
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
import time

# ===== Version for this script =====
VERSION = "1.2"  # bump this when you change rng_game.py

# ===== Configuration =====
# Rarity tiers and base odds: 1 in X
RARITIES = [
    ("Common",    1),
    ("Uncommon",  5),
    ("Rare",      25),
    ("Epic",      250),
    ("Legendary", 2500),
    ("Mythic",    100000),
    ("Divine",    1000000000),
]

# Aura names per rarity (your edited list)
AURAS = {
    "Common":    ["Common", "Uncommon", "Rare", "Crystallised"],
    "Uncommon":  ["Powered", "Undead", "Siderium", "Storm"],
    "Rare":      ["Undead: Devil", "Comet", "Aether"],
    "Epic":      ["Eclipse", "Supernova", "Diaboli: Void"],
    "Legendary": ["Poisoned", "Celestial", "Prism"],
    "Mythic":    ["Archangel", "Memory", "Perplexed"],
    "Mythic":    ["Perplexed: Pixels", "Oblivion", "Luminosity"],
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(BASE_DIR, "rng_save.json")

COOLDOWN_SECS = 10 * 60        # 10 minutes
LUCK_BOOST_FACTOR = 15         # Normal potion
CELESTIAL_BOOST_FACTOR = 100   # Celestial potion
INSANE_BOOST_FACTOR = 100000000000000 # Secret insane multiplier

ROLL_INTERVAL_SEC = 0.5        # autoroll speed

SECRET_CODE = "1028777"


# ===== RNG helpers =====
def build_weights(boost_factor=1):
    weights = []
    for name, one_in in RARITIES:
        if boost_factor > 1 and name != "Common":
            weights.append(1 / max(1, one_in // boost_factor))
        else:
            weights.append(1 / one_in)
    total = sum(weights)
    probs = [w / total for w in weights]
    return probs

def choose_rarity(boost_factor=1):
    r_names = [r[0] for r in RARITIES]
    rarity = random.choices(r_names, weights=build_weights(boost_factor), k=1)[0]
    return rarity

def odds_for_rarity(rarity_name, boost_factor=1):
    for name, one_in in RARITIES:
        if name == rarity_name:
            if boost_factor > 1 and name != "Common":
                return max(1, one_in // boost_factor)
            return one_in
    return None


class RNGGame:
    def __init__(self, root):
        self.root = root
        self.root.title("RNG Game")
        self.root.geometry("540x400")
        self.root.resizable(False, False)

        # Game state
        self.total_rolls = 0
        self.best_rarity_index = None
        self.best_aura = "None"
        self.inventory = []

        # Potion system
        self.last_used_potion_time = 0
        self.last_used_celestial_potion_time = 0
        self.luck_boost_factor_next_roll = 1

        # Autoroll system
        self.autoroll_enabled = False
        self.autoroll_job = None

        # Widgets / text vars
        self.potion_button = None
        self.celestial_button = None
        self.countdown_var = tk.StringVar()
        self.celestial_countdown_var = tk.StringVar()

        self.load_game()
        self.build_ui()
        self.check_potion_cooldown()
        self.check_celestial_potion_cooldown()
        self.update_stats()

    # ===== Save / load =====
    def load_game(self):
        if not os.path.exists(SAVE_PATH):
            return
        try:
            with open(SAVE_PATH, "r") as f:
                data = json.load(f)
        except Exception:
            return

        self.total_rolls = int(data.get("total_rolls", 0))
        self.best_aura = data.get("best_aura", "None")
        best_rarity_name = data.get("best_rarity", None)
        if best_rarity_name is not None:
            self.best_rarity_index = self.rarity_index(best_rarity_name)
        else:
            self.best_rarity_index = None

        self.inventory = data.get("inventory", [])
        self.last_used_potion_time = float(data.get("last_used_potion_time", 0))
        self.last_used_celestial_potion_time = float(data.get("last_used_celestial_potion_time", 0))
        # autoroll state is not persisted on purpose (always off on start)

    def save_game(self):
        try:
            best_rarity_name = None
            if self.best_rarity_index is not None:
                best_rarity_name = RARITIES[self.best_rarity_index][0]
            data = {
                "total_rolls": self.total_rolls,
                "best_aura": self.best_aura,
                "best_rarity": best_rarity_name,
                "inventory": self.inventory,
                "last_used_potion_time": self.last_used_potion_time,
                "last_used_celestial_potion_time": self.last_used_celestial_potion_time,
                "rng_game_version": VERSION,
            }
            with open(SAVE_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save RNG game:\n{e}")

    # ===== UI =====
    def build_ui(self):
        main = tk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        title = tk.Label(main, text=f"RNG Roll Game (v{VERSION})", font=("Helvetica", 16, "bold"))
        title.pack(pady=(0, 10))

        # Row 1: roll + inventory
        row1 = tk.Frame(main)
        row1.pack()

        roll_btn = tk.Button(row1, text="Roll!", font=("Helvetica", 14), width=10, command=self.roll)
        roll_btn.pack(side="left", padx=3)

        inv_btn = tk.Button(row1, text="View Inventory", font=("Helvetica", 10), command=self.open_inventory_window)
        inv_btn.pack(side="left", padx=3)

        # Row 2: potions
        row2 = tk.Frame(main)
        row2.pack(pady=(4, 0))

        self.potion_button = tk.Button(
            row2,
            text=f"Use Luck Potion (x{LUCK_BOOST_FACTOR})",
            font=("Helvetica", 10),
            command=self.use_potion
        )
        self.potion_button.pack(side="left", padx=3)

        self.celestial_button = tk.Button(
            row2,
            text=f"Use Celestial Potion (x{CELESTIAL_BOOST_FACTOR})",
            font=("Helvetica", 10),
            command=self.use_celestial_potion
        )
        self.celestial_button.pack(side="left", padx=3)

        # Cooldowns
        self.cd_label = tk.Label(main, textvariable=self.countdown_var, fg="green", font=("Helvetica", 11))
        self.cd_label.pack(pady=(4, 0))

        self.celestial_cd_label = tk.Label(main, textvariable=self.celestial_countdown_var, fg="purple", font=("Helvetica", 11))
        self.celestial_cd_label.pack(pady=(0, 4))

        # Secret code button
        secret_btn = tk.Button(
            main,
            text="Enter Secret Code",
            font=("Helvetica", 9),
            command=self.open_code_prompt
        )
        secret_btn.pack(pady=(0, 4))

        # Last roll info
        self.last_aura_var = tk.StringVar(value="Last Aura: None")
        self.last_rarity_var = tk.StringVar(value="Rarity: -")
        self.last_odds_var = tk.StringVar(value="Odds: -")

        tk.Label(main, textvariable=self.last_aura_var).pack(pady=(8, 0))
        tk.Label(main, textvariable=self.last_rarity_var).pack()
        tk.Label(main, textvariable=self.last_odds_var).pack()

        # Stats
        sep = ttk.Separator(main, orient="horizontal")
        sep.pack(fill="x", pady=8)

        self.total_rolls_var = tk.StringVar()
        self.best_aura_var = tk.StringVar()
        self.best_rarity_var = tk.StringVar()

        tk.Label(main, textvariable=self.total_rolls_var).pack()
        tk.Label(main, textvariable=self.best_aura_var).pack()
        tk.Label(main, textvariable=self.best_rarity_var).pack()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ===== Potion System =====
    def check_potion_cooldown(self):
        now = time.time()
        rem = int(self.last_used_potion_time + COOLDOWN_SECS - now)
        if rem > 0:
            mins, secs = divmod(rem, 60)
            if self.potion_button is not None:
                self.potion_button.config(state="disabled")
            self.countdown_var.set(f"Luck Potion cooldown: {mins:02d}:{secs:02d} left")
            self.root.after(1000, self.check_potion_cooldown)
        else:
            self.countdown_var.set("")
            if self.potion_button is not None:
                self.potion_button.config(state="normal")

    def check_celestial_potion_cooldown(self):
        now = time.time()
        rem = int(self.last_used_celestial_potion_time + COOLDOWN_SECS - now)
        if rem > 0:
            mins, secs = divmod(rem, 60)
            if self.celestial_button is not None:
                self.celestial_button.config(state="disabled")
            self.celestial_countdown_var.set(f"Celestial Potion cooldown: {mins:02d}:{secs:02d} left")
            self.root.after(1000, self.check_celestial_potion_cooldown)
        else:
            self.celestial_countdown_var.set("")
            if self.celestial_button is not None:
                self.celestial_button.config(state="normal")

    def use_potion(self):
        now = time.time()
        if now < self.last_used_potion_time + COOLDOWN_SECS:
            return
        self.luck_boost_factor_next_roll = LUCK_BOOST_FACTOR
        self.last_used_potion_time = now
        self.countdown_var.set("Luck Potion active! Your next roll is boosted!")
        if self.potion_button is not None:
            self.potion_button.config(state="disabled")
        self.save_game()
        self.root.after(1000, self.check_potion_cooldown)

    def use_celestial_potion(self):
        now = time.time()
        if now < self.last_used_celestial_potion_time + COOLDOWN_SECS:
            return
        self.luck_boost_factor_next_roll = CELESTIAL_BOOST_FACTOR
        self.last_used_celestial_potion_time = now
        self.celestial_countdown_var.set("Celestial Potion active! Your next roll is insanely lucky!")
        if self.celestial_button is not None:
            self.celestial_button.config(state="disabled")
        self.save_game()
        self.root.after(1000, self.check_celestial_potion_cooldown)

    # ===== Secret Code & Special GUI =====
    def open_code_prompt(self):
        win = tk.Toplevel(self.root)
        win.title("Enter Code")
        win.geometry("260x120")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(frame, text="Enter secret code:").pack(anchor="w")

        code_var = tk.StringVar()
        entry = tk.Entry(frame, textvariable=code_var, show="*")
        entry.pack(fill="x", pady=4)
        entry.focus_set()

        def submit():
            code = code_var.get().strip()
            if code == SECRET_CODE:
                win.destroy()
                self.open_special_gui()
            else:
                messagebox.showerror("Wrong Code", "That code is not correct.")
                code_var.set("")
                entry.focus_set()

        submit_btn = tk.Button(frame, text="Submit", command=submit)
        submit_btn.pack(pady=4)

        win.bind("<Return>", lambda e: submit())

    def open_special_gui(self):
        win = tk.Toplevel(self.root)
        win.title("dev tools :3")
        win.geometry("420x260")
        win.resizable(False, False)

        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        title = tk.Label(frame, text="Sneaky Dev Tools", font=("Helvetica", 14, "bold"))
        title.pack(pady=(0, 8))

        info = tk.Label(
            frame,
            text="You unlocked the secret menu.\nDeveloper / cheat tools here."
        )
        info.pack(pady=(0, 8))

        stats = tk.Label(
            frame,
            text=f"Total Rolls: {self.total_rolls}\nBest Aura: {self.best_aura}"
        )
        stats.pack(pady=4)

        # Buttons in secret menu
        btn_row1 = tk.Frame(frame)
        btn_row1.pack(pady=(6, 2))

        reset_cd_btn = tk.Button(
            btn_row1,
            text="Reset Potion Cooldowns",
            command=self.reset_potion_cooldowns
        )
        reset_cd_btn.pack(side="left", padx=4)

        insane_btn = tk.Button(
            btn_row1,
            text="Next Roll x10,000,000",
            command=self.set_insane_multiplier
        )
        insane_btn.pack(side="left", padx=4)

        btn_row2 = tk.Frame(frame)
        btn_row2.pack(pady=(4, 6))

        autoroll_toggle_btn = tk.Button(
            btn_row2,
            text="Toggle Autoroll",
            command=self.toggle_autoroll
        )
        autoroll_toggle_btn.pack(side="left", padx=4)

        close_btn = tk.Button(frame, text="Close", command=win.destroy)
        close_btn.pack(pady=8)

    def reset_potion_cooldowns(self):
        self.last_used_potion_time = 0
        self.last_used_celestial_potion_time = 0
        self.check_potion_cooldown()
        self.check_celestial_potion_cooldown()
        self.save_game()
        messagebox.showinfo("Potions", "Potion cooldowns have been reset.")

    def set_insane_multiplier(self):
        self.luck_boost_factor_next_roll = INSANE_BOOST_FACTOR
        messagebox.showinfo("Insane Boost", "Next roll will use x10,000,000 multiplier!")

    # ===== Autoroll =====
    def toggle_autoroll(self):
        self.autoroll_enabled = not self.autoroll_enabled
        if self.autoroll_enabled:
            messagebox.showinfo("Autoroll", "Autoroll enabled. Rolling automatically.")
            self.schedule_next_autoroll()
        else:
            self.stop_autoroll()
            messagebox.showinfo("Autoroll", "Autoroll disabled.")

    def schedule_next_autoroll(self):
        if not self.autoroll_enabled:
            return
        self.autoroll_job = self.root.after(int(ROLL_INTERVAL_SEC * 1000), self.autoroll_tick)

    def autoroll_tick(self):
        if not self.autoroll_enabled:
            return
        self.roll()
        self.schedule_next_autoroll()

    def stop_autoroll(self):
        if self.autoroll_job is not None:
            try:
                self.root.after_cancel(self.autoroll_job)
            except Exception:
                pass
            self.autoroll_job = None

    # ===== Inventory helpers =====
    def rarity_index(self, rarity_name):
        for i, (name, _) in enumerate(RARITIES):
            if name == rarity_name:
                return i
        return None

    def is_rarity_better(self, new_rarity):
        idx_new = self.rarity_index(new_rarity)
        if idx_new is None:
            return False
        if self.best_rarity_index is None:
            return True
        return idx_new > self.best_rarity_index

    def add_to_inventory(self, aura_name, rarity):
        for item in self.inventory:
            if item["aura"] == aura_name and item["rarity"] == rarity:
                item["count"] += 1
                return
        self.inventory.append({"aura": aura_name, "rarity": rarity, "count": 1})

    # ===== Inventory window =====
    def open_inventory_window(self):
        win = tk.Toplevel(self.root)
        win.title("Inventory")
        win.geometry("380x260")
        win.resizable(False, False)

        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True, padx=8, pady=8)

        info_label = tk.Label(frame, text="All auras you have rolled (name, rarity, count):")
        info_label.pack(pady=(0, 5), anchor="w")

        list_frame = tk.Frame(frame)
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def rarity_sort_key(item):
            idx = self.rarity_index(item["rarity"])
            return (idx if idx is not None else -1, item["aura"])

        sorted_inv = sorted(self.inventory, key=rarity_sort_key)

        if not sorted_inv:
            listbox.insert("end", "No auras yet. Start rolling!")
        else:
            for item in sorted_inv:
                text = f'{item["aura"]}  |  {item["rarity"]}  |  x{item["count"]}'
                listbox.insert("end", text)

        close_btn = tk.Button(frame, text="Close", command=win.destroy)
        close_btn.pack(pady=6)

    # ===== Core game =====
    def roll(self):
        self.total_rolls += 1

        boost = self.luck_boost_factor_next_roll
        rarity = choose_rarity(boost_factor=boost)
        odds = odds_for_rarity(rarity, boost_factor=boost)

        # boost applies only to this one roll
        self.luck_boost_factor_next_roll = 1

        aura_list = AURAS.get(rarity, ["Unknown"])
        aura_name = random.choice(aura_list)

        self.add_to_inventory(aura_name, rarity)

        self.last_aura_var.set(f"Last Aura: {aura_name}")
        self.last_rarity_var.set(f"Rarity: {rarity}")
        if odds is not None:
            self.last_odds_var.set(f"Odds: 1 in {odds}")
        else:
            self.last_odds_var.set("Odds: -")

        if self.is_rarity_better(rarity):
            self.best_rarity_index = self.rarity_index(rarity)
            self.best_aura = aura_name

        self.update_stats()
        self.save_game()

    def update_stats(self):
        self.total_rolls_var.set(f"Total Rolls: {self.total_rolls}")
        self.best_aura_var.set(f"Best Aura: {self.best_aura}")
        if self.best_rarity_index is None:
            self.best_rarity_var.set("Best Rarity: None")
        else:
            self.best_rarity_var.set(f"Best Rarity: {RARITIES[self.best_rarity_index][0]}")

    def on_close(self):
        self.stop_autoroll()
        self.save_game()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    game = RNGGame(root)
    root.mainloop()
