# G-Buffer Technical Specification

This document provides a technical specification for the G-Buffer implementation in Flycast, specifically focusing on the structure and encoding of the exported OpenEXR files.

## Overview

The G-Buffer is part of the deferred rendering pipeline in the Vulkan renderer. It captures essential scene information in a single pass, which is then used for post-processing effects such as SSAO (Screen Space Ambient Occlusion), Depth of Field (DoF), and material visualization.

The G-Buffer can be exported to an OpenEXR file by pressing **ALT+G** during emulation.

## OpenEXR File Structure

The exported `.exr` file is a multi-channel image containing 9 channels. All channels are stored as **16-bit half-precision floats** (FP16), even if their source data was integer or 32-bit float.

### Channel Mapping

| EXR Channel Name | Source Attachment | Description | Data Range |
| :--- | :--- | :--- | :--- |
| `Albedo.R` | Attachment 0 (R8G8B8A8) | Diffuse Color (Red) | [0.0, 1.0] |
| `Albedo.G` | Attachment 0 (R8G8B8A8) | Diffuse Color (Green) | [0.0, 1.0] |
| `Albedo.B` | Attachment 0 (R8G8B8A8) | Diffuse Color (Blue) | [0.0, 1.0] |
| `Normal.X` | Attachment 1 (R16G16B16A16F) | World/View Space Normal (X) | [-1.0, 1.0] |
| `Normal.Y` | Attachment 1 (R16G16B16A16F) | World/View Space Normal (Y) | [-1.0, 1.0] |
| `Normal.Z` | Attachment 1 (R16G16B16A16F) | World/View Space Normal (Z) | [-1.0, 1.0] |
| `Depth.Z` | Depth Attachment | Linearized/Raw Depth | [0.0, 1.0] |
| `Material.ID` | Attachment 2 (R8Uint) | Encoded Material Properties | [0.0, 1.0] (ID/255) |
| `SSAO.AO` | SSAO Pass (R8Unorm) | Ambient Occlusion Factor | [0.0, 1.0] |

## Buffer Details

### 1. Albedo (`Albedo.R/G/B`)
*   **Format**: Originally `eR8G8B8A8Unorm`.
*   **Content**: The base color of the surface after texture sampling and vertex coloring, but before lighting.
*   **Normalization**: Divided by 255.0 to map to [0, 1].

### 2. Normals (`Normal.X/Y/Z`)
*   **Format**: Originally `eR16G16B16A16Sfloat`.
*   **Content**: Surface normals. If vertex normals are missing, they are generated using cross-products of position derivatives (`dFdx`/`dFdy`).
*   **Range**: Real values representing the normal vector components.

### 3. Depth (`Depth.Z`)
*   **Format**: Originally `eD32Sfloat` or `eD24UnormS8Uint`.
*   **Content**: The depth value from the depth buffer.
*   **Normalization**: For `D24S8`, the 24-bit value is normalized by `16777215.0`.

### 4. Material ID (`Material.ID`)
*   **Format**: Originally `eR8Uint`.
*   **Normalization**: Stored as `matID / 255.0` in the EXR.
*   **Reconstruction**: To get the original 8-bit ID, use: `uint8_t id = round(Material.ID * 255.0)`.

#### Bitmask Encoding (8 bits)
The Material ID encodes several properties from the PowerVR (PVR) hardware:

| Bits | Name | Description | Values |
| :--- | :--- | :--- | :--- |
| **7-5** | `list_type` | PVR List Type | 0: Opaque, 1: Opaque Mod, 2: Translucent, 3: Translucent Mod, 4: Punch-Through |
| **4** | `has_texture` | Texture presence | 0: No texture, 1: Textured |
| **3** | `is_gouraud` | Shading mode | 0: Flat, 1: Gouraud |
| **2** | `has_bumpmap` | Bump mapping | 0: No bump, 1: Bump map active |
| **1-0** | `fog_ctrl` | Fog control | 0-3: PVR Fog modes |

### 5. SSAO (`SSAO.AO`)
*   **Format**: Originally `eR8Unorm`.
*   **Content**: Pre-calculated Screen Space Ambient Occlusion factor.
*   **Range**: `1.0` means no occlusion, `0.0` means full occlusion.

## Technical Notes

*   **File Naming**: Files are saved as `gbuffer_YYYYMMDD_HHMMSS.exr` in the screenshots directory.
*   **Library**: The export uses `tinyexr` for writing the OpenEXR files.
*   **Layout**: EXR channels are sorted alphabetically by most tools, but the internal order in the file is determined by the `tinyexr` header initialization.
