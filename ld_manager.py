"""
Javis - LDPlayer Manager
Quản lý nhiều tab LDPlayer: bật/tắt, mở Chrome, mở Chrome vào link tùy chọn.
Chạy trên Windows, Python 3.8+ (chỉ dùng thư viện chuẩn).
"""

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Khi đóng gói exe (PyInstaller), lưu config cạnh file .exe thay vì thư mục tạm
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

DEFAULT_CONFIG = {
    "ld_dir": r"C:\LDPlayer\LDPlayer4.0",
    "chrome_package": "com.android.chrome",
    "saved_links": ["https://www.google.com"],
}

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


# ---------------------------------------------------------------- config
def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- ldconsole
class LDConsole:
    def __init__(self, ld_dir):
        self.ld_dir = ld_dir

    @property
    def exe(self):
        return os.path.join(self.ld_dir, "ldconsole.exe")

    def run(self, *args, timeout=60):
        if not os.path.isfile(self.exe):
            raise FileNotFoundError(f"Không thấy ldconsole.exe trong: {self.ld_dir}")
        p = subprocess.run(
            [self.exe, *args],
            capture_output=True,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
        raw = p.stdout or b""
        for enc in ("utf-8", "mbcs", "latin-1"):
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode("utf-8", errors="replace")

    def list_instances(self):
        """list2: index,title,top_hwnd,bind_hwnd,android_started,pid,vbox_pid,..."""
        result = []
        for line in self.run("list2").splitlines():
            parts = line.strip().split(",")
            if len(parts) < 5 or not parts[0].isdigit():
                continue
            result.append({
                "index": int(parts[0]),
                "title": parts[1],
                "running": parts[4] == "1",
            })
        return result

    def launch(self, idx):
        self.run("launch", "--index", str(idx))

    def quit(self, idx):
        self.run("quit", "--index", str(idx))

    def reboot(self, idx):
        self.run("reboot", "--index", str(idx))

    def sort_windows(self):
        self.run("sortWnd")

    def shell(self, idx, command):
        return self.run("adb", "--index", str(idx), "--command", f"shell {command}")

    def open_chrome(self, idx, package):
        return self.run("runapp", "--index", str(idx), "--packagename", package)

    def open_url(self, idx, url, package):
        safe = url.replace("'", "%27")
        out = self.shell(
            idx,
            f"am start -a android.intent.action.VIEW -d '{safe}' -p {package}",
        )
        # Nếu Chrome chưa cài -> mở bằng trình duyệt mặc định
        if "Error" in out or "unable to resolve" in out.lower():
            out = self.shell(idx, f"am start -a android.intent.action.VIEW -d '{safe}'")
        return out


# ---------------------------------------------------------------- GUI
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Javis - LDPlayer Manager")
        self.geometry("760x560")
        self.minsize(640, 480)

        self.cfg = load_config()
        self.ld = LDConsole(self.cfg["ld_dir"])

        self._build_ui()
        self.refresh()

    # ---------- UI
    def _build_ui(self):
        pad = {"padx": 6, "pady": 4}

        # Thư mục LDPlayer
        top = ttk.Frame(self)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="Thư mục LDPlayer:").pack(side="left")
        self.dir_var = tk.StringVar(value=self.cfg["ld_dir"])
        ttk.Entry(top, textvariable=self.dir_var).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(top, text="Chọn…", command=self.pick_dir).pack(side="left")
        ttk.Button(top, text="Lưu", command=self.save_dir).pack(side="left", padx=4)

        # Danh sách tab
        mid = ttk.LabelFrame(self, text="Danh sách tab giả lập")
        mid.pack(fill="both", expand=True, **pad)

        cols = ("index", "title", "status")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("index", text="#")
        self.tree.heading("title", text="Tên")
        self.tree.heading("status", text="Trạng thái")
        self.tree.column("index", width=50, anchor="center")
        self.tree.column("title", width=320)
        self.tree.column("status", width=120, anchor="center")
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Nút điều khiển tab
        ctl = ttk.Frame(self)
        ctl.pack(fill="x", **pad)
        for text, cmd in [
            ("Làm mới", self.refresh),
            ("Chọn tất cả", self.select_all),
            ("Bật", lambda: self.each_selected(self.ld.launch, "Bật")),
            ("Tắt", lambda: self.each_selected(self.ld.quit, "Tắt")),
            ("Khởi động lại", lambda: self.each_selected(self.ld.reboot, "Reboot")),
            ("Xếp cửa sổ", lambda: self.bg(self.ld.sort_windows, "Xếp cửa sổ")),
        ]:
            ttk.Button(ctl, text=text, command=cmd).pack(side="left", padx=2)

        # Chọn nhanh theo khoảng số tab
        rng = ttk.Frame(self)
        rng.pack(fill="x", **pad)
        ttk.Label(rng, text="Chọn từ tab #").pack(side="left")
        self.from_var = tk.StringVar(value="0")
        self.to_var = tk.StringVar(value="0")
        from_box = ttk.Spinbox(rng, from_=0, to=9999, width=6, textvariable=self.from_var)
        from_box.pack(side="left", padx=2)
        ttk.Label(rng, text="đến tab #").pack(side="left")
        to_box = ttk.Spinbox(rng, from_=0, to=9999, width=6, textvariable=self.to_var)
        to_box.pack(side="left", padx=2)
        ttk.Button(rng, text="Chọn", command=lambda: self.select_range(add=False)).pack(side="left", padx=2)
        ttk.Button(rng, text="Thêm vào chọn", command=lambda: self.select_range(add=True)).pack(side="left", padx=2)
        ttk.Button(rng, text="Bỏ chọn", command=self.clear_selection).pack(side="left", padx=2)
        self.sel_count = ttk.Label(rng, text="Đã chọn: 0")
        self.sel_count.pack(side="right")
        for box in (from_box, to_box):
            box.bind("<Return>", lambda e: self.select_range(add=False))
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.update_count())

        # Chrome + link
        web = ttk.LabelFrame(self, text="Chrome")
        web.pack(fill="x", **pad)

        row1 = ttk.Frame(web)
        row1.pack(fill="x", padx=6, pady=4)
        ttk.Button(row1, text="Mở Chrome (tab đã chọn)", command=self.open_chrome).pack(side="left")

        row2 = ttk.Frame(web)
        row2.pack(fill="x", padx=6, pady=4)
        ttk.Label(row2, text="Link:").pack(side="left")
        self.url_var = tk.StringVar()
        self.url_box = ttk.Combobox(row2, textvariable=self.url_var, values=self.cfg["saved_links"])
        self.url_box.pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(row2, text="Mở link trên tab đã chọn", command=self.open_url).pack(side="left")

        row3 = ttk.Frame(web)
        row3.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(row3, text="Lưu link", command=self.save_link).pack(side="left")
        ttk.Button(row3, text="Xóa link", command=self.delete_link).pack(side="left", padx=4)

        # Log
        self.log_box = tk.Text(self, height=7, state="disabled")
        self.log_box.pack(fill="x", **pad)

    # ---------- helpers
    def log(self, msg):
        def _write():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, _write)

    def bg(self, fn, label):
        def worker():
            try:
                fn()
                self.log(f"✔ {label}")
            except Exception as e:
                self.log(f"✘ {label}: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def selected_indexes(self):
        idxs = [int(self.tree.set(i, "index")) for i in self.tree.selection()]
        if not idxs:
            messagebox.showinfo("Javis", "Hãy chọn ít nhất 1 tab (giữ Ctrl/Shift để chọn nhiều).")
        return idxs

    def each_selected(self, fn, label):
        idxs = self.selected_indexes()
        if not idxs:
            return

        def worker():
            for idx in idxs:
                try:
                    fn(idx)
                    self.log(f"✔ {label} tab #{idx}")
                except Exception as e:
                    self.log(f"✘ {label} tab #{idx}: {e}")
            self.after(1500, self.refresh)
        threading.Thread(target=worker, daemon=True).start()

    # ---------- actions
    def pick_dir(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get() or "C:\\")
        if d:
            self.dir_var.set(os.path.normpath(d))

    def save_dir(self):
        self.cfg["ld_dir"] = self.dir_var.get().strip()
        self.ld.ld_dir = self.cfg["ld_dir"]
        save_config(self.cfg)
        self.log(f"Đã lưu thư mục: {self.cfg['ld_dir']}")
        self.refresh()

    def refresh(self):
        def worker():
            try:
                items = self.ld.list_instances()
            except Exception as e:
                self.log(f"✘ Không đọc được danh sách tab: {e}")
                return

            def fill():
                selected = {self.tree.set(i, "index") for i in self.tree.selection()}
                self.tree.delete(*self.tree.get_children())
                for it in items:
                    iid = self.tree.insert("", "end", values=(
                        it["index"], it["title"], "Đang chạy" if it["running"] else "Tắt"))
                    if str(it["index"]) in selected:
                        self.tree.selection_add(iid)
            self.after(0, fill)
        threading.Thread(target=worker, daemon=True).start()

    def select_all(self):
        self.tree.selection_set(self.tree.get_children())

    def clear_selection(self):
        self.tree.selection_remove(self.tree.selection())

    def update_count(self):
        self.sel_count.configure(text=f"Đã chọn: {len(self.tree.selection())}")

    def select_range(self, add=False):
        try:
            a, b = int(self.from_var.get()), int(self.to_var.get())
        except ValueError:
            messagebox.showinfo("Javis", "Hãy nhập số tab (ví dụ: từ 0 đến 10).")
            return
        lo, hi = min(a, b), max(a, b)
        items = [i for i in self.tree.get_children()
                 if lo <= int(self.tree.set(i, "index")) <= hi]
        if not add:
            self.clear_selection()
        self.tree.selection_add(items)
        if items:
            self.tree.see(items[0])
        self.log(f"Chọn tab #{lo} → #{hi}: {len(items)} tab")

    def open_chrome(self):
        pkg = self.cfg["chrome_package"]
        self.each_selected(lambda i: self.ld.open_chrome(i, pkg), "Mở Chrome")

    def open_url(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showinfo("Javis", "Hãy nhập link.")
            return
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        pkg = self.cfg["chrome_package"]
        self.each_selected(lambda i: self.ld.open_url(i, url, pkg), f"Mở {url}")

    def save_link(self):
        url = self.url_var.get().strip()
        if url and url not in self.cfg["saved_links"]:
            self.cfg["saved_links"].append(url)
            save_config(self.cfg)
            self.url_box["values"] = self.cfg["saved_links"]
            self.log(f"Đã lưu link: {url}")

    def delete_link(self):
        url = self.url_var.get().strip()
        if url in self.cfg["saved_links"]:
            self.cfg["saved_links"].remove(url)
            save_config(self.cfg)
            self.url_box["values"] = self.cfg["saved_links"]
            self.url_var.set("")
            self.log(f"Đã xóa link: {url}")


if __name__ == "__main__":
    App().mainloop()
