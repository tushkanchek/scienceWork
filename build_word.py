"""Export the current LaTeX report to DOCX and readable TXT; no external upload.

Requires python-docx and Pandoc (or pypandoc_binary). Pass --pandoc PATH when
Pandoc is installed outside PATH. Statistical results are read without changes.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.text.paragraph import Paragraph
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'coursework_check.docx'
TXT = ROOT / 'coursework_check.txt'
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'}


def pandoc_path(explicit: str | None) -> str:
    if explicit:
        return explicit
    found = shutil.which('pandoc')
    if found:
        return found
    try:
        import pypandoc
        return pypandoc.get_pandoc_path()
    except (ImportError, OSError):
        raise SystemExit('Install Pandoc or pypandoc_binary, or pass --pandoc PATH.')


def run(pandoc: str, *args: str, source: str = '') -> str:
    result = subprocess.run([pandoc, *args], input=source, text=True,
                            capture_output=True, cwd=ROOT, check=True)
    if result.stderr.strip():
        # Never silently deliver formulas that the converter could not handle.
        raise RuntimeError(result.stderr)
    return result.stdout


def prepare_source() -> tuple[str, dict]:
    tex = (ROOT / 'coursework.tex').read_text()
    body = tex[tex.index(r'\chapter*{Введение}'):tex.index(r'\end{document}')]
    refs, counts, equations = {}, {'table': 0, 'figure': 0, 'equation': 0}, []
    chapter, last = 0, None
    tokens = re.compile(
        r'\\workchapter\{(\d+)\.\}\{[^{}]+\}'
        r'|\\result(table|figure)\{([^{}]+)\}\{([^{}]+)\}\{([^{}]+)\}'
        r'|\\begin\{(table|figure|equation)\}'
        r'|\\label\{([^{}]+)\}')
    for match in tokens.finditer(body):
        if match[1]:
            chapter = int(match[1])
            counts = dict.fromkeys(counts, 0)
        elif match[2]:
            kind = match[2]
            counts[kind] += 1
            refs[match[5]] = f'{chapter}.{counts[kind]}'
        elif match[6]:
            kind = match[6]
            counts[kind] += 1
            last = f'{chapter}.{counts[kind]}'
            if kind == 'equation':
                equations.append(last)
        elif match[7]:
            refs[match[7]] = last

    def table(match):
        file, caption, label = match.groups()
        content = (ROOT / 'report_tables' / f'{file}.tex').read_text()
        return (f'\n\\begin{{table}}\n\\caption{{Таблица {refs[label]} --- {caption}}}\n'
                f'{content}\n\\end{{table}}\n')

    def figure(match):
        file, caption, label = match.groups()
        return (f'\n\\begin{{figure}}\n'
                f'\\includegraphics[width=16cm]{{figures/{file}.png}}\n'
                f'\\caption{{Рисунок {refs[label]} --- {caption}}}\n\\end{{figure}}\n')

    # Number the one table written directly in the report before expanding macros.
    def direct_table(match):
        text = match[0]
        label = re.search(r'\\label\{([^{}]+)\}', text)[1]
        return re.sub(r'\\caption\{([^{}]+)\}',
                      lambda m: f'\\caption{{Таблица {refs[label]} --- {m[1]}}}', text)

    body = re.sub(r'\\begin\{table\}.*?\\end\{table\}', direct_table, body, flags=re.S)
    body = re.sub(r'\\resulttable\{([^{}]+)\}\{([^{}]+)\}\{([^{}]+)\}', table, body)
    body = re.sub(r'\\resultfigure\{([^{}]+)\}\{([^{}]+)\}\{([^{}]+)\}', figure, body)
    body = re.sub(r'\\input\{(report_tables/[^{}]+)\}',
                  lambda m: (ROOT / m[1]).read_text(), body)

    def code(match):
        content = (ROOT / match[1]).read_text().rstrip('\n')
        assert r'\end{verbatim}' not in content
        return '\n\\begin{verbatim}\n' + content + '\n\\end{verbatim}\n'

    body = re.sub(r'\\VerbatimInput\[[^\]]*\]\{([^{}]+)\}', code, body)
    body = re.sub(r'\\(?:eqref|ref)\{([^{}]+)\}', lambda m: refs[m[1]], body)
    chapter, section = 0, 0

    def headings(match):
        nonlocal chapter, section
        if match[1]:
            chapter, section = int(match[1]), 0
            return f'\\chapter*{{{chapter} {match[2]}}}'
        section += 1
        return f'\\section*{{{chapter}.{section} {match[3]}}}'

    body = re.sub(r'\\workchapter\{(\d+)\.\}\{([^{}]+)\}|\\section\{([^{}]+)\}',
                  headings, body)
    body = re.sub(r'\\workappendix\{([^{}]+)\}\{([^{}]+)\}',
                  lambda m: f'\\chapter*{{Приложение {m[1]}. {m[2]}}}', body)
    body = re.sub(r'\\addcontentsline\{[^{}]+\}\{[^{}]+\}\{[^{}]+\}', '', body)
    body = body.replace(r'\clearpage', '\n\n')
    body = re.sub(r'(\\begin\{enumerate\})\[[^\]]*\]', r'\1', body)
    # texmath does not parse the old plain-TeX font switch inside mathop.
    body = body.replace(r'\mathop{\rm argmin}', r'\operatorname*{argmin}')
    return '\\documentclass{report}\n\\begin{document}\n' + body + '\n\\end{document}', {
        'equations': equations, 'references': refs}


def style_font(style, name='Times New Roman', size=14):
    style.font.name = name
    style.font.size = Pt(size)
    style.font.color.rgb = RGBColor(0, 0, 0)
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn('w:rFonts'))
    if fonts is None:
        fonts = OxmlElement('w:rFonts')
        rpr.insert(0, fonts)
    # Word theme fonts take precedence over explicit family names.
    for attribute in list(fonts.attrib):
        if attribute.rsplit('}', 1)[-1].lower().endswith('theme'):
            del fonts.attrib[attribute]
    for kind in ['ascii', 'hAnsi', 'eastAsia', 'cs']:
        fonts.set(qn(f'w:{kind}'), name)
    lang = OxmlElement('w:lang')
    lang.set(qn('w:val'), 'ru-RU')
    rpr.append(lang)


def reference_docx(path: Path):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin, sec.right_margin = Cm(3), Cm(1.5)
    sec.top_margin = sec.bottom_margin = Cm(2)
    for name in ['Normal', 'Body Text', 'First Paragraph', 'Compact']:
        if name not in doc.styles:
            doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        s = doc.styles[name]
        style_font(s)
        f = s.paragraph_format
        f.alignment, f.first_line_indent = WD_ALIGN_PARAGRAPH.JUSTIFY, Cm(1.25)
        f.line_spacing, f.space_before, f.space_after = 1.5, Pt(0), Pt(0)
        f.widow_control = True
    for level in [1, 2, 3]:
        s = doc.styles[f'Heading {level}']
        style_font(s)
        s.font.bold = True
        f = s.paragraph_format
        f.space_before, f.space_after = Pt(14), Pt(7)
        f.first_line_indent = Cm(1.25)
        f.line_spacing, f.keep_with_next = 1.5, True
        f.page_break_before = level == 1
    # Explicit cover emphasis, independent of the viewer's default body style.
    s = doc.styles.add_style('Cover Emphasis', WD_STYLE_TYPE.PARAGRAPH)
    s.base_style = doc.styles['Normal']
    style_font(s)
    s.font.bold = True
    s.font.cs_bold = True
    for name in ['Caption', 'Table Caption', 'Image Caption']:
        if name not in doc.styles:
            doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        s = doc.styles[name]
        style_font(s, size=12)
        s.font.italic = False
        f = s.paragraph_format
        f.first_line_indent, f.line_spacing = Cm(0), 1
        f.space_before, f.space_after = Pt(6), Pt(6)
    if 'Source Code' not in doc.styles:
        doc.styles.add_style('Source Code', WD_STYLE_TYPE.PARAGRAPH)
    s = doc.styles['Source Code']
    style_font(s, 'Courier New', 8)
    s.paragraph_format.first_line_indent = Cm(0)
    s.paragraph_format.line_spacing = 1
    s.paragraph_format.space_before = s.paragraph_format.space_after = Pt(0)
    doc.save(path)


def add_cover(doc):
    """Use the report's own editable metadata, with the supplied cover structure."""
    source = (ROOT / 'titlepage.tex').read_text()
    def value(name):
        s = re.search(r'\\newcommand\{\\' + name + r'\}\{([^{}]*)\}', source)[1]
        return re.sub(r'\\\\\s*', '\n', s.replace(r'\,', ' '))
    holder = Document()
    def para(text='', align=WD_ALIGN_PARAGRAPH.LEFT, bold=False, after=0, before=0):
        p = holder.add_paragraph()
        f = p.paragraph_format
        f.first_line_indent, f.line_spacing = Cm(0), 1.15
        f.space_before, f.space_after = Pt(before), Pt(after)
        f.keep_with_next, f.keep_together = True, True
        p.alignment = align
        r = p.add_run(text)
        r.font.name, r.font.size, r.bold = 'Times New Roman', Pt(14), bold
        r.font.cs_bold = bold
        fonts = r._r.get_or_add_rPr().find(qn('w:rFonts'))
        for kind in ['ascii', 'hAnsi', 'eastAsia', 'cs']:
            fonts.set(qn(f'w:{kind}'), 'Times New Roman')
        return p
    center = WD_ALIGN_PARAGRAPH.CENTER
    para('Министерство науки и высшего образования Российской Федерации\n'
         'Федеральное государственное автономное образовательное учреждение\n'
         'высшего образования «КАЗАНСКИЙ (ПРИВОЛЖСКИЙ)\n'
         'ФЕДЕРАЛЬНЫЙ УНИВЕРСИТЕТ»', center, True, after=32)
    para('ИНСТИТУТ МАТЕМАТИКИ И МЕХАНИКИ ИМ. Н.И. ЛОБАЧЕВСКОГО\n'
         'КАФЕДРА МАТЕМАТИЧЕСКОЙ СТАТИСТИКИ', center, after=32)
    para('Направление подготовки (специальность): 02.03.01 – Математика и компьютерные науки')
    para('Профиль (специализация): Наука о данных', after=58)
    para('КУРСОВАЯ РАБОТА', center, after=18)
    para(value('CourseworkTitle'), center, True, after=105)
    date = f'«____» __________ {value("CourseworkYear")} г.'
    para(f'Студент {value("CourseworkCourse")} курса')
    p = para(f'группы {value("CourseworkGroup")}\t{value("CourseworkStudent")}')
    p.paragraph_format.tab_stops.add_tab_stop(Cm(16.5), WD_TAB_ALIGNMENT.RIGHT)
    para(date, after=18)
    para('Научный руководитель')
    p = para(value('CourseworkSupervisorDegree') + '\t' + value('CourseworkSupervisor'))
    p.paragraph_format.tab_stops.add_tab_stop(Cm(16.5), WD_TAB_ALIGNMENT.RIGHT)
    para(date)
    p = para('Казань – ', center, before=90)
    p.add_run(value('CourseworkYear')).italic = True
    p.paragraph_format.keep_with_next = False
    holder.add_page_break()
    elements = [deepcopy(x) for x in holder.element.body if x.tag != qn('w:sectPr')]
    for element in reversed(elements):
        doc.element.body.insert(0, element)
    for paragraph in doc.paragraphs[:len(holder.paragraphs)]:
        if (paragraph.text.startswith('Министерство')
                or paragraph.text == value('CourseworkTitle')):
            paragraph.style = doc.styles['Cover Emphasis']


def fill_toc(doc):
    """Provide a readable TOC cache with real PAGEREF fields, not an empty TOC."""
    container = doc.element.body.xpath('.//w:sdtContent')[0]
    title = Paragraph(container[0], doc)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.first_line_indent = Cm(0)
    for run in title.runs:
        run.bold = True
        run.font.size = Pt(14)
        run.font.name = 'Times New Roman'
    field_paragraph = container[1]
    for end in field_paragraph.xpath('.//w:fldChar[@w:fldCharType="end"]'):
        end.getparent().remove(end)
    next_id = max([int(x.get(qn('w:id'))) for x in doc.element.body.xpath('.//w:bookmarkStart')]
                  + [0]) + 1
    headings = [p for p in doc.paragraphs if p.style.name in ['Heading 1', 'Heading 2']]
    for i, heading in enumerate(headings, next_id):
        bookmark = f'coursework_heading_{i}'
        start, end = OxmlElement('w:bookmarkStart'), OxmlElement('w:bookmarkEnd')
        start.set(qn('w:id'), str(i))
        start.set(qn('w:name'), bookmark)
        end.set(qn('w:id'), str(i))
        heading._p.insert(1 if heading._p.pPr is not None else 0, start)
        heading._p.append(end)
        element = OxmlElement('w:p')
        container.append(element)
        entry = Paragraph(element, doc)
        f = entry.paragraph_format
        f.first_line_indent, f.line_spacing = Cm(0), 1
        f.left_indent = Cm(0.7 if heading.style.name == 'Heading 2' else 0)
        f.space_before, f.space_after = Pt(0), Pt(5)
        f.tab_stops.add_tab_stop(Cm(16.5), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        entry.add_run(heading.text + '\t')
        page = OxmlElement('w:fldSimple')
        page.set(qn('w:instr'), f'PAGEREF {bookmark} \\h')
        page.set(qn('w:dirty'), 'true')
        entry._p.append(page)
    closing = OxmlElement('w:r')
    end_field = OxmlElement('w:fldChar')
    end_field.set(qn('w:fldCharType'), 'end')
    closing.append(end_field)
    container[-1].append(closing)


def postprocess(path: Path, equations: list[str]):
    doc = Document(path)
    doc.core_properties.title = 'Анализ данных розничной торговли с помощью множественной регрессии'
    doc.core_properties.author = 'Кибардин Максим Олегович'
    doc.core_properties.subject = 'Курсовая работа; Word-копия актуального LaTeX-отчёта'
    section = doc.sections[0]
    section.different_first_page_header_footer = True
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    if 'Equation' not in doc.styles:
        doc.styles.add_style('Equation', WD_STYLE_TYPE.PARAGRAPH)
    style_font(doc.styles['Equation'])
    numbers = iter(equations)
    for p in doc.paragraphs:
        if p.style.name == 'Heading 1':
            if not re.match(r'\d+ ', p.text):
                # Preserve appendix letters; uppercase only structural headings.
                if not p.text.startswith('Приложение'):
                    p.text = p.text.upper()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.first_line_indent = Cm(0)
        if p.style.name in ['Image Caption', 'Caption'] and p.text.startswith('Рисунок'):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if p.text.startswith('Таблица '):
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.keep_with_next = True
        if p._p.xpath('.//m:oMathPara'):
            p.style = doc.styles['Equation']
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.line_spacing = 1
            p.paragraph_format.tab_stops.add_tab_stop(Cm(8.25), WD_TAB_ALIGNMENT.CENTER)
            p.paragraph_format.tab_stops.add_tab_stop(Cm(16.5), WD_TAB_ALIGNMENT.RIGHT)
            # A standard Word equation paragraph: center tab, native math,
            # right tab and an ordinary text number. No fake math whitespace.
            wrapper = p._p.xpath('./m:oMathPara')[0]
            math = wrapper.find(qn('m:oMath'))
            before = OxmlElement('w:r')
            before.append(OxmlElement('w:tab'))
            position = list(p._p).index(wrapper)
            p._p.remove(wrapper)
            p._p.insert(position, before)
            p._p.insert(position + 1, math)
            p.add_run('\t(' + next(numbers) + ')')
        if p._p.xpath('.//w:drawing'):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.keep_with_next = True
    for table in doc.tables:
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for row_index, row in enumerate(table.rows):
            cant_split = OxmlElement('w:cantSplit')
            row._tr.get_or_add_trPr().append(cant_split)
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.first_line_indent = Cm(0)
                    p.paragraph_format.line_spacing = 1
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.keep_with_next = row_index < len(table.rows) - 1
                    for r in p.runs:
                        r.font.size = Pt(10)
        header = table.rows[0]._tr.get_or_add_trPr()
        repeat = OxmlElement('w:tblHeader')
        header.append(repeat)
    update = OxmlElement('w:updateFields')
    update.set(qn('w:val'), 'true')
    doc.settings.element.append(update)
    add_cover(doc)
    fill_toc(doc)
    doc.save(path)


def check_prose(ast: dict, path: Path) -> int:
    """Check every prose segment between formulas against actual DOCX text."""
    from zipfile import ZipFile
    from lxml import etree
    normalize = lambda s: re.sub(r'\s+', ' ', s).strip().casefold()
    with ZipFile(path) as archive:
        root = etree.fromstring(archive.read('word/document.xml'))
    text = normalize(' '.join(''.join(p.xpath('.//w:t/text()', namespaces=NS))
                              for p in root.xpath('//w:p', namespaces=NS)))
    checked = 0

    def fragments(inlines):
        for node in inlines:
            kind, content = node['t'], node.get('c')
            if kind == 'Str':
                yield content
            elif kind in ['Space', 'SoftBreak', 'LineBreak']:
                yield ' '
            elif kind == 'Code':
                yield content[1]
            elif kind in ['Strong', 'Emph', 'SmallCaps', 'Strikeout']:
                yield from fragments(content)
            elif kind in ['Span', 'Link', 'Quoted']:
                yield from fragments(content[1])
            else:
                yield None  # Math and images are verified separately.

    def visit(node):
        nonlocal checked
        if isinstance(node, list):
            for item in node:
                visit(item)
        elif isinstance(node, dict):
            if node.get('t') in ['Para', 'Plain', 'Header']:
                inlines = node['c'][2] if node['t'] == 'Header' else node['c']
                pending = ''
                for fragment in [*fragments(inlines), None]:
                    if fragment is None:
                        segment = normalize(pending)
                        if len(segment) >= 12:
                            assert segment in text, ('Missing DOCX prose:', segment[:180])
                            checked += 1
                        pending = ''
                    else:
                        pending += fragment
            else:
                for item in node.values():
                    visit(item)
    visit(ast['blocks'])
    return checked


def cache_page_references(path: Path, pdf: Path) -> None:
    """Populate TOC field results from a local layout preview, preserving fields."""
    extracted = subprocess.run(['pdftotext', '-layout', str(pdf), '-'], text=True,
                               capture_output=True, check=True).stdout
    normalize = lambda s: re.sub(r'\s+', ' ', s).strip().casefold()
    pages = [normalize(p) for p in extracted.split('\f')]
    doc = Document(path)
    headings = [p for p in doc.paragraphs if p.style.name in ['Heading 1', 'Heading 2']]
    fields = doc.element.body.xpath('.//w:fldSimple[starts-with(@w:instr,"PAGEREF ")]')
    assert len(fields) == len(headings)
    for heading, field in zip(headings, fields):
        matches = [i for i, text in enumerate(pages, 1)
                   if i > 2 and normalize(heading.text) in text]
        assert matches, ('Heading missing in layout preview:', heading.text)
        for child in list(field):
            field.remove(child)
        run_element, text = OxmlElement('w:r'), OxmlElement('w:t')
        text.text = str(matches[0])
        run_element.append(text)
        field.append(run_element)
    doc.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pandoc')
    parser.add_argument('--preview-pdf', type=Path,
                        help='Optional matching local Word preview to cache TOC page fields.')
    args = parser.parse_args()
    pandoc = pandoc_path(args.pandoc)
    source, metadata = prepare_source()
    ast = json.loads(run(pandoc, '-f', 'latex', '-t', 'json', source=source))
    display_count = 0

    # LaTeX may place a display and following prose in a single Pandoc paragraph.
    # Separate them so editable Word equations get a paragraph of their own.
    blocks = []
    for block in ast['blocks']:
        if block['t'] != 'Para':
            blocks.append(block)
            continue
        pending = []
        for inline in block['c']:
            if inline['t'] == 'Math' and inline['c'][0]['t'] == 'DisplayMath':
                if any(x['t'] not in ['Space', 'SoftBreak'] for x in pending):
                    blocks.append({'t': 'Para', 'c': pending})
                pending = []
                expression = inline['c'][1]
                inline['c'][1] = expression
                blocks.append({'t': 'Para', 'c': [inline]})
                display_count += 1
            else:
                pending.append(inline)
        if any(x['t'] not in ['Space', 'SoftBreak'] for x in pending):
            blocks.append({'t': 'Para', 'c': pending})
    assert display_count == len(metadata['equations']) == 17
    ast['blocks'] = blocks
    def compatible_math(node):
        if isinstance(node, list):
            for x in node:
                compatible_math(x)
        elif isinstance(node, dict):
            if node.get('t') == 'Math':
                expression = node['c'][1]
                threshold = re.fullmatch(r'\s*([<>])\s*(\d+)\{,\}(\d+)\s*', expression)
                if threshold:
                    # A p-value table cell such as '< 0,001' is ordinary text,
                    # not an equation with a missing left operand.
                    node.update(t='Str', c=f'{threshold[1]} {threshold[2]},{threshold[3]}')
                    return
                if r'\begin{split}' in expression:
                    expression = (expression.replace(r'\begin{split}', r'\begin{gathered}')
                                  .replace(r'\end{split}', r'\end{gathered}')
                                  .replace('&', '').replace('{}', ''))
                # Native delimiter objects also render correctly in LibreOffice.
                expression = re.sub(r'(?<!\\)\|([^|]+)\|',
                                    lambda m: r'\left\lvert ' + m[1] + r'\right\rvert ', expression)
                node['c'][1] = expression
            else:
                for x in node.values():
                    compatible_math(x)
    compatible_math(ast['blocks'])
    ast['meta']['lang'] = {'t': 'MetaString', 'c': 'ru-RU'}
    ast['meta']['toc-title'] = {'t': 'MetaString', 'c': 'СОДЕРЖАНИЕ'}
    ast_json = json.dumps(ast, ensure_ascii=False)
    with tempfile.TemporaryDirectory(prefix='coursework-word-') as temporary:
        reference = Path(temporary) / 'reference.docx'
        reference_docx(reference)
        run(pandoc, '-f', 'json', '-t', 'docx', '--standalone', '--toc', '--toc-depth=2',
            '--syntax-highlighting=none', '--reference-doc', str(reference),
            '--resource-path', str(ROOT), '-o', str(OUTPUT), source=ast_json)
    postprocess(OUTPUT, metadata['equations'])
    if args.preview_pdf:
        cache_page_references(OUTPUT, args.preview_pdf)
    prose_count = check_prose(ast, OUTPUT)
    # TXT retains all sections, bibliography and code. Complex formulas remain
    # explicit LaTeX text: plain text cannot preserve the native Word math layout.
    plain_ast = deepcopy(ast)
    def plain_math(node):
        if isinstance(node, list):
            for x in node:
                plain_math(x)
        elif isinstance(node, dict):
            if node.get('t') == 'Math':
                expression = node['c'][1]
                node.update(t='Code', c=[['', [], []], expression])
            else:
                for x in node.values():
                    plain_math(x)
    plain_math(plain_ast['blocks'])
    report_plain = run(pandoc, '-f', 'json', '-t', 'plain', '--wrap=none',
                       source=json.dumps(plain_ast, ensure_ascii=False))
    doc = Document(OUTPUT)
    cover = []
    for p in doc.paragraphs:
        if p.style.name == 'TOC Heading' or p.text == 'СОДЕРЖАНИЕ':
            break
        if p.style.name == 'Heading 1':
            break
        if p.text.strip():
            cover.append(p.text)
    plain = '\n'.join(cover) + '\n\n' + report_plain
    TXT.write_text(plain)
    sources = [ROOT / n for n in ['coursework.tex', 'titlepage.tex', 'build_word.py']]
    for directory in ['report_tables', 'appendix', 'figures']:
        sources.extend(sorted((ROOT / directory).glob('*')))
    manifest = {
        'docx': OUTPUT.name, 'txt': TXT.name,
        'pandoc': run(pandoc, '--version').splitlines()[0],
        'display_equations': display_count,
        'prose_segments_checked': prose_count,
        'sources': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sources if p.is_file()},
        'outputs': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUTPUT, TXT]},
        'note': 'Format export only; no plagiarism or AI detector was run.'}
    (ROOT / 'word_export_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f'Created {OUTPUT.name}: {OUTPUT.stat().st_size:,} bytes; {display_count} display equations.')
    print(f'Created {TXT.name}: {len(plain):,} characters; all report sections retained.')


if __name__ == '__main__':
    main()
