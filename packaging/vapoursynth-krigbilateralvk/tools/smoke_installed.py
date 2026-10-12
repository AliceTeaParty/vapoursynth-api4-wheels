"""Verify the installed wheel autoload path; optionally render real Vulkan frames."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import vapoursynth as vs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exercise',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    native='krigbilateralvk.dll' if sys.platform=='win32' else 'krigbilateralvk.so'
    folder=Path(vs.__file__).resolve().parent/'plugins/krigbilateralvk'
    plugin=folder/native
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    installed=importlib.metadata.version('vapoursynth-krigbilateralvk')
    assert installed==manifest['version']
    assert hashlib.sha256(plugin.read_bytes()).hexdigest()==manifest['sha256'][native]
    assert (folder/'manifest.vs').read_text().splitlines()==['[VapourSynth Manifest V1]','krigbilateralvk']
    core=vs.core
    assert hasattr(core,'krigvk')
    functions={f.name:f.signature for f in core.krigvk.functions()}
    assert set(functions)=={'KrigBilateral','KrigBilateralGPU'}
    assert all('reference:' not in signature for signature in functions.values())
    actual=next(p for p in core.plugins() if p.namespace=='krigvk')
    assert Path(actual.plugin_path).resolve()==plugin.resolve(),actual.plugin_path
    result={'version':installed,'platform':manifest['platform'],'native_sha256':manifest['sha256'][native],
            'upstream_commit':manifest['upstream_commit'],'autoload':True,'functions':functions,'rendered':False}
    if args.exercise:
        core.num_threads=4
        source=core.std.BlankClip(width=16,height=12,format=vs.YUV420P16,color=[16384,32768,32768],length=4)
        normal=core.krigvk.KrigBilateral(source)
        resident=core.krigvk.KrigBilateralGPU(core.std.GPUUpload(source))
        gpu=core.std.GPUDownload(resident)
        assert resident.gpu_resident and not normal.gpu_resident
        for n in (0,3,1):
            with source.get_frame(n) as original,normal.get_frame(n) as output,gpu.get_frame(n) as other:
                assert output.format.id==int(vs.YUV444P16)
                assert output[0].tobytes()==original[0].tobytes()
                assert all(output[p].tobytes()==other[p].tobytes() for p in range(3))
                for p in (1,2):
                    assert all(value==32768 for row in output[p].tolist() for value in row)
        for fmt in (vs.YUV420PH,vs.YUV420PS):
            clip=core.std.BlankClip(source,format=fmt,color=[0.25,-0.25,0.25])
            with core.krigvk.KrigBilateral(clip).get_frame(0) as output:
                assert all(v==-0.25 for row in output[1].tolist() for v in row)
                assert all(v==0.25 for row in output[2].tolist() for v in row)
        tiles=[core.std.BlankClip(source,color=color) for color in
               ([16384,12000,45000],[50000,48000,16000],[30000,24000,55000],[45000,55000,22000])]
        patterned=core.std.StackVertical([core.std.StackHorizontal(tiles[:2]),core.std.StackHorizontal(tiles[2:])])
        output=core.krigvk.KrigBilateral(patterned)
        other=core.std.GPUDownload(core.krigvk.KrigBilateralGPU(core.std.GPUUpload(patterned)))
        with patterned.get_frame(1) as original,output.get_frame(1) as reconstructed,other.get_frame(1) as resident:
            assert reconstructed[0].tobytes()==original[0].tobytes()
            assert all(reconstructed[p].tobytes()==resident[p].tobytes() for p in range(3))
            assert '_ChromaLocation' not in reconstructed.props
            for p in (1,2):
                values=[v for row in reconstructed[p].tolist() for v in row]
                assert max(values)>min(values)
        result|={'rendered':True,'cpu_gpu_equal':True,'luma_exact':True,'signed_float_chroma':True,
                 'nonuniform_chroma':True,
                 'devices':[{k:v for k,v in entry.items() if k not in ('uuid','luid')} for entry in core.vulkan_devices]}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
