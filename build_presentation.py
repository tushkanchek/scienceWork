"""Rebuild the five-minute presentation in the style of the supplied KFU sample."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import os

from lxml import etree
from PIL import Image


ROOT = Path(__file__).resolve().parent
PPTX = ROOT / "presentation_5min.pptx"
TMP_PPTX = ROOT / "presentation_5min.build.pptx"
ASSETS = ROOT / "presentation_assets"
CHARTS = {
    "price": ROOT / "price_distribution_simple.png",
    "coefficients": ROOT / "coefficients_ci_simple.png",
    "residuals": ROOT / "residuals_simple.png",
}
BRAND = {
    "sidebar": ASSETS / "reference_sidebar.png",
    "kfu": ASSETS / "kfu_seal_white.png",
    "institute": ASSETS / "institute_mark_white.png",
}

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
XML_NS = "http://www.w3.org/XML/1998/namespace"
EMU = 914400

NAVY = "00467C"
BLUE = "1E6DA8"
GRAY = "B7C0C8"
INK = "111111"
MUTED = "454545"
WHITE = "FFFFFF"


def q(namespace, name):
    return f"{{{namespace}}}{name}"


class Slide:
    def __init__(self, background=WHITE):
        self.root = etree.Element(q(P_NS, "sld"), nsmap={"a": A_NS, "r": R_NS, "p": P_NS})
        c_sld = etree.SubElement(self.root, q(P_NS, "cSld"))
        bg = etree.SubElement(c_sld, q(P_NS, "bg"))
        bg_pr = etree.SubElement(bg, q(P_NS, "bgPr"))
        self._solid_fill(bg_pr, background)
        etree.SubElement(bg_pr, q(A_NS, "effectLst"))
        self.tree = etree.SubElement(c_sld, q(P_NS, "spTree"))
        nv = etree.SubElement(self.tree, q(P_NS, "nvGrpSpPr"))
        etree.SubElement(nv, q(P_NS, "cNvPr"), id="1", name="")
        etree.SubElement(nv, q(P_NS, "cNvGrpSpPr"))
        etree.SubElement(nv, q(P_NS, "nvPr"))
        grp = etree.SubElement(self.tree, q(P_NS, "grpSpPr"))
        xfrm = etree.SubElement(grp, q(A_NS, "xfrm"))
        etree.SubElement(xfrm, q(A_NS, "off"), x="0", y="0")
        etree.SubElement(xfrm, q(A_NS, "ext"), cx="0", cy="0")
        etree.SubElement(xfrm, q(A_NS, "chOff"), x="0", y="0")
        etree.SubElement(xfrm, q(A_NS, "chExt"), cx="0", cy="0")
        self.next_id = 2

    @staticmethod
    def _solid_fill(parent, color, alpha=None):
        solid = etree.SubElement(parent, q(A_NS, "solidFill"))
        rgb = etree.SubElement(solid, q(A_NS, "srgbClr"), val=color)
        if alpha is not None:
            etree.SubElement(rgb, q(A_NS, "alpha"), val=str(alpha))

    def rect(self, x, y, w, h, color, name="Rectangle"):
        sp = etree.SubElement(self.tree, q(P_NS, "sp"))
        nv = etree.SubElement(sp, q(P_NS, "nvSpPr"))
        etree.SubElement(nv, q(P_NS, "cNvPr"), id=str(self.next_id), name=name)
        etree.SubElement(nv, q(P_NS, "cNvSpPr"))
        etree.SubElement(nv, q(P_NS, "nvPr"))
        self.next_id += 1
        sp_pr = etree.SubElement(sp, q(P_NS, "spPr"))
        xfrm = etree.SubElement(sp_pr, q(A_NS, "xfrm"))
        etree.SubElement(xfrm, q(A_NS, "off"), x=str(round(x * EMU)), y=str(round(y * EMU)))
        etree.SubElement(xfrm, q(A_NS, "ext"), cx=str(round(w * EMU)), cy=str(round(h * EMU)))
        geom = etree.SubElement(sp_pr, q(A_NS, "prstGeom"), prst="rect")
        etree.SubElement(geom, q(A_NS, "avLst"))
        self._solid_fill(sp_pr, color)
        line = etree.SubElement(sp_pr, q(A_NS, "ln"))
        etree.SubElement(line, q(A_NS, "noFill"))

    def text(self, x, y, w, h, value, size=16, color=INK, bold=False,
             align="l", valign="ctr", font="Arial", alpha=None,
             margin=0.06, name="Text"):
        sp = etree.SubElement(self.tree, q(P_NS, "sp"))
        nv = etree.SubElement(sp, q(P_NS, "nvSpPr"))
        etree.SubElement(nv, q(P_NS, "cNvPr"), id=str(self.next_id), name=name)
        etree.SubElement(nv, q(P_NS, "cNvSpPr"), txBox="1")
        etree.SubElement(nv, q(P_NS, "nvPr"))
        self.next_id += 1
        sp_pr = etree.SubElement(sp, q(P_NS, "spPr"))
        xfrm = etree.SubElement(sp_pr, q(A_NS, "xfrm"))
        etree.SubElement(xfrm, q(A_NS, "off"), x=str(round(x * EMU)), y=str(round(y * EMU)))
        etree.SubElement(xfrm, q(A_NS, "ext"), cx=str(round(w * EMU)), cy=str(round(h * EMU)))
        geom = etree.SubElement(sp_pr, q(A_NS, "prstGeom"), prst="rect")
        etree.SubElement(geom, q(A_NS, "avLst"))
        etree.SubElement(sp_pr, q(A_NS, "noFill"))
        line = etree.SubElement(sp_pr, q(A_NS, "ln"))
        etree.SubElement(line, q(A_NS, "noFill"))
        body = etree.SubElement(sp, q(P_NS, "txBody"))
        body_pr = etree.SubElement(
            body, q(A_NS, "bodyPr"), wrap="square", anchor=valign,
            lIns=str(round(margin * EMU)), rIns=str(round(margin * EMU)),
            tIns=str(round(margin * EMU)), bIns=str(round(margin * EMU)),
        )
        etree.SubElement(body_pr, q(A_NS, "noAutofit"))
        etree.SubElement(body, q(A_NS, "lstStyle"))
        for line_text in str(value).split("\n"):
            para = etree.SubElement(body, q(A_NS, "p"))
            etree.SubElement(para, q(A_NS, "pPr"), algn=align)
            run = etree.SubElement(para, q(A_NS, "r"))
            props = etree.SubElement(run, q(A_NS, "rPr"), lang="ru-RU", sz=str(round(size * 100)), b="1" if bold else "0")
            self._solid_fill(props, color, alpha)
            for tag in ("latin", "ea", "cs"):
                etree.SubElement(props, q(A_NS, tag), typeface=font)
            node = etree.SubElement(run, q(A_NS, "t"))
            node.set(q(XML_NS, "space"), "preserve")
            node.text = line_text
            etree.SubElement(para, q(A_NS, "endParaRPr"), lang="ru-RU", sz=str(round(size * 100)))

    def picture(self, rel_id, asset, x, y, max_w, max_h, name):
        with Image.open(asset) as im:
            ratio = im.width / im.height
        w = min(max_w, max_h * ratio)
        h = w / ratio
        x += (max_w - w) / 2
        y += (max_h - h) / 2
        pic = etree.SubElement(self.tree, q(P_NS, "pic"))
        nv = etree.SubElement(pic, q(P_NS, "nvPicPr"))
        etree.SubElement(nv, q(P_NS, "cNvPr"), id=str(self.next_id), name=name)
        c_pic = etree.SubElement(nv, q(P_NS, "cNvPicPr"))
        etree.SubElement(c_pic, q(A_NS, "picLocks"), noChangeAspect="1")
        etree.SubElement(nv, q(P_NS, "nvPr"))
        self.next_id += 1
        blip_fill = etree.SubElement(pic, q(P_NS, "blipFill"))
        etree.SubElement(blip_fill, q(A_NS, "blip"), attrib={q(R_NS, "embed"): rel_id})
        stretch = etree.SubElement(blip_fill, q(A_NS, "stretch"))
        etree.SubElement(stretch, q(A_NS, "fillRect"))
        sp_pr = etree.SubElement(pic, q(P_NS, "spPr"))
        xfrm = etree.SubElement(sp_pr, q(A_NS, "xfrm"))
        etree.SubElement(xfrm, q(A_NS, "off"), x=str(round(x * EMU)), y=str(round(y * EMU)))
        etree.SubElement(xfrm, q(A_NS, "ext"), cx=str(round(w * EMU)), cy=str(round(h * EMU)))
        geom = etree.SubElement(sp_pr, q(A_NS, "prstGeom"), prst="rect")
        etree.SubElement(geom, q(A_NS, "avLst"))

    def bytes(self):
        clr = etree.SubElement(self.root, q(P_NS, "clrMapOvr"))
        etree.SubElement(clr, q(A_NS, "masterClrMapping"))
        return etree.tostring(self.root, xml_declaration=True, encoding="UTF-8", standalone=True)


def add_body_title(slide, title):
    slide.picture("rId2", BRAND["sidebar"], 0, 0, 1.21, 7.5, "KFU and institute sidebar")
    slide.text(1.30, 0.03, 11.80, 0.62, title, 25, INK, True, valign="t", name="Slide title")


def add_rule(slide, x, y, w, color=GRAY, thickness=0.012):
    slide.rect(x, y, w, thickness, color, name="Table separator")


def create_slides():
    slides = []

    # Cover: blue ground, mathematical watermark, and the reference KFU marks.
    s = Slide(NAVY)
    s.text(0.45, 1.35, 5.4, 5.5, "∫", 400, "2479B7", alpha=25000, font="Times New Roman", name="Cover watermark integral")
    s.text(7.35, 1.65, 5.2, 4.8, "R²", 250, "2479B7", alpha=26000, font="Times New Roman", name="Cover watermark R squared")
    s.picture("rId2", BRAND["kfu"], 4.70, 0.48, 1.35, 1.35, "KFU seal")
    s.rect(6.48, 0.58, 0.02, 1.08, WHITE, name="Cover logo divider")
    s.picture("rId3", BRAND["institute"], 7.02, 0.50, 1.42, 1.30, "Institute mark")
    s.rect(2.88, 2.96, 7.58, 0.025, WHITE, name="Cover separator")
    s.text(1.10, 3.32, 11.15, 1.03,
           "Линейная регрессия для анализа факторов,\nсвязанных с ценой товара",
           25, WHITE, align="ctr", font="Times New Roman", name="Presentation title")
    s.text(1.50, 4.62, 10.30, 0.76,
           "Сравнение трёх цен конкурентов отдельно\nи в одной множественной модели",
           17, WHITE, align="ctr", font="Times New Roman", name="Research question")
    s.text(1.20, 6.56, 10.95, 0.40,
           "Максим Кибардин  ·  группа 05-308  ·  Казань, 2026",
           14, WHITE, align="ctr", name="Author")
    slides.append((s, [("rId2", "kfu_seal_white.png"), ("rId3", "institute_mark_white.png")]))

    # Data and price distribution.
    s = Slide()
    add_body_title(s, "Данные набора Retail Price")
    s.text(1.40, 0.85, 11.25, 0.38,
           "676 наблюдений по 52 товарам · январь 2017 — август 2018",
           16, INK, True, name="Data summary")
    s.text(1.40, 1.28, 11.25, 0.40,
           "Средняя общая цена — 1 423; медиана — 808. Факторы: покупатели, вес и цены трёх конкурентов.",
           14, MUTED, name="Variables and summary statistics")
    s.picture("rId3", CHARTS["price"], 1.40, 1.80, 11.40, 4.62, "Price distribution")
    s.text(1.50, 6.52, 11.05, 0.32,
           "Логарифмирование сжимает длинный правый хвост общей цены.",
           13, MUTED, align="ctr", name="Histogram caption")
    slides.append((s, [("rId2", "reference_sidebar.png"), ("rId3", "image_price_distribution.png")]))

    # Method, in two columns and short table rows like the sample's content pages.
    s = Slide()
    add_body_title(s, "Схема исследования")
    s.text(1.42, 1.00, 5.25, 0.38, "Три модели по отдельности", 18, INK, True, name="Separate model heading")
    s.text(1.42, 1.47, 5.25, 0.67,
           "Покупатели + вес + цена одного конкурента.\nln(total_price) ~ ln(customers) + ln(comp_j) + ln(weight)",
           13.5, INK, name="Separate model formula")
    s.text(7.05, 1.00, 5.55, 0.38, "Множественная модель", 18, INK, True, name="Multiple model heading")
    s.text(7.05, 1.47, 5.55, 0.67,
           "Покупатели + вес + цены всех трёх конкурентов.\nДобавлены ln(comp_1), ln(comp_2) и ln(comp_3).",
           14, INK, name="Multiple model formula")
    add_rule(s, 1.40, 2.38, 11.35)
    rows = [
        ("Что сравниваю", "Скорректированный R² трёх отдельных моделей на одной выборке."),
        ("Коэффициенты", "p-value и 95%-ные доверительные интервалы; ошибки сгруппированы по товару."),
        ("Общий вклад", "Кластерный F-тест проверяет совместную значимость трёх цен конкурентов."),
    ]
    for i, (label, body) in enumerate(rows):
        y = 2.62 + i * 1.06
        s.text(1.48, y, 2.45, 0.55, label, 16, INK, True, name="Method row heading")
        s.text(4.05, y, 8.45, 0.62, body, 15, INK, name="Method row description")
        add_rule(s, 1.40, y + 0.78, 11.35)
    s.text(1.50, 6.12, 11.05, 0.42,
           "Во всех моделях одинаковые 676 наблюдений; ошибки кластеризованы по 52 товарам.",
           13, MUTED, align="ctr", name="Cluster note")
    slides.append((s, [("rId2", "reference_sidebar.png")]))

    # Three one-competitor models, shown as a plain table.
    s = Slide()
    add_body_title(s, "Сравнение трёх отдельных моделей")
    s.text(1.42, 0.82, 11.25, 0.40,
           "Во всех моделях учтены число покупателей и вес товара.",
           15, MUTED, name="Comparison description")
    x0 = 1.42
    widths = [2.42, 1.75, 1.70, 3.02, 2.20]
    headers = ["Конкурент", "Коэффициент", "p-value", "95%-ный интервал", "Скорр. R²"]
    x = x0
    for label, w in zip(headers, widths):
        s.text(x, 1.50, w, 0.45, label, 14, INK, True, name="Comparison table header")
        x += w
    add_rule(s, x0, 2.02, 11.10, "929292", 0.018)
    rows = [
        ("comp_1", "0,364", "0,0134", "[0,079; 0,649]", "0,236"),
        ("comp_2", "0,669", "0,000028", "[0,377; 0,961]", "0,286"),
        ("comp_3", "0,526", "0,00048", "[0,243; 0,809]", "0,254"),
    ]
    for i, row in enumerate(rows):
        y = 2.13 + i * 0.92
        x = x0
        for value, w in zip(row, widths):
            s.text(x, y, w, 0.56, value, 16, INK, (i == 1 and value == "comp_2"), name="Comparison table cell")
            x += w
        add_rule(s, x0, y + 0.69, 11.10, "D0D0D0", 0.012)
    s.text(1.48, 5.18, 11.0, 0.45,
           "Во всех трёх моделях связь положительная и значима на уровне 5%.",
           17, INK, True, name="Comparison conclusion one")
    s.text(1.48, 5.78, 11.0, 0.46,
           "Наибольший скорректированный R² — у модели с comp_2: 0,286.",
           17, INK, True, name="Comparison conclusion two")
    s.text(1.48, 6.50, 11.0, 0.36,
           "Это лучшая подгонка в данной выборке, но не проверка прогноза на новых данных.",
           13, MUTED, name="Comparison caveat")
    slides.append((s, [("rId2", "reference_sidebar.png")]))

    # Full model and coefficient intervals.
    s = Slide()
    add_body_title(s, "Множественная модель: все цены конкурентов вместе")
    s.text(1.40, 0.82, 11.25, 0.40,
           "Каждый коэффициент показывает условную связь при прочих равных.",
           15, MUTED, name="Multiple model description")
    s.picture("rId3", CHARTS["coefficients"], 1.25, 1.38, 7.25, 4.90, "Multiple regression coefficients")
    x, w = 8.72, 4.08
    s.text(x, 1.37, w, 0.38, "Значимы по отдельности", 17, INK, True, name="Significant heading")
    s.text(x, 1.83, w, 1.02,
           "Покупатели: β=0,543; p<0,001\ncomp_2: β=0,532; p=0,011\nВес: β=0,135; p=0,037",
           14, INK, name="Significant coefficients")
    add_rule(s, x, 2.94, w, "C0C0C0", 0.012)
    s.text(x, 3.09, w, 0.38, "Не подтверждены отдельно", 16, INK, True, name="Not significant heading")
    s.text(x, 3.52, w, 0.55,
           "comp_1 (p=0,802) и comp_3 (p=0,253): интервалы включают ноль.",
           13.5, INK, name="Not significant coefficients")
    add_rule(s, x, 4.18, w, "C0C0C0", 0.012)
    s.text(x, 4.32, w, 0.36, "Совместные тесты", 16, INK, True, name="Tests heading")
    s.text(x, 4.72, w, 1.12,
           "Конкуренты: F(3, 51)=10,58; p<0,001.\nМодель: F(5, 51)=28,73; p<0,001.\nR²=0,298; скорр. R²=0,293.",
           13.5, INK, name="Joint tests")
    s.text(1.40, 6.42, 7.15, 0.39,
           "Линии показывают кластерные 95%-ные доверительные интервалы.",
           12, MUTED, align="ctr", name="Coefficient plot caption")
    slides.append((s, [("rId2", "reference_sidebar.png"), ("rId3", "image_coefficients.png")]))

    # Limitations and practical interpretation, with residual diagnostic.
    s = Slide()
    add_body_title(s, "Интерпретация и ограничения")
    s.picture("rId3", CHARTS["residuals"], 1.22, 1.22, 6.86, 4.28, "Residual plot")
    s.text(1.38, 5.58, 6.52, 0.66,
           "Разброс остатков неодинаков. Это визуальная диагностика, а не формальный тест.",
           13, MUTED, align="ctr", name="Residual plot caption")
    x, w = 8.30, 4.48
    s.text(x, 1.28, w, 0.40, "Ограничения", 18, INK, True, name="Limitations heading")
    limits = [
        "Данные наблюдательные: причинность не устанавливается.",
        "52 товара и только период 2017–2018 годов.",
        "Не учтены сезонность, категории и другие факторы.",
        "Нет проверки модели на новых наблюдениях.",
    ]
    for i, line in enumerate(limits):
        s.text(x, 1.83 + i * 0.82, w, 0.68, "• " + line, 14.5, INK, name="Limitation")
        if i < len(limits) - 1:
            add_rule(s, x, 2.52 + i * 0.82, w, "D0D0D0", 0.010)
    s.text(x, 5.32, w, 1.17,
           "При росте на 10% модельная оценка цены меняется примерно на: покупатели +5,3%, comp_2 +5,2%, вес +1,3% (при прочих равных).",
           13.5, INK, True, name="Ten percent interpretation")
    slides.append((s, [("rId2", "reference_sidebar.png"), ("rId3", "image_residuals.png")]))

    # Closing, mirroring the sample's branded blue final slide.
    s = Slide(NAVY)
    s.text(0.25, 1.15, 5.3, 5.2, "∫", 390, "2479B7", alpha=25000, font="Times New Roman", name="Closing watermark integral")
    s.text(7.80, 1.25, 4.9, 4.7, "R²", 245, "2479B7", alpha=26000, font="Times New Roman", name="Closing watermark R squared")
    s.picture("rId2", BRAND["kfu"], 0.58, 0.42, 0.86, 0.88, "KFU seal")
    s.rect(1.58, 0.47, 0.018, 0.78, WHITE, name="Closing logo divider")
    s.picture("rId3", BRAND["institute"], 1.82, 0.48, 0.93, 0.78, "Institute mark")
    s.text(3.02, 0.52, 8.9, 0.65,
           "Линейная регрессия для анализа факторов, связанных с ценой товара",
           17, WHITE, font="Times New Roman", name="Closing running title")
    s.text(1.15, 3.00, 11.0, 0.80,
           "Спасибо за внимание!", 34, WHITE, True, align="ctr", font="Times New Roman", name="Thank you")
    s.text(1.15, 4.16, 11.0, 0.70,
           "Максим Кибардин\nСтудент группы 05-308",
           16, WHITE, align="ctr", font="Times New Roman", name="Author")
    slides.append((s, [("rId2", "kfu_seal_white.png"), ("rId3", "institute_mark_white.png")]))

    return slides


def slide_rels(images):
    root = etree.Element(q(PKG_REL_NS, "Relationships"), nsmap={None: PKG_REL_NS})
    for rel_id, target in images:
        etree.SubElement(root, q(PKG_REL_NS, "Relationship"), Id=rel_id,
                         Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                         Target="../media/" + target)
    etree.SubElement(root, q(PKG_REL_NS, "Relationship"), Id=f"rId{len(images) + 2}",
                     Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout",
                     Target="../slideLayouts/slideLayout1.xml")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def rebuild_package(slides):
    with ZipFile(PPTX, "r") as source:
        entries = {name: source.read(name) for name in source.namelist()}

    pres = etree.fromstring(entries["ppt/presentation.xml"])
    slide_list = pres.find(q(P_NS, "sldIdLst"))
    for child in list(slide_list):
        slide_list.remove(child)
    for i in range(1, len(slides) + 1):
        etree.SubElement(slide_list, q(P_NS, "sldId"), id=str(255 + i), attrib={q(R_NS, "id"): f"rId{i+1}"})
    entries["ppt/presentation.xml"] = etree.tostring(pres, xml_declaration=True, encoding="UTF-8", standalone=True)

    pres_rels = etree.fromstring(entries["ppt/_rels/presentation.xml.rels"])
    for rel in list(pres_rels):
        if rel.get("Type", "").endswith("/slide"):
            pres_rels.remove(rel)
    for i in range(1, len(slides) + 1):
        etree.SubElement(pres_rels, q(PKG_REL_NS, "Relationship"), Id=f"rId{i+1}",
                         Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide",
                         Target=f"slides/slide{i}.xml")
    entries["ppt/_rels/presentation.xml.rels"] = etree.tostring(pres_rels, xml_declaration=True, encoding="UTF-8", standalone=True)

    content_types = etree.fromstring(entries["[Content_Types].xml"])
    existing = {el.get("PartName") for el in content_types.findall(q(CT_NS, "Override"))}
    for i in range(1, len(slides) + 1):
        part = f"/ppt/slides/slide{i}.xml"
        if part not in existing:
            etree.SubElement(content_types, q(CT_NS, "Override"), PartName=part,
                             ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml")
    entries["[Content_Types].xml"] = etree.tostring(content_types, xml_declaration=True, encoding="UTF-8", standalone=True)

    for i, (slide, images) in enumerate(slides, start=1):
        entries[f"ppt/slides/slide{i}.xml"] = slide.bytes()
        entries[f"ppt/slides/_rels/slide{i}.xml.rels"] = slide_rels(images)

    media = {
        "reference_sidebar.png": BRAND["sidebar"],
        "kfu_seal_white.png": BRAND["kfu"],
        "institute_mark_white.png": BRAND["institute"],
        "image_price_distribution.png": CHARTS["price"],
        "image_coefficients.png": CHARTS["coefficients"],
        "image_residuals.png": CHARTS["residuals"],
    }
    for name, path in media.items():
        entries[f"ppt/media/{name}"] = path.read_bytes()

    core_path = "docProps/core.xml"
    if core_path in entries:
        core = etree.fromstring(entries[core_path])
        for el in core:
            if el.tag.endswith("}title"):
                el.text = "Линейная регрессия для анализа факторов, связанных с ценой товара"
            elif el.tag.endswith("}subject"):
                el.text = "Презентация к курсовой работе"
        entries[core_path] = etree.tostring(core, xml_declaration=True, encoding="UTF-8", standalone=True)

    with ZipFile(TMP_PPTX, "w", ZIP_DEFLATED) as target:
        for name, data in entries.items():
            target.writestr(name, data)
    os.replace(TMP_PPTX, PPTX)


def main():
    required = [PPTX, *CHARTS.values(), *BRAND.values()]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
    rebuild_package(create_slides())
    print(f"Updated {PPTX.name} with 7 slides in the reference style.")


if __name__ == "__main__":
    main()
