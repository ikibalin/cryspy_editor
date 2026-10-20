# cryspy_editor
 Editor for CrysPy library

## AI assistant (optional)

CrysPy Editor can use a local language model to answer questions and run
simple actions on the opened file (refine, calculate, fix all parameters,
show refined parameters, show the model). The model runs on your computer;
nothing is sent to the internet.

1. Install the optional dependency: `pip install cryspy_editor[ai]`
   (or `pip install llama-cpp-python`).
2. Download any chat model in GGUF format, for example
   Llama-3-8B-Instruct Q4_K_M (about 5 GB).
3. In CrysPy Editor choose **AI assistant → Load local model (*.gguf)...**.
   The model is loaded in the background and is loaded again at the next start.
