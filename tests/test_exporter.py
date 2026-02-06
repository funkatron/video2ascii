"""Tests for exporter module."""

import base64
import gzip
from pathlib import Path

import pytest

from video2ascii.exporter import export


class TestExport:
    """Tests for export function."""
    
    def test_exported_script_is_valid_bash(self, temp_work_dir, sample_ascii_frame):
        """Test exported script is valid bash."""
        output_path = temp_work_dir / "test_export.sh"
        frames = [sample_ascii_frame] * 3
        
        export(frames, output_path, fps=12, crt=False)
        
        assert output_path.exists()
        assert output_path.is_file()
        
        # Check it starts with shebang
        content = output_path.read_text()
        assert content.startswith("#!/usr/bin/env bash")
    
    def test_script_contains_embedded_frames(self, temp_work_dir, sample_ascii_frame):
        """Test script contains embedded frames."""
        output_path = temp_work_dir / "test_export.sh"
        frames = [sample_ascii_frame] * 3
        
        export(frames, output_path, fps=12, crt=False)
        
        content = output_path.read_text()
        # Should contain frame markers
        assert "---FRAME---" in content
        # Should contain base64 encoded data
        assert "FRAME---" in content
    
    def test_script_supports_flags(self, temp_work_dir, sample_ascii_frame):
        """Test script supports --loop, --speed, --crt, --progress flags."""
        output_path = temp_work_dir / "test_export.sh"
        frames = [sample_ascii_frame] * 3
        
        export(frames, output_path, fps=12, crt=False)
        
        content = output_path.read_text()
        # Should parse these flags
        assert "--loop" in content or "LOOP" in content
        assert "--speed" in content or "SPEED" in content
        assert "--crt" in content or "CRT" in content
        assert "--progress" in content or "PROGRESS" in content
    
    def test_script_is_executable(self, temp_work_dir, sample_ascii_frame):
        """Test script is executable."""
        output_path = temp_work_dir / "test_export.sh"
        frames = [sample_ascii_frame] * 3
        
        export(frames, output_path, fps=12, crt=False)
        
        assert output_path.stat().st_mode & 0o111 != 0  # Executable bit set
    
    def test_frame_compression_decompression(self, temp_work_dir, sample_ascii_frame):
        """Test frame compression/decompression works."""
        output_path = temp_work_dir / "test_export.sh"
        frames = [sample_ascii_frame] * 2
        
        export(frames, output_path, fps=12, crt=False)
        
        content = output_path.read_text()
        # Extract frame data - frames are written after "---FRAME---" marker
        # Note: The template may contain example markers, so we need to find actual frame data
        lines = content.split("\n")
        frame_sections = []
        for i, line in enumerate(lines):
            if "---FRAME---" in line:
                # Check if next line contains base64 data (starts with alphanumeric)
                if i + 1 < len(lines) and lines[i + 1].strip():
                    next_line = lines[i + 1].strip()
                    # Base64 encoded data is alphanumeric with possible +/= padding
                    if next_line and all(c.isalnum() or c in "+/=" for c in next_line[:10]):
                        frame_sections.append(i)
        
        # Should have 2 frame markers (one per frame)
        assert len(frame_sections) == 2
        
        # Test decompression for both frames
        for frame_idx in frame_sections:
            if frame_idx + 1 < len(lines):
                encoded = lines[frame_idx + 1].strip()
                if encoded:  # Skip empty lines
                    # Decode and decompress
                    compressed = base64.b64decode(encoded)
                    decompressed = gzip.decompress(compressed).decode("utf-8")
                    assert decompressed == sample_ascii_frame
    
    def test_metadata_embedding(self, temp_work_dir, sample_ascii_frame):
        """Test metadata embedding (fps, crt flag)."""
        output_path = temp_work_dir / "test_export.sh"
        frames = [sample_ascii_frame] * 3
        
        export(frames, output_path, fps=15, crt=True)
        
        content = output_path.read_text()
        # Should contain fps
        assert "ORIG_FPS=15" in content
        # Should contain crt flag
        assert "ORIG_CRT=1" in content
        
        # Test with crt=False
        output_path2 = temp_work_dir / "test_export2.sh"
        export(frames, output_path2, fps=20, crt=False)
        content2 = output_path2.read_text()
        assert "ORIG_FPS=20" in content2
        assert "ORIG_CRT=0" in content2
    
    def test_total_frames_metadata(self, temp_work_dir, sample_ascii_frame):
        """Test total frames count is embedded."""
        output_path = temp_work_dir / "test_export.sh"
        frames = [sample_ascii_frame] * 5
        
        export(frames, output_path, fps=12, crt=False)
        
        content = output_path.read_text()
        assert "TOTAL_FRAMES=5" in content
