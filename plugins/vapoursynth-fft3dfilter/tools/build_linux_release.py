from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "fft3dfilter"


def run(cmd: list[str], env: dict[str, str]) -> None:
    print("+ " + subprocess.list2cmdline(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def vapoursynth_package(root: Path) -> Path:
    for candidate in (root / "vapoursynth", root):
        if (candidate / "include" / "VapourSynth4.h").exists() and (candidate / "pkgconfig" / "vapoursynth.pc").exists():
            return candidate
    raise FileNotFoundError(root / "vapoursynth" / "include" / "VapourSynth4.h")


def native_module(build_dir: Path) -> Path:
    for candidate in [build_dir / "libfft3dfilter.so", build_dir / "fft3dfilter.so", *build_dir.rglob("*fft3dfilter*.so")]:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(build_dir / "libfft3dfilter.so")


def ensure_ninja_on_path(env: dict[str, str]) -> None:
    if shutil.which("ninja", path=env.get("PATH")):
        return
    try:
        import ninja
    except ImportError as exc:
        raise RuntimeError("ninja is not installed") from exc
    ninja_dir = Path(ninja.BIN_DIR)
    if not (ninja_dir / "ninja").exists():
        raise RuntimeError("the installed ninja package does not provide a ninja executable")
    env["PATH"] = os.pathsep.join([str(ninja_dir), env.get("PATH", "")])


def write_fftw_pc(prefix: Path, pc_dir: Path) -> Path:
    pc_dir.mkdir(parents=True, exist_ok=True)
    pc = pc_dir / "fftw3f.pc"
    pc.write_text(
        "\n".join(
            [
                f"prefix={prefix.resolve().as_posix()}",
                "libdir=${prefix}/lib",
                "includedir=${prefix}/include",
                "",
                "Name: fftw3f",
                "Description: statically linked single-precision FFTW3 with threads",
                "Version: 3.3.10",
                "Libs: -L${libdir} -lfftw3f_threads -lfftw3f -lm -pthread",
                "Cflags: -I${includedir}",
                "",
            ]
        ),
        encoding="ascii",
        newline="\n",
    )
    return pc


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build the portable Linux FFT3DFilter plugin package.")
    parser.add_argument("--vapoursynth-root", required=True, help="Extracted VapourSynth wheel root.")
    parser.add_argument("--output-dir", default=str(ROOT / "dist" / "linux-x86_64"))
    parser.add_argument("--build-dir", default=str(ROOT / "build-linux-release"))
    parser.add_argument("--fftw-prefix", help="Static FFTW prefix; creates a matching pkg-config file.")
    parser.add_argument("--static-runtime", action="store_true")
    args = parser.parse_args(argv)

    vs_pkg = vapoursynth_package(Path(args.vapoursynth_root).resolve())
    output_dir = Path(args.output_dir).resolve()
    build_dir = Path(args.build_dir).resolve()
    package_dir = output_dir / PLUGIN_NAME
    shutil.rmtree(build_dir, ignore_errors=True)
    shutil.rmtree(output_dir, ignore_errors=True)

    env = os.environ.copy()
    pc_entries = [vs_pkg / "pkgconfig"]
    if args.fftw_prefix:
        pc_entries.append(write_fftw_pc(Path(args.fftw_prefix).resolve(), build_dir / "pkgconfig"))
        pc_entries[-1] = pc_entries[-1].parent
    existing = env.get("PKG_CONFIG_PATH")
    env["PKG_CONFIG_PATH"] = os.pathsep.join([*(str(path) for path in pc_entries), *([existing] if existing else [])])
    print(f"PKG_CONFIG_PATH={env['PKG_CONFIG_PATH']}")
    ensure_ninja_on_path(env)

    meson = shutil.which("meson", path=env.get("PATH"))
    meson_command = [meson] if meson else [sys.executable, "-m", "mesonbuild.mesonmain"]
    try:
        __import__("mesonbuild.mesonmain")
    except ImportError:
        if not meson:
            raise RuntimeError("meson is not installed") from None
    setup = [*meson_command, "setup", str(build_dir), str(ROOT), "--buildtype", "release"]
    if args.static_runtime:
        setup.append("-Dstatic-runtime=true")
    run(setup, env)
    run([*meson_command, "compile", "-C", str(build_dir)], env)

    package_dir.mkdir(parents=True, exist_ok=True)
    module = native_module(build_dir)
    shutil.copy2(module, package_dir / "fft3dfilter.so")
    (package_dir / "manifest.vs").write_text(
        "[VapourSynth Manifest V1]\nfft3dfilter\n", encoding="ascii", newline="\n"
    )
    print(
        json.dumps(
            {
                "package_dir": str(package_dir),
                "plugin": str(package_dir / "fft3dfilter.so"),
                "vapoursynth_pkgconfig": str(vs_pkg / "pkgconfig"),
                "fftw": "static" if args.fftw_prefix else "system",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
