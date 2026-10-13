"""Check installed-path autoloading and exercise the packaged Vulkan plugin."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

import vapoursynth as vs
from hardware_device import select_hardware_device


def exercise(core):
    import numpy as np
    rows = []
    core.num_threads = 4
    for format_id in (vs.GRAY16, vs.GRAYS, vs.YUV420P16, vs.YUV444PS, vs.RGBS):
        blank = core.std.BlankClip(width=32, height=24, format=format_id, length=5)

        def fill(n, f):
            output = f.copy()
            for plane in range(output.format.num_planes):
                array = np.asarray(output[plane])
                y, x = np.mgrid[:array.shape[0], :array.shape[1]]
                values = 0.3 + 0.1 * np.sin((x + n + plane) / 3) + 0.08 * np.cos((y - n) / 4)
                if output.format.sample_type == vs.INTEGER:
                    values = np.floor(values * ((1 << output.format.bits_per_sample) - 1) + 0.5)
                elif output.format.color_family == vs.YUV and plane:
                    values -= 0.5
                array[:] = values.astype(array.dtype)
            output.props['WheelFixture'] = n
            return output

        source = core.std.ModifyFrame(blank, blank, selector=fill)
        for cache in (0, 1):
            options = dict(sigma=8, tbsize=3, planes=[0], cache=cache, cache_frames=1)
            normal = core.dfttestvk.DFTTest(source, **options)
            resident = core.dfttestvk.DFTTestGPU(core.std.GPUUpload(source), **options)
            downloaded = core.std.GPUDownload(resident)
            assert resident.gpu_resident and not normal.gpu_resident
            assert normal.format.id == source.format.id and (normal.width, normal.height) == (32, 24)
            for n in (0, 4, 2, 0):
                with source.get_frame(n) as original, normal.get_frame(n) as output, downloaded.get_frame(n) as other:
                    assert dict(output.props) == dict(original.props) == dict(other.props)
                    for plane in range(output.format.num_planes):
                        actual = np.asarray(output[plane])
                        assert np.isfinite(actual).all()
                        assert np.array_equal(actual, np.asarray(other[plane]))
                        if plane:
                            assert np.array_equal(actual, np.asarray(original[plane]))
            rows.append({'format': source.format.name, 'cache': cache,
                         'cpu_gpu_equal': True, 'properties_preserved': True,
                         'unselected_planes_exact': True})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exercise', action='store_true')
    parser.add_argument('--require-hardware', action='store_true')
    parser.add_argument('--device-index', type=int)
    parser.add_argument('--oracle-suite', choices=('smoke', 'full', 'half'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if (args.require_hardware or args.oracle_suite) and not args.exercise:
        parser.error('Hardware and numerical validation require --exercise')
    if args.oracle_suite and not args.output:
        parser.error('--oracle-suite requires --output')
    if args.device_index is not None and (not args.require_hardware or args.device_index < 0):
        parser.error('--device-index requires --require-hardware and a nonnegative index')
    folder = Path(vs.__file__).resolve().parent / 'plugins/dfttestvk'
    native = 'dfttestvk.dll' if sys.platform == 'win32' else 'dfttestvk.so'
    plugin = folder / native
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    installed = importlib.metadata.version('vapoursynth-dfttestvk')
    assert installed == manifest['version']
    assert hashlib.sha256(plugin.read_bytes()).hexdigest() == manifest['sha256'][native]
    assert (folder / 'manifest.vs').read_text().splitlines() == ['[VapourSynth Manifest V1]', 'dfttestvk']
    core = vs.core
    functions = {f.name: f.signature for f in core.dfttestvk.functions()}
    assert set(functions) == {'DFTTest', 'DFTTestGPU'}
    loaded = next(p for p in core.plugins() if p.namespace == 'dfttestvk')
    assert Path(loaded.plugin_path).resolve() == plugin.resolve()
    selected = select_hardware_device(core, args.device_index) if args.require_hardware else None
    result = {'version': installed, 'platform': manifest['platform'],
              'upstream_commit': manifest['upstream_commit'],
              'native_sha256': manifest['sha256'][native], 'autoload': True,
              'functions': functions, 'rendered': args.exercise}
    if selected is not None:
        result['selected_device'] = selected
    if args.exercise:
        result['cases'] = exercise(core)
        result['active_device'] = {k: v for k, v in core.vulkan_device_info.items() if k not in ('uuid', 'luid')}
    if args.oracle_suite:
        output = args.output.with_suffix('.oracle-' + args.oracle_suite + '.json')
        output.parent.mkdir(parents=True, exist_ok=True)
        test = Path(__file__).resolve().parents[1] / 'native/tests/correctness.py'
        env = os.environ.copy()
        if selected is not None:
            env['DFTTESTVK_DEVICE'] = str(selected['index'])
        subprocess.run([sys.executable, str(test), '--backend', 'vk', '--against', 'oracle',
                        '--suite', args.oracle_suite, '--dll', str(plugin), '--output', str(output)],
                       check=True, env=env)
        oracle = json.loads(output.read_text(encoding='utf-8'))
        assert oracle['passed']
        result['oracle'] = {'passed': True, 'suite': args.oracle_suite, 'cases': len(oracle['cases'])}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
