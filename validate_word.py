"""Verify that the Word/TXT export is complete and matches current sources."""
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import re

from docx import Document
from lxml import etree

ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT / 'word_export_manifest.json').read_text())
for group in ['sources', 'outputs']:
    for name, digest in manifest[group].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, ('Stale export', name)
assert manifest['prose_segments_checked'] >= 300
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'}
tex = (ROOT / 'coursework.tex').read_text().split(r'\begin{document}', 1)[1]
with ZipFile(ROOT / manifest['docx']) as archive:
    assert archive.testzip() is None
    root = etree.fromstring(archive.read('word/document.xml'))
    formulas = root.xpath('//w:p[w:pPr/w:pStyle[@w:val="Equation"]]/m:oMath', namespaces=ns)
    assert len(formulas) == tex.count(r'\begin{equation}') == 17
    images = root.xpath('//w:drawing', namespaces=ns)
    assert len(images) == len(re.findall(r'\\resultfigure\{', tex)) == 7
    figures = re.findall(r'\\resultfigure\{([^{}]+)\}', tex)
    expected = {hashlib.sha256((ROOT / 'figures' / f'{name}.png').read_bytes()).hexdigest()
                for name in figures}
    embedded = {hashlib.sha256(archive.read(name)).hexdigest()
                for name in archive.namelist() if name.startswith('word/media/')}
    assert expected == embedded, 'Missing or changed embedded figures'
    assert len(root.xpath('//w:tbl', namespaces=ns)) == 15
    assert not root.xpath('//w:vanish|//w:del|//w:ins', namespaces=ns)
    assert not any(x in ''.join(root.xpath('//w:t/text()', namespaces=ns))
                   for x in [r'\resulttable', r'\workchapter', r'\begin{equation}'])
    fields = root.xpath('//w:fldSimple[starts-with(@w:instr,"PAGEREF ")]', namespaces=ns)
    assert len(fields) == 20, 'Incomplete contents'
doc = Document(ROOT / manifest['docx'])
assert doc.styles['Normal'].font.name == 'Times New Roman'
assert doc.styles['Normal'].font.size.pt == 14
assert doc.styles['Body Text'].paragraph_format.line_spacing == 1.5
assert doc.sections[0].different_first_page_header_footer
headings = [p.text for p in doc.paragraphs if p.style.name == 'Heading 1']
for letter in 'АБВГД':
    assert any(s.startswith(f'Приложение {letter}.') for s in headings)
assert 'СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ' in headings
code = [p.text for p in doc.paragraphs if p.style.name == 'Source Code']
assert len(code) == 8
for i, block in enumerate(code, 1):
    assert block.strip() == (ROOT / 'appendix' / f'code_{i:02}.py').read_text().strip(), i
plain = (ROOT / manifest['txt']).read_text()
for literal in ['0,061', '0,116', '1,033', 'Кибардин', 'Салимов']:
    assert literal in plain, literal
print('PASS: current Word/TXT sources and hashes, 17 editable display equations,')
print('15 tables, 7 identical embedded figures, 20 TOC entries, 8 unchanged code blocks;')
print(f'{manifest["prose_segments_checked"]} prose segments checked during export.')
print('No plagiarism or AI detection score was measured.')
