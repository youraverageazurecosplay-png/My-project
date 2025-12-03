import random
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
import time

# ===== Version for this script =====
VERSION = "2.2"

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
    ("DEV",       1000000000000),  # ultra rare dev-only rarity
]

# Aura names per rarity (your edited list + DEV)
AURAS = {
    "Common":    ["Common", "Uncommon", "Rare", "Crystallised"],
    "Uncommon":  ["Powered", "Undead", "Siderium", "Storm"],
    "Rare":      ["Undead: Devil", "Comet", "Aether"],
    "Epic":      ["Eclipse", "Supernova", "Diaboli: Void"],
    "Legendary": ["Poisoned", "Celestial", "Prism"],
    "Mythic":    ["Archangel", "Memory", "Perplexed"],
    "Divine":    ["Perplexed: Pixels", "Oblivion", "Luminosity"],
    "DEV":       ["DEV"],   # single dev-only aura
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(BASE_DIR, "rng_save.json")

COOLDOWN_SECS = 10 * 60        # 10 minutes
LUCK_BOOST_FACTOR = 15         # Normal potion
CELESTIAL_BOOST_FACTOR = 100   # Celestial potion
INSANE_BOOST_FACTOR = 100000000000000  # Secret insane multiplier

ROLL_INTERVAL_SEC = 0.5        # autoroll speed (seconds)

SECRET_CODE = "1028777"

# Money for selling auras
PRICE_PER_RARITY = {
    "Common": 1,
    "Uncommon": 5,
    "Rare": 25,
    "Epic": 100,
    "Legendary": 500,
    "Mythic": 5000,
    "Divine": 25000,
    "DEV": 0,  # cannot sell DEV
}

# Glove recipes (crafting)
GLOVE_RECIPES = [
    {
        "name": "Celestial Glove",
        "cost": 10000,
        "required_auras": [("Celestial", "Legendary")],
    },
    {
        "name": "Mythic Glove",
        "cost": 25000,
        "required_auras": [("Archangel", "Mythic"), ("Memory", "Mythic")],
    },
    {
        "name": "Divine Glove",
        "cost": 100000,
        "required_auras": [("Perplexed: Pixels", "Divine")],
    },
    {
        "name": "Admin Glove",
        "cost": 0,
        "required_auras": [("DEV", "DEV")],  # only from DEV aura
    },
]


# ===== RNG helpers =====
def build_weights(boost_factor=1.0):
    weights = []
    for name, one_in in RARITIES:
        if boost_factor > 1 and name not in ("Common", "DEV"):
            weights.append(1 / max(1, one_in // int(boost_factor)))
        else:
            weights.append(1 / one_in)
    total = sum(weights)
    probs = [w / total for w in weights]
    return probs

def choose_rarity(boost_factor=1.0):
    r_names = [r[0] for r in RARITIES]
    rarity = random.choices(r_names, weights=build_weights(boost_factor), k=1)[0]
    return rarity

def odds_for_rarity(rarity_name, boost_factor=1.0):
    for name, one_in in RARITIES:
        if name == rarity_name:
            if boost_factor > 1 and name not in ("Common", "DEV"):
                return max(1, one_in // int(boost_factor))
            return one_in
    return None


class RNGGame:
    def __init__(self, root):
        self.root = root
        self.root.title("RNG Game")
        self.root.geometry("560x480")
        self.root.resizable(False, False)

        # Game state
        self.total_rolls = 0
        self.best_rarity_index = None
        self.best_aura = "None"
        self.inventory = []

        # Currency and gloves
        self.money = 0
        self.gloves = []  # list of glove names

        # Potion system
        self.last_used_potion_time = 0
        self.last_used_celestial_potion_time = 0
        self.luck_boost_factor_next_roll = 1.0

        # Custom luck (persistent until disabled)
        self.custom_luck_enabled = False
        self.custom_luck_value = 1.0

        # Dev potion (guarantees DEV aura next roll)
        self.dev_potion_next_roll_dev = False

        # Autoroll system
        self.autoroll_enabled = False
        self.autoroll_job = None

        # Widgets / text vars
        self.potion_button = None
        self.celestial_button = None
        self.countdown_var = tk.StringVar()
        self.celestial_countdown_var = tk.StringVar()

        # Dev tools fields
        self.autoroll_interval_var = tk.StringVar(value=str(ROLL_INTERVAL_SEC))
        self.custom_luck_var = tk.StringVar(value="1")
        self.custom_luck_status_var = tk.StringVar(value="Custom luck: OFF")

        # UI stats vars
        self.total_rolls_var = tk.StringVar()
        self.best_aura_var = tk.StringVar()
        self.best_rarity_var = tk.StringVar()
        self.money_var = tk.StringVar()

        self.load_game()
        self.build_ui()
        self.check_potion_cooldown()
        self.check_celestial_potion_cooldown()
        self.update_stats()
        self.update_money_label()
        self.update_custom_luck_status()

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
        self.money = int(data.get("money", 0))
        self.gloves = data.get("gloves", [])

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
                "money": self.money,
                "gloves": self.gloves,
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

        # Row 1: roll + inventory + sell
        row1 = tk.Frame(main)
        row1.pack()

        roll_btn = tk.Button(row1, text="Roll!", font=("Helvetica", 14), width=10, command=self.roll)
        roll_btn.pack(side="left", padx=3)

        inv_btn = tk.Button(row1, text="View Inventory", font=("Helvetica", 10), command=self.open_inventory_window)
        inv_btn.pack(side="left", padx=3)

        sell_btn = tk.Button(row1, text="Sell All", font=("Helvetica", 10), command=self.sell_all_auras)
        sell_btn.pack(side="left", padx=3)

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

        tk.Label(main, textvariable=self.total_rolls_var).pack()
        tk.Label(main, textvariable=self.best_aura_var).pack()
        tk.Label(main, textvariable=self.best_rarity_var).pack()
        tk.Label(main, textvariable=self.money_var).pack(pady=(2, 0))

        # Custom luck status label
        tk.Label(main, textvariable=self.custom_luck_status_var, fg="orange").pack(pady=(4, 0))

        # Glove shop button
        shop_btn = tk.Button(
            main,
            text="Open Glove Shop",
            font=("Helvetica", 10),
            command=self.open_glove_shop
        )
        shop_btn.pack(pady=(4, 2))

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
        self.root
import random
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
import time

# ===== Version for this script =====
VERSION = "2.2"

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
    ("DEV",       1000000000000),  # ultra rare dev-only rarity
]

# Aura names per rarity (your edited list + DEV)
AURAS = {
    "Common":    ["Common", "Uncommon", "Rare", "Crystallised"],
    "Uncommon":  ["Powered", "Undead", "Siderium", "Storm"],
    "Rare":      ["Undead: Devil", "Comet", "Aether"],
    "Epic":      ["Eclipse", "Supernova", "Diaboli: Void"],
    "Legendary": ["Poisoned", "Celestial", "Prism"],
    "Mythic":    ["Archangel", "Memory", "Perplexed"],
    "Divine":    ["Perplexed: Pixels", "Oblivion", "Luminosity"],
    "DEV":       ["DEV"],   # single dev-only aura
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(BASE_DIR, "rng_save.json")

COOLDOWN_SECS = 10 * 60        # 10 minutes
LUCK_BOOST_FACTOR = 15         # Normal potion
CELESTIAL_BOOST_FACTOR = 100   # Celestial potion
INSANE_BOOST_FACTOR = 100000000000000  # Secret insane multiplier

ROLL_INTERVAL_SEC = 0.5        # autoroll speed (seconds)

SECRET_CODE = "1028777"

# Money for selling auras
PRICE_PER_RARITY = {
    "Common": 1,
    "Uncommon": 5,
    "Rare": 25,
    "Epic": 100,
    "Legendary": 500,
    "Mythic": 5000,
    "Divine": 25000,
    "DEV": 0,  # cannot sell DEV
}

# Glove recipes (crafting)
GLOVE_RECIPES = [
    {
        "name": "Celestial Glove",
        "cost": 10000,
        "required_auras": [("Celestial", "Legendary")],
    },
    {
        "name": "Mythic Glove",
        "cost": 25000,
        "required_auras": [("Archangel", "Mythic"), ("Memory", "Mythic")],
    },
    {
        "name": "Divine Glove",
        "cost": 100000,
        "required_auras": [("Perplexed: Pixels", "Divine")],
    },
    {
        "name": "Admin Glove",
        "cost": 0,
        "required_auras": [("DEV", "DEV")],  # only from DEV aura
    },
]


# ===== RNG helpers =====
def build_weights(boost_factor=1.0):
    weights = []
    for name, one_in in RARITIES:
        if boost_factor > 1 and name not in ("Common", "DEV"):
            weights.append(1 / max(1, one_in // int(boost_factor)))
        else:
            weights.append(1 / one_in)
    total = sum(weights)
    probs = [w / total for w in weights]
    return probs

def choose_rarity(boost_factor=1.0):
    r_names = [r[0] for r in RARITIES]
    rarity = random.choices(r_names, weights=build_weights(boost_factor), k=1)[0]
    return rarity

def odds_for_rarity(rarity_name, boost_factor=1.0):
    for name, one_in in RARITIES:
        if name == rarity_name:
            if boost_factor > 1 and name not in ("Common", "DEV"):
                return max(1, one_in // int(boost_factor))
            return one_in
    return None


class RNGGame:
    def __init__(self, root):
        self.root = root
        self.root.title("RNG Game")
        self.root.geometry("560x480")
        self.root.resizable(False, False)

        # Game state
        self.total_rolls = 0
        self.best_rarity_index = None
        self.best_aura = "None"
        self.inventory = []

        # Currency and gloves
        self.money = 0
        self.gloves = []  # list of glove names

        # Potion system
        self.last_used_potion_time = 0
        self.last_used_celestial_potion_time = 0
        self.luck_boost_factor_next_roll = 1.0

        # Custom luck (persistent until disabled)
        self.custom_luck_enabled = False
        self.custom_luck_value = 1.0

        # Dev potion (guarantees DEV aura next roll)
        self.dev_potion_next_roll_dev = False

        # Autoroll system
        self.autoroll_enabled = False
        self.autoroll_job = None

        # Widgets / text vars
        self.potion_button = None
        self.celestial_button = None
        self.countdown_var = tk.StringVar()
        self.celestial_countdown_var = tk.StringVar()

        # Dev tools fields
        self.autoroll_interval_var = tk.StringVar(value=str(ROLL_INTERVAL_SEC))
        self.custom_luck_var = tk.StringVar(value="1")
        self.custom_luck_status_var = tk.StringVar(value="Custom luck: OFF")

        # UI stats vars
        self.total_rolls_var = tk.StringVar()
        self.best_aura_var = tk.StringVar()
        self.best_rarity_var = tk.StringVar()
        self.money_var = tk.StringVar()

        self.load_game()
        self.build_ui()
        self.check_potion_cooldown()
        self.check_celestial_potion_cooldown()
        self.update_stats()
        self.update_money_label()
        self.update_custom_luck_status()

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
        self.money = int(data.get("money", 0))
        self.gloves = data.get("gloves", [])

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
                "money": self.money,
                "gloves": self.gloves,
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

        # Row 1: roll + inventory + sell
        row1 = tk.Frame(main)
        row1.pack()

        roll_btn = tk.Button(row1, text="Roll!", font=("Helvetica", 14), width=10, command=self.roll)
        roll_btn.pack(side="left", padx=3)

        inv_btn = tk.Button(row1, text="View Inventory", font=("Helvetica", 10), command=self.open_inventory_window)
        inv_btn.pack(side="left", padx=3)

        sell_btn = tk.Button(row1, text="Sell All", font=("Helvetica", 10), command=self.sell_all_auras)
        sell_btn.pack(side="left", padx=3)

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

        tk.Label(main, textvariable=self.total_rolls_var).pack()
        tk.Label(main, textvariable=self.best_aura_var).pack()
        tk.Label(main, textvariable=self.best_rarity_var).pack()
        tk.Label(main, textvariable=self.money_var).pack(pady=(2, 0))

        # Custom luck status label
        tk.Label(main, textvariable=self.custom_luck_status_var, fg="orange").pack(pady=(4, 0))

        # Glove shop button
        shop_btn = tk.Button(
            main,
            text="Open Glove Shop",
            font=("Helvetica", 10),
            command=self.open_glove_shop
        )
        shop_btn.pack(pady=(4, 2))

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
            self.potion_button.
