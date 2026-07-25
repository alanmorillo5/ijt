from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS

def render_resume_to_pdf(resume_data: dict, template_dir: Path, output_path: Path):
    """Render a JSON resume dictionary into a PDF file using WeasyPrint."""
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("resume.html")
    
    html_content = template.render(**resume_data)
    
    # Render PDF using WeasyPrint
    HTML(string=html_content, base_url=str(template_dir)).write_pdf(
        target=str(output_path),
        stylesheets=[CSS(filename=str(template_dir / "resume.css"))]
    )
