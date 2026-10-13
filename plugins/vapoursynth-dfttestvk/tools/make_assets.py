"""Build central native payload zips from the exact plugin files in a built wheel."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    with zipfile.ZipFile(args.wheel) as wheel:
        files={name.split('vapoursynth/plugins/',1)[1]:wheel.read(name) for name in wheel.namelist()
               if name.startswith('vapoursynth/plugins/dfttestvk/') and not name.endswith('/')}
        if not files:
            raise ValueError('Wheel has no DFTTestVK package')
        manifest=json.loads(files['dfttestvk/manifest.json'])
        for name,digest in manifest['sha256'].items():
            if hashlib.sha256(files['dfttestvk/'+name]).hexdigest()!=digest:
                raise ValueError('Wheel package hash mismatch: '+name)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(files.items()):
            archive.writestr(name,data)
    receipt={'file':args.output.name,'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),
             'wheel':args.wheel.name,'wheel_sha256':hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
             'manifest':manifest}
    args.output.with_suffix('.zip.sha256').write_text(receipt['sha256']+'  '+args.output.name+'\n',encoding='ascii')
    args.output.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
