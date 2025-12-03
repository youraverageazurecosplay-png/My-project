import random
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
import time

# ===== Version for this script =====
VERSION = "2.9"

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
    "Common
