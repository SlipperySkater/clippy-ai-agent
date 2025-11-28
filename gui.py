"""
Simple Tkinter GUI for Clippy AI Agent.
"""

import asyncio
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from loguru import logger

from main import ClippyAgent


class TextboxLogHandler:
    """Loguru sink that writes log messages to a Tkinter text widget."""

    def __init__(self, widget: tk.Text):
        self.widget = widget

    def __call__(self, message):
        formatted = message.strip() + "\n"
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, formatted)
        self.widget.see(tk.END)
        self.widget.configure(state="disabled")


class ClippyGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Clippy AI - Video Repurposing")
        self.root.geometry("840x620")

        self.agent = None
        self.agent_config_path = None
        self.log_sink_id = None

        self.url_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.batch_file_var = tk.StringVar()
        self.config_file_var = tk.StringVar(value="config.yaml")
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)

        header = ttk.Label(
            self.root,
            text="Clippy - Autonomous Video Repurposing Agent",
            font=("Helvetica", 16, "bold"),
        )
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        desc = ttk.Label(
            self.root,
            text="Process long-form videos into short clips with AI-powered analysis.",
            font=("Helvetica", 11),
        )
        desc.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        config_frame = ttk.LabelFrame(self.root, text="Configuration", padding=12)
        config_frame.grid(row=2, column=0, padx=16, pady=8, sticky="ew")
        config_frame.columnconfigure(1, weight=1)

        ttk.Label(config_frame, text="Config file:").grid(row=0, column=0, sticky="w")
        config_entry = ttk.Entry(config_frame, textvariable=self.config_file_var)
        config_entry.grid(row=0, column=1, padx=8, sticky="ew")
        ttk.Button(config_frame, text="Browse", command=self._select_config).grid(row=0, column=2)

        input_frame = ttk.LabelFrame(self.root, text="Single Video", padding=12)
        input_frame.grid(row=3, column=0, padx=16, pady=8, sticky="ew")
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="URL or file:").grid(row=0, column=0, sticky="w")
        url_entry = ttk.Entry(input_frame, textvariable=self.url_var)
        url_entry.grid(row=0, column=1, padx=8, sticky="ew")
        ttk.Button(input_frame, text="Browse", command=self._select_video).grid(row=0, column=2)

        ttk.Label(input_frame, text="Title override (optional):").grid(row=1, column=0, pady=6, sticky="w")
        ttk.Entry(input_frame, textvariable=self.title_var).grid(row=1, column=1, padx=8, pady=6, sticky="ew")

        ttk.Button(input_frame, text="Process Video", command=self._on_process_single).grid(
            row=2, column=0, columnspan=3, pady=(8, 0), sticky="e"
        )

        batch_frame = ttk.LabelFrame(self.root, text="Batch Processing", padding=12)
        batch_frame.grid(row=4, column=0, padx=16, pady=8, sticky="ew")
        batch_frame.columnconfigure(1, weight=1)

        ttk.Label(batch_frame, text="Batch file (one URL/path per line):").grid(row=0, column=0, sticky="w")
        batch_entry = ttk.Entry(batch_frame, textvariable=self.batch_file_var)
        batch_entry.grid(row=0, column=1, padx=8, sticky="ew")
        ttk.Button(batch_frame, text="Browse", command=self._select_batch).grid(row=0, column=2)

        ttk.Button(batch_frame, text="Process Batch", command=self._on_process_batch).grid(
            row=1, column=0, columnspan=3, pady=(8, 0), sticky="e"
        )

        scheduler_frame = ttk.LabelFrame(self.root, text="Scheduler", padding=12)
        scheduler_frame.grid(row=5, column=0, padx=16, pady=8, sticky="ew")

        ttk.Button(scheduler_frame, text="Start Scheduler", command=self._on_start_scheduler).grid(
            row=0, column=0, padx=4
        )
        ttk.Button(scheduler_frame, text="Stop Scheduler", command=self._on_stop_scheduler).grid(
            row=0, column=1, padx=4
        )

        status_frame = ttk.Frame(self.root, padding=(16, 8))
        status_frame.grid(row=6, column=0, sticky="ew")
        ttk.Label(status_frame, textvariable=self.status_var, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)

        log_frame = ttk.LabelFrame(self.root, text="Activity", padding=12)
        log_frame.grid(row=7, column=0, padx=16, pady=(0, 16), sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_widget = tk.Text(log_frame, height=12, wrap="word", state="disabled", bg="#0f172a", fg="#e2e8f0")
        self.log_widget.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_widget.configure(yscrollcommand=scrollbar.set)

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

        threading.Thread(target=task, daemon=True).start()

    def _toggle_buttons(self, state):
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.LabelFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button):
                        child.config(state=state)

    def _set_status(self, text: str):
        self.status_var.set(text)

    def _on_process_single(self):
        source = self.url_var.get().strip()
        if not source:
            messagebox.showwarning("Missing input", "Please enter a URL or choose a video file.")
            return

        self._ensure_agent()
        self._set_status("Processing single video…")
        self._toggle_buttons(state=tk.DISABLED)
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
        self._run_async(self.agent.batch_process(entries))

    def _on_start_scheduler(self):
        self._ensure_agent()
        self.agent.scheduler.start()
        self._set_status("Scheduler running")

    def _on_stop_scheduler(self):
        if self.agent:
            self.agent.scheduler.stop()
            self._set_status("Scheduler stopped")

    def run(self):
        self.root.mainloop()


def main():
    gui = ClippyGUI()
    gui.run()


if __name__ == "__main__":
    main()
