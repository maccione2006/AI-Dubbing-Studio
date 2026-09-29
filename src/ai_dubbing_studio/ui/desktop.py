from __future__ import annotations

import os
import queue
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from typing import Callable

from ai_dubbing_studio.audio.analysis import AudioMetrics, analyze_wav
from ai_dubbing_studio.config import Settings
from ai_dubbing_studio.core.workflow import WorkflowResult, compare_existing_candidates


class DubbingStudioApp:
    _ELEVENLABS_URL = "https://elevenlabs.io/app/speech-synthesis"

    def __init__(self, root: tk.Tk, settings: Settings) -> None:
        self.root = root
        self.settings = settings
        self._events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._on_success: Callable[[object], None] | None = None
        self._error_title = "Operazione non riuscita"
        self._busy = False
        self._voice_ids: dict[str, str] = {}
        self._result: WorkflowResult | None = None

        root.title(settings.app_name)
        root.geometry("1040x820")
        root.minsize(820, 680)
        self._build_layout()
        self.root.after(100, self._process_events)

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=18)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)
        container.rowconfigure(5, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        ttk.Label(header, text=self.settings.app_name, font=("Segoe UI", 19, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Analisi WAV locale  |  Generazione sul sito ufficiale ElevenLabs",
        ).pack(anchor="w", pady=(3, 0))

        input_frame = ttk.LabelFrame(container, text="Materiale sorgente", padding=12)
        input_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        input_frame.columnconfigure(1, weight=1)
        self.audio_path = tk.StringVar()
        ttk.Label(input_frame, text="Audio originale (PCM WAV)").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(input_frame, textvariable=self.audio_path).grid(row=0, column=1, sticky="ew")
        ttk.Button(input_frame, text="Sfoglia", command=self._choose_audio).grid(row=0, column=2, padx=(8, 0))
        self.analyze_button = ttk.Button(input_frame, text="Analizza audio", command=self._analyze_source)
        self.analyze_button.grid(row=0, column=3, padx=(8, 0))
        self.source_summary = ttk.Label(input_frame, text="Nessun audio analizzato", foreground="#555555")
        self.source_summary.grid(row=1, column=1, columnspan=3, sticky="w", pady=(7, 0))

        script_frame = ttk.LabelFrame(container, text="Script", padding=12)
        script_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 12))
        script_frame.columnconfigure(0, weight=1)
        script_frame.rowconfigure(0, weight=1)
        self.script_text = ScrolledText(script_frame, height=7, wrap="word", undo=True)
        self.script_text.grid(row=0, column=0, sticky="nsew")
        ttk.Button(script_frame, text="Carica file TXT", command=self._load_script).grid(
            row=1, column=0, sticky="e", pady=(8, 0)
        )

        options_frame = ttk.LabelFrame(container, text="ElevenLabs ufficiale", padding=12)
        options_frame.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        self.open_site_button = ttk.Button(
            options_frame,
            text="Copia script e apri ElevenLabs",
            command=self._open_elevenlabs,
        )
        self.open_site_button.pack(side="left")
        self.import_candidates_button = ttk.Button(
            options_frame,
            text="Importa WAV scaricati",
            command=self._choose_candidates,
        )
        self.import_candidates_button.pack(side="left", padx=(8, 0))
        self.compare_button = ttk.Button(
            options_frame,
            text="Confronta candidati",
            command=self._compare_downloaded,
            state="disabled",
        )
        self.compare_button.pack(side="left", padx=(8, 0))
        self.selected_files_summary = ttk.Label(options_frame, text="Nessun candidato importato")
        self.selected_files_summary.pack(side="right", padx=(12, 0))
        self._candidate_paths: tuple[str, ...] = ()

        action_frame = ttk.Frame(container)
        action_frame.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        self.open_folder_button = ttk.Button(
            action_frame,
            text="Apri cartella candidati",
            command=self._open_output_folder,
            state="disabled",
        )
        self.open_folder_button.pack(side="left")

        results_frame = ttk.LabelFrame(container, text="Confronto candidati", padding=12)
        results_frame.grid(row=5, column=0, sticky="nsew", pady=(0, 10))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        columns = ("candidate", "score", "duration", "pauses", "intensity")
        self.results_table = ttk.Treeview(results_frame, columns=columns, show="headings", height=5, selectmode="browse")
        for column, title, width in (
            ("candidate", "Candidata", 210),
            ("score", "Punteggio", 100),
            ("duration", "Durata", 100),
            ("pauses", "Pause", 100),
            ("intensity", "Intensita dBFS", 120),
        ):
            self.results_table.heading(column, text=title)
            self.results_table.column(column, width=width, anchor="w" if column == "candidate" else "center")
        self.results_table.grid(row=0, column=0, sticky="nsew")
        self.results_table.bind("<<TreeviewSelect>>", self._show_selected_candidate)
        result_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_table.yview)
        result_scroll.grid(row=0, column=1, sticky="ns")
        self.results_table.configure(yscrollcommand=result_scroll.set)
        self.details = ScrolledText(results_frame, height=6, wrap="word", state="disabled")
        self.details.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.play_button = ttk.Button(results_frame, text="Apri candidato selezionato", command=self._open_selected_candidate, state="disabled")
        self.play_button.grid(row=2, column=0, sticky="e", pady=(8, 0))

        footer = ttk.Frame(container)
        footer.grid(row=6, column=0, sticky="ew")
        self.status = tk.StringVar(value="Pronto")
        ttk.Label(footer, textvariable=self.status).pack(side="left")
        ttk.Label(
            footer,
            text="Voce e parametri li scegli sul sito; confronto audio locale, senza chiave API.",
        ).pack(side="right")

    def _choose_audio(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleziona audio sorgente",
            filetypes=[("WAV PCM", "*.wav"), ("Tutti i file", "*.*")],
        )
        if path:
            self.audio_path.set(path)
            self.source_summary.configure(text="Audio selezionato; analisi non ancora eseguita")

    def _load_script(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleziona script",
            filetypes=[("File di testo", "*.txt"), ("Tutti i file", "*.*")],
        )
        if path:
            try:
                text = Path(path).read_text(encoding="utf-8-sig")
            except OSError as error:
                messagebox.showerror("Lettura script", str(error))
                return
            self.script_text.delete("1.0", "end")
            self.script_text.insert("1.0", text)

    def _analyze_source(self) -> None:
        source = self.audio_path.get().strip()
        if not source:
            messagebox.showwarning("Analisi audio", "Seleziona prima un file WAV.")
            return
        self._start_task(lambda: analyze_wav(source), self._show_source_metrics, "Analisi audio")

    def _show_source_metrics(self, result: object) -> None:
        metrics = result
        assert isinstance(metrics, AudioMetrics)
        self.source_summary.configure(
            text=(
                f"{metrics.duration_seconds:.2f} s | {metrics.pause_count} pause "
                f"({metrics.pause_ratio * 100:.1f}%) | intensita {metrics.intensity_dbfs:.1f} dBFS "
                f"| {metrics.sample_rate} Hz, {metrics.channels} canali"
            )
        )
        self.status.set("Analisi sorgente completata")

    def _open_elevenlabs(self) -> None:
        script = self.script_text.get("1.0", "end").strip()
        if not script:
            messagebox.showwarning("ElevenLabs", "Inserisci o carica prima lo script.")
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(script)
            opened = webbrowser.open(self._ELEVENLABS_URL)
        except tk.TclError as error:
            messagebox.showerror("ElevenLabs", f"Impossibile copiare lo script: {error}")
            return
        if not opened:
            messagebox.showerror("ElevenLabs", "Impossibile aprire il sito nel browser predefinito.")
            return
        self.status.set("Script copiato: incollalo nel sito, scegli voce e parametri, poi scarica i WAV.")

    def _choose_candidates(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Seleziona i WAV generati sul sito",
            filetypes=[("WAV PCM", "*.wav")],
        )
        if paths:
            self._candidate_paths = tuple(paths)
            self.selected_files_summary.configure(text=f"{len(paths)} file selezionati")
            self.compare_button.configure(state="normal")

    def _compare_downloaded(self) -> None:
        audio_path = self.audio_path.get().strip()
        script = self.script_text.get("1.0", "end").strip()
        if not audio_path or not script or not self._candidate_paths:
            messagebox.showwarning("Confronto", "Seleziona l'audio sorgente, inserisci lo script e importa almeno un WAV.")
            return
        self._start_task(
            lambda: compare_existing_candidates(
                audio_path,
                script,
                list(self._candidate_paths),
            ),
            self._show_result,
            "Confronto candidati",
        )

    def _start_task(
        self,
        operation: Callable[[], object],
        on_success: Callable[[object], None],
        error_title: str,
    ) -> None:
        if self._busy:
            return
        self._busy = True
        self._on_success = on_success
        self._error_title = error_title
        self._set_busy(True)
        self.status.set("Operazione in corso...")

        def run() -> None:
            try:
                self._events.put(("result", operation()))
            except Exception as error:
                self._events.put(("error", error))

        threading.Thread(target=run, daemon=True).start()

    def _process_events(self) -> None:
        while True:
            try:
                event, payload = self._events.get_nowait()
            except queue.Empty:
                break
            if event == "progress":
                current, total, name = payload
                self.status.set(f"Generazione {current}/{total}: {name}")
            elif event == "result":
                self._busy = False
                self._set_busy(False)
                if self._on_success:
                    self._on_success(payload)
            elif event == "error":
                self._busy = False
                self._set_busy(False)
                self.status.set("Operazione non riuscita")
                messagebox.showerror(self._error_title, str(payload))
        self.root.after(100, self._process_events)

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.analyze_button.configure(state=state)
        self.open_site_button.configure(state=state)
        self.import_candidates_button.configure(state=state)
        self.compare_button.configure(state="normal" if not busy and self._candidate_paths else "disabled")

    def _show_result(self, result: object) -> None:
        self._result = result
        assert isinstance(result, WorkflowResult)
        for item in self.results_table.get_children():
            self.results_table.delete(item)
        for index, candidate in enumerate(result.candidates):
            metrics = candidate.audio_metrics
            candidate_name = candidate.profile.name if candidate.profile else candidate.audio_path.name
            label = f"Tentativo {index + 1}: {candidate_name}"
            if index == result.best_index:
                label += " (migliore)"
            self.results_table.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    label,
                    f"{candidate.assessment.score:.1f}/100",
                    f"{metrics.duration_seconds:.2f} s",
                    f"{metrics.pause_ratio * 100:.1f}%",
                    f"{metrics.intensity_dbfs:.1f}",
                ),
            )
        self.open_folder_button.configure(state="normal")
        self.play_button.configure(state="normal")
        self.results_table.selection_set(str(result.best_index))
        self.status.set(
            f"Selezionato tentativo {result.best_index + 1}; risultati in {result.output_directory}"
        )

    def _show_selected_candidate(self, _event: tk.Event) -> None:
        if not self._result:
            return
        selection = self.results_table.selection()
        if not selection:
            return
        candidate = self._result.candidates[int(selection[0])]
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        generation_details = (
            f"Stability {candidate.profile.stability:.2f}, style {candidate.profile.style:.2f}, "
            f"speed {candidate.profile.speed:.2f}."
            if candidate.profile
            else "Generato dal sito ufficiale; voce e parametri selezionati sul sito."
        )
        self.details.insert(
            "1.0",
            f"{generation_details}\n{candidate.assessment.explanation}",
        )
        self.details.configure(state="disabled")

    def _open_selected_candidate(self) -> None:
        if not self._result:
            return
        selection = self.results_table.selection()
        if selection:
            self._open_path(self._result.candidates[int(selection[0])].audio_path)

    def _open_output_folder(self) -> None:
        if self._result:
            self._open_path(self._result.output_directory)

    @staticmethod
    def _open_path(path: Path) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            else:
                webbrowser.open(path.resolve().as_uri())
        except OSError as error:
            messagebox.showerror("Apertura file", str(error))


def run_app(settings: Settings) -> int:
    root = tk.Tk()
    DubbingStudioApp(root, settings)
    root.mainloop()
    return 0