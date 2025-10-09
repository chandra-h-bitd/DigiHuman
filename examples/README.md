Place your example PDFs and DOCX files here.

Optional: you can generate simple samples with the following Python snippet:

```
from reportlab.pdfgen import canvas
c = canvas.Canvas("examples/sample.pdf")
c.drawString(100, 800, "Document Q&A Sample PDF")
c.drawString(100, 780, "This document describes a fictional product.")
c.save()
```

And a DOCX using python-docx:

```
from docx import Document
D = Document()
D.add_heading('Sample Document', 0)
D.add_paragraph('This DOCX is used for testing the parser and chunker.')
D.save('examples/sample.docx')
```
