from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_example_configs_disable_implicit_external_config():
    ini = (ROOT / "base/pref.example.ini").read_text()
    toml = (ROOT / "base/pref.example.toml").read_text()
    yaml = (ROOT / "base/pref.example.yml").read_text()

    assert re.search(r"(?m)^default_external_config\s*=\s*$", ini)
    assert re.search(r'(?m)^default_external_config\s*=\s*""\s*$', toml)
    assert re.search(r'(?m)^\s*default_external_config:\s*""\s*$', yaml)


def test_settings_loader_has_no_implicit_cocr_url():
    settings = (ROOT / "src/handler/settings.cpp").read_text()

    assert "Custom_OpenClash_Rules@refs/heads/main/cfg/Custom_Clash.ini" not in settings
    assert "if (global.defaultExtConfig.empty())" not in settings


def test_active_toml_rulesets_have_no_cocr_remote_entries():
    rulesets = (ROOT / "base/snippets/rulesets.toml").read_text().splitlines()

    active_lines = [
        line
        for line in rulesets
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert not any("Custom_OpenClash_Rules" in line for line in active_lines)
    assert not any(
        "testingcf.jsdelivr.net/gh/Aethersailor" in line
        for line in active_lines
    )
