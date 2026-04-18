# G-Buffer Architecture

This document provides a technical specification for the G-Buffer implementation in Flycast, specifically focusing on the deferred shading pipeline, post-processing chain, and the structure of the exported OpenEXR files.

## Overview

The G-Buffer is part of a **modern Deferred Shading pipeline** in the Vulkan renderer. It captures essential scene information in a single geometry pass. All G-Buffer attachments are treated as **read-only** after the geometry pass; no post-process writes back into them (non-destructive principle).

The G-Buffer can be exported to an OpenEXR file by pressing **ALT+9** during emulation.

## Rendering Pipeline

The pipeline follows a strict 5-phase execution order within `GBufferVulkanRenderer::Present()`:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Phase A: Geometry Pass (G-Buffer Fill)                             │
│  → Writes: Albedo, Normals, MaterialID, Motion, HUD, Depth          │
│  → After this pass, ALL G-Buffer attachments become READ-ONLY       │
└────────────────────────┬────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Phase B: SSAOPass (Screen-Space Ambient Occlusion)                 │
│  → Reads: Depth, Normals                                            │
│  → Writes: ssaoTex (R8Unorm) — isolated, non-destructive            │
└────────────────────────┬────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Phase C: CompositePass (Deferred Lighting)                         │
│  → Reads: Albedo, Normals, Depth, MaterialID, Motion, ssaoTex, HUD  │
│  → Writes: Accumulation Buffer (R16G16B16A16Sfloat — HDR)           │
│  → Formula: color = Albedo.rgb * SSAO                               │
└────────────────────────┬────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Phase D: DoFPass (Depth of Field — Post-Processing)                │
│  → Reads: Accumulation Buffer, Depth                                │
│  → Writes: Accumulation Buffer (ping-pong via temp buffer)          │
│  → Operates on the lit HDR image, not raw Albedo                    │
└────────────────────────┬────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Phase E: FinalPass (Tonemapping + HUD Overlay)                     │
│  → Reads: Accumulation Buffer (post-processed), HUD Buffer          │
│  → Writes: Final output (R8G8B8A8Unorm → Swapchain)                 │
│  → HUD is composited here (unaffected by DoF)                       │
│  → Tonemapping (Reinhard) can be enabled here                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **G-Buffer Immutability**: Once the geometry pass completes, G-Buffer attachments (Albedo, Normals, Depth, etc.) are 100% read-only (`ShaderReadOnlyOptimal`). No post-process writes into them.
2. **Dedicated Accumulation Buffer**: Lighting and global effects are computed and stored in a dedicated HDR buffer (`R16G16B16A16Sfloat`), separate from the raw G-Buffer data.
3. **Strict Pass Separation**: Each pass has well-defined inputs and a single output. No implicit side effects.
4. **Non-Destructive HUD**: The HUD is composited only in the final pass, ensuring it is never affected by DoF or other camera effects.

## Passes Implementation

### SSAOPass

- **Shader**: `vulkan_ssao.frag`
- **Input**: Depth attachment, Normal attachment
- **Output**: `ssaoTex` (R8Unorm) — standalone AO factor
- **Note**: Writes exclusively to its own buffer. The old destructive multiply-on-Albedo behavior has been removed.

### CompositePass (Lighting Pass)

- **Shader**: `vulkan_gbuffer_composite.frag`
- **Input**: All G-Buffer attachments + ssaoTex
- **Output**: Accumulation Buffer (`R16G16B16A16Sfloat`)
- **Debug modes**: viewMode push constant selects between Final (0), Albedo (1), Normals (2), Depth (3), Material (4), Motion (5), SSAO (6), HUD (7)

### DoFPass (Depth of Field)

- **Shader**: `vulkan_dof.frag`
- **Input**: Accumulation Buffer, Depth attachment
- **Output**: Accumulation Buffer (via blit from temp buffer)
- **Note**: Operates on the lit HDR image, not raw Albedo. Internal format is `R16G16B16A16Sfloat` to preserve HDR precision.

### FinalPass (Tonemapping + HUD Overlay)

- **Shader**: `vulkan_gbuffer_final.frag`
- **Input**: Accumulation Buffer, HUD attachment
- **Output**: Final image (`R8G8B8A8Unorm`) ready for swapchain presentation
- **Note**: Only executed for `viewMode == 0` (Final) or `viewMode == 7` (HUD debug). Other debug views bypass this pass and present the Accumulation Buffer directly.

## OpenEXR Export Structure

The exported `.exr` file is a multi-channel image containing **15 channels**. The export pipeline uses a **data-driven mapping** and enforces **lexicographical sorting** for maximum compatibility with professional VFX tools (Nuke, Photoshop, DJV).

### Channel Mapping

| EXR Channel Name | Format | Source | Data Range |
| :--- | :--- | :--- | :--- |
| `R, G, B, A` | Half 16b | Albedo Buffer (Att 0) | [0.0, 1.0] |
| `Normal.X/Y/Z` | Half 16b | Normal Buffer (Att 1) | [-1.0, 1.0] |
| `Depth.Z` | **Float 32b** | Depth Buffer | [0.0 (Far), 1.0 (Near)] |
| `Material.ID` | **Uint 32b** | Material Buffer (Att 2) | [0, 255] |
| `SSAO.AO` | Float 32b | SSAO Texture | [0.0, 1.0] |
| `Motion.X/Y` | Half 16b | Motion Buffer (Att 3) | Pixel Velocity |
| `HUD.R/G/B/A` | Float 32b | HUD Buffer (Att 4) | [0.0, 1.0] |

## G-Buffer Export for AI and Deep Learning

The G-Buffer export is specifically designed to provide high-quality "Ground Truth" data for machine learning tasks.

### 1. High Precision Depth

Unlike standard renders, the **Depth.Z** channel is exported as a **32-bit floating point** value. 
*   **Reverse-Z Mapping**: Flycast uses an inverted Z-buffer where **1.0 is the Near plane** and **0.0 is the Far plane (Infinity)**. 
*   **Zero Transformation**: The depth data is copied directly from the GPU memory (`D32_SFLOAT`) to ensure no quantization errors occur.

### 2. Lexicographical Sorting

OpenEXR standard requires channels to be sorted alphabetically in the file header. The export pipeline automatically sorts all 15 channels (e.g., `A`, `B`, `Depth.Z`, `G`, `HUD.A`...) before serialization. This prevents channel misalignment in standard EXR viewers.

### 3. Native Material Segmentation

The **Material.ID** is exported as a native 32-bit unsigned integer. This allows for perfect per-object or per-material segmentation without the precision issues of normalized float IDs.

## Technical Notes

*   **File Naming**: `gbuffer_YYYYMMDD_HHMMSS.exr` in the screenshots directory.
*   **Hotkeys**:
    *   **ALT+1/2/3/4/5/6/7/8**: Toggle various debug views (Depth, Normals, SSAO, Motion, Material, Albedo, HUD).
    *   **ALT+7**: Show pure Albedo buffer (No HUD, No post-effects).
    *   **ALT+8**: Show HUD attachment alone.
    *   **ALT+0**: Return to final composite view.
    *   **ALT+9**: Export current G-Buffer to EXR.

## Key Source Files

| File | Role |
| :--- | :--- |
| `core/rend/vulkan/gbuffer/gbuffer_renderer.cpp` | Pipeline orchestration, EXR Export, `Present()` |
| `core/rend/vulkan/gbuffer/gbuffer_constants.h` | G-Buffer attachment index constants |
| `core/rend/vulkan/shaders/vulkan_gbuffer_composite.frag` | Deferred Lighting / Debug views shader |
| `core/rend/vulkan/shaders/vulkan_gbuffer_final.frag` | Tonemapping + HUD overlay shader |
| `core/rend/vulkan/shaders/vulkan_ssao.frag` | SSAO computation shader |
| `core/rend/vulkan/shaders/vulkan_main.frag` | Geometry pass (G-Buffer fill) |

## Changelog

- **2026-04-18**: Fixed Depth export regression. Enabled full 32-bit float precision for Depth.Z and Uint32 for Material.ID. Standardized channel naming (R,G,B,A) for Albedo. Improved OpenEXR documentation for Deep Learning use cases.
- **2026-04-17**: Complete refactor into a non-destructive Deferred Shading pipeline. Added HDR Accumulation Buffer, FinalPass, isolated SSAO, fixed DoF (operates on lit image), isolated HUD into final pass. Added Motion and HUD buffers to 15-channel EXR export.
- **2026-04-16**: Separated HUD into a dedicated G-Buffer attachment.
