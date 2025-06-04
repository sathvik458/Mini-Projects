import tkinter as tk
import psutil
import platform
import time
import threading


class PowerHud:
    def __init__(self, win):
        self.win = win
        win.title("Power HUD")
        win.geometry("320x180+50+50")
        win.configure(bg="black")
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-transparentcolor", "black")
        win.bind("<Double-Button-1>", self.toggle_visibility)


        self.visible = True

        self.font_big = ("Consolas", 32, "bold")
        self.font_mid = ("Consolas", 14, "bold")
        self.font_small = ("Consolas", 11)

        self.cpu_name = platform.processor() or "Unknown CPU"
        freq = psutil.cpu_freq()
        self.cpu_max_ghz = round(freq.max / 1000, 1) if freq else 0

        self.cpu_tdp = self.ask_cpu_tdp()

        self.batt_lbl = tk.Label(win, text="--%", font=self.font_big, fg="#39FF14", bg="black")
        self.batt_lbl.pack(pady=(10, 0))

        self.state_lbl = tk.Label(win, text="DISCHARGING", font=self.font_mid, fg="#FF4444", bg="black")
        self.state_lbl.pack()

        self.cpu_lbl = tk.Label(win, text="CPU: 0.0 W", font=self.font_mid, fg="orange", bg="black")
        self.cpu_lbl.pack(pady=4)

        self.time_lbl = tk.Label(win, text="Estimating...", font=self.font_small, fg="#AAAAAA", bg="black")
        self.time_lbl.pack()

        self.info_lbl = tk.Label(
            win,
            text=f"{self.cpu_name} @ {self.cpu_max_ghz}GHz | TDP {self.cpu_tdp}W",
            font=self.font_small,
            fg="#666666",
            bg="black"
        )
        self.info_lbl.pack(pady=(2, 0))

        self.prev_pct = None
        self.prev_time = None
        self.drain_avg = None
        self.cpu_watt_smooth = 0.0

        win.bind("<Button-1>", self._drag_start)
        win.bind("<B1-Motion>", self._drag_move)

        # global hotkey in background thread
        threading.Thread(target=self._hotkey_loop, daemon=True).start()

        self.loop()

    def _hotkey_loop(self):
        keyboard.add_hotkey("ctrl+shift+h", self.toggle_visibility)
        keyboard.wait()
    def toggle_visibility(self, event=None):
        if self.visible:
            self.win.withdraw()
        else:
            self.win.deiconify()
            self.win.focus_force()
        self.visible = not self.visible





    def ask_cpu_tdp(self):
        popup = tk.Toplevel(self.win)
        popup.title("CPU TDP")
        popup.geometry("260x120+200+200")
        popup.configure(bg="black")
        popup.attributes("-topmost", True)

        tk.Label(popup, text="Enter CPU TDP (Watts)", fg="white", bg="black").pack(pady=10)

        entry = tk.Entry(popup, justify="center")
        entry.insert(0, "45")
        entry.pack()

        result = {"tdp": 45}

        def submit():
            try:
                result["tdp"] = float(entry.get())
            except ValueError:
                pass
            popup.destroy()

        tk.Button(popup, text="OK", command=submit).pack(pady=8)
        popup.grab_set()
        self.win.wait_window(popup)

        return result["tdp"]

    def _drag_start(self, e):
        self._dx = e.x
        self._dy = e.y

    def _drag_move(self, e):
        self.win.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def cpu_watts_estimate(self):
        load = psutil.cpu_percent(interval=0.3)
        watts = (load / 100) * self.cpu_tdp
        self.cpu_watt_smooth = 0.7 * self.cpu_watt_smooth + 0.3 * watts
        return self.cpu_watt_smooth

    def loop(self):
        batt = psutil.sensors_battery()
        now = time.time()

        if batt:
            pct = batt.percent
            plugged = batt.power_plugged
            secs_left = batt.secsleft
        else:
            pct, plugged, secs_left = 0, False, -1

        col = "#39FF14" if pct > 50 else "orange" if pct > 20 else "red"
        self.batt_lbl.config(text=f"{int(pct)}%", fg=col)

        self.state_lbl.config(
            text="CHARGING" if plugged else "DISCHARGING",
            fg="cyan" if plugged else "#FF4444"
        )

        cpu_w = self.cpu_watts_estimate()
        self.cpu_lbl.config(text=f"CPU: {cpu_w:.1f} W")

        if plugged:
            self.time_lbl.config(text="Power Connected")
        elif 0 < secs_left < 86400:
            h, rem = divmod(secs_left, 3600)
            m, _ = divmod(rem, 60)
            self.time_lbl.config(text=f"{h:02}:{m:02} remaining")
        elif self.prev_pct is not None:
            dp = self.prev_pct - pct
            dt = now - self.prev_time
            if dp > 0 and dt > 0:
                rate = (dp / dt) * 60
                self.drain_avg = rate if self.drain_avg is None else 0.3 * rate + 0.7 * self.drain_avg
                mins = pct / self.drain_avg
                h, m = divmod(mins, 60)
                self.time_lbl.config(text=f"{int(h):02}:{int(m):02} predicted")

        self.prev_pct = pct
        self.prev_time = now

        self.win.after(1000, self.loop)


if __name__ == "__main__":
    root = tk.Tk()
    PowerHud(root)
    root.mainloop()
