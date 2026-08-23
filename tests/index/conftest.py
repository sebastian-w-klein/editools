import pytest
from docx import Document


@pytest.fixture
def make_docx(tmp_path):
    """Build a .docx from (text, italic) pieces, one paragraph per entry."""
    def build(*paragraphs, name="index.docx"):
        document = Document()
        for pieces in paragraphs:
            if isinstance(pieces, str):
                pieces = [(pieces, None)]
            paragraph = document.add_paragraph()
            for text, italic in pieces:
                run = paragraph.add_run(text)
                if italic is not None:
                    run.italic = italic
        path = tmp_path / name
        document.save(str(path))
        return path
    return build
