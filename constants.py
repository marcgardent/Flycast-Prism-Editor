# List of channels defined in the Flycast technical specification

class Channels:
    ALBEDO_R = 'R'
    ALBEDO_G = 'G'
    ALBEDO_B = 'B'
    ALBEDO_A = 'A'
    NORMAL_X = 'Normal.X'
    NORMAL_Y = 'Normal.Y'
    NORMAL_Z = 'Normal.Z'
    DEPTH_Z = 'Depth.Z'
    MATERIAL_ID = 'Material.ID'
    SSAO_AO = 'SSAO.AO'
    HUD_R = 'HUD.R'
    HUD_G = 'HUD.G'
    HUD_B = 'HUD.B'
    HUD_A = 'HUD.A'

    # Metadata channels
    METADATA_WORLDPOS_X = 'Metadata.WorldPos.X'
    METADATA_WORLDPOS_Y = 'Metadata.WorldPos.Y'
    METADATA_WORLDPOS_Z = 'Metadata.WorldPos.Z'
    METADATA_TEXTURE_HASH = 'Metadata.TextureHash'
    METADATA_POLY_COUNT = 'Metadata.PolyCount'

    # Composite Modes
    COMBINED_METADATA = 'Metadata'


STANDARD_CHANNELS = [
    Channels.ALBEDO_R, Channels.ALBEDO_G, Channels.ALBEDO_B,
    Channels.NORMAL_X, Channels.NORMAL_Y, Channels.NORMAL_Z,
    Channels.DEPTH_Z, Channels.MATERIAL_ID, Channels.SSAO_AO,
    Channels.METADATA_WORLDPOS_X, Channels.METADATA_WORLDPOS_Y, Channels.METADATA_WORLDPOS_Z,
    Channels.METADATA_TEXTURE_HASH, Channels.METADATA_POLY_COUNT
]
