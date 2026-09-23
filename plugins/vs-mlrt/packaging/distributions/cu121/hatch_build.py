import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from entry_hook import EntryBuildHook as CustomBuildHook


def get_build_hook():
    return CustomBuildHook
