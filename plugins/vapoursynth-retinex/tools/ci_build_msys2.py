from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEPS = ROOT / "_deps"
DEFAULT_BUILD = ROOT / "build-ci-msys2"
DEFAULT_DIST = ROOT / "dist" / "msys2-ucrt64"
PLUGIN_NAME = "retinex"

SYSTEM_DLLS = {
    "advapi32.dll",
    "cfgmgr32.dll",
    "comdlg32.dll",
    "gdi32.dll",
    "kernel32.dll",
    "oleaut32.dll",
    "shell32.dll",
    "user32.dll",
    "version.dll",
    "winspool.drv",
    "ws2_32.dll",
    "bcrypt.dll",
    "msvcrt.dll",
    "ntdll.dll",
    "ole32.dll",
}


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+ " + subprocess.list2cmdline(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def find_tool(name: str, env: dict[str, str] | None = None) -> str:
    found = shutil.which(name, path=env.get("PATH") if env else None)
    if found:
        return found
    python_scripts = Path(sys.executable).resolve().parent / "Scripts" / f"{name}.exe"
    if python_scripts.exists():
        return str(python_scripts)
    raise RuntimeError(f"{name} is not on PATH")


def prepend_path_entries(env: dict[str, str], entries: list[Path]) -> None:
    parts = [str(entry) for entry in entries if entry.exists()]
    if not parts:
        return
    existing = env.get("PATH")
    env["PATH"] = os.pathsep.join(parts + ([existing] if existing else []))


def candidate_msys2_prefixes(env: dict[str, str]) -> list[Path]:
    prefixes: list[Path] = []
    msystem_prefix = env.get("MSYSTEM_PREFIX")
    if msystem_prefix:
        prefixes.append(Path(msystem_prefix))
    prefixes.extend(
        [
            ROOT.parents[2] / "msys2" / "ucrt64",
            Path(r"C:\msys64\ucrt64"),
            Path(r"C:\msys64\mingw64"),
        ]
    )
    seen: set[str] = set()
    unique: list[Path] = []
    for prefix in prefixes:
        key = str(prefix).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(prefix)
    return unique


def path_for_meson(path: Path) -> str:
    return path.resolve().as_posix()


def dll_dependencies(objdump: str, dll: Path) -> list[str]:
    completed = subprocess.run(
        [objdump, "-p", str(dll)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    deps = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if line.startswith("DLL Name: "):
            deps.append(line.removeprefix("DLL Name: "))
    return deps


def collect_runtime_dlls(pkg_dir: Path, search_dirs: list[Path], env: dict[str, str]) -> None:
    objdump = find_tool("objdump", env)
    queue = sorted(pkg_dir.glob("*.dll"))
    seen: set[str] = set()
    while queue:
        dll = queue.pop(0)
        key = dll.name.lower()
        if key in seen:
            continue
        seen.add(key)
        for dep in dll_dependencies(objdump, dll):
            dep_key = dep.lower()
            if dep_key in SYSTEM_DLLS or dep_key.startswith("api-ms-win-"):
                continue
            dst = pkg_dir / dep
            if dst.exists():
                if dep_key not in seen:
                    queue.append(dst)
                continue
            for search_dir in search_dirs:
                src = search_dir / dep
                if src.exists():
                    shutil.copy2(src, dst)
                    queue.append(dst)
                    break


def configure_env(vs_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    msys2_prefixes = candidate_msys2_prefixes(env)
    prepend_path_entries(
        env,
        [
            *(prefix / "bin" for prefix in msys2_prefixes),
            *(prefix.parent / "usr" / "bin" for prefix in msys2_prefixes),
        ],
    )
    pc_paths = [str((vs_root / "vapoursynth" / "lib" / "pkgconfig").resolve())]
    existing_pc = env.get("PKG_CONFIG_PATH")
    if existing_pc:
        pc_paths.append(existing_pc)
    env["PKG_CONFIG_PATH"] = os.pathsep.join(pc_paths)
    if "PKG_CONFIG" not in env:
        for prefix in msys2_prefixes:
            for candidate in (
                prefix.parent / "usr" / "bin" / "pkg-config.exe",
                prefix.parent / "usr" / "bin" / "pkgconf.exe",
                prefix / "bin" / "pkg-config.exe",
                prefix / "bin" / "pkgconf.exe",
            ):
                if candidate.exists():
                    env["PKG_CONFIG"] = str(candidate)
                    break
            if "PKG_CONFIG" in env:
                break
    if "CC" not in env or "CXX" not in env:
        for prefix in msys2_prefixes:
            gcc = prefix / "bin" / "gcc.exe"
            gxx = prefix / "bin" / "g++.exe"
            if gcc.exists() and "CC" not in env:
                env["CC"] = str(gcc)
            if gxx.exists() and "CXX" not in env:
                env["CXX"] = str(gxx)
            if "CC" in env and "CXX" in env:
                break
    return env


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build and package Retinex with MSYS2 UCRT64.")
    parser.add_argument("--deps-dir", default=str(DEFAULT_DEPS))
    parser.add_argument("--build-dir", default=str(DEFAULT_BUILD))
    parser.add_argument("--dist-dir", default=str(DEFAULT_DIST))
    parser.add_argument("--vapoursynth-wheel-root")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args(argv)

    deps = Path(args.deps_dir).resolve()
    build_dir = Path(args.build_dir).resolve()
    dist_dir = Path(args.dist_dir).resolve()
    pkg_dir = dist_dir / PLUGIN_NAME
    vs_root = Path(args.vapoursynth_wheel_root).resolve() if args.vapoursynth_wheel_root else deps / "vapoursynth-wheel-R77"
    vs_pkg = vs_root / "vapoursynth"
    for path in [
        vs_pkg / "include" / "vapoursynth" / "VapourSynth4.h",
        vs_pkg / "include" / "vapoursynth" / "VSHelper4.h",
        vs_pkg / "lib" / "pkgconfig" / "vapoursynth.pc",
    ]:
        if not path.exists():
            raise FileNotFoundError(path)

    if args.clean and build_dir.exists():
        shutil.rmtree(build_dir)
    if args.clean and dist_dir.exists():
        shutil.rmtree(dist_dir)

    env = configure_env(vs_root)
    meson = find_tool("meson", env)
    ninja = find_tool("ninja", env)

    setup_cmd = [
        meson,
        "setup",
        str(build_dir),
        str(ROOT),
        "--backend",
        "ninja",
        "--buildtype",
        "release",
    ]
    if build_dir.exists():
        setup_cmd.insert(2, "--reconfigure")
    run(setup_cmd, cwd=ROOT, env=env)
    run([ninja, "-C", str(build_dir), "-v"], cwd=ROOT, env=env)

    pkg_dir.mkdir(parents=True, exist_ok=True)
    dll = build_dir / "libretinex.dll"
    if not dll.exists():
        dll = build_dir / "retinex.dll"
    if not dll.exists():
        raise FileNotFoundError(dll)
    shutil.copy2(dll, pkg_dir / "retinex.dll")
    (pkg_dir / "manifest.vs").write_text("[VapourSynth Manifest V1]\nretinex\n", encoding="ascii", newline="\n")

    search_dirs = [Path(p) for p in env.get("PATH", "").split(os.pathsep) if p]
    collect_runtime_dlls(pkg_dir, search_dirs, env)

    print(f"artifact_dir={dist_dir}")
    for path in sorted(pkg_dir.iterdir()):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
