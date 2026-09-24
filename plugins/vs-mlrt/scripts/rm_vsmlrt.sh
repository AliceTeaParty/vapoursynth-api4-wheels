#!/bin/sh
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ -x "$script_dir/python" ]; then
    exec "$script_dir/python" -m rm_vsmlrt "$@"
fi
if [ -x "$script_dir/python.exe" ]; then
    exec "$script_dir/python.exe" -m rm_vsmlrt "$@"
fi
if command -v python >/dev/null 2>&1; then
    exec python -m rm_vsmlrt "$@"
fi
exec python3 -m rm_vsmlrt "$@"
