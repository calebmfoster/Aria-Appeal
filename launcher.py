import json
import os
import sys
import subprocess
import threading
import shutil
import urllib.request
from pathlib import Path
import tkinter as tk
from tkinter import scrolledtext, font as tkfont

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

_HARDCODED_REPO = Path(r"D:\Repo\Aria Appeal")

if getattr(sys, 'frozen', False):
    REPO_ROOT = _HARDCODED_REPO
else:
    REPO_ROOT = Path(__file__).resolve().parent

BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
VENV_UVICORN = BACKEND_DIR / ".venv" / "Scripts" / "uvicorn.exe"
VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
CONFIG_FILE = BACKEND_DIR / "config.json"

CREATE_NO_WINDOW = 0x08000000

STATUS_COLORS = {
    "stopped":  "#9ca3af",
    "starting": "#fbbf24",
    "running":  "#22c55e",
    "error":    "#ef4444",
}

BG = "#1e1e1e"
FG = "#e5e5e5"
BTN_BG = "#2d2d2d"
BTN_ACTIVE = "#3d3d3d"
LOG_BG = "#141414"
LOG_FG = "#a3a3a3"
PANEL_BG = "#252525"
INPUT_BG = "#1a1a1a"
INPUT_FG = "#e5e5e5"
ACCENT = "#dc2626"  # moore-red

CLAUDE_MODELS = [
    ("Claude Haiku 4.5  (fast, cheap)", "claude-haiku-4-5"),
    ("Claude Sonnet 4.6  (balanced)", "claude-sonnet-4-6"),
    ("Claude Opus 4.7  (best quality)", "claude-opus-4-7"),
]

LOCAL_MODELS = [
    ("Qwen3-8B  (NF4, ~4.5 GB VRAM)", "Qwen/Qwen3-8B"),
    ("Qwen3-4B  (NF4, ~2.5 GB VRAM)", "Qwen/Qwen3-4B"),
    ("Qwen2.5-3B  (float16, ~6 GB VRAM)", "Qwen/Qwen2.5-3B-Instruct"),
]

DEFAULT_CONFIG = {
    "llm_provider": "claude",
    "claude_model": "claude-haiku-4-5",
    "anthropic_api_key": "",
    "llm_model_id": "Qwen/Qwen3-8B",
    "tts_provider": "qwen3-local",
    "tts_model": "qwen3-tts",
}


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return {**DEFAULT_CONFIG, **json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))}
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def _save_config(data: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


class LauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Aria Appeal — Launcher")
        self.configure(bg=BG)
        self.resizable(False, False)

        self._procs: dict[str, subprocess.Popen | None] = {"backend": None, "frontend": None}
        self._status: dict[str, str] = {"backend": "stopped", "frontend": "stopped"}
        self._log_threads: dict[str, threading.Thread | None] = {"backend": None, "frontend": None}

        self._cfg = _load_config()
        self._settings_open = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        self._mono_font   = tkfont.Font(family="Consolas", size=9)
        self._label_font  = tkfont.Font(family="Segoe UI", size=9)
        self._title_font  = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self._btn_font    = tkfont.Font(family="Segoe UI", size=9)
        self._small_font  = tkfont.Font(family="Segoe UI", size=8)

        # Title bar
        header = tk.Frame(self, bg=BG)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))

        tk.Label(header, text="Aria Appeal  —  Dev Launcher",
                 font=self._title_font, bg=BG, fg=FG).pack(side="left")

        self._settings_btn = tk.Button(
            header, text="⚙  Settings", font=self._small_font,
            bg=BTN_BG, fg="#9ca3af", activebackground=BTN_ACTIVE, activeforeground=FG,
            relief="flat", padx=8, pady=3, cursor="hand2",
            command=self._toggle_settings
        )
        self._settings_btn.pack(side="right")

        # Status row
        status_frame = tk.Frame(self, bg=BG)
        status_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))

        _urls = {"backend": "http://localhost:8000", "frontend": "http://localhost:3000"}

        self._dots: dict[str, tk.Canvas] = {}
        for name in ("backend", "frontend"):
            c = tk.Canvas(status_frame, width=12, height=12, bg=BG, highlightthickness=0)
            c.create_oval(2, 2, 10, 10, fill=STATUS_COLORS["stopped"], outline="", tags="dot")
            c.pack(side="left", padx=(0, 4))
            self._dots[name] = c

            tk.Label(status_frame, text=name.capitalize(),
                     font=self._label_font, bg=BG, fg=FG).pack(side="left", padx=(0, 4))
            tk.Label(status_frame, text=_urls[name],
                     font=tkfont.Font(family="Consolas", size=9),
                     bg=BG, fg="#6b7280").pack(side="left", padx=(0, 20))

        # Buttons
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.grid(row=2, column=0, padx=12, pady=(0, 8))

        self._start_btn = tk.Button(
            btn_frame, text="Start All", font=self._btn_font,
            bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE, activeforeground=FG,
            relief="flat", padx=18, pady=5, cursor="hand2",
            command=self.start_all
        )
        self._start_btn.pack(side="left", padx=(0, 8))

        self._stop_btn = tk.Button(
            btn_frame, text="Stop All", font=self._btn_font,
            bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE, activeforeground=FG,
            relief="flat", padx=18, pady=5, cursor="hand2",
            command=self.stop_all, state="disabled"
        )
        self._stop_btn.pack(side="left")

        # Settings panel (hidden by default)
        self._settings_frame = tk.Frame(self, bg=PANEL_BG)
        # inserted at row 3; log at row 4 — settings frame is only grid-managed when open

        # Separator
        tk.Frame(self, bg="#333333", height=1).grid(row=4, column=0, sticky="ew")

        # LLM indicator strip (shows current provider under the separator)
        self._provider_strip = tk.Label(
            self, text="", font=self._small_font, bg="#1a1a1a", fg="#6b7280",
            pady=3, anchor="w", padx=12
        )
        self._provider_strip.grid(row=5, column=0, sticky="ew")
        self._refresh_provider_strip()

        # Log area
        self._log = scrolledtext.ScrolledText(
            self, width=72, height=20, font=self._mono_font,
            bg=LOG_BG, fg=LOG_FG, insertbackground=FG,
            relief="flat", borderwidth=0, padx=8, pady=8,
            state="disabled"
        )
        self._log.grid(row=6, column=0, sticky="nsew")

        self.geometry("")

    def _build_settings_panel(self):
        """Build the settings widgets inside self._settings_frame."""
        f = self._settings_frame
        for w in f.winfo_children():
            w.destroy()

        pad = {"padx": 12, "pady": 4}

        # ── Provider ────────────────────────────────────────────────────────
        tk.Label(f, text="LLM Provider", font=self._label_font,
                 bg=PANEL_BG, fg="#9ca3af").grid(row=0, column=0, sticky="w", **pad)

        self._provider_var = tk.StringVar(value=self._cfg.get("llm_provider", "claude"))

        prov_frame = tk.Frame(f, bg=PANEL_BG)
        prov_frame.grid(row=0, column=1, sticky="w", **pad)

        for label, val in [("Claude API", "claude"), ("Local Model", "local")]:
            rb = tk.Radiobutton(
                prov_frame, text=label, variable=self._provider_var, value=val,
                font=self._label_font, bg=PANEL_BG, fg=FG,
                selectcolor=BG, activebackground=PANEL_BG, activeforeground=FG,
                command=self._on_provider_change
            )
            rb.pack(side="left", padx=(0, 12))

        # ── Claude model ─────────────────────────────────────────────────────
        self._claude_model_label = tk.Label(f, text="Claude Model", font=self._label_font,
                                            bg=PANEL_BG, fg="#9ca3af")
        self._claude_model_label.grid(row=1, column=0, sticky="w", **pad)

        self._claude_model_var = tk.StringVar(value=self._cfg.get("claude_model", "claude-haiku-4-5"))
        self._claude_model_frame = tk.Frame(f, bg=PANEL_BG)
        self._claude_model_frame.grid(row=1, column=1, sticky="w", **pad)

        for display, val in CLAUDE_MODELS:
            rb = tk.Radiobutton(
                self._claude_model_frame, text=display, variable=self._claude_model_var, value=val,
                font=self._small_font, bg=PANEL_BG, fg=FG,
                selectcolor=BG, activebackground=PANEL_BG, activeforeground=FG,
            )
            rb.pack(anchor="w")

        # ── API key ──────────────────────────────────────────────────────────
        self._api_key_label = tk.Label(f, text="API Key", font=self._label_font,
                                       bg=PANEL_BG, fg="#9ca3af")
        self._api_key_label.grid(row=2, column=0, sticky="w", **pad)

        key_frame = tk.Frame(f, bg=PANEL_BG)
        key_frame.grid(row=2, column=1, sticky="w", **pad)

        self._api_key_var = tk.StringVar(value=self._cfg.get("anthropic_api_key", ""))
        self._api_key_entry = tk.Entry(
            key_frame, textvariable=self._api_key_var, show="•",
            width=38, font=self._mono_font,
            bg=INPUT_BG, fg=INPUT_FG, insertbackground=FG,
            relief="flat", bd=4
        )
        self._api_key_entry.pack(side="left", padx=(0, 6))

        self._show_key_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            key_frame, text="Show", variable=self._show_key_var,
            font=self._small_font, bg=PANEL_BG, fg="#9ca3af",
            selectcolor=BG, activebackground=PANEL_BG,
            command=self._toggle_key_visibility
        ).pack(side="left")

        # ── Local model ──────────────────────────────────────────────────────
        self._local_model_label = tk.Label(f, text="Local Model", font=self._label_font,
                                           bg=PANEL_BG, fg="#9ca3af")
        self._local_model_label.grid(row=3, column=0, sticky="w", **pad)

        self._local_model_var = tk.StringVar(value=self._cfg.get("llm_model_id", "Qwen/Qwen3-8B"))
        self._local_model_frame = tk.Frame(f, bg=PANEL_BG)
        self._local_model_frame.grid(row=3, column=1, sticky="w", **pad)

        for display, val in LOCAL_MODELS:
            rb = tk.Radiobutton(
                self._local_model_frame, text=display, variable=self._local_model_var, value=val,
                font=self._small_font, bg=PANEL_BG, fg=FG,
                selectcolor=BG, activebackground=PANEL_BG, activeforeground=FG,
            )
            rb.pack(anchor="w")

        # ── Save button ──────────────────────────────────────────────────────
        save_frame = tk.Frame(f, bg=PANEL_BG)
        save_frame.grid(row=4, column=0, columnspan=2, sticky="e", padx=12, pady=(6, 10))

        self._save_status_label = tk.Label(save_frame, text="", font=self._small_font,
                                           bg=PANEL_BG, fg="#22c55e")
        self._save_status_label.pack(side="left", padx=(0, 10))

        tk.Button(
            save_frame, text="Save Settings", font=self._btn_font,
            bg=ACCENT, fg="white", activebackground="#b91c1c", activeforeground="white",
            relief="flat", padx=14, pady=4, cursor="hand2",
            command=self._save_settings
        ).pack(side="left")

        # Sync visibility to current provider
        self._on_provider_change()

    def _toggle_settings(self):
        if self._settings_open:
            self._settings_frame.grid_remove()
            self._settings_open = False
            self._settings_btn.configure(fg="#9ca3af")
        else:
            self._build_settings_panel()
            self._settings_frame.grid(row=3, column=0, sticky="ew")
            self._settings_open = True
            self._settings_btn.configure(fg=FG)

    def _on_provider_change(self):
        is_claude = self._provider_var.get() == "claude"
        claude_fg = "#9ca3af" if is_claude else "#4b5563"
        local_fg = "#4b5563" if is_claude else "#9ca3af"

        self._claude_model_label.configure(fg=claude_fg)
        self._api_key_label.configure(fg=claude_fg)
        self._local_model_label.configure(fg=local_fg)

        state_claude = "normal" if is_claude else "disabled"
        state_local = "disabled" if is_claude else "normal"

        for w in self._claude_model_frame.winfo_children():
            w.configure(state=state_claude)
        self._api_key_entry.configure(state=state_claude)
        for w in self._local_model_frame.winfo_children():
            w.configure(state=state_local)

    def _toggle_key_visibility(self):
        self._api_key_entry.configure(show="" if self._show_key_var.get() else "•")

    def _save_settings(self):
        self._cfg["llm_provider"] = self._provider_var.get()
        self._cfg["claude_model"] = self._claude_model_var.get()
        self._cfg["anthropic_api_key"] = self._api_key_var.get().strip()
        self._cfg["llm_model_id"] = self._local_model_var.get()
        _save_config(self._cfg)
        self._refresh_provider_strip()
        self._save_status_label.configure(text="Saved ✓")
        self.after(2500, lambda: self._save_status_label.configure(text=""))
        self._append_log("[settings] Config saved. Restart backend to apply changes.\n")

    def _refresh_provider_strip(self):
        provider = self._cfg.get("llm_provider", "claude")
        if provider == "claude":
            model = self._cfg.get("claude_model", "claude-haiku-4-5")
            text = f"LLM: Claude API  ·  {model}"
        else:
            model = self._cfg.get("llm_model_id", "Qwen/Qwen3-8B")
            text = f"LLM: Local  ·  {model}"
        self._provider_strip.configure(text=text)

    # ── Status helpers ───────────────────────────────────────────────────────

    def _set_status(self, name: str, status: str):
        self._status[name] = status
        color = STATUS_COLORS[status]
        canvas = self._dots[name]
        canvas.itemconfig("dot", fill=color)

    def _append_log(self, text: str):
        self._log.configure(state="normal")
        self._log.insert("end", text)
        self._log.see("end")
        self._log.configure(state="disabled")

    # ── Server control ───────────────────────────────────────────────────────

    def start_all(self):
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")

        npm = shutil.which("npm")
        if not npm:
            self._append_log("[ERROR] npm not found on PATH. Cannot start frontend.\n")
            self._set_status("frontend", "error")

        if not VENV_UVICORN.exists():
            self._append_log(f"[ERROR] Uvicorn not found at {VENV_UVICORN}\n")
            self._set_status("backend", "error")
        else:
            self._launch("backend",
                         [str(VENV_UVICORN), "app.main:app", "--reload", "--host", "0.0.0.0"],
                         cwd=str(BACKEND_DIR),
                         env={**os.environ, "PYTHONPATH": str(BACKEND_DIR)})

        if npm:
            self._launch("frontend", [npm, "run", "dev"], cwd=str(FRONTEND_DIR))

    def stop_all(self):
        self._stop_btn.configure(state="disabled")
        self._kill("backend")
        self._kill("frontend")
        self._start_btn.configure(state="normal")

    def _launch(self, name: str, cmd: list, cwd: str, env=None):
        self._set_status(name, "starting")
        self._append_log(f"[{name}] Starting: {' '.join(cmd)}\n")
        try:
            proc = subprocess.Popen(
                cmd, cwd=cwd, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW
            )
            self._procs[name] = proc
        except Exception as e:
            self._append_log(f"[{name}] FAILED to launch: {e}\n")
            self._set_status(name, "error")
            return

        t = threading.Thread(target=self._tail, args=(name, proc), daemon=True)
        self._log_threads[name] = t
        t.start()

        if name == "backend":
            threading.Thread(target=self._health_check,
                             args=("backend", "http://localhost:8000/health"),
                             daemon=True).start()
        elif name == "frontend":
            threading.Thread(target=self._health_check,
                             args=("frontend", "http://localhost:3000"),
                             daemon=True).start()

    def _tail(self, name: str, proc: subprocess.Popen):
        try:
            for raw in proc.stdout:
                line = raw.decode("utf-8", errors="replace")
                self.after(0, self._append_log, f"[{name}] {line}")
        except Exception:
            pass
        if self._status[name] != "error":
            self.after(0, self._set_status, name, "stopped")

    def _health_check(self, name: str, url: str):
        import time
        for _ in range(45):
            time.sleep(2)
            try:
                urllib.request.urlopen(url, timeout=2)
                self.after(0, self._set_status, name, "running")
                return
            except Exception:
                pass
        proc = self._procs.get(name)
        if proc and proc.poll() is None:
            self.after(0, self._set_status, name, "running")

    def _kill(self, name: str):
        proc = self._procs.get(name)
        if not proc:
            self._set_status(name, "stopped")
            return
        self._append_log(f"[{name}] Stopping...\n")
        try:
            if HAS_PSUTIL:
                parent = psutil.Process(proc.pid)
                for child in parent.children(recursive=True):
                    try:
                        child.kill()
                    except Exception:
                        pass
                parent.kill()
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        except Exception as e:
            self._append_log(f"[{name}] Kill error: {e}\n")
        self._procs[name] = None
        self._set_status(name, "stopped")
        self._append_log(f"[{name}] Stopped.\n")

    # ── Shutdown ─────────────────────────────────────────────────────────────

    def _on_close(self):
        self.stop_all()
        self.after(500, self.destroy)


def main():
    app = LauncherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
