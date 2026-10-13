"""Verify the installed wheel autoload path; optionally render real Vulkan frames."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import vapoursynth as vs
from hardware_device import select_hardware_device


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exercise',action='store_true')
    parser.add_argument('--require-hardware',action='store_true',help='Select a physical Vulkan 1.4 device and reject software execution')
    parser.add_argument('--device-index',type=int,help='Select a specific physical Vulkan device for hardware validation')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.require_hardware and not args.exercise:
        parser.error('--require-hardware requires --exercise')
    if args.device_index is not None and (not args.require_hardware or args.device_index < 0):
        parser.error('--device-index requires --require-hardware and a nonnegative index')
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
    assert all('debug:' not in signature for signature in functions.values())
    assert all(all(option in signature for option in ('bits:int:opt;','sample_type:int:opt;')) for signature in functions.values())
    assert all('dither_type:' not in signature for signature in functions.values())
    actual=next(p for p in core.plugins() if p.namespace=='krigvk')
    assert Path(actual.plugin_path).resolve()==plugin.resolve(),actual.plugin_path
    selected=select_hardware_device(core,args.device_index) if args.require_hardware else None
    result={'version':installed,'platform':manifest['platform'],'native_sha256':manifest['sha256'][native],
            'upstream_commit':manifest['upstream_commit'],'autoload':True,'functions':functions,'rendered':False}
    if selected is not None:
        result|={'hardware_required':True,'selected_device':selected}
    if args.exercise:
        core.num_threads=4
        source=core.std.BlankClip(width=16,height=12,format=vs.YUV420P16,color=[16384,32768,32768],length=4)
        for entry in ('KrigBilateral','KrigBilateralGPU'):
            try:
                getattr(core.krigvk,entry)(source,debug=0)
            except vs.Error as error:
                assert 'debug' in str(error)
            else:
                raise AssertionError('Removed debug option accepted')
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
        limited=core.std.SetFrameProps(core.std.BlankClip(source,format=vs.YUV420P8,color=[16,128,128]),_Range=0)
        full=core.std.SetFrameProps(core.std.BlankClip(source,format=vs.YUV420P8,color=[0,128,128]),_Range=1)
        for clip in (limited,full):
            with core.krigvk.KrigBilateral(clip,bits=32).get_frame(0) as converted:
                assert converted.format.id==int(vs.YUV444PS)
                assert all(value==0 for p in range(3) for row in converted[p].tolist() for value in row)
        warnings=[]
        handler=core.add_log_handler(lambda level,message: warnings.append(message) if level==vs.MESSAGE_TYPE_WARNING else None)
        try:
            for entry in ('KrigBilateral','KrigBilateralGPU'):
                warnings.clear()
                default=getattr(core.krigvk,entry)(limited)
                assert default.format.id==int(vs.YUV444P16) and not warnings
                low=getattr(core.krigvk,entry)(patterned,bits=8)
                assert len(warnings)==1 and 'no dithering' in warnings[0] and 'banding' in warnings[0]
                read=core.std.GPUDownload(low) if low.gpu_resident else low
                with read.get_frame(1) as frame:
                    assert frame.format.id==int(vs.YUV444P8)
                assert len(warnings)==1
                for mode in ('none','ordered','random','error_diffusion'):
                    try:
                        getattr(core.krigvk,entry)(patterned,bits=8,dither_type=mode)
                    except vs.Error as error:
                        assert 'dither_type' in str(error)
                    else:
                        raise AssertionError('Removed dither_type argument accepted: '+mode)
        finally:
            core.remove_log_handler(handler)
        normal=core.krigvk.KrigBilateral(patterned,bits=8)
        resident=core.krigvk.KrigBilateralGPU(core.std.GPUUpload(patterned),bits=8)
        with normal.get_frame(1) as frame,core.std.GPUDownload(resident).get_frame(1) as other:
            assert all(frame[p].tobytes()==other[p].tobytes() for p in range(3))
        floating=core.resize.Point(patterned,format=vs.YUV420PS)
        with core.krigvk.KrigBilateral(floating,bits=16,sample_type=vs.INTEGER).get_frame(1) as frame:
            assert frame.format.id==int(vs.YUV444P16)
        result|={'rendered':True,'cpu_gpu_equal':True,'luma_exact':True,'signed_float_chroma':True,
                 'range_aware':True,'output_depth_control':True,'fp32_conversion':True,
                 'dithering':False,'integer_default_bits':16,'low_depth_warning':True,
                 'dither_parameter_removed':True,
                 'nonuniform_chroma':True,
                 'devices':[{k:v for k,v in entry.items() if k not in ('uuid','luid')} for entry in core.vulkan_devices]}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
