from __future__ import annotations

import sys
from pathlib import Path
import pytest
import shutil
import platform

from graphify.install import dispatch_install_cli, _platform_skill_destination, _PLATFORM_CONFIG

def test_install_align_behavior(tmp_path, monkeypatch, capsys):
    # Mock home directory to isolate tests
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    # Force project root path for testing
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Pre-install opencode skill with customized content
    platform_name = "opencode"
    skill_dst = _platform_skill_destination(platform_name, project=False)
    skill_dst.parent.mkdir(parents=True, exist_ok=True)
    
    custom_content = "# Customized graphify skill\nSome special rules."
    skill_dst.write_text(custom_content, encoding="utf-8")
    
    # Write older version
    version_file = skill_dst.parent / ".graphify_version"
    version_file.write_text("0.1.0", encoding="utf-8")

    # Run dispatch_install_cli install --align
    monkeypatch.setattr(sys, "argv", ["graphify", "install", "--align"])
    
    # We also mock _install_opencode_plugin and _copy_skill_file outputs if they hit sys.exit
    # But since we have correctly created directories, it should run normally.
    dispatch_install_cli("install")

    out = capsys.readouterr().out
    assert "Aligning skill for opencode..." in out
    assert "skill customized ->  preserved" in out

    # Check that content was preserved (not overwritten with default)
    assert skill_dst.read_text(encoding="utf-8") == custom_content
    # Check that version was updated to match package version
    from graphify.install import __version__
    assert version_file.read_text(encoding="utf-8") == __version__

    # Now run with --force
    monkeypatch.setattr(sys, "argv", ["graphify", "install", "--align", "--force"])
    dispatch_install_cli("install")

    # Check that content was overwritten with standard packaged skill
    assert skill_dst.read_text(encoding="utf-8") != custom_content
    assert "skill installed" in capsys.readouterr().out
