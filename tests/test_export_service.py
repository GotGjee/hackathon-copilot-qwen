"""
Tests for the ExportService.
Covers ZIP creation for code and pitch materials, file formatting, and edge cases.
"""

import pytest
import zipfile
import os
from pathlib import Path
from datetime import datetime

from src.services.export_service import ExportService


class TestExportServiceInit:
    """Tests for ExportService initialization."""

    def test_create_with_default_dir(self, tmp_path):
        """Test creating ExportService with default directory."""
        export_dir = str(tmp_path / "exports")
        service = ExportService(export_dir=export_dir)
        assert os.path.exists(export_dir)

    def test_create_with_custom_dir(self, tmp_path):
        """Test creating ExportService with custom directory."""
        export_dir = str(tmp_path / "custom_exports")
        service = ExportService(export_dir=export_dir)
        assert os.path.exists(export_dir)

    def test_existing_dir_not_recreated(self, tmp_path):
        """Test that existing directory is not recreated."""
        export_dir = tmp_path / "exports"
        export_dir.mkdir()
        marker = export_dir / "marker.txt"
        marker.write_text("test")
        
        service = ExportService(export_dir=str(export_dir))
        assert marker.exists()


class TestExportCodeZip:
    """Tests for export_code_zip method."""

    def test_export_basic(self, tmp_path):
        """Test basic code export creates a ZIP file."""
        service = ExportService(export_dir=str(tmp_path))
        code_artifacts = {
            "main.py": {"content": "print('hello')"}
        }
        zip_path = service.export_code_zip("test-001", code_artifacts, title="test")
        assert os.path.exists(zip_path)
        assert zip_path.endswith(".zip")

    def test_export_creates_readme(self, tmp_path):
        """Test export includes README.md."""
        service = ExportService(export_dir=str(tmp_path))
        code_artifacts = {
            "main.py": {"content": "print('hello')"}
        }
        zip_path = service.export_code_zip("test-001", code_artifacts, title="TestProject")
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "README.md" in names

    def test_export_includes_all_files(self, tmp_path):
        """Test export includes all code artifacts."""
        service = ExportService(export_dir=str(tmp_path))
        code_artifacts = {
            "main.py": {"content": "print('main')"},
            "models.py": {"content": "class Model: pass"},
            "utils.py": {"content": "def helper(): pass"},
        }
        zip_path = service.export_code_zip("test-001", code_artifacts)
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "main.py" in names
            assert "models.py" in names
            assert "utils.py" in names

    def test_export_skips_empty_files(self, tmp_path):
        """Test export skips files with empty content."""
        service = ExportService(export_dir=str(tmp_path))
        code_artifacts = {
            "main.py": {"content": "print('hello')"},
            "empty.py": {"content": ""},
        }
        zip_path = service.export_code_zip("test-001", code_artifacts)
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "main.py" in names
            assert "empty.py" not in names

    def test_export_filename_format(self, tmp_path):
        """Test export filename includes title, session_id, and timestamp."""
        service = ExportService(export_dir=str(tmp_path))
        code_artifacts = {"main.py": {"content": "pass"}}
        zip_path = service.export_code_zip("test-001", code_artifacts, title="My Project")
        filename = os.path.basename(zip_path)
        assert "My_Project" in filename
        assert "test-001" in filename
        assert filename.endswith(".zip")

    def test_export_code_content(self, tmp_path):
        """Test exported code content matches input."""
        service = ExportService(export_dir=str(tmp_path))
        expected_content = "from fastapi import FastAPI\n\napp = FastAPI()"
        code_artifacts = {
            "main.py": {"content": expected_content}
        }
        zip_path = service.export_code_zip("test-001", code_artifacts)
        with zipfile.ZipFile(zip_path, "r") as zf:
            content = zf.read("main.py").decode("utf-8")
            assert content == expected_content

    def test_export_with_codefile_objects(self, tmp_path, sample_code_file):
        """Test export with CodeFile Pydantic model objects."""
        service = ExportService(export_dir=str(tmp_path))
        code_artifacts = {
            "main.py": sample_code_file
        }
        zip_path = service.export_code_zip("test-001", code_artifacts)
        with zipfile.ZipFile(zip_path, "r") as zf:
            content = zf.read("main.py").decode("utf-8")
            assert "FastAPI" in content

    def test_export_multiple_files(self, tmp_path):
        """Test export with multiple files creates valid ZIP."""
        service = ExportService(export_dir=str(tmp_path))
        code_artifacts = {
            "src/main.py": {"content": "print('main')"},
            "src/utils.py": {"content": "print('utils')"},
        }
        zip_path = service.export_code_zip("test-001", code_artifacts)
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Verify ZIP is valid and contains files
            names = zf.namelist()
            assert len(names) >= 3  # README + 2 files

    def test_export_readme_contains_files(self, tmp_path):
        """Test README.md contains list of exported files."""
        service = ExportService(export_dir=str(tmp_path))
        code_artifacts = {
            "main.py": {"content": "pass"},
            "utils.py": {"content": "pass"},
        }
        zip_path = service.export_code_zip("test-001", code_artifacts)
        with zipfile.ZipFile(zip_path, "r") as zf:
            readme = zf.read("README.md").decode("utf-8")
            assert "main.py" in readme
            assert "utils.py" in readme


class TestExportPitchMaterials:
    """Tests for export_pitch_materials method."""

    def test_export_pitch_basic(self, tmp_path, sample_narrative, sample_slides, sample_script):
        """Test basic pitch export creates a ZIP file."""
        service = ExportService(export_dir=str(tmp_path))
        zip_path = service.export_pitch_materials(
            "test-001",
            narrative=sample_narrative.model_dump(),
            slides=[s.model_dump() for s in sample_slides],
            script=[s.model_dump() for s in sample_script],
            title="TestPitch"
        )
        assert os.path.exists(zip_path)
        assert zip_path.endswith(".zip")

    def test_export_pitch_contains_all_files(self, tmp_path, sample_narrative, sample_slides, sample_script):
        """Test pitch export includes all material files."""
        service = ExportService(export_dir=str(tmp_path))
        zip_path = service.export_pitch_materials(
            "test-001",
            narrative=sample_narrative.model_dump(),
            slides=[s.model_dump() for s in sample_slides],
            script=[s.model_dump() for s in sample_script],
            title="Test"
        )
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "01_narrative.txt" in names
            assert "02_slides_outline.txt" in names
            assert "03_speaker_script.txt" in names

    def test_export_pitch_filename_format(self, tmp_path, sample_narrative):
        """Test pitch export filename format."""
        service = ExportService(export_dir=str(tmp_path))
        zip_path = service.export_pitch_materials(
            "test-001",
            narrative=sample_narrative.model_dump(),
            slides=[],
            script=[],
            title="My Pitch"
        )
        filename = os.path.basename(zip_path)
        assert "pitch" in filename
        assert "My_Pitch" in filename
        assert "test-001" in filename

    def test_narrative_format(self, tmp_path, sample_narrative):
        """Test narrative text file format."""
        service = ExportService(export_dir=str(tmp_path))
        zip_path = service.export_pitch_materials(
            "test-001",
            narrative=sample_narrative.model_dump(),
            slides=[],
            script=[]
        )
        with zipfile.ZipFile(zip_path, "r") as zf:
            content = zf.read("01_narrative.txt").decode("utf-8")
            assert "NARRATIVE ARC" in content
            assert sample_narrative.problem in content
            assert sample_narrative.solution in content

    def test_slides_format(self, tmp_path, sample_slides):
        """Test slides text file format."""
        service = ExportService(export_dir=str(tmp_path))
        zip_path = service.export_pitch_materials(
            "test-001",
            narrative=None,
            slides=[s.model_dump() for s in sample_slides],
            script=[]
        )
        with zipfile.ZipFile(zip_path, "r") as zf:
            content = zf.read("02_slides_outline.txt").decode("utf-8")
            assert "SLIDE DECK OUTLINE" in content
            assert "Slide 1" in content

    def test_script_format(self, tmp_path, sample_script):
        """Test script text file format."""
        service = ExportService(export_dir=str(tmp_path))
        zip_path = service.export_pitch_materials(
            "test-001",
            narrative=None,
            slides=[],
            script=[s.model_dump() for s in sample_script]
        )
        with zipfile.ZipFile(zip_path, "r") as zf:
            content = zf.read("03_speaker_script.txt").decode("utf-8")
            assert "SPEAKER SCRIPT" in content
            assert "[Slide 1]" in content

    def test_export_with_empty_narrative(self, tmp_path, sample_slides):
        """Test pitch export handles empty narrative."""
        service = ExportService(export_dir=str(tmp_path))
        zip_path = service.export_pitch_materials(
            "test-001",
            narrative=None,
            slides=[s.model_dump() for s in sample_slides],
            script=[]
        )
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "01_narrative.txt" not in names
            assert "02_slides_outline.txt" in names

    def test_export_with_empty_slides(self, tmp_path, sample_narrative):
        """Test pitch export handles empty slides."""
        service = ExportService(export_dir=str(tmp_path))
        zip_path = service.export_pitch_materials(
            "test-001",
            narrative=sample_narrative.model_dump(),
            slides=[],
            script=[]
        )
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "01_narrative.txt" in names
            assert "02_slides_outline.txt" not in names

    def test_export_with_empty_script(self, tmp_path, sample_narrative):
        """Test pitch export handles empty script."""
        service = ExportService(export_dir=str(tmp_path))
        zip_path = service.export_pitch_materials(
            "test-001",
            narrative=sample_narrative.model_dump(),
            slides=[],
            script=[]
        )
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "03_speaker_script.txt" not in names


class TestFormatMethods:
    """Tests for internal formatting methods."""

    def test_format_narrative(self):
        """Test _format_narrative method."""
        service = ExportService()
        narrative = {
            "problem": "Test problem",
            "solution": "Test solution",
            "impact": "Test impact"
        }
        result = service._format_narrative(narrative)
        assert "PROBLEM:" in result
        assert "SOLUTION:" in result
        assert "Test problem" in result

    def test_format_slides(self):
        """Test _format_slides method."""
        service = ExportService()
        slides = [
            {"slide_number": 1, "title": "Title", "subtitle": "Sub", "bullet_points": ["Point 1"], "visual_suggestion": "Image"}
        ]
        result = service._format_slides(slides)
        assert "Slide 1: Title" in result
        assert "Point 1" in result

    def test_format_script(self):
        """Test _format_script method."""
        service = ExportService()
        script = [
            {"slide_number": 1, "section": "hook", "text": "Hello everyone!", "tone": "energetic", "notes": "Smile"}
        ]
        result = service._format_script(script)
        assert "[Slide 1]" in result
        assert "(hook)" in result
        assert "Hello everyone!" in result
        assert "Smile" in result


class TestGetExports:
    """Tests for get_exports method."""

    def test_get_exports_empty(self, tmp_path):
        """Test get_exports returns empty list when no files exist."""
        service = ExportService(export_dir=str(tmp_path))
        result = service.get_exports()
        assert result == []

    def test_get_exports_with_files(self, tmp_path):
        """Test get_exports returns list of ZIP files."""
        service = ExportService(export_dir=str(tmp_path))
        # Create a dummy ZIP file
        zip_path = tmp_path / "test_export.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.txt", "test")
        
        result = service.get_exports()
        assert len(result) == 1
        assert str(zip_path) in result

    def test_get_exports_igns_other_files(self, tmp_path):
        """Test get_exports only returns ZIP files."""
        service = ExportService(export_dir=str(tmp_path))
        # Create a non-ZIP file
        (tmp_path / "readme.txt").write_text("test")
        
        result = service.get_exports()
        assert result == []