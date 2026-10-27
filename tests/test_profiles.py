import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from profiles import catalog, COMPONENTS

class ProfileTests(unittest.TestCase):
    def test_expected_profiles(self):
        profiles = catalog()
        self.assertEqual(len(profiles), 6)
        self.assertIn("25.12.6/mips_24kc", profiles)
        self.assertIn("25.12.5/arm_cortex-a7_neon-vfpv4", profiles)
        self.assertNotIn("25.12.5/x86_64", profiles)

    def test_arch_profiles_keep_separate_sdk_targets(self):
        profiles = catalog()
        arm = profiles["25.12.6/arm_cortex-a7_neon-vfpv4"]
        self.assertEqual(arm["targets"], ["ipq40xx/generic", "bcm27xx/bcm2709"])

    def test_components_are_independent(self):
        self.assertEqual(set(COMPONENTS), {"rust", "glib", "dbus", "openssl"})

if __name__ == "__main__":
    unittest.main()
