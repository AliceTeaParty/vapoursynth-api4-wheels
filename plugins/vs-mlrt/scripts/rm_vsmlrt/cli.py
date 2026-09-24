from __future__ import annotations

import argparse
import ctypes
from importlib import metadata
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


NEW_DISTRIBUTIONS = (
    "vs-mlrt-generic",
    "vs-mlrt-cu121",
    "vs-mlrt-cu129",
    "vs-mlrt-models",
    "vs-ov",
    "vs-ncnn",
    "vs-cublas-cu121",
    "vs-cudnn-cu121",
    "vs-tensorrt-core-cu121",
    "vs-tensorrt-builder-cu121",
    "vs-trtexec-cu121",
    "vs-trt-cu121",
    "vs-tensorrt-core-cu129",
    "vs-tensorrt-builder-cu129-base",
    "vs-tensorrt-builder-cu129-modern",
    "vs-trtexec-cu129",
    "vs-trt-cu129",
    "vs-tensorrt-rtx-cu129",
    "vs-trt-rtx-cu129",
)
LEGACY_DISTRIBUTIONS = (
    "vs-mlrt",
    "vs-mlrt-payload-generic",
    "vs-mlrt-payload-cu121",
    "vs-mlrt-payload-cu129",
    "vs-mlrt-cu129-payload-2",
    "vs-mlrt-cu129-payload-3",
)
KNOWN_DISTRIBUTIONS = (*NEW_DISTRIBUTIONS, *LEGACY_DISTRIBUTIONS)
ENTRY_DISTRIBUTIONS = ("vs-mlrt-generic", "vs-mlrt-cu121", "vs-mlrt-cu129")
LEGACY_FILES = ("vsmlrt.py", "vsmlrt_dll_paths.py", "vs_mlrt_dll_paths.pth")


def normalize_distribution(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def installed_distributions() -> dict[str, str]:
    installed: dict[str, str] = {}
    for distribution in metadata.distributions():
        name = distribution.metadata.get("Name")
        if name:
            installed[normalize_distribution(name)] = name
    return installed


def selected_distributions() -> list[str]:
    installed = installed_distributions()
    return [installed[name] for value in KNOWN_DISTRIBUTIONS if (name := normalize_distribution(value)) in installed]


def site_packages_root() -> Path:
    import vapoursynth

    package = Path(vapoursynth.__file__).resolve().parent
    if package.name != "vapoursynth":
        raise RuntimeError(f"Unexpected VapourSynth package location: {package}")
    return package.parent


def cleanup_targets(site_root: Path) -> list[Path]:
    plugin_root = site_root / "vapoursynth" / "plugins" / "vsmlrt"
    targets = [plugin_root, *(site_root / name for name in LEGACY_FILES)]
    cache = site_root / "__pycache__"
    if cache.is_dir():
        for stem in ("vsmlrt", "vsmlrt_dll_paths"):
            targets.extend(sorted(cache.glob(f"{stem}.*.pyc")))
    return targets


def ensure_safe_target(site_root: Path, target: Path) -> None:
    root = site_root.resolve()
    resolved = target.resolve(strict=False)
    if resolved == root or not resolved.is_relative_to(root):
        raise RuntimeError(f"Refusing cleanup target outside site-packages: {target} -> {resolved}")


def remove_target(site_root: Path, target: Path, *, dry_run: bool, verbose: bool) -> None:
    ensure_safe_target(site_root, target)
    if not target.exists() and not target.is_symlink():
        return
    if verbose or dry_run:
        print(f"rm_vsmlrt: remove {target}")
    if dry_run:
        return
    if target.is_dir() and not target.is_symlink():
        shutil.rmtree(target)
    else:
        target.unlink()


def uninstall(distributions: list[str], *, dry_run: bool, verbose: bool) -> int:
    if not distributions:
        return 0
    command = [sys.executable, "-m", "pip", "uninstall", "-y", *distributions]
    if verbose or dry_run:
        print("rm_vsmlrt:", subprocess.list2cmdline(command))
    if dry_run:
        return 0
    return subprocess.run(command, check=False).returncode


def wait_for_parent(pid: int) -> None:
    if pid <= 0:
        return
    if os.name == "nt":
        synchronize = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, pid)
        if handle:
            try:
                ctypes.windll.kernel32.WaitForSingleObject(handle, 30000)
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        return
    for _ in range(300):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Completely uninstall every vs-mlrt component and payload.")
    parser.add_argument("--dry-run", action="store_true", help="show actions without changing the environment")
    parser.add_argument("--yes", action="store_true", help="do not ask for interactive confirmation")
    parser.add_argument("--verbose", action="store_true", help="show resolved distributions and paths")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--parent-pid", type=int, default=0, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def print_removal_summary(distributions: list[str], targets: list[Path]) -> None:
    print("rm_vsmlrt: installed distributions:", ", ".join(distributions) or "none")
    print(f"rm_vsmlrt: shared payload: {targets[0]}")


def confirm_removal(distributions: list[str], targets: list[Path]) -> bool:
    del distributions, targets
    answer = input("Remove all listed vs-mlrt distributions, plugins, models, and generated engines? [y/N] ")
    return answer.strip().lower() in {"y", "yes"}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    wait_for_parent(args.parent_pid)
    site_root = site_packages_root()
    distributions = selected_distributions()
    targets = cleanup_targets(site_root)
    defer_entry_cleanup = (
        not args.worker
        and not args.dry_run
        and os.name == "nt"
        and os.environ.get("RM_VSMLRT_DEFER_ENTRY_CLEANUP") == "1"
    )

    print_removal_summary(distributions, targets)
    if not args.yes and not args.dry_run:
        if not confirm_removal(distributions, targets):
            print("rm_vsmlrt: cancelled")
            return 2

    foreground_distributions = distributions
    if defer_entry_cleanup:
        entry_names = {normalize_distribution(name) for name in ENTRY_DISTRIBUTIONS}
        foreground_distributions = [
            name for name in distributions if normalize_distribution(name) not in entry_names
        ]
    pip_status = uninstall(foreground_distributions, dry_run=args.dry_run, verbose=args.verbose)
    cleanup_status = 0
    for target in targets:
        try:
            remove_target(site_root, target, dry_run=args.dry_run, verbose=args.verbose)
        except OSError as error:
            cleanup_status = 1
            print(f"rm_vsmlrt: failed to remove {target}: {error}", file=sys.stderr)

    if args.dry_run:
        return 0
    if defer_entry_cleanup:
        command = [
            sys.executable,
            "-m",
            "rm_vsmlrt",
            "--worker",
            "--parent-pid",
            str(os.getpid()),
            "--yes",
        ]
        subprocess.Popen(
            command,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return 1 if pip_status or cleanup_status else 0
    remaining = selected_distributions()
    remaining_paths = [str(path) for path in targets if path.exists() or path.is_symlink()]
    if remaining:
        print(f"rm_vsmlrt: distributions remain installed: {', '.join(remaining)}", file=sys.stderr)
    if remaining_paths:
        print(f"rm_vsmlrt: paths remain: {', '.join(remaining_paths)}", file=sys.stderr)
    return 1 if pip_status or cleanup_status or remaining or remaining_paths else 0
