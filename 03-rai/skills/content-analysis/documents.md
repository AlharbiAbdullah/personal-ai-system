# Documents

Process documents across four major formats. Create new documents,
extract content from existing ones, fill forms, and convert between formats.

## Supported Formats

| Format | Create | Read/Extract | Edit | Form Fill |
|--------|--------|-------------|------|-----------|
| DOCX | Yes | Yes | Yes | N/A |
| PDF | Limited | Yes | Limited | Yes |
| PPTX | Yes | Yes | Yes | N/A |
| XLSX | Yes | Yes | Yes | N/A |

## Operations

### Creation
- DOCX: Use python-docx. Headings, paragraphs, tables, images, styles.
- PPTX: Use python-pptx. Slides, layouts, text, charts, images.
- XLSX: Use openpyxl. Sheets, formulas, charts, formatting.
- PDF: Use reportlab for generation, or convert from DOCX.

### Extraction
- PDF: Use pdfplumber for text, tables. PyMuPDF for images.
- DOCX: Use python-docx for structured content.
- PPTX: Use python-pptx for slide text and notes.
- XLSX: Use openpyxl for cell data and formulas.

### Form Filling
- PDF forms: Use PyMuPDF or pdfrw to fill form fields.
- Identify field names first, then populate values.

## Best Practices

- **DOCX**: Use styles, not direct formatting. Keeps documents consistent.
- **PDF**: Extract with pdfplumber for tables, PyMuPDF for mixed content.
- **PPTX**: Start from a template when possible. Respect slide master.
- **XLSX**: Named ranges over cell references. Preserve formulas on edit.
- **All formats**: Save output to ~/Downloads/ with descriptive filenames.

## Process

1. **Identify format and operation**: What format, what action
2. **Read existing file** (if editing): Extract current content/structure
3. **Perform operation**: Create, edit, extract, or fill
4. **Save output**: Write to ~/Downloads/[name].[ext]
5. **Confirm**: Report what was done, file path, page/slide count

## Examples

- "Create a DOCX report with these sections and tables"
- "Extract all tables from this PDF"
- "Fill out this PDF form with these values"
- "Convert this PPTX slide text to markdown"

## Scope vs content-analysis

This skill is for format-level document manipulation (extract text, fill forms, convert formats) using python-docx, pdfplumber, python-pptx, openpyxl. For pattern-driven extraction (named Fabric patterns), use /content-analysis/fabric. For entity JSON extraction, use /content-analysis/parser. For semantic insight mining, use /research/extract-wisdom.
