#!/bin/sh
set -eu

wrapper=/workspace/packaging/vapoursynth-krigbilateralvk
assets=/workspace/.work/krig-gpu-assets
mkdir -p /results /tmp/krig-xdg
chmod 700 /tmp/krig-xdg
export XDG_RUNTIME_DIR=/tmp/krig-xdg

VK_DRIVER_FILES=$(python - <<'PY'
from pathlib import Path
import ctypes
import json

errors = []
for folder in ('/etc/vulkan/icd.d', '/usr/share/vulkan/icd.d'):
    for path in sorted(Path(folder).glob('*nvidia*.json')):
        try:
            library = json.loads(path.read_text())['ICD']['library_path']
            if not Path(library).is_absolute() and '/' in library:
                library = str(path.parent / library)
            driver = ctypes.CDLL(library)
            getattr(driver, 'vk_icdGetInstanceProcAddr')
        except Exception as error:
            errors.append(f'{path}: {error}')
            continue
        print(path)
        raise SystemExit(0)
raise SystemExit('No loadable NVIDIA Vulkan ICD was injected. ' + '; '.join(errors))
PY
)
export VK_DRIVER_FILES
printf '%s\n' "$VK_DRIVER_FILES" > /results/selected-icd.txt
vulkaninfo --summary > /results/vulkaninfo.txt 2>&1
python -m pip install --no-deps "$assets"/*manylinux*.whl
python "$wrapper/tools/smoke_installed.py" --exercise --require-hardware --output /results/linux-hardware-wheel.json
python -m pip uninstall -y vapoursynth-krigbilateralvk
export KRIGVK_PREBUILT_URL="$assets/krigbilateralvk-linux-x86_64.zip"
cp -a "$wrapper" /work/package
python -m pip install --no-deps --no-build-isolation /work/package
python "$wrapper/tools/smoke_installed.py" --exercise --require-hardware --output /results/linux-hardware-loopback.json
python - <<'PY'
from pathlib import Path
import json
first = json.loads(Path('/results/linux-hardware-wheel.json').read_text())
second = json.loads(Path('/results/linux-hardware-loopback.json').read_text())
assert first['native_sha256'] == second['native_sha256']
assert first['upstream_commit'] == second['upstream_commit']
assert first['selected_device'] == second['selected_device']
PY
