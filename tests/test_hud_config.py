import unittest
import json
import os
import tempfile
from hud_config import HudConfig
from hud_compositor import Anchor

class TestHudConfig(unittest.TestCase):
    def setUp(self):
        self.image_size = (1280, 960) # 2x the virtual height (480)
        self.v_scale = 480.0 / 960.0 # 0.5
        
        self.valid_json = {
            "hud_zones": [
                {
                    "name": "Test Zone",
                    "w": 100,
                    "h": 50,
                    "zen_mode": True,
                    "source": {"x": 10, "y": 20, "anchor": "SCREEN_CENTER"},
                    "mapping": {"x": 30, "y": 40, "anchor": "SCREEN_TOP_LEFT"}
                }
            ]
        }
        
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(self.valid_json, self.temp_file)
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_load_valid(self):
        rects = HudConfig.load(self.temp_file.name, self.image_size)
        self.assertEqual(len(rects), 1)
        r = rects[0]
        self.assertEqual(r["name"], "Test Zone")
        self.assertEqual(r["zen"], True)
        self.assertEqual(r["anchor"], Anchor.SCREEN_TOP_LEFT)
        
        # Check coordinate conversion
        # Virtual w=100 -> Pixel w = 100 / 0.5 = 200
        self.assertEqual(r["w"], 200)
        self.assertEqual(r["h"], 100)

    def test_load_missing_hud_zones(self):
        with open(self.temp_file.name, 'w') as f:
            json.dump({"something": []}, f)
        
        with self.assertRaises(KeyError) as cm:
            HudConfig.load(self.temp_file.name, self.image_size)
        self.assertIn("hud_zones", str(cm.exception))

    def test_load_missing_key_in_zone(self):
        bad_json = {"hud_zones": [{"name": "bad"}]} # Missing 'w', 'h', etc.
        with open(self.temp_file.name, 'w') as f:
            json.dump(bad_json, f)
            
        with self.assertRaises(RuntimeError) as cm:
            HudConfig.load(self.temp_file.name, self.image_size)
        self.assertIn("'w' is missing", str(cm.exception))

    def test_load_invalid_anchor(self):
        bad_json = self.valid_json.copy()
        bad_json["hud_zones"][0]["mapping"]["anchor"] = "INVALID_ANCHOR"
        with open(self.temp_file.name, 'w') as f:
            json.dump(bad_json, f)
            
        with self.assertRaises(RuntimeError) as cm:
            HudConfig.load(self.temp_file.name, self.image_size)
        self.assertIn("Invalid anchor name", str(cm.exception))

    def test_export(self):
        hud_rects = [
            {
                "name": "Export Zone",
                "sx": 640, "sy": 480, # Pixel center of 1280x960
                "dx": 0, "dy": 0,
                "w": 200, "h": 100,
                "anchor": Anchor.SCREEN_TOP_LEFT,
                "zen": False
            }
        ]
        
        data = HudConfig.export(hud_rects, self.image_size)
        self.assertIn("hud_zones", data)
        self.assertEqual(len(data["hud_zones"]), 1)
        
        zone = data["hud_zones"][0]
        self.assertEqual(zone["name"], "Export Zone")
        # Pixel center (640, 480) -> Virtual center (320, 240)
        # Relative to SCREEN_CENTER (320, 240) -> (0, 0)
        self.assertEqual(zone["source"]["x"], 0)
        self.assertEqual(zone["source"]["y"], 0)
        
        # Pixel (0,0) -> Virtual (0,0)
        # Relative to SCREEN_TOP_LEFT (0,0) -> (0,0)
        self.assertEqual(zone["mapping"]["x"], 0)
        self.assertEqual(zone["mapping"]["y"], 0)
        
        # Pixel w=200 -> Virtual w=100
        self.assertEqual(zone["w"], 100)
        self.assertEqual(zone["h"], 50)

    def test_export_preserve_keys(self):
        # Create a file with extra keys
        with open(self.temp_file.name, 'w') as f:
            json.dump({"custom_key": "val", "hud_zones": []}, f)
            
        hud_rects = [] # Empty but will update
        data = HudConfig.export(hud_rects, self.image_size, existing_path=self.temp_file.name)
        
        self.assertEqual(data["custom_key"], "val")
        self.assertIn("hud_zones", data)

if __name__ == '__main__':
    unittest.main()
