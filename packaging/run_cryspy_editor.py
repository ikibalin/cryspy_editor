"""Entry point of the standalone CrysPy Editor built by PyInstaller."""
import multiprocessing

from cryspy_editor.__main__ import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
