/*
 *  vs-cfl: Chroma-from-Luma Reconstruction Filters
 */

#include "VapourSynth4.h"
#include "VSHelper4.h"
#include "kACfL.h"

VS_EXTERNAL_API(void)
VapourSynthPluginInit2(VSPlugin *plugin, const VSPLUGINAPI *vspapi)
{
    vspapi->configPlugin(
        "com.hooke007.cfl",                // identifier
        "cfl",                             // namespace
        "Chroma-from-Luma Reconstruction", // name
        VS_MAKE_VERSION(1, 0),
        VAPOURSYNTH_API_VERSION,
        0,                                 // flags
        plugin);

    kacflRegister(plugin, vspapi);
}
