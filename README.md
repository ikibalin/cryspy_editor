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
model.

The assistant works in its own window, **AI Assistant / CrysPy Editor**,
opened by **AI assistant → Show assistant**. One request may hold several
actions (e.g. "fix everything, refine the cell and run the refinement"); a
call with wrong arguments goes back to the model to be corrected, and
questions are answered from the results of the actions. The window and the
logic are the same as in the assistant of PyColl5; only the actions differ.

1. Install the optional dependency: `pip install cryspy_editor[ai]`
   (or `pip install llama-cpp-python`).
2. Download once any instruct (chat) model in GGUF format, Q4_K_M
   quantization. The file should take no more than half of the memory:

   | Memory | Model | Q4_K_M file |
   | --- | --- | --- |
   | < 8 GB | Qwen2.5-3B-Instruct (single requests only: too weak for recipes) | 2 GB |
   | 8 GB | Qwen2.5-7B-Instruct | 4.7 GB |
   | 16 GB and more | Qwen2.5-14B-Instruct | 9 GB |

   Recommended: Qwen2.5-7B-Instruct Q4_K_M; with 16 GB of memory or more
   Qwen2.5-14B-Instruct Q4_K_M, which follows the step-by-step recipes much
   more reliably. Take a general *Instruct* model, not a *Coder* one, and the
   Q4_K_M quantization (more accurate than Q4_0 at the same size). For the
   step-by-step work by recipes set the context to 8192 or more.

3. In CrysPy Editor choose **AI assistant → Load local model (*.gguf)...**,
   pick the file and, if needed, the threads, GPU layers, context size,
   answer length and temperature. The same table is shown there, with the row
   for your computer in bold. The model is loaded in the background and is
   loaded again at the next start, until **Unload model**; the window opens
   again at the next start if it was open when the program was closed.

**Recipes.** A task of several steps (e.g. "refine the structure step by
step", "refine the flip ratios") is done by a recipe of CrysPy: the model
reads its steps and works one action at a time, judging each result by
chi_sq/n, R_F2 and the warnings of CrysPy. Each step is written in the chat
as it starts and when its result comes; **Stop** ends the work, and at most
"Maximal number of steps of the agent" actions (12 by default, in the model
settings) are done for one request. The recipes
for the experiments of the opened file (single crystal, powder, flip ratios,
nuclear or magnetic crystal) are given to the model. **AI assistant →
Recipes...** lists the recipes, shows their text and lets you write new ones
or change those of CrysPy (New, Check, Save, Delete); your recipes are kept in
the `recipes` folder next to the settings and replace the recipes of CrysPy
with the same name.

**Commands.** Type `@` in the input line to see the names of the recipes and
of the actions with a short description, and run one directly, without the
model choosing it: `@refine_flip_ratio_nuclear`, `@refine_parameters scale`,
`@set_parameter path=cell.length_a value=5.43` or with a JSON object of the
arguments. Without a loaded model a recipe is done as it is written, step by
step. "What can you do?" (or `help`, `?`) lists the recipes and the actions.

## Development

- `main` holds releases, `develop` is the integration branch. Branch off
  `develop` and open pull requests into `develop`.
- Every pull request needs one label: `[scope] bug`, `[scope] enhancement`,
  `[scope] documentation`, `[scope] maintenance` or `[scope] significant`.
  The label decides the next version in the release draft.
- The version comes from git tags (plain, e.g. `1.9.10`) via versioningit.
- Tests: `pip install -e .[dev]`, then `python -m pytest`. Qt runs without a
  display in tests (`QT_QPA_PLATFORM=offscreen`).
