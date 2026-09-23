"""Build a small TensorRT engine through the public vsmlrt wrapper."""
from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

import vsmlrt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--network",
        type=Path,
        default=Path(vsmlrt.models_path) / "dpir" / "drunet_gray.onnx",
    )
    parser.add_argument("--shape", type=int, default=16)
    parser.add_argument("--channels", type=int, default=2)
    args = parser.parse_args()

    trtexec = Path(vsmlrt.trtexec_path).resolve()
    if not trtexec.is_file():
        raise SystemExit(f"Packaged trtexec does not exist: {trtexec}")
    if not args.network.is_file():
        raise SystemExit(f"Network does not exist: {args.network}")

    with tempfile.TemporaryDirectory(prefix="vsmlrt-trtexec-") as directory:
        engine = Path(
            vsmlrt.trtexec(
                network_path=str(args.network),
                channels=args.channels,
                opt_shapes=(args.shape, args.shape),
                max_shapes=(args.shape, args.shape),
                fp16=False,
                device_id=0,
                use_cuda_graph=False,
                engine_folder=directory,
            )
        )
        if not engine.is_file() or engine.stat().st_size < 1024:
            raise SystemExit(f"TensorRT did not create a usable engine: {engine}")
        print(f"Built TensorRT engine with {trtexec}: {engine.stat().st_size} bytes")


if __name__ == "__main__":
    main()
