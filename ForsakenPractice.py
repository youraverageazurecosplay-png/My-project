import tkinter as tk
from tkinter import ttk, messagebox
import time
import json
import os
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(BASE_DIR, "forsaken_practice_save.json")

VERSION = "1.1"  # bump when you change this file


class ForsakenPracticeApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Forsaken Generator Practice (v{VERSION})")
        self.root.geometry("480x420")
        self.root.resizable(False, False)

        # Practice config
        self.sequence_length = 5
        self.allowed_keys = ["w", "a", "s", "d", "space"]
        self.current_sequence = []
        self.current_index = 0
        self.sequence_start_time = None

        # Stats
        self.total_sequences = 0
        self.completed_sequences = 0
        self.fastest_time = None  # seconds
        self.last_time = None

        self.load_stats()
        self.build_ui()
        self.new_sequence()

    # ===== Save / load =====
    def load_stats(self):
        if not os.path.exists(SAVE_PATH):
            return
        try:
            with open(SAVE_PATH, "r") as f:
                data = json.load(f)
        except Exception:
            return
        self.total_sequences = int(data.get("total_sequences", 0))
        self.completed_sequences = int(data.get("completed_sequences", 0))
        self.fastest_time = data.get("fastest_time", None)
        self.last_time = data.get("last_time", None)

    def save_stats(self):
        try:
            data = {
                "total_sequences": self.total_sequences,
                "completed_sequences": self.completed_sequences,
                "fastest_time": self.fastest_time,
                "last_time": self.last_time,
                "version": VERSION,
            }
            with open(SAVE_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            # silent fail
            pass

    # ===== UI =====
    def build_ui(self):
        main = tk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        title = tk.Label(main, text="Forsaken Generator Practice", font=("Helvetica", 16, "bold"))
        title.pack(pady=(0, 6))

        info = tk.Label(
            main,
            text="Type the sequence shown, in order, as fast as you can.\n"
                 "Keys: W, A, S, D, SPACE"
        )
        info.pack(pady=(0, 8))

        # Difficulty
        diff_frame = tk.Frame(main)
        diff_frame.pack(pady=(0, 6))

        tk.Label(diff_frame, text="Sequence length:").pack(side="left", padx=(0, 4))

        self.seq_len_var = tk.IntVar(value=self.sequence_length)
        seq_len_spin = tk.Spinbox(
            diff_frame,
            from_=3,
            to=12,
            width=4,
            textvariable=self.seq_len_var,
            command=self.apply_sequence_length
        )
        seq_len_spin.pack(side="left")

        new_btn = tk.Button(diff_frame, text="New sequence", command=self.new_sequence)
        new_btn.pack(side="left", padx=6)

        # Sequence display
        seq_frame = tk.Frame(main)
        seq_frame.pack(pady=(6, 6), fill="x")

        tk.Label(seq_frame, text="Sequence:").pack(anchor="w")

        self.sequence_var = tk.StringVar(value="")
        seq_label = tk.Label(
            seq_frame,
            textvariable=self.sequence_var,
            font=("Consolas", 18, "bold")
        )
        seq_label.pack pady=(0, 4)

        self.progress_var = tk.StringVar(value="")
        progress_label = tk.Label(seq_frame, textvariable=self.progress_var)
        progress_label.pack()

        # Feedback + stats
        fb_frame = tk.Frame(main)
        fb_frame.pack(pady=(6, 4), fill="x")

        self.feedback_var = tk.StringVar(value="Press the first key to start.")
        fb_label = tk.Label(fb_frame, textvariable=self.feedback_var, fg="blue")
        fb_label.pack(anchor="w")

        stats_frame = tk.Frame(main)
        stats_frame.pack(pady=(4, 4), fill="x")

        self.total_var = tk.StringVar()
        self.completed_var = tk.StringVar()
        self.fastest_var = tk.StringVar()
        self.last_var = tk.StringVar()

        tk.Label(stats_frame, textvariable=self.total_var).pack(anchor="w")
        tk.Label(stats_frame, textvariable=self.completed_var).pack(anchor="w")
        tk.Label(stats_frame, textvariable=self.fastest_var).pack(anchor="w")
        tk.Label(stats_frame, textvariable=self.last_var).pack(anchor="w")

        self.update_stats_labels()

        # Controls
        ctrl_frame = tk.Frame(main)
        ctrl_frame.pack(pady=(8, 0), fill="x")

        reset_stats_btn = tk.Button(ctrl_frame, text="Reset stats", command=self.reset_stats)
        reset_stats_btn.pack(side="left")

        quit_btn = tk.Button(ctrl_frame, text="Quit", command=self.on_close)
        quit_btn.pack(side="right")

        # Bind keys
        self.root.bind("<Key>", self.on_key_press)

    # ===== Logic =====
    def apply_sequence_length(self):
        try:
            n = int(self.seq_len_var.get())
            if n < 3:
                n = 3
            if n > 12:
                n = 12
            self.sequence_length = n
        except ValueError:
            self.sequence_length = 5
        self.seq_len_var.set(self.sequence_length)
        self.new_sequence()

    def make_random_sequence(self):
        seq = []
        for _ in range(self.sequence_length):
            key = random.choice(self.allowed_keys)
            seq.append(key)
        return seq

    def format_key(self, k):
        if k == "space":
            return "SPACE"
        return k.upper()

    def new_sequence(self):
        self.current_sequence = self.make_random_sequence()
        self.current_index = 0
        self.sequence_start_time = None

        formatted = "  ".join(self.format_key(k) for k in self.current_sequence)
        self.sequence_var.set(formatted)
        self.progress_var.set("Progress: 0 / {}".format(self.sequence_length))
        self.feedback_var.set("Press the first key in the sequence to start.")
        self.root.focus_set()

    def on_key_press(self, event):
        if not self.current_sequence:
            return

        # Normalize key
        key = event.keysym.lower()
        if key == " ":
            key = "space"

        if key not in self.allowed_keys:
            return

        # Start timer on first correct key
        if self.current_index == 0 and key == self.current_sequence[0]:
            self.sequence_start_time = time.time()

        expected = self.current_sequence[self.current_index]

        if key == expected:
            self.current_index += 1
            self.progress_var.set(f"Progress: {self.current_index} / {self.sequence_length}")
            self.feedback_var.set("Good!")

            if self.current_index == self.sequence_length:
                self.on_sequence_complete()
        else:
            self.feedback_var.set(f"Wrong key! Expected {self.format_key(expected)}.")
            # reset this sequence
            self.current_index = 0
            self.sequence_start_time = None
            self.progress_var.set(f"Progress: 0 / {self.sequence_length}")

    def on_sequence_complete(self):
        self.total_sequences += 1
        self.completed_sequences += 1

        if self.sequence_start_time is not None:
            elapsed = time.time() - self.sequence_start_time
        else:
            elapsed = 0.0

        self.last_time = elapsed
        if self.fastest_time is None or elapsed < self.fastest_time:
            self.fastest_time = elapsed

        self.feedback_var.set(f"Sequence complete in {elapsed:.2f}s! New one ready.")
        self.update_stats_labels()
        self.save_stats()

        # Generate next sequence
        self.current_index = 0
        self.sequence_start_time = None
        self.current_sequence = self.make_random_sequence()
        formatted = "  ".join(self.format_key(k) for k in self.current_sequence)
        self.sequence_var.set(formatted)
        self.progress_var.set("Progress: 0 / {}".format(self.sequence_length))

    def update_stats_labels(self):
        self.total_var.set(f"Total sequences attempted: {self.total_sequences}")
        self.completed_var.set(f"Sequences completed: {self.completed_sequences}")
        if self.fastest_time is not None:
            self.fastest_var.set(f"Best time: {self.fastest_time:.2f}s")
        else:
            self.fastest_var.set("Best time: -")
        if self.last_time is not None:
            self.last_var.set(f"Last time: {self.last_time:.2f}s")
        else:
            self.last_var.set("Last time: -")

    def reset_stats(self):
        if not messagebox.askyesno("Reset stats", "Really reset all stats?"):
            return
        self.total_sequences = 0
        self.completed_sequences = 0
        self.fastest_time = None
        self.last_time = None
        self.update_stats_labels()
        self.save_stats()

    def on_close(self):
        self.save_stats()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ForsakenPracticeApp(root)
    root.mainloop()
