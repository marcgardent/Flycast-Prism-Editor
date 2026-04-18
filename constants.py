# Liste des canaux définis dans le référentiel technique Flycast

class Channels:
    ALBEDO_R = 'R'
    ALBEDO_G = 'G'
    ALBEDO_B = 'B'
    NORMAL_X = 'Normal.X'
    NORMAL_Y = 'Normal.Y'
    NORMAL_Z = 'Normal.Z'
    DEPTH_Z = 'Depth.Z'
    MATERIAL_ID = 'Material.ID'
    SSAO_AO = 'SSAO.AO'

STANDARD_CHANNELS = [
    Channels.ALBEDO_R, Channels.ALBEDO_G, Channels.ALBEDO_B,
    Channels.NORMAL_X, Channels.NORMAL_Y, Channels.NORMAL_Z,
    Channels.DEPTH_Z, Channels.MATERIAL_ID, Channels.SSAO_AO
]
