from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DefaultRemotePolicyTests(unittest.TestCase):
    def test_example_configs_disable_implicit_external_config(self):
        ini = (ROOT / "base/pref.example.ini").read_text()
        toml = (ROOT / "base/pref.example.toml").read_text()
        yaml = (ROOT / "base/pref.example.yml").read_text()

        self.assertRegex(ini, r"(?m)^default_external_config\s*=\s*$")
        self.assertRegex(toml, r'(?m)^default_external_config\s*=\s*""\s*$')
        self.assertRegex(yaml, r'(?m)^\s*default_external_config:\s*""\s*$')

    def test_runtime_loaders_have_no_implicit_cocr_url(self):
        settings = (ROOT / "src/handler/settings.cpp").read_text()
        interfaces = (ROOT / "src/handler/interfaces.cpp").read_text()

        for source in (settings, interfaces):
            self.assertNotIn(
                "Custom_OpenClash_Rules@refs/heads/main/cfg/Custom_Clash.ini",
                source,
            )
        self.assertNotIn("if (global.defaultExtConfig.empty())", settings)
        self.assertIn("global.defaultExtConfig.clear();", settings)
        self.assertIn(
            "if (global.fallbackToDefaultExternalConfig &&",
            interfaces,
        )

    def test_imported_default_rulesets_have_no_cocr_remote_entries(self):
        imported_rulesets = [
            ROOT / "base/snippets/rulesets.toml",
            ROOT / "base/snippets/rulesets.txt",
        ]

        active_lines = []
        for path in imported_rulesets:
            active_lines.extend(
                line
                for line in path.read_text().splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            )
        self.assertFalse(any("Custom_OpenClash_Rules" in line for line in active_lines))
        self.assertFalse(
            any(
                "testingcf.jsdelivr.net/gh/Aethersailor" in line
                for line in active_lines
            )
        )


if __name__ == "__main__":
    unittest.main()
