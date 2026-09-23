from __future__ import annotations

import os
import platform
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


PLUGIN_ROOT = "vapoursynth/plugins/vsmlrt"
CUDA_ROOT = f"{PLUGIN_ROOT}/vsmlrt-cuda"

WINDOWS_FILES = {
    "vs-ov": (
        "vsov.dll", "openvino.dll", "openvino_c.dll", "openvino_onnx_frontend.dll",
        "openvino_auto_plugin.dll", "openvino_auto_batch_plugin.dll", "openvino_hetero_plugin.dll",
        "openvino_intel_cpu_plugin.dll", "openvino_intel_gpu_plugin.dll", "openvino_intel_npu_plugin.dll",
        "tbb12.dll", "cache.json",
    ),
    "vs-ncnn": ("vsncnn.dll",),
    "vs-cublas-cu121": ("vsmlrt-cuda/cublas64_12.dll", "vsmlrt-cuda/cublasLt64_12.dll"),
    "vs-cudnn-cu121": (
        "vsmlrt-cuda/cudnn64_8.dll", "vsmlrt-cuda/cudnn_ops_infer64_8.dll",
        "vsmlrt-cuda/cudnn_cnn_infer64_8.dll", "vsmlrt-cuda/cudnn_adv_infer64_8.dll",
    ),
    "vs-tensorrt-core-cu121": tuple(
        f"vsmlrt-cuda/{name}.dll"
        for name in ("nvinfer", "nvinfer_plugin", "nvinfer_lean", "nvinfer_dispatch", "nvinfer_vc_plugin", "nvonnxparser")
    ),
    "vs-tensorrt-builder-cu121": ("vsmlrt-cuda/nvinfer_builder_resource.dll",),
    "vs-trtexec-cu121": ("vsmlrt-cuda/trtexec.exe", "vsmlrt-cuda/trtexec-build.json"),
    "vs-trt-cu121": ("vstrt.dll",),
    "vs-tensorrt-core-cu129": tuple(
        f"vsmlrt-cuda/{name}_11.dll"
        for name in ("nvinfer", "nvinfer_plugin", "nvinfer_lean", "nvinfer_dispatch", "nvinfer_vc_plugin", "nvonnxparser")
    ),
    "vs-tensorrt-builder-cu129-base": tuple(
        f"vsmlrt-cuda/nvinfer_builder_resource_{arch}_11.dll" for arch in ("ptx", "sm75", "sm80", "sm86", "sm89")
    ),
    "vs-tensorrt-builder-cu129-modern": tuple(
        f"vsmlrt-cuda/nvinfer_builder_resource_{arch}_11.dll" for arch in ("sm90", "sm100", "sm120")
    ),
    "vs-trtexec-cu129": ("vsmlrt-cuda/trtexec.exe", "vsmlrt-cuda/trtexec-build.json"),
    "vs-trt-cu129": ("vstrt.dll",),
    "vs-tensorrt-rtx-cu129": (
        "vsmlrt-cuda/tensorrt_rtx_1_5.dll", "vsmlrt-cuda/tensorrt_onnxparser_rtx_1_5.dll",
        "vsmlrt-cuda/tensorrt_rtx.exe",
    ),
    "vs-trt-rtx-cu129": ("vstrt_rtx.dll",),
}

LINUX_FILES = {
    "vs-ov": (
        "vsov.so", "libopenvino.so.2460", "libopenvino_c.so.2460", "libopenvino_onnx_frontend.so.2460",
        "libopenvino_auto_plugin.so", "libopenvino_auto_batch_plugin.so", "libopenvino_hetero_plugin.so",
        "libopenvino_intel_cpu_plugin.so", "libopenvino_intel_gpu_plugin.so", "libopenvino_intel_npu_plugin.so",
        "libtbb.so.12", "libtbbmalloc.so.2", "libtbbmalloc_proxy.so.2", "libtbbbind_2_5.so.3", "libhwloc.so.15",
    ),
    "vs-ncnn": ("vsncnn.so",),
    "vs-cublas-cu121": ("vsmlrt-cuda/libcublas.so.12", "vsmlrt-cuda/libcublasLt.so.12"),
    "vs-cudnn-cu121": (
        "vsmlrt-cuda/libcudnn.so.8", "vsmlrt-cuda/libcudnn_ops_infer.so.8",
        "vsmlrt-cuda/libcudnn_cnn_infer.so.8", "vsmlrt-cuda/libcudnn_adv_infer.so.8",
    ),
    "vs-tensorrt-core-cu121": tuple(
        f"vsmlrt-cuda/{name}.so.8"
        for name in ("libnvinfer", "libnvinfer_plugin", "libnvinfer_lean", "libnvinfer_dispatch", "libnvinfer_vc_plugin", "libnvonnxparser")
    ),
    "vs-tensorrt-builder-cu121": ("vsmlrt-cuda/libnvinfer_builder_resource.so.8.6.1",),
    "vs-trtexec-cu121": ("vsmlrt-cuda/trtexec", "vsmlrt-cuda/trtexec-build.json"),
    "vs-trt-cu121": ("vstrt.so",),
    "vs-tensorrt-core-cu129": tuple(
        f"vsmlrt-cuda/{name}.so.11"
        for name in ("libnvinfer", "libnvinfer_plugin", "libnvinfer_lean", "libnvinfer_dispatch", "libnvinfer_vc_plugin", "libnvonnxparser")
    ),
    "vs-tensorrt-builder-cu129-base": tuple(
        f"vsmlrt-cuda/libnvinfer_builder_resource_{arch}.so.11.1.0" for arch in ("ptx", "sm75", "sm80", "sm86", "sm89")
    ),
    "vs-tensorrt-builder-cu129-modern": tuple(
        f"vsmlrt-cuda/libnvinfer_builder_resource_{arch}.so.11.1.0" for arch in ("sm90", "sm100", "sm120")
    ),
    "vs-trtexec-cu129": ("vsmlrt-cuda/trtexec", "vsmlrt-cuda/trtexec-build.json"),
    "vs-trt-cu129": ("vstrt.so",),
    "vs-tensorrt-rtx-cu129": (
        "vsmlrt-cuda/libtensorrt_rtx.so.1", "vsmlrt-cuda/libtensorrt_onnxparser_rtx.so.1",
        "vsmlrt-cuda/tensorrt_rtx",
    ),
    "vs-trt-rtx-cu129": ("vstrt_rtx.so",),
}


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        del version
        if self.target_name != "wheel":
            return
        component = Path(self.root).name
        system = platform.system()
        files_by_component = WINDOWS_FILES if system == "Windows" else LINUX_FILES if system == "Linux" else None
        if files_by_component is None or platform.machine().lower() not in {"amd64", "x86_64"}:
            raise RuntimeError("vs-mlrt components support only Windows and Linux x86_64")
        if component not in files_by_component:
            raise RuntimeError(f"Unknown vs-mlrt component project: {component}")
        source_value = os.environ.get("VSMLRT_COMPONENT_SOURCE")
        if not source_value:
            raise RuntimeError("VSMLRT_COMPONENT_SOURCE must name the staged vsmlrt directory")
        source_root = Path(source_value).expanduser().resolve()
        if not source_root.is_dir():
            raise RuntimeError(f"VSMLRT_COMPONENT_SOURCE is not a directory: {source_root}")

        force_include = build_data.setdefault("force_include", {})
        for relative in files_by_component[component]:
            source = source_root / relative
            if not source.is_file():
                raise RuntimeError(f"{component} is missing required staged file: {relative}")
            destination = f"{PLUGIN_ROOT}/{relative}"
            force_include[str(source)] = destination
        if system == "Windows":
            build_data["tag"] = "py3-none-win_amd64"
        else:
            baseline = "manylinux_2_27_x86_64" if component in {"vs-ov", "vs-ncnn"} else "manylinux_2_34_x86_64"
            build_data["tag"] = f"py3-none-{baseline}"


def get_build_hook():
    return CustomBuildHook
