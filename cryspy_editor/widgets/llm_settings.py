"""Dialog with settings of the local model and a hint which model to take."""
import html
import os

from PyQt5 import QtWidgets

from cryspy_editor.widgets.llm_local import (
    DEFAULT_SETTINGS,
    L_RECOMMENDED_MODELS,
    get_total_memory_gb,
    take_recommended_index,
    take_settings,
)


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
<p>Any <i>instruct</i> (chat) model in GGUF format works. Take the Q4_K_M
quantization: the model file should take no more than half of the memory.
{s_memory}</p>
<table border="1" cellpadding="3" cellspacing="0">
<tr><th>Memory</th><th>Model</th><th>Q4_K_M file</th></tr>
{''.join(ls_rows)}
</table>
<p>Download the file once from huggingface.co (search for the model name
with "GGUF", e.g. bartowski/Meta-Llama-3.1-8B-Instruct-GGUF) and save it in
any folder. After that no internet connection is needed: the model runs on
this computer.</p>
<p><b>Threads</b>: 0 uses all cores but one. <b>GPU layers</b>: -1 puts the
whole model on the GPU (Metal on Apple Silicon), 0 runs on CPU only.
<b>Context</b>: the length of the conversation the model sees, in tokens;
larger needs more memory.</p>"""


class LLMSettingsDialog(QtWidgets.QDialog):
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
