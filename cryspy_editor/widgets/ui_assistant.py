"""Qt part of the AI assistant: the window "AI Assistant / CrysPy Editor",
the dialog of the model settings, the background workers and the menu.

The structure is the one of ui_assistant.py of PyColl5.
"""
import html
import os
import traceback

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, QThread, pyqtSignal

from cryspy_editor.widgets.assistant import (
    DEFAULT_SETTINGS,
    INSTALL_HINT,
    L_RECOMMENDED_MODELS,
    Assistant,
    get_total_memory_gb,
    take_recommended_index,
    take_settings,
)
from cryspy_editor.widgets.assistant_commands import COMMAND_PREFIX, form_completions
from cryspy_editor.widgets.recipe_editor import init_user_recipe_folder

WINDOW_TITLE = "AI Assistant / CrysPy Editor"
PLACEHOLDER = "Ask the question or request an action"
PLACEHOLDER_ANSWER = "Answer the question ('cancel' to stop)"
EXAMPLES = (
    "Examples of requests:\n"
    "- which parameters are refined?\n"
    "- fix all parameters and refine only atomic positions of all atoms\n"
    "- refine the scale factor; refine the polarization\n"
    "- set a of crystal_pbso4 to 8.48 and run the refinement\n"
    "- calculate the nuclear structure factor of the reflection (5 0 3)\n"
    "- download Al from COD and add it to my data\n"
    "- how to describe thermal vibrations?\n"
    "- what can you do?\n"
    "- @refine_structure (a recipe), @refine_parameters scale (an action): the names are proposed after @")


def form_hint_html(memory_gb) -> str:
    """Table of recommended models; the row for this computer is bold."""
    index = take_recommended_index(memory_gb)
    ls_rows = []
    for ind, (min_memory, models, size) in enumerate(L_RECOMMENDED_MODELS):
        s_memory = f"&lt; 8 GB" if min_memory == 0 else f"{min_memory} GB and more"
        cells = [s_memory, html.escape(models), size]
        if ind == index:
            cells = [f"<b>{cell}</b>" for cell in cells]
        ls_rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    if memory_gb is None:
        s_memory = "The memory of this computer is unknown."
    else:
        s_memory = (f"This computer has {memory_gb:.0f} GB of memory; "
                    "the matching row is in bold.")
    return f"""
<p>Any <i>instruct</i> (chat) model in GGUF format works. Recommended:
<b>Qwen2.5-7B-Instruct Q4_K_M</b>; with 16 GB of memory or more
<b>Qwen2.5-14B-Instruct Q4_K_M</b>, which follows the step-by-step recipes
(e.g. the structure refinement) much more reliably. Take a general
<i>Instruct</i> model, not a <i>Coder</i> one: coder models follow
instructions and reason step by step worse. Take the Q4_K_M quantization:
it is more accurate than Q4_0 at the same size. The model file should take
no more than half of the memory.
{s_memory}</p>
<table border="1" cellpadding="3" cellspacing="0">
<tr><th>Memory</th><th>Model</th><th>Q4_K_M file</th></tr>
{''.join(ls_rows)}
</table>
<p>Download the file once from huggingface.co (search for the model name
with "GGUF", e.g. bartowski/Qwen2.5-7B-Instruct-GGUF) and save it in
any folder. After that no internet connection is needed: the model runs on
this computer.</p>
<p><b>Threads</b>: 0 uses all cores but one. <b>GPU layers</b>: -1 puts the
whole model on the GPU (Metal on Apple Silicon), 0 runs on CPU only.
<b>Context</b>: the length of the conversation the model sees, in tokens;
larger needs more memory. For the step-by-step work by recipes take 8192
or more.</p>"""


class ModelSettingsDialog(QtWidgets.QDialog):
    """Choose the model file and its parameters."""

    def __init__(self, model_path: str = "", settings: dict = None,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI assistant: model settings")
        settings = take_settings(settings)

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()

        layout_path = QtWidgets.QHBoxLayout()
        self.line_model_path = QtWidgets.QLineEdit(model_path, self)
        self.line_model_path.setMinimumWidth(400)
        layout_path.addWidget(self.line_model_path)
        button_browse = QtWidgets.QPushButton("Browse...", self)
        button_browse.clicked.connect(self.browse_model)
        layout_path.addWidget(button_browse)
        form.addRow("Model file (*.gguf)", layout_path)

        self.sb_threads = QtWidgets.QSpinBox(self)
        self.sb_threads.setRange(0, max(1, os.cpu_count() or 1))
        self.sb_threads.setValue(settings["n_threads"])
        form.addRow(f"Threads (0 = auto, {os.cpu_count()} cores)", self.sb_threads)

        self.sb_gpu_layers = QtWidgets.QSpinBox(self)
        self.sb_gpu_layers.setRange(-1, 1000)
        self.sb_gpu_layers.setValue(settings["n_gpu_layers"])
        form.addRow("GPU layers (-1 = all, 0 = CPU)", self.sb_gpu_layers)

        self.sb_n_ctx = QtWidgets.QSpinBox(self)
        self.sb_n_ctx.setRange(512, 131072)
        self.sb_n_ctx.setSingleStep(1024)
        self.sb_n_ctx.setValue(settings["n_ctx"])
        form.addRow("Context (tokens)", self.sb_n_ctx)

        self.sb_max_tokens = QtWidgets.QSpinBox(self)
        self.sb_max_tokens.setRange(64, 8192)
        self.sb_max_tokens.setSingleStep(128)
        self.sb_max_tokens.setValue(settings["max_tokens"])
        form.addRow("Maximal answer length (tokens)", self.sb_max_tokens)

        self.dsb_temperature = QtWidgets.QDoubleSpinBox(self)
        self.dsb_temperature.setRange(0.0, 2.0)
        self.dsb_temperature.setSingleStep(0.1)
        self.dsb_temperature.setValue(settings["temperature"])
        form.addRow("Temperature", self.dsb_temperature)
        layout.addLayout(form)

        hint = QtWidgets.QTextBrowser(self)
        hint.setOpenExternalLinks(True)
        hint.setHtml(form_hint_html(get_total_memory_gb()))
        hint.setMinimumHeight(260)
        layout.addWidget(hint)

        buttons = QtWidgets.QDialogButtonBox(self)
        button_defaults = buttons.addButton(
            "Defaults", QtWidgets.QDialogButtonBox.ResetRole)
        button_defaults.clicked.connect(self.set_defaults)
        buttons.addButton("Load model", QtWidgets.QDialogButtonBox.AcceptRole)
        buttons.addButton(QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def browse_model(self):
        f_dir = os.path.dirname(self.line_model_path.text())
        if not os.path.isdir(f_dir):
            f_dir = os.path.expanduser("~")
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose local model", f_dir,
            "GGUF models (*.gguf);; All Files (*)")
        if file_name:
            self.line_model_path.setText(file_name)

    def set_defaults(self):
        self.sb_threads.setValue(DEFAULT_SETTINGS["n_threads"])
        self.sb_gpu_layers.setValue(DEFAULT_SETTINGS["n_gpu_layers"])
        self.sb_n_ctx.setValue(DEFAULT_SETTINGS["n_ctx"])
        self.sb_max_tokens.setValue(DEFAULT_SETTINGS["max_tokens"])
        self.dsb_temperature.setValue(DEFAULT_SETTINGS["temperature"])

    def accept_if_valid(self):
        if not os.path.isfile(self.model_path()):
            QtWidgets.QMessageBox.warning(
                self, "AI assistant",
                "Choose an existing model file (*.gguf).")
            return
        self.accept()

    def model_path(self) -> str:
        return self.line_model_path.text().strip()

    def settings(self) -> dict:
        return {
            "n_ctx": self.sb_n_ctx.value(),
            "n_threads": self.sb_threads.value(),
            "n_gpu_layers": self.sb_gpu_layers.value(),
            "max_tokens": self.sb_max_tokens.value(),
            "temperature": self.dsb_temperature.value(),
        }


class LoadWorker(QObject):
    """Loads the model in a background thread."""

    finished = pyqtSignal(object)  # emits Assistant
    error = pyqtSignal(str)

    def __init__(self, model_path: str, settings: dict = None):
        super().__init__()
        self.model_path = model_path
        self.settings = settings
        self.assistant = None

    def run(self):
        try:
            from cryspy_editor.widgets.assistant import LocalModel
            # kept here too: shutdown frees it if the window never gets it
            self.assistant = Assistant(LocalModel(self.model_path, self.settings))
            self.finished.emit(self.assistant)
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")


class AskWorker(QObject):
    """Runs Assistant.ask in a background thread: the model and the tools
    of CrysPy work on the object there; the window reads the object only
    after the reply."""

    finished = pyqtSignal(dict)  # emits the result of Assistant.ask
    error = pyqtSignal(str)
    action_started = pyqtSignal(str)
    step_text = pyqtSignal(str)  # a step of the work by a recipe, as it goes

    def __init__(self, assistant: Assistant, question: str, cryspy_object):
        super().__init__()
        self.assistant = assistant
        self.question = question
        self.cryspy_object = cryspy_object

    def run(self):
        try:
            self.finished.emit(self.assistant.ask(
                self.question, self.cryspy_object, on_action=self.action_started.emit,
                on_step=self.step_text.emit))
        except Exception as e:
            traceback.print_exc()
            self.error.emit(f"{type(e).__name__}: {e}")


class AssistantWindow(QtWidgets.QWidget):
    """Chat with the assistant in a window of its own. Closing hides it, so
    that the chat, the size and the position stay for the session."""

    signal_object_changed = pyqtSignal()
    signal_model_loaded = pyqtSignal(str)  # model path, empty if failed

    def __init__(self, take_cryspy_object=None, parent=None):
        super().__init__(parent, QtCore.Qt.Window)
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(600, 500)
        self.assistant = None
        self.assistant_no_model = None  # '@name' commands without a model
        self.take_cryspy_object = take_cryspy_object
        self.thread = None
        self.worker = None

        layout = QtWidgets.QVBoxLayout(self)

        layout_title = QtWidgets.QHBoxLayout()
        self.label_model = QtWidgets.QLabel("No model loaded")
        layout_title.addWidget(self.label_model, 1)
        self.button_clear = QtWidgets.QPushButton("Clear chat")
        self.button_clear.clicked.connect(self.clear_chat)
        layout_title.addWidget(self.button_clear)
        layout.addLayout(layout_title)

        self.history_view = QtWidgets.QTextEdit(self)
        self.history_view.setReadOnly(True)
        self.history_view.setPlaceholderText(EXAMPLES)
        layout.addWidget(self.history_view)

        self.input_line = QtWidgets.QLineEdit(self)
        self.input_line.setPlaceholderText(PLACEHOLDER)
        self.input_line.returnPressed.connect(self.on_send)
        self.input_line.textEdited.connect(self.on_text_edited)
        # '@' proposes the recipes and the actions with their descriptions
        self.completer = QtWidgets.QCompleter(QtGui.QStandardItemModel(self), self)
        self.completer.setCompletionRole(QtCore.Qt.UserRole)
        self.completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.completer.setMaxVisibleItems(12)
        self.input_line.setCompleter(self.completer)
        # Tab and Shift+Tab go through the proposed names instead of moving the focus
        self.input_line.installEventFilter(self)
        self.completer.popup().installEventFilter(self)
        self.update_completions()
        layout_input = QtWidgets.QHBoxLayout()
        layout_input.addWidget(self.input_line, 1)
        # the step-by-step work of the assistant stops after the running action
        self.button_stop = QtWidgets.QPushButton("Stop")
        self.button_stop.setToolTip("Stop the step-by-step work after the running action")
        self.button_stop.clicked.connect(self.on_stop)
        self.button_stop.setEnabled(False)
        layout_input.addWidget(self.button_stop)
        layout.addLayout(layout_input)

    def update_completions(self):
        """The recipes (they may be changed in the window of recipes) and
        the actions: '@name' is completed, 'name: description' is shown."""
        model = self.completer.model()
        model.clear()
        for command, description in form_completions():
            item = QtGui.QStandardItem(f"{command}  {description}")
            item.setData(command, QtCore.Qt.UserRole)
            item.setToolTip(description)
            model.appendRow(item)

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.KeyPress and watched in (self.completer.popup(), self.input_line):
            if event.key() in (QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab):
                if self.cycle_completion(event.key() == QtCore.Qt.Key_Backtab):
                    return True
            elif event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter) and self.take_completion():
                return True
        return super().eventFilter(watched, event)

    def take_completion(self) -> bool:
        """Enter on a proposed name writes it in the input line, followed by
        a space for the arguments; the next Enter sends the request."""
        popup = self.completer.popup()
        index = popup.currentIndex()
        if not popup.isVisible() or not index.isValid():
            return False
        self.input_line.setText(f"{index.data(QtCore.Qt.UserRole)} ")
        popup.hide()
        return True

    def cycle_completion(self, flag_back: bool = False) -> bool:
        """Highlight the next (previous) proposed name, which is written in
        the input line; Enter takes it. After '@name' without the list the
        list is opened. False when there is nothing to propose: Tab then
        moves the focus as usual."""
        popup = self.completer.popup()
        if not popup.isVisible():
            text = self.input_line.text()
            if not text.startswith(COMMAND_PREFIX) or " " in text:
                return False
            self.completer.setCompletionPrefix(text)
            if self.completer.completionCount() == 0:
                return False
            self.completer.complete()
        n_row = self.completer.completionCount()
        if n_row == 0:
            return False
        row = popup.currentIndex().row()
        if row < 0:
            row = n_row - 1 if flag_back else 0
        else:
            row = (row + (-1 if flag_back else 1)) % n_row
        index = self.completer.completionModel().index(row, 0)
        popup.setCurrentIndex(index)
        popup.scrollTo(index)
        return True

    def on_text_edited(self, text: str):
        if text == COMMAND_PREFIX:
            self.update_completions()
            self.completer.complete()

    def take_assistant(self):
        """The assistant with the model, or one without a model for the
        commands '@name' and the question 'what can you do?'."""
        if self.assistant is not None:
            return self.assistant
        if self.assistant_no_model is None:
            self.assistant_no_model = Assistant(None)
        return self.assistant_no_model

    def show_window(self):
        """Show the window, or raise it if it is already open."""
        self.show()
        self.raise_()
        self.activateWindow()

    def is_busy(self) -> bool:
        return self.thread is not None

    def _start_thread(self, worker, on_finished, on_error):
        self.thread = QThread()
        self.worker = worker
        worker.moveToThread(self.thread)
        self.thread.started.connect(worker.run)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.finished.connect(self.thread.quit)
        worker.error.connect(self.thread.quit)
        self.thread.finished.connect(self._thread_done)
        self.thread.start()

    def _thread_done(self):
        self.thread.deleteLater()
        self.thread = None
        self.worker = None

    def load_model(self, model_path: str, settings: dict = None):
        if self.is_busy():
            return
        self.assistant = None
        self.input_line.setEnabled(False)
        self.label_model.setText(f"Loading {model_path} ...")
        self._start_thread(
            LoadWorker(model_path, settings), self.on_model_loaded,
            self.on_model_error)

    def unload_model(self):
        if self.is_busy():
            return
        self._free_model()
        self.label_model.setText("No model loaded")

    def _free_model(self):
        assistant, self.assistant = self.assistant, None
        if assistant is not None:
            assistant.close()

    def shutdown(self):
        """Before the program exits: wait for the running request or load
        and free the model, so that llama.cpp does not abort at exit."""
        thread, worker = self.thread, self.worker
        self.thread = None
        self.worker = None
        if thread is not None:
            # no queued slot of the finished thread may run later: with
            # self.thread None, _thread_done would raise and PyQt aborts
            thread.finished.disconnect()
            worker.finished.disconnect()
            worker.error.disconnect()
            thread.quit()
            thread.wait()
            thread.deleteLater()
            # the result of a load finished now never reaches the window
            loaded = getattr(worker, "assistant", None)
            if loaded is not None and loaded is not self.assistant:
                loaded.close()
        self._free_model()

    def on_model_loaded(self, assistant: Assistant):
        self.assistant = assistant
        self.label_model.setText(f"Model: {assistant.model_name}")
        self.input_line.setEnabled(True)
        self.input_line.setFocus()
        self.signal_model_loaded.emit(assistant.model_path)

    def on_model_error(self, msg: str):
        self.label_model.setText("No model loaded")
        self.append_history("Error", msg)
        self.input_line.setEnabled(True)
        self.signal_model_loaded.emit("")

    def clear_chat(self):
        self.history_view.clear()
        if self.assistant is not None:
            self.assistant.clear_history()

    def append_history(self, role: str, text: str):
        # escape: replies contain CIF text and '<' signs
        self.history_view.append(
            f"<b>{html.escape(role)}:</b>"
            f"<pre style='white-space: pre-wrap'>{html.escape(text)}</pre>")

    def append_step(self, text: str):
        """A step of the work by a recipe, shown as it goes."""
        self.history_view.append(f"<pre style='white-space: pre-wrap'>{html.escape(text)}</pre>")
        self.history_view.moveCursor(QtGui.QTextCursor.End)

    def on_send(self):
        question = self.input_line.text().strip()
        if question == "" or self.is_busy():
            return
        assistant = self.take_assistant()
        self.append_history("You", question)
        self.input_line.clear()
        self.input_line.setEnabled(False)
        self.input_line.setPlaceholderText("Thinking...")
        cryspy_object = None
        if self.take_cryspy_object is not None:
            cryspy_object = self.take_cryspy_object()
        worker = AskWorker(assistant, question, cryspy_object)
        self.button_stop.setEnabled(True)
        worker.action_started.connect(
            lambda action: self.input_line.setPlaceholderText(f"Running '{action}'... (Stop ends the work)"))
        worker.step_text.connect(self.append_step)
        self._start_thread(worker, self.on_reply, self.on_error)

    def on_stop(self):
        if isinstance(self.worker, AskWorker):
            self.worker.assistant.request_stop()
            self.button_stop.setEnabled(False)
            self.input_line.setPlaceholderText("Stopping after the running action...")

    def _ready_for_input(self, flag_question: bool = False):
        self.button_stop.setEnabled(False)
        self.input_line.setEnabled(True)
        self.input_line.setPlaceholderText(PLACEHOLDER_ANSWER if flag_question else PLACEHOLDER)
        self.input_line.setFocus()

    def on_reply(self, result: dict):
        self.append_history("AI", result["text"])
        self._ready_for_input(bool(result.get("question", False)))
        if result.get("flag_object_changed", False):
            self.signal_object_changed.emit()

    def on_error(self, msg: str):
        self.append_history("Error", msg)
        self._ready_for_input(self.take_assistant().is_asking())


class AssistantController(QObject):
    """Menu "AI assistant" of the main window: Load local model, Show
    assistant, Unload model; loads the model of the last session at start.

    d_setup keys (kept from older versions): llm_model_path, llm_settings,
    llm_autoload; assistant_window_visible.
    """

    def __init__(self, main_window, d_setup: dict, save_settings, take_cryspy_object, on_object_changed):
        super().__init__(main_window)
        self.main_window = main_window
        self.d_setup = d_setup
        self.save_settings = save_settings
        self.window = AssistantWindow(take_cryspy_object=take_cryspy_object, parent=main_window)
        self.window.signal_object_changed.connect(on_object_changed)
        self.window.signal_model_loaded.connect(self.on_model_loaded)
        self.recipe_dialog = None
        init_user_recipe_folder()
        app = QtWidgets.QApplication.instance()
        if app is not None:
            # also when the program quits without closing the main window
            app.aboutToQuit.connect(self.shutdown)

    def init_menu(self, menu_bar):
        menu_ai = menu_bar.addMenu("AI assistant")
        load_action = menu_ai.addAction("Load local model (*.gguf)...")
        load_action.setStatusTip(
            "Choose a GGUF chat model and its settings; it runs on this computer.")
        load_action.triggered.connect(self.choose_model)
        show_action = menu_ai.addAction("Show assistant")
        show_action.triggered.connect(self.show_window)
        unload_action = menu_ai.addAction("Unload model")
        unload_action.triggered.connect(self.unload_model)
        menu_ai.addSeparator()
        recipes_action = menu_ai.addAction("CookBook...")
        recipes_action.setStatusTip(
            "Read, write and edit the recipes: the steps of typical analyses the assistant follows.")
        recipes_action.triggered.connect(self.show_recipes)
        return menu_ai

    def show_recipes(self):
        from cryspy_editor.widgets.recipe_editor import (
            RecipeEditorDialog,
            flag_recipe_files,
        )
        if not flag_recipe_files():
            QtWidgets.QMessageBox.information(
                self.main_window, WINDOW_TITLE,
                "Editing of recipes needs a newer CrysPy (with recipes as text files).")
            return
        if self.recipe_dialog is None:
            self.recipe_dialog = RecipeEditorDialog(parent=self.main_window)
        else:
            self.recipe_dialog.update_list()
        self.recipe_dialog.show()
        self.recipe_dialog.raise_()

    def show_window(self):
        self.window.show_window()
        self.d_setup["assistant_window_visible"] = True

    def choose_model(self):
        from cryspy_editor.widgets.assistant import flag_llama_cpp
        if not flag_llama_cpp:
            QtWidgets.QMessageBox.information(self.main_window, WINDOW_TITLE, INSTALL_HINT)
            return
        if self.window.is_busy():
            QtWidgets.QMessageBox.information(
                self.main_window, WINDOW_TITLE, "The assistant is busy, try again later.")
            return
        dialog = ModelSettingsDialog(
            model_path=self.d_setup.get("llm_model_path", ""),
            settings=self.d_setup.get("llm_settings", None), parent=self.main_window)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.d_setup["llm_settings"] = dialog.settings()
            self.show_window()
            self.load_model(dialog.model_path())

    def load_model(self, model_path: str):
        self.window.load_model(model_path, self.d_setup.get("llm_settings", None))

    def autoload_model(self):
        """Load the model of the last session, if llama-cpp-python is
        installed; the window is shown if it was open then."""
        from cryspy_editor.widgets.assistant import flag_llama_cpp
        model_path = self.d_setup.get("llm_model_path", "")
        flag_autoload = bool(self.d_setup.get("llm_autoload", False))
        if flag_llama_cpp and flag_autoload and os.path.isfile(model_path):
            if bool(self.d_setup.get("assistant_window_visible", True)):
                self.window.show_window()
            self.load_model(model_path)

    def unload_model(self):
        if self.window.is_busy():
            return
        self.window.unload_model()
        # keep the path and settings for the dialog, but do not load at start
        self.d_setup["llm_autoload"] = False
        self.save_settings()

    def on_model_loaded(self, model_path: str):
        if model_path != "":
            self.d_setup["llm_model_path"] = model_path
        self.d_setup["llm_autoload"] = model_path != ""
        self.save_settings()

    def shutdown(self):
        """Free the model before the program exits."""
        self.window.shutdown()

    def save_window_state(self):
        """Remember for the next session whether the window is open."""
        self.d_setup["assistant_window_visible"] = self.window.isVisible()
