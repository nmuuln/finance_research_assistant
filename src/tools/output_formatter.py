from datetime import datetime
from docx import Document
import os

class OutputFormatterTool:
    """
    Converts final text into a .docx file and returns the path and text.
    """
    name = "OutputFormatterTool"
    description = "Converts final text into a .docx and returns {'path','text'}."

    def __call__(self, text: str, out_dir: str = "outputs", filename_prefix: str = "ufe_finance_report"):
        os.makedirs(out_dir, exist_ok=True)
        fname = f"{filename_prefix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.docx"
        path = os.path.join(out_dir, fname)
        doc = Document()
        for line in text.split("\n"):
            doc.add_paragraph(line)
        doc.save(path)
        return {"path": path, "text": text}
