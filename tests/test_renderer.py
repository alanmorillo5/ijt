import pytest
from pathlib import Path
from ijt.renderer.pdf import render_resume_to_pdf
import json

def test_pdf_generation(tmp_path):
    resume_data = {
        "personal": {"name": "Test User", "email": "test@example.com"},
        "education": [],
        "experience": [],
        "projects": [],
        "skills": {}
    }
    
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "resume.html").write_text("<html><body><h1>{{ personal.name }}</h1></body></html>")
    (templates_dir / "resume.css").write_text("h1 { color: red; }")
    
    output_pdf = tmp_path / "output.pdf"
    render_resume_to_pdf(resume_data, templates_dir, output_pdf)
    
    assert output_pdf.exists()
    assert output_pdf.stat().st_size > 0
