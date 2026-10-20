# cryspy_editor
 Editor for CrysPy library

## Start

```
cryspy-editor                  # opens the last used file
cryspy-editor path/file.rcif   # opens the given file
python -m cryspy_editor path/file.rcif
```

Other programs (for example PyColl5) can open a file in CrysPy Editor the
same way. Recent files are in **File → Open recent**.

Settings are kept in `settings.json` in the user's folder:
`%APPDATA%\CrysPyEditor` on Windows, `~/Library/Application Support/CrysPyEditor`
on macOS, `~/.config/cryspy_editor` on Linux. Settings of older versions are
moved there at the first start.

## AI assistant (optional)

CrysPy Editor can use a local language model to answer questions and work
on the opened file. The model runs on your computer; nothing is sent to the
internet. It calls the tools of CrysPy (`cryspy.assistant_tools()`): help
lookup, list / refine / fix / set parameters by their paths, calculate,
refine, show the model, add an atom, run CrysPy procedures. Questions such as
"how to describe multipoles?" or "what should be used for thermal
vibrations?" are answered from the help pages of CrysPy, which are shown in
the answer. The same help is in **Options → CrysPy help...** (F1) without a
model. The tools and the help need a CrysPy version that has
`cryspy.call_assistant_tool`.

1. Install the optional dependency: `pip install cryspy_editor[ai]`
   (or `pip install llama-cpp-python`).
2. Download once any instruct (chat) model in GGUF format, Q4_K_M
   quantization. The file should take no more than half of the memory:

   | Memory | Model | Q4_K_M file |
   | --- | --- | --- |
   | < 8 GB | Qwen2.5-1.5B-Instruct | 1 GB |
   | 8 GB | Qwen2.5-3B-Instruct, Llama-3.2-3B-Instruct | 2 GB |
   | 16 GB | Llama-3.1-8B-Instruct, Qwen2.5-7B-Instruct | 5 GB |
   | 32 GB and more | Qwen2.5-14B-Instruct | 9 GB |

3. In CrysPy Editor choose **AI assistant → Load local model (*.gguf)...**,
   pick the file and, if needed, the threads, GPU layers, context size,
   answer length and temperature. The same table is shown there, with the row
   for your computer in bold. The model is loaded in the background and is
   loaded again at the next start, until **Unload model**.

## Development

- `main` holds releases, `develop` is the integration branch. Branch off
  `develop` and open pull requests into `develop`.
- Every pull request needs one label: `[scope] bug`, `[scope] enhancement`,
  `[scope] documentation`, `[scope] maintenance` or `[scope] significant`.
  The label decides the next version in the release draft.
- The version comes from git tags (plain, e.g. `1.9.10`) via versioningit.
- Tests: `pip install -e .[dev]`, then `python -m pytest`. Qt runs without a
  display in tests (`QT_QPA_PLATFORM=offscreen`).
