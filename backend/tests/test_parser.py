try:
    import pytest
except ImportError:
    pytest = None

from app.services.document_parser import extract_text_from_file


def test_txt_file_extraction():
    sample_text = "John Doe\nSoftware Engineer\nSkills: Python, FastAPI"
    file_bytes = sample_text.encode("utf-8")
    result = extract_text_from_file(file_bytes, "resume.txt")
    assert "John Doe" in result
    assert "FastAPI" in result


def test_markdown_file_extraction():
    sample_text = "# Jane Doe\n## Senior Developer\n- Python\n- React"
    file_bytes = sample_text.encode("utf-8")
    result = extract_text_from_file(file_bytes, "resume.md")
    assert "Jane Doe" in result
    assert "React" in result


if __name__ == "__main__":
    test_txt_file_extraction()
    test_markdown_file_extraction()
    print("All document parser tests passed successfully!")
