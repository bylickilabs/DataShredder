import os
import sys
import stat
import csv
import json
import time
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_NAME    = "Data Shredder"
APP_AUTHOR  = "©Thorsten Bylicki | ©BYLICKILABS"
APP_VERSION = "1.0.0"
GITHUB_URL  = "https://github.com/bylickilabs"

I18N = {
    "de": {
        "title": f"{APP_NAME} v{APP_VERSION} - {APP_AUTHOR}",
        "add_files": "Dateien hinzufügen",
        "add_folder": "Ordner hinzufügen",
        "remove_selected": "Auswahl entfernen",
        "clear_list": "Liste leeren",
        "include_sub": "Unterordner einbeziehen",
        "method": "Methode",
        "verify": "Verifizieren (nur feste Muster)",
        "rename": "Vor Löschen umbenennen",
        "rename_times": "Umbenennungen",
        "start": "Starten",
        "cancel": "Abbrechen",
        "export": "Report exportieren (CSV/JSON)",
        "github": "GitHub",
        "info": "Info",
        "lang": "DE/EN",
        "files": "Ziele (Dateien/Ordner)",
        "options": "Optionen",
        "size": "Größe",
        "status": "Status",
        "progress": "Fortschritt",
        "log": "Protokoll",
        "confirm": "Bist du sicher? Dieser Vorgang ist irreversibel.",
        "done": "Fertig. Erfolgreich: {ok}, Fehler: {fail}",
        "report_saved": "Report gespeichert: {p}",
        "about_title": "Über diese Anwendung",
        "about_text": (
            f"{APP_NAME} {APP_VERSION}\nBYLICKILABS Edition\n\n"
            "Sicheres Löschen von Dateien/Ordnern mittels Mehrfachüberschreibung.\n"
            "Hinweis: SSDs bieten keine garantierte sichere Löschung.\n"
            "Empfohlen: Vollverschlüsselung und hersteller-spezifische Secure-Erase-Verfahren.\n\n"
            "© Thorsten Bylicki | © BYLICKILABS"
        ),
        "eta": "Restzeit ~ {mins}m",
        "columns": {"path": "Pfad", "size": "Größe", "status": "Status"},
        "methods": {
            "ZERO": "Zero Fill (1 Pass)",
            "RANDOM": "Random (1 Pass)",
            "DOD3": "DoD 5220.22-M (3 Durchläufe)",
            "NIST1": "NIST SP 800-88 (1 Durchlauf random)",
            "GUTMANN": "Gutmann (35 Durchläufe)"
        },
        "started": "Löschung gestartet …",
        "skipped_link": "Symlink übersprungen: {p}",
        "error": "Fehler: {e}",
        "deleted": "Gelöscht",
        "pass_ok": "Pass {i}/{n} OK",
        "renamed": "Umbenannt",
        "ver_ok": "Verifiziert",
        "ver_skip": "Verifizierung übersprungen (zufälliges Muster)",
    },
    "en": {
        "title": f"{APP_NAME} v{APP_VERSION} - {APP_AUTHOR}",
        "add_files": "Add Files",
        "add_folder": "Add Folder",
        "remove_selected": "Remove Selected",
        "clear_list": "Clear List",
        "include_sub": "Include subfolders",
        "method": "Method",
        "verify": "Verify (fixed patterns only)",
        "rename": "Rename before delete",
        "rename_times": "Renames",
        "start": "Start",
        "cancel": "Cancel",
        "export": "Export Report (CSV/JSON)",
        "github": "GitHub",
        "info": "Info",
        "lang": "DE/EN",
        "files": "Targets (files/folders)",
        "options": "Options",
        "size": "Size",
        "status": "Status",
        "progress": "Progress",
        "log": "Log",
        "confirm": "Are you sure? This operation is irreversible.",
        "done": "Done. Success: {ok}, Failures: {fail}",
        "report_saved": "Report saved: {p}",
        "about_title": "About this App",
        "about_text": (
            f"{APP_NAME} {APP_VERSION}\nBYLICKILABS Edition\n\n"
            "Secure deletion of files/folders via multi-pass overwrite.\n"
            "Note: SSDs cannot guarantee secure erasure due to wear-leveling.\n"
            "Prefer full-disk encryption and vendor secure erase where required.\n\n"
            "© Thorsten Bylicki | © BYLICKILABS"
        ),
        "eta": "ETA ~ {mins}m",
        "columns": {"path": "Path", "size": "Size", "status": "Status"},
        "methods": {
            "ZERO": "Zero Fill (1 Pass)",
            "RANDOM": "Random (1 Pass)",
            "DOD3": "DoD 5220.22-M (3 Passes)",
            "NIST1": "NIST SP 800-88 (1 Pass Random)",
            "GUTMANN": "Gutmann (35 Passes)"
        },
        "started": "Wipe started …",
        "skipped_link": "Symlink skipped: {p}",
        "error": "Error: {e}",
        "deleted": "Deleted",
        "pass_ok": "Pass {i}/{n} OK",
        "renamed": "Renamed",
        "ver_ok": "Verified",
        "ver_skip": "Verification skipped (random pattern)",
    }
}

class WipeMethod:
    ZERO = "ZERO"
    RANDOM = "RANDOM"
    DOD3 = "DOD3"
    NIST1 = "NIST1"
    GUTMANN = "GUTMANN"

GUTMANN_SEQUENCE: List[Optional[int]] = [
    None, None, None, None,
    0x55, 0xAA, 0x92, 0x49, 0x24,
    0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF,
    0x92, 0x49, 0x24, 0x6D, 0xB6, 0xDB,
    None, None, None, None
]

@dataclass
class TargetItem:
    path: str
    size: int
    status: str = "PENDING"

@dataclass
class ReportRow:
    path: str
    method: str
    size: int
    passes: int
    renamed: int
    verified: str
    duration_sec: float
    result: str
    error: str = ""

def human_size(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    f = float(n)
    for u in units:
        if f < 1024 or u == units[-1]:
            return f"{f:.1f} {u}"
        f /= 1024

def random_name(length: int = 12) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(random.choice(alphabet) for _ in range(length))

def ensure_writeable(p: Path):
    try:
        mode = os.stat(p).st_mode
        if not (mode & stat.S_IWRITE):
            os.chmod(p, mode | stat.S_IWRITE)
    except Exception:
        pass

def is_symlink(p: Path) -> bool:
    try:
        return p.is_symlink()
    except Exception:
        return False

class Shredder:
    def __init__(self, log_fn):
        self._cancel = False
        self.log = log_fn

    def cancel(self):
        self._cancel = True

    def wipe_file(self, p: Path, method: str, verify_fixed: bool, rename_times: int,
                  chunk_size: int = 8 * 1024 * 1024) -> ReportRow:
        start = time.time()
        size = 0
        try:
            if not p.exists():
                return ReportRow(str(p), method, 0, 0, 0, "NO", 0.0, "MISSING", "File not found")
            if is_symlink(p):
                p.unlink()
                return ReportRow(str(p), method, 0, 0, 0, "NO", 0.0, "LINK_REMOVED", "")

            ensure_writeable(p)
            size = p.stat().st_size
            passes = self._method_passes(method)

            with open(p, "r+b", buffering=0) as f:
                for i, pattern in enumerate(passes, 1):
                    if self._cancel:
                        raise RuntimeError("Cancelled")
                    f.seek(0)
                    remaining = size
                    while remaining > 0:
                        if self._cancel:
                            raise RuntimeError("Cancelled")
                        n = min(chunk_size, remaining)
                        buf = os.urandom(n) if pattern is None else bytes([pattern]) * n
                        written = f.write(buf)
                        if written != n:
                            raise IOError("Short write")
                        remaining -= n
                    f.flush(); os.fsync(f.fileno())
                    self.log(f"[PASS] {i}/{len(passes)} done for {p}")

                    if verify_fixed and pattern is not None:
                        if not self._verify_pattern(f, size, chunk_size, pattern):
                            raise IOError("Verification failed")
                        self.log(f"[VER] pass {i} verified")

            ren_ct = 0
            for _ in range(max(0, rename_times)):
                if self._cancel:
                    raise RuntimeError("Cancelled")
                new_name = random_name(random.randint(8, 18))
                new_path = p.with_name(new_name)
                try:
                    p.rename(new_path)
                    p = new_path
                    ren_ct += 1
                    self.log(f"[RENAME] -> {p.name}")
                except Exception as e:
                    self.log(f"[WARN] rename failed: {e}")
                    break

            try:
                p.unlink()
            except PermissionError:
                ensure_writeable(p)
                p.unlink()

            dur = time.time() - start
            return ReportRow(str(p), method, size, len(passes), ren_ct, "YES" if verify_fixed else "N/A", dur, "DELETED", "")

        except Exception as e:
            dur = time.time() - start
            return ReportRow(str(p), method, size, 0, 0, "NO", dur, "ERROR", str(e))

    def _method_passes(self, method: str) -> List[Optional[int]]:
        if method == WipeMethod.ZERO:
            return [0x00]
        if method in (WipeMethod.RANDOM, WipeMethod.NIST1):
            return [None]
        if method == WipeMethod.DOD3:
            return [0xFF, 0x00, None]
        if method == WipeMethod.GUTMANN:
            return GUTMANN_SEQUENCE
        raise ValueError("Unknown method")

    def _verify_pattern(self, f, size: int, chunk_size: int, byte_val: int) -> bool:
        f.flush(); os.fsync(f.fileno())
        f.seek(0)
        remaining = size
        while remaining > 0:
            n = min(chunk_size, remaining)
            data = f.read(n)
            if data != (bytes([byte_val]) * n):
                return False
            remaining -= n
        return True

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.lang = "de"
        self.targets: List[TargetItem] = []
        self.include_sub = tk.BooleanVar(value=True)
        self.verify_fixed = tk.BooleanVar(value=True)
        self.rename_before = tk.BooleanVar(value=True)
        self.rename_times = tk.IntVar(value=2)
        self.method_code = WipeMethod.DOD3
        self.method_label_var = tk.StringVar(value=self._method_label(self.method_code))
        self.worker = None
        self._cancel_flag = False
        self.report: List[ReportRow] = []

        self.title(I18N[self.lang]["title"])
        self.geometry("1180x760")
        self.minsize(1100, 660)
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
        self._apply_light_theme()
        self._build_ui()
        self._i18n_apply()

    def _apply_light_theme(self):
        bg = "#F8FAFC"; fg = "#0F172A"; entry_bg = "#FFFFFF"
        self.configure(bg=bg)
        self.style.configure("TFrame", background=bg)
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure("TButton", foreground=fg)
        self.style.configure("TCheckbutton", background=bg, foreground=fg)
        self.style.configure("TLabelframe", background=bg, foreground=fg)
        self.style.configure("TLabelframe.Label", background=bg, foreground=fg)
        self.style.configure("Treeview", background=entry_bg, fieldbackground=entry_bg, foreground=fg)
        self.style.configure("TEntry", fieldbackground=entry_bg)
        self.style.configure("Horizontal.TProgressbar", troughcolor=entry_bg)

    def _method_label(self, code: str) -> str:
        return I18N[self.lang]["methods"][code]

    def _method_code_from_label(self, label: str) -> str:
        for k, v in I18N[self.lang]["methods"].items():
            if v == label:
                return k
        return self.method_code

    def _method_values(self) -> List[str]:
        return [I18N[self.lang]["methods"][k] for k in (WipeMethod.ZERO, WipeMethod.RANDOM, WipeMethod.DOD3, WipeMethod.NIST1, WipeMethod.GUTMANN)]

    def _build_ui(self):
        top = ttk.Frame(self); top.pack(fill="x", padx=12, pady=10)
        self.lbl_title = ttk.Label(top, text=APP_NAME, font=("Segoe UI", 16, "bold"))
        self.lbl_title.pack(side="left")
        right = ttk.Frame(top); right.pack(side="right")
        self.btn_github = ttk.Button(right, text=I18N[self.lang]["github"], command=self._open_github)
        self.btn_info = ttk.Button(right, text=I18N[self.lang]["info"], command=self._show_info)
        self.btn_lang = ttk.Button(right, text="EN", command=self._toggle_lang)
        self.btn_github.grid(row=0, column=0, padx=4)
        self.btn_info.grid(row=0, column=1, padx=4)
        self.btn_lang.grid(row=0, column=2, padx=4)

        self.cfg_frame = ttk.LabelFrame(self, text=I18N[self.lang]["files"]) ; self.cfg_frame.pack(fill="x", padx=12, pady=(0,10))
        row = ttk.Frame(self.cfg_frame); row.pack(fill="x", padx=8, pady=8)
        self.btn_add_files = ttk.Button(row, text=I18N[self.lang]["add_files"], command=self._add_files)
        self.btn_add_folder = ttk.Button(row, text=I18N[self.lang]["add_folder"], command=self._add_folder)
        self.btn_remove = ttk.Button(row, text=I18N[self.lang]["remove_selected"], command=self._remove_selected)
        self.btn_clear = ttk.Button(row, text=I18N[self.lang]["clear_list"], command=self._clear_list)
        self.chk_include = ttk.Checkbutton(row, text=I18N[self.lang]["include_sub"], variable=self.include_sub)
        self.btn_add_files.pack(side="left", padx=4)
        self.btn_add_folder.pack(side="left", padx=4)
        self.btn_remove.pack(side="left", padx=4)
        self.btn_clear.pack(side="left", padx=4)
        self.chk_include.pack(side="left", padx=16)

        cols = ("path", "size", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("path", text=I18N[self.lang]["columns"]["path"]) ; self.tree.column("path", width=720)
        self.tree.heading("size", text=I18N[self.lang]["columns"]["size"]) ; self.tree.column("size", width=120, anchor="e")
        self.tree.heading("status", text=I18N[self.lang]["columns"]["status"]) ; self.tree.column("status", width=160, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0,10))

        self.opt_frame = ttk.LabelFrame(self, text=I18N[self.lang]["options"]) ; self.opt_frame.pack(fill="x", padx=12, pady=(0,10))
        ttk.Label(self.opt_frame, text=I18N[self.lang]["method"]).grid(row=0, column=0, sticky="w")
        self.cmb_method = ttk.Combobox(self.opt_frame, state="readonly", width=34, textvariable=self.method_label_var, values=self._method_values())
        self.cmb_method.grid(row=0, column=1, padx=8, sticky="w")
        self.cmb_method.bind("<<ComboboxSelected>>", self._on_method_changed)
        self.chk_verify = ttk.Checkbutton(self.opt_frame, text=I18N[self.lang]["verify"], variable=self.verify_fixed)
        self.chk_verify.grid(row=0, column=2, padx=16, sticky="w")
        self.chk_rename = ttk.Checkbutton(self.opt_frame, text=I18N[self.lang]["rename"], variable=self.rename_before)
        self.chk_rename.grid(row=0, column=3, padx=16, sticky="w")
        self.lbl_ren = ttk.Label(self.opt_frame, text=I18N[self.lang]["rename_times"]) ; self.lbl_ren.grid(row=0, column=4, padx=4, sticky="e")
        self.spn_times = ttk.Spinbox(self.opt_frame, from_=0, to=10, width=5, textvariable=self.rename_times)
        self.spn_times.grid(row=0, column=5, padx=4, sticky="w")

        act = ttk.Frame(self); act.pack(fill="x", padx=12, pady=(0,10))
        self.btn_start = ttk.Button(act, text=I18N[self.lang]["start"], command=self._start)
        self.btn_cancel = ttk.Button(act, text=I18N[self.lang]["cancel"], command=self._cancel, state="disabled")
        self.btn_export = ttk.Button(act, text=I18N[self.lang]["export"], command=self._export_report)
        self.btn_start.pack(side="left", padx=4)
        self.btn_cancel.pack(side="left", padx=4)
        self.btn_export.pack(side="left", padx=4)

        prog = ttk.LabelFrame(self, text=I18N[self.lang]["progress"]) ; prog.pack(fill="x", padx=12, pady=(0,10))
        self.pbar = ttk.Progressbar(prog, mode="determinate", maximum=100)
        self.pbar.pack(fill="x", padx=8, pady=8)
        self.lbl_eta = ttk.Label(prog, text="")
        self.lbl_eta.pack(anchor="e", padx=8, pady=(0,8))

        self.log_frame = ttk.LabelFrame(self, text=I18N[self.lang]["log"]) ; self.log_frame.pack(fill="both", expand=True, padx=12, pady=(0,12))
        self.txt_log = tk.Text(self.log_frame, height=10, wrap="word", state="disabled")
        self.txt_log.pack(fill="both", expand=True)

    def _i18n(self, key):
        return I18N[self.lang][key]

    def _i18n_apply(self):
        self.title(self._i18n("title"))
        
        self.btn_github.config(text=self._i18n("github"))
        self.btn_info.config(text=self._i18n("info"))
        self.btn_lang.config(text=("EN" if self.lang == "de" else "DE"))

        self.cfg_frame.config(text=self._i18n("files"))
        self.opt_frame.config(text=self._i18n("options"))
        self.log_frame.config(text=self._i18n("log"))

        self.tree.heading("path", text=I18N[self.lang]["columns"]["path"]) ;
        self.tree.heading("size", text=I18N[self.lang]["columns"]["size"]) ;
        self.tree.heading("status", text=I18N[self.lang]["columns"]["status"]) ;

        self.btn_add_files.config(text=self._i18n("add_files"))
        self.btn_add_folder.config(text=self._i18n("add_folder"))
        self.btn_remove.config(text=self._i18n("remove_selected"))
        self.btn_clear.config(text=self._i18n("clear_list"))
        self.chk_include.config(text=self._i18n("include_sub"))

        current_code = self.method_code
        self.cmb_method.config(values=self._method_values())
        self.method_label_var.set(self._method_label(current_code))
        self.chk_verify.config(text=self._i18n("verify"))
        self.chk_rename.config(text=self._i18n("rename"))
        self.lbl_ren.config(text=self._i18n("rename_times"))
        self.btn_start.config(text=self._i18n("start"))
        self.btn_cancel.config(text=self._i18n("cancel"))
        self.btn_export.config(text=self._i18n("export"))

    def _toggle_lang(self):
        self.lang = "en" if self.lang == "de" else "de"
        self._i18n_apply()

    def _on_method_changed(self, _evt):
        label = self.method_label_var.get()
        self.method_code = self._method_code_from_label(label)

    def _open_github(self):
        import webbrowser
        webbrowser.open(GITHUB_URL)

    def _show_info(self):
        messagebox.showinfo(self._i18n("about_title"), self._i18n("about_text"))

    def _add_files(self):
        paths = filedialog.askopenfilenames(title=self._i18n("add_files"))
        if not paths: return
        for p in paths:
            self._add_path(Path(p))

    def _add_folder(self):
        d = filedialog.askdirectory(title=self._i18n("add_folder"))
        if not d: return
        base = Path(d)
        if self.include_sub.get():
            for root, _, files in os.walk(base):
                for f in files:
                    self._add_path(Path(root)/f)
        else:
            for f in base.iterdir():
                if f.is_file():
                    self._add_path(f)

    def _add_path(self, p: Path):
        try:
            size = p.stat().st_size if p.is_file() else 0
            self.targets.append(TargetItem(str(p), size, "PENDING"))
            self.tree.insert("", "end", values=(str(p), human_size(size), "PENDING"))
        except Exception as e:
            self._log(f"[ERR] add {p}: {e}")

    def _remove_selected(self):
        sel = self.tree.selection()
        if not sel: return
        paths = set()
        for iid in sel:
            v = self.tree.item(iid, "values")
            paths.add(v[0])
            self.tree.delete(iid)
        self.targets = [t for t in self.targets if t.path not in paths]

    def _clear_list(self):
        self.targets.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)

    def _start(self):
        if not self.targets:
            return
        if not messagebox.askyesno(APP_NAME, self._i18n("confirm")):
            return
        self.report.clear()
        self._cancel_flag = False
        self.btn_start.config(state="disabled")
        self.btn_cancel.config(state="normal")
        self.pbar["value"] = 0
        self._log(f"[INFO] {self._i18n('started')}")
        self.after(50, self._run_worker)

    def _cancel(self):
        self._cancel_flag = True

    def _run_worker(self):
        shred = Shredder(self._log)
        total = len(self.targets)
        start_all = time.time()
        ok = 0; fail = 0
        for idx, t in enumerate(list(self.targets)):
            if self._cancel_flag:
                break
            p = Path(t.path)
            if not p.exists():
                self._update_status(idx, "MISSING")
                self.report.append(ReportRow(str(p), self.method_code, 0, 0, 0, "NO", 0.0, "MISSING", ""))
                continue
            if p.is_dir():
                for root, _, files in os.walk(p, topdown=False):
                    for name in files:
                        if self._cancel_flag: break
                        file_path = Path(root)/name
                        rr = shred.wipe_file(file_path, self.method_code, self.verify_fixed.get(), self.rename_times.get() if self.rename_before.get() else 0)
                        self.report.append(rr)
                        self._log_row(rr)
                    try:
                        Path(root).rmdir()
                    except OSError:
                        pass
                try:
                    p.rmdir()
                    self._update_status(idx, self._i18n("deleted"))
                    ok += 1
                except OSError:
                    self._update_status(idx, "PARTIAL")
            else:
                rr = shred.wipe_file(p, self.method_code, self.verify_fixed.get(), self.rename_times.get() if self.rename_before.get() else 0)
                self.report.append(rr)
                self._log_row(rr)
                self._update_status(idx, rr.result)
                if rr.result == "DELETED":
                    ok += 1
                else:
                    fail += 1

            prog = int(((idx+1) / total) * 100)
            self.pbar["value"] = prog
            elapsed = time.time() - start_all
            left = (elapsed/(idx+1))*(total-(idx+1)) if idx+1>0 else 0
            mins = int(left/60)
            self.lbl_eta.config(text=self._i18n("eta").format(mins=mins) if mins>0 else "")
            self.update_idletasks()

        msg = self._i18n("done").format(ok=ok, fail=fail)
        self._log(f"[INFO] {msg}")
        self.btn_start.config(state="normal")
        self.btn_cancel.config(state="disabled")

    def _export_report(self):
        if not self.report:
            return
        path = filedialog.asksaveasfilename(title="Export report", defaultextension=".csv",
            filetypes=[("CSV","*.csv"),("JSON","*.json")], initialfile="data_shredder_report.csv")
        if not path:
            return
        p = Path(path)
        try:
            if p.suffix.lower() == ".json":
                with p.open("w", encoding="utf-8") as f:
                    json.dump([asdict(r) for r in self.report], f, indent=2)
            else:
                with p.open("w", encoding="utf-8", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["path","method","size","passes","renamed","verified","duration_sec","result","error"])
                    for r in self.report:
                        w.writerow([r.path, r.method, r.size, r.passes, r.renamed, r.verified, f"{r.duration_sec:.3f}", r.result, r.error])
            messagebox.showinfo(APP_NAME, self._i18n("report_saved").format(p=p))
        except Exception as e:
            messagebox.showerror(APP_NAME, str(e))

    def _log(self, msg: str):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _log_row(self, rr: ReportRow):
        if rr.result == "DELETED":
            self._log(f"[OK] {rr.path} ({human_size(rr.size)}) in {rr.duration_sec:.2f}s")
        elif rr.result == "ERROR":
            self._log(f"[ERR] {rr.path}: {rr.error}")
        else:
            self._log(f"[INFO] {rr.path}: {rr.result}")

    def _update_status(self, idx: int, text: str):
        try:
            iid = self.tree.get_children()[idx]
            vals = list(self.tree.item(iid, "values"))
            vals[2] = text
            self.tree.item(iid, values=vals)
        except Exception:
            pass

if __name__ == "__main__":
    app = App()
    app.mainloop()
