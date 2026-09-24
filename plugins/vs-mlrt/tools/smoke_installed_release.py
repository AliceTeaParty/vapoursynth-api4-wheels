"""Black-box local smoke tests for one installed vs-mlrt entry release."""
from __future__ import annotations

import importlib.metadata
import os
import platform
import sys
import tempfile
from pathlib import Path


ENTRY_DISTRIBUTIONS = ("vs-mlrt-generic", "vs-mlrt-cu121", "vs-mlrt-cu129")


def fail(message: str) -> "None":
    raise SystemExit(f"SMOKE TEST FAILED: {message}")


def installed_entries() -> list[str]:
    entries: list[str] = []
    for name in ENTRY_DISTRIBUTIONS:
        try:
            importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
        entries.append(name)
    return entries


def require_distribution(variant: str) -> None:
    expected = f"vs-mlrt-{variant}"
    entries = installed_entries()
    if entries != [expected]:
        fail(
            f"expected exactly {expected!r}, found {entries or 'no vs-mlrt entry package'}. "
            "Run `python -m rm_vsmlrt_helper` and execute its printed command before installing another variant."
        )
    print(f"entry package: {expected} {importlib.metadata.version(expected)}")


def plugin_directory() -> Path:
    try:
        import vsmlrt_dll_paths  # noqa: F401 - configures DLL search paths on Windows.
        import vsmlrt
    except Exception as exc:
        fail(f"could not import the installed wrapper: {exc}")

    root = Path(vsmlrt.models_path).resolve().parent
    if not root.is_dir():
        fail(f"installed plugin directory does not exist: {root}")
    print(f"vsmlrt: {Path(vsmlrt.__file__).resolve()}")
    print(f"plugin directory: {root}")
    return root


def plugin_suffix() -> str:
    suffixes = {"Windows": ".dll", "Linux": ".so"}
    try:
        return suffixes[platform.system()]
    except KeyError:
        fail(f"unsupported platform: {platform.system()}")


def load_plugin(core: object, path: Path) -> None:
    if not path.is_file():
        fail(f"missing packaged plugin: {path}")
    try:
        core.std.LoadPlugin(path=str(path))
    except Exception as exc:
        if "already loaded" not in str(exc).lower():
            fail(f"could not load {path.name}: {exc}")


def load_common_plugins(plugin_dir: Path) -> object:
    import vapoursynth as vs

    core = vs.core
    suffix = plugin_suffix()
    for name in ("vsncnn", "vsov"):
        load_plugin(core, plugin_dir / f"{name}{suffix}")
    try:
        print(f"NCNN: {core.ncnn.Version()}")
        print(f"OpenVINO: {core.ov.Version()}")
    except Exception as exc:
        fail(f"common plugin version query failed: {exc}")
    return core


def render_dpir(backend: object, label: str) -> None:
    import vapoursynth as vs
    import vsmlrt

    clip = vs.core.std.BlankClip(width=32, height=32, format=vs.GRAYS, length=1)
    try:
        output = vsmlrt.DPIR(
            clip,
            strength=5.0,
            tilesize=(32, 32),
            overlap=8,
            backend=backend,
        )
        frame = output.get_frame(0)
    except Exception as exc:
        fail(f"{label} DPIR render failed: {exc}")
    if frame.width != 32 or frame.height != 32:
        fail(f"{label} DPIR returned {frame.width}x{frame.height}, expected 32x32")
    print(f"{label}: rendered one 32x32 DPIR frame")


def smoke_generic(plugin_dir: Path) -> None:
    load_common_plugins(plugin_dir)
    import vsmlrt

    render_dpir(vsmlrt.Backend.OV_CPU(num_streams=1, num_threads=1), "OpenVINO CPU")


def smoke_cuda(plugin_dir: Path, variant: str) -> None:
    import vapoursynth as vs
    import vsmlrt

    core = vs.core
    suffix = plugin_suffix()
    load_plugin(core, plugin_dir / f"vstrt{suffix}")
    try:
        print(f"TensorRT: {core.trt.Version()}")
    except Exception as exc:
        fail(f"TensorRT version query failed: {exc}")

    with tempfile.TemporaryDirectory(prefix=f"vsmlrt-{variant}-smoke-") as engine_folder:
        backend = vsmlrt.Backend.TRT(
            fp16=False,
            use_cuda_graph=False,
            static_shape=True,
            device_id=0,
            engine_folder=str(Path(engine_folder) / "trt"),
        )
        render_dpir(backend, "TensorRT")

        if variant == "cu129":
            load_plugin(core, plugin_dir / f"vstrt_rtx{suffix}")
            try:
                print(f"TensorRT-RTX: {core.trt_rtx.Version()}")
            except Exception as exc:
                fail(f"TensorRT-RTX version query failed: {exc}")
            render_dpir(
                vsmlrt.Backend.TRT_RTX(
                    fp16=False,
                    use_cuda_graph=False,
                    static_shape=True,
                    device_id=0,
                    engine_folder=str(Path(engine_folder) / "trt-rtx"),
                ),
                "TensorRT-RTX",
            )


def main(variant: str) -> None:
    if variant not in {"generic", "cu121", "cu129"}:
        raise ValueError(f"unknown variant: {variant}")
    if sys.version_info < (3, 12):
        fail(f"Python 3.12+ is required; running {sys.version.split()[0]}")
    require_distribution(variant)
    plugin_dir = plugin_directory()
    smoke_generic(plugin_dir)
    if variant != "generic":
        smoke_cuda(plugin_dir, variant)
    print(f"SMOKE TEST PASSED: vs-mlrt-{variant}")


if __name__ == "__main__":
    variant = os.environ.get("VSMLRT_SMOKE_VARIANT")
    if variant is None:
        fail("run one of smoke_vsmlrt_generic.py, smoke_vsmlrt_cu121.py, or smoke_vsmlrt_cu129.py")
    main(variant)
