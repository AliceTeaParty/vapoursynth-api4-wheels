"""Verify native wheel layout, metadata, package hashes and optional Linux ABI floor."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile
from email.parser import BytesParser
from packaging.requirements import Requirement


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel',type=Path,required=True)
    parser.add_argument('--max-glibc')
    args=parser.parse_args()
    with zipfile.ZipFile(args.wheel) as archive:
        names=archive.namelist()
        assert len(set(names))==len(names),'Duplicate wheel entries'
        assert 'vapoursynth/__init__.py' not in names,'Wheel must not own the runtime initializer'
        prefix='vapoursynth/plugins/dfttestvk/'
        payload={n[len(prefix):]:archive.read(n) for n in names if n.startswith(prefix) and not n.endswith('/')}
        manifest=json.loads(payload['manifest.json'])
        suffix='.dll' if manifest['platform']=='windows-x86_64' else '.so'
        plugin='dfttestvk'+suffix
        assert plugin in payload and 'manifest.vs' in payload and 'LICENSE' in payload and 'THIRD_PARTY.md' in payload
        for name,digest in manifest['sha256'].items():
            assert hashlib.sha256(payload[name]).hexdigest()==digest,name
        metadata=BytesParser().parsebytes(archive.read(next(n for n in names if n.endswith('.dist-info/METADATA'))))
        assert metadata['Name']=='vapoursynth-dfttestvk' and metadata['Version']==manifest['version']
        requirements=[Requirement(r) for r in metadata.get_all('Requires-Dist')]
        runtime=next(r for r in requirements if r.name.lower()=='vapoursynth')
        assert str(runtime.specifier)=='>=81', 'VapourSynth must have a minimum version and no upper cap'
        tags=archive.read(next(n for n in names if n.endswith('.dist-info/WHEEL'))).decode()
        assert 'Root-Is-Purelib: false' in tags
        assert ('win_amd64' if suffix=='.dll' else 'manylinux_2_28_x86_64') in tags
        if args.max_glibc:
            with tempfile.TemporaryDirectory() as directory:
                native=Path(directory)/plugin
                native.write_bytes(payload[plugin])
                output=subprocess.check_output(['readelf','--version-info',str(native)],text=True)
                versions=[tuple(map(int,x.split('.'))) for x in re.findall(r'GLIBC_(\d+\.\d+)',output)]
                floor=tuple(map(int,args.max_glibc.split('.')))
                assert versions and all(v<=floor for v in versions),versions
                needed=subprocess.check_output(['readelf','-d',str(native)],text=True)
                assert 'libstdc++.so' not in needed and 'libgcc_s.so' not in needed,needed
    print(json.dumps({'wheel':args.wheel.name,'version':manifest['version'],'platform':manifest['platform'],
                      'native_sha256':manifest['sha256'][plugin],'validated':True},indent=2))


if __name__=='__main__':
    main()
