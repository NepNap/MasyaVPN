import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
import tkinter as tk
from tkinter import messagebox

# ==== ВШИТАЯ sing-box подписка (замени на свой subId при необходимости) ====
DEFAULT_URL = "http://103.245.229.41/singbox/iou2aco9coby82qo"

CONFIG_PATH = os.path.join(tempfile.gettempdir(), "vpn_singbox_config.json")


def resource_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


SINGBOX = os.path.join(resource_dir(), "sing-box.exe")
WINTUN = os.path.join(resource_dir(), "wintun.dll")


class VpnApp:
    def __init__(self, root):
        self.root = root
        self.proc = None
        self.logf = None

        root.title("VPN")
        root.geometry("500x130")
        root.resizable(False, False)

        self.url = tk.StringVar(value=DEFAULT_URL)

        frame = tk.Frame(root, padx=14, pady=12)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Подписка (sing-box URL):", anchor="w").pack(fill="x")
        tk.Entry(frame, textvariable=self.url, width=64).pack(fill="x", pady=(2, 10))

        self.button = tk.Button(frame, text="Запустить", height=2, command=self.toggle)
        self.button.pack(fill="x")

        self.status = tk.Label(frame, text="Отключено", fg="#888888", anchor="w")
        self.status.pack(fill="x", pady=(8, 0))

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def set_status(self, text, color="#333333"):
        self.status.config(text=text, fg=color)

    def toggle(self):
        if self.proc and self.proc.poll() is None:
            self.stop()
        else:
            self.start()

    def start(self):
        url = self.url.get().strip()
        if not url:
            messagebox.showerror("VPN", "Укажи ссылку подписки")
            return
        if not os.path.exists(SINGBOX):
            messagebox.showerror("VPN", "Не найден sing-box.exe (сборка повреждена)")
            return

        self.button.config(state="disabled")
        self.set_status("Загрузка конфига...")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "singbox-client"})
            data = urllib.request.urlopen(req, timeout=25).read()
            json.loads(data)  # проверка, что это валидный JSON
            with open(CONFIG_PATH, "wb") as f:
                f.write(data)
        except Exception as e:
            self.button.config(state="normal")
            self.set_status("Ошибка загрузки конфига", "#bb0000")
            messagebox.showerror("VPN", "Не удалось скачать конфиг:\n%s" % e)
            return

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        log_path = os.path.join(tempfile.gettempdir(), "vpn_singbox_log.txt")
        try:
            self.logf = open(log_path, "w", encoding="utf-8")
            self.proc = subprocess.Popen(
                [SINGBOX, "run", "-c", CONFIG_PATH],
                cwd=resource_dir(),
                stdout=self.logf,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
            )
        except Exception as e:
            self.button.config(state="normal")
            self.set_status("Ошибка запуска sing-box", "#bb0000")
            messagebox.showerror("VPN", "Не удалось запустить sing-box:\n%s" % e)
            return

        self.button.config(state="normal", text="Остановить")
        self.set_status("Подключено", "#008800")
        threading.Thread(target=self.watch, daemon=True).start()

    def watch(self):
        proc = self.proc
        if proc is not None:
            proc.wait()
        self.root.after(0, self._apply_stopped)

    def _apply_stopped(self):
        self.button.config(text="Запустить")
        self.set_status("Отключено")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
        self.proc = None
        if self.logf:
            try:
                self.logf.close()
            except Exception:
                pass
            self.logf = None
        self._apply_stopped()

    def on_close(self):
        self.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    VpnApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
