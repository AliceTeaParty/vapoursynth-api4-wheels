"""Select and verify the physical Vulkan device used by a runtime smoke."""


def select_hardware_device(core, device_index=None):
    devices = core.vulkan_devices
    candidates = [
        device for device in devices
        if device['usable'] and device['type'] in ('discrete', 'integrated')
        and tuple(device['api_version'][:2]) >= (1, 4)
    ]
    if not candidates:
        details = '; '.join(
            f"{d['name']}: type={d['type']}, Vulkan={d['api_version']}, reason={d.get('reason', '')}"
            for d in devices
        )
        raise RuntimeError('No usable Vulkan 1.4 hardware device: ' + (details or 'no devices'))
    if device_index is None:
        selected = max(candidates, key=lambda device: device['device_memory'])
    else:
        selected = next((device for device in candidates if device['index'] == device_index), None)
        if selected is None:
            raise RuntimeError(f'Vulkan device {device_index} is not a usable Vulkan 1.4 hardware device')
    core.set_vulkan_device(selected['index'])
    actual = core.vulkan_device_info
    if not selected.get('uuid') or actual.get('uuid') != selected['uuid']:
        raise RuntimeError('The active Vulkan device does not match the selected hardware device')
    return {k: v for k, v in selected.items() if k not in ('uuid', 'luid')}
