"""
Modernized Tkinter GUI for Clippy AI Agent.
"""

import asyncio
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from loguru import logger

from main import ClippyAgent


class TextboxLogHandler:
    """Loguru sink that writes log messages to a Tkinter text widget in the UI thread."""

    def __init__(self, widget: tk.Text):
        self.widget = widget

    def __call__(self, message):
        formatted = message.strip() + "\n"
        self.widget.after(0, self._write, formatted)

    def _write(self, text: str):
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, text)
        self.widget.see(tk.END)
        self.widget.configure(state="disabled")


class ClippyGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Clippy AI - Video Repurposing")
        self.root.geometry("980x680")
        self._init_style()

        self.agent = None
        self.agent_config_path = None
        self.log_sink_id = None
        self.buttons = []

        self.url_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.batch_file_var = tk.StringVar()
        self.config_file_var = tk.StringVar(value="config.yaml")
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.IntVar(value=0)
        self.max_clips_var = tk.IntVar(value=5)

        self._build_ui()

    def _init_style(self):
        style = ttk.Style()
        if os.name == "nt":
            style.theme_use("vista")
        else:
            style.theme_use("clam")

        primary = "#111827"
        accent = "#2563eb"
        surface = "#0b1221"
        text = "#e5e7eb"
        border = "#1f2937"

        style.configure(
            "TFrame",
            background=primary,
        )
        style.configure(
            "TLabel",
            background=primary,
            foreground=text,
        )
        style.configure(
            "TLabelframe",
            background=primary,
            foreground=text,
            bordercolor=border,
            relief="groove",
        )
        style.configure(
            "TLabelframe.Label",
            background=primary,
            foreground=text,
        )
        style.configure(
            "TButton",
            padding=(10, 6),
        )
        style.map("TButton", background=[("active", accent)], foreground=[("active", "white")])
        style.configure("Card.TFrame", background=surface, borderwidth=1, relief="solid", bordercolor=border)
        style.configure("Accent.TButton", background=accent, foreground="white")
        style.map("Accent.TButton", background=[("active", "#1d4ed8")], foreground=[("active", "white")])
        style.configure("Status.TLabel", font=("Helvetica", 10, "bold"))

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        header = ttk.Frame(self.root, padding=(20, 16), style="Card.TFrame")
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        header.columnconfigure(1, weight=1)

        icon = ttk.Label(header, text="🧠", font=("Helvetica", 24))
        icon.grid(row=0, column=0, rowspan=2, padx=(0, 12))

        title = ttk.Label(
            header,
            text="Clippy - Autonomous Video Repurposing Agent",
            font=("Helvetica", 17, "bold"),
        )
        title.grid(row=0, column=1, sticky="w")

        subtitle = ttk.Label(
            header,
            text="Process long-form videos into short clips with AI-powered analysis.",
            font=("Helvetica", 11),
        )
        subtitle.grid(row=1, column=1, sticky="w")

        main_area = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_area.grid(row=2, column=0, padx=16, pady=8, sticky="nsew")

        control_panel = ttk.Frame(main_area, padding=6, style="Card.TFrame")
        control_panel.columnconfigure(0, weight=1)
        main_area.add(control_panel, weight=3)

        log_panel = ttk.Frame(main_area, padding=6, style="Card.TFrame")
        log_panel.columnconfigure(0, weight=1)
        log_panel.rowconfigure(1, weight=1)
        main_area.add(log_panel, weight=4)

        self._build_controls(control_panel)
        self._build_log_area(log_panel)

        status_frame = ttk.Frame(self.root, padding=(16, 8))
        status_frame.grid(row=3, column=0, sticky="ew")
        status_frame.columnconfigure(1, weight=1)

        self.status_dot = tk.Canvas(status_frame, width=14, height=14, highlightthickness=0, bg="#111827")
        self.status_dot.grid(row=0, column=0, padx=(0, 8))
        self._set_status("Ready")

        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        progress = ttk.Progressbar(status_frame, mode="determinate", maximum=100, variable=self.progress_var)
        progress.grid(row=0, column=2, padx=8, sticky="e")

    def _build_controls(self, parent: ttk.Frame):
        # Configuration card
        config_frame = ttk.LabelFrame(parent, text="Configuration", padding=12)
        config_frame.grid(row=0, column=0, padx=4, pady=(4, 10), sticky="ew")
        config_frame.columnconfigure(1, weight=1)

        ttk.Label(config_frame, text="Config file:").grid(row=0, column=0, sticky="w")
        config_entry = ttk.Entry(config_frame, textvariable=self.config_file_var)
        config_entry.grid(row=0, column=1, padx=8, sticky="ew")
        self._add_button(config_frame, text="Browse", command=self._select_config).grid(row=0, column=2)

        ttk.Label(config_frame, text="Max clips to generate:").grid(row=1, column=0, sticky="w")
        ttk.Spinbox(
            config_frame,
            from_=1,
            to=20,
            textvariable=self.max_clips_var,
            width=6,
        ).grid(row=1, column=1, padx=8, sticky="w")

        ttk.Label(
            config_frame,
            text="Tip: copy config.example.yaml to config.yaml then update your keys before running.",
            font=("Helvetica", 9),
            foreground="#cbd5e1",
        ).grid(row=2, column=0, columnspan=3, pady=(6, 0), sticky="w")

        notebook = ttk.Notebook(parent)
        notebook.grid(row=1, column=0, sticky="nsew", padx=4)
        parent.rowconfigure(1, weight=1)

        single_tab = ttk.Frame(notebook, padding=12)
        batch_tab = ttk.Frame(notebook, padding=12)
        scheduler_tab = ttk.Frame(notebook, padding=12)
        notebook.add(single_tab, text="Single Video")
        notebook.add(batch_tab, text="Batch")
        notebook.add(scheduler_tab, text="Scheduler")

        self._build_single_tab(single_tab)
        self._build_batch_tab(batch_tab)
        self._build_scheduler_tab(scheduler_tab)

    def _build_single_tab(self, tab: ttk.Frame):
        tab.columnconfigure(1, weight=1)

        ttk.Label(tab, text="URL or file:").grid(row=0, column=0, sticky="w")
        url_entry = ttk.Entry(tab, textvariable=self.url_var)
        url_entry.grid(row=0, column=1, padx=8, sticky="ew")
        self._add_button(tab, text="Browse", command=self._select_video).grid(row=0, column=2)

        ttk.Label(tab, text="Title override (optional):").grid(row=1, column=0, pady=8, sticky="w")
        ttk.Entry(tab, textvariable=self.title_var).grid(row=1, column=1, padx=8, pady=8, sticky="ew")

        self._add_button(tab, text="Process Video", style="Accent.TButton", command=self._on_process_single).grid(
            row=2, column=0, columnspan=3, pady=(12, 0), sticky="e"
        )

    def _build_batch_tab(self, tab: ttk.Frame):
        tab.columnconfigure(1, weight=1)

        ttk.Label(tab, text="Batch file (one URL/path per line):").grid(row=0, column=0, sticky="w")
        batch_entry = ttk.Entry(tab, textvariable=self.batch_file_var)
        batch_entry.grid(row=0, column=1, padx=8, sticky="ew")
        self._add_button(tab, text="Browse", command=self._select_batch).grid(row=0, column=2)

        self._add_button(tab, text="Process Batch", style="Accent.TButton", command=self._on_process_batch).grid(
            row=1, column=0, columnspan=3, pady=(12, 0), sticky="e"
        )

    def _build_scheduler_tab(self, tab: ttk.Frame):
        ttk.Label(tab, text="Start or stop the automated scheduler for continuous pulls.").grid(
            row=0, column=0, columnspan=2, pady=(0, 12), sticky="w"
        )

        self._add_button(tab, text="Start Scheduler", command=self._on_start_scheduler, style="Accent.TButton").grid(
            row=1, column=0, padx=4, sticky="w"
        )
        self._add_button(tab, text="Stop Scheduler", command=self._on_stop_scheduler).grid(row=1, column=1, padx=4)

        ttk.Label(tab, text="The scheduler uses settings from the selected config file.", font=("Helvetica", 9)).grid(
            row=2, column=0, columnspan=2, pady=(12, 0), sticky="w"
        )

    def _build_log_area(self, parent: ttk.Frame):
        header = ttk.Frame(parent)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Activity", font=("Helvetica", 12, "bold")).grid(row=0, column=0, sticky="w")
        self._add_button(header, text="Clear", command=self._clear_logs).grid(row=0, column=1, padx=4)
        self._add_button(header, text="Copy", command=self._copy_logs).grid(row=0, column=2)

        log_frame = ttk.Frame(parent)
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_widget = tk.Text(
            log_frame,
            height=18,
            wrap="word",
            state="disabled",
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
            relief="flat",
            borderwidth=6,
            highlightthickness=0,
        )
        self.log_widget.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_widget.configure(yscrollcommand=scrollbar.set)

    def _add_button(self, parent, **kwargs):
        button = ttk.Button(parent, **kwargs)
        self.buttons.append(button)
        return button

    def _select_config(self):
        filename = filedialog.askopenfilename(title="Select config.yaml", filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")])
        if filename:
            self.config_file_var.set(filename)

    def _select_video(self):
        filename = filedialog.askopenfilename(title="Select video file")
        if filename:
            self.url_var.set(filename)

    def _select_batch(self):
        filename = filedialog.askopenfilename(title="Select batch list")
        if filename:
            self.batch_file_var.set(filename)

    def _ensure_agent(self):
        config_path = self.config_file_var.get().strip() or "config.yaml"
        if self.agent and self.agent_config_path == config_path:
            return

        self.agent = ClippyAgent(config_path)
        self.agent_config_path = config_path

        # Pull UI defaults from the loaded config
        self.max_clips_var.set(self.agent.config.get("video.max_highlights", self.max_clips_var.get()))

        if self.log_sink_id is not None:
            logger.remove(self.log_sink_id)
        self.log_sink_id = logger.add(TextboxLogHandler(self.log_widget), format="{time:HH:mm:ss} | {level} | {message}")

    def _run_async(self, coro):
        def task():
            try:
                asyncio.run(coro)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Error", str(exc))
                logger.error(f"GUI task error: {exc}")
            finally:
                self._set_status("Ready")
                self._toggle_buttons(state=tk.NORMAL)
                self.progress_var.set(0)

        threading.Thread(target=task, daemon=True).start()

    def _toggle_buttons(self, state):
        for button in self.buttons:
            button.config(state=state)

    def _set_status(self, text: str):
        self.status_var.set(text)
        self._update_status_dot(text)

    def _update_status_dot(self, text: str):
        color = "#10b981" if "ready" in text.lower() else "#f59e0b"
        if any(word in text.lower() for word in ["error", "fail"]):
            color = "#ef4444"
        self.status_dot.delete("all")
        self.status_dot.create_oval(2, 2, 12, 12, fill=color, outline=color)

    def _on_process_single(self):
        source = self.url_var.get().strip()
        if not source:
            messagebox.showwarning("Missing input", "Please enter a URL or choose a video file.")
            return

        self._ensure_agent()
        self._set_status("Processing single video…")
        self._toggle_buttons(state=tk.DISABLED)
        self.progress_var.set(25)
        self._apply_clip_preferences()
        self._run_async(self.agent.process_video(source, title=self.title_var.get().strip() or None))

    def _on_process_batch(self):
        batch_file = self.batch_file_var.get().strip()
        if not batch_file:
            messagebox.showwarning("Missing batch file", "Please select a batch list file.")
            return

        try:
            with open(batch_file, "r", encoding="utf-8") as f:
                entries = [line.strip() for line in f.readlines() if line.strip()]
        except OSError as exc:  # noqa: PERF203
            messagebox.showerror("Error", f"Unable to read batch file: {exc}")
            return

        if not entries:
            messagebox.showwarning("Empty batch", "The selected batch file has no entries.")
            return

        self._ensure_agent()
        self._set_status(f"Processing batch ({len(entries)} items)…")
        self._toggle_buttons(state=tk.DISABLED)
        self.progress_var.set(35)
        self._apply_clip_preferences()
        self._run_async(self.agent.batch_process(entries))

    def _on_start_scheduler(self):
        self._ensure_agent()
        self._apply_clip_preferences()
        self.agent.scheduler.start()
        self._set_status("Scheduler running")
        self.progress_var.set(100)

    def _on_stop_scheduler(self):
        if self.agent:
            self.agent.scheduler.stop()
            self._set_status("Scheduler stopped")
            self.progress_var.set(0)

    def _clear_logs(self):
        self.log_widget.configure(state="normal")
        self.log_widget.delete("1.0", tk.END)
        self.log_widget.configure(state="disabled")

    def _copy_logs(self):
        content = self.log_widget.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Nothing to copy", "There are no log messages yet.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        messagebox.showinfo("Copied", "Logs copied to clipboard.")

    def _apply_clip_preferences(self):
        if not self.agent:
            return

        try:
            max_clips = max(1, int(self.max_clips_var.get()))
        except (TypeError, tk.TclError):
            max_clips = 5

        self.max_clips_var.set(max_clips)
        self.agent.config.set("video.max_highlights", max_clips)

    def run(self):
        self.root.mainloop()


def main():
    gui = ClippyGUI()
    gui.run()


if __name__ == "__main__":
    main()
