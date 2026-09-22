# vs-cfl

Chroma-from-Luma for VapourSynth — 亮度引导的色度重建类算法集

## 函数签名

### kACfL

```python
cfl.KACFL(clip, pb=0.8, ep=2.0, cox=None, coy=None)
```

| 参数 | 类型 | 默认值 | 范围 | 说明 |
|------|------|--------|------|------|
| `pb` | float | `0.8` | `[0.0, 1.0]` | 预测混合权重。越大越依赖线性预测，越小越依赖空间滤波 |
| `ep` | float | `2.0` | `[0.0, 10.0]` | 边缘保护。越大则空间滤波对亮度差异越敏感，边缘越锐利 |
| `cox` | float | `None` | x | 亮度 X 偏移（像素）。 `None` 时从帧属性 `_ChromaLocation` 自动检测 |
| `coy` | float | `None` | x | 亮度 Y 偏移（像素）。 `None` 时从帧属性 `_ChromaLocation` 自动检测 |

自动检测模式从帧属性 `_ChromaLocation` 推导偏移。基准位置等价于亮度块中心，即 CENTER 色度位置，偏移表示从该中心到实际色度采样点的位移（单位：亮度像素）：

| ChromaLoc | cox | coy (420) | coy (422) |
|------|------|--------|------|
| LEFT | -0.5 | 0 | 0 |
| CENTER | 0 | 0 | 0 |
| TOP_LEFT | -0.5 | -0.5 | 0 |
| TOP | 0 | -0.5 | 0 |
| BOTTOM_LEFT | -0.5 | 0.5 | 0 |
| BOTTOM | 0 | 0.5 | 0 |

- 支持格式  
  输入： YUV420P8 YUV422P8 YUV420P9 YUV422P9 YUV420P10 YUV422P10 YUV420P12 YUV422P12 YUV420P14 YUV422P14 YUV420P16 YUV422P16  
  输出： YUV444P8/YUV444P9/YUV444P10/YUV444P12/YUV444P14/YUV444P16 （位深与输入一致）

## 构建

msvc, meson, ninja

```bash
meson setup build
meson compile -C build
```

> MSVC 需在 VS Developer Command Prompt 或执行 `vcvars64.bat` 后运行。

## 许可

MIT
