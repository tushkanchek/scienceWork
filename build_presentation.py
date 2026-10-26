"""Rebuild the five-minute presentation from the current regression results."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import os

from lxml import etree
from PIL import Image


ROOT = Path(__file__).resolve().parent
PPTX = ROOT / "presentation_5min.pptx"
TMP_PPTX = ROOT / "presentation_5min.build.pptx"
CHART_PRICE = ROOT / "price_distribution_simple.png"
CHART_COEFFICIENTS = ROOT / "coefficients_ci_simple.png"
CHART_RESIDUALS = ROOT / "residuals_simple.png"

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"p": P_NS, "a": A_NS, "r": R_NS}
EMU = 914400

NAVY = "07528B"
BLUE = "2878B8"
PALE_BLUE = "E8F2FA"
PALE = "F4F7FA"
INK = "17232E"
MUTED = "526575"
WHITE = "FFFFFF"
ACCENT = "8FC4EA"


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
    def _solid_fill(parent, color):
        solid = etree.SubElement(parent, q(A_NS, "solidFill"))
        etree.SubElement(solid, q(A_NS, "srgbClr"), val=color)

    def rect(self, x, y, w, h, color, rounded=False, name="Rectangle"):
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
        geom = etree.SubElement(sp_pr, q(A_NS, "prstGeom"), prst="roundRect" if rounded else "rect")
        etree.SubElement(geom, q(A_NS, "avLst"))
        self._solid_fill(sp_pr, color)
        line = etree.SubElement(sp_pr, q(A_NS, "ln"))
        etree.SubElement(line, q(A_NS, "noFill"))
        return sp

    def text(self, x, y, w, h, value, size=16, color=INK, bold=False,
             align="l", valign="ctr", fill=None, rounded=False,
             margin=0.08, name="Text"):
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
        geom = etree.SubElement(sp_pr, q(A_NS, "prstGeom"), prst="roundRect" if rounded else "rect")
        etree.SubElement(geom, q(A_NS, "avLst"))
        if fill:
            self._solid_fill(sp_pr, fill)
        else:
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
            props = etree.SubElement(
                run, q(A_NS, "rPr"), lang="ru-RU", sz=str(round(size * 100)),
                b="1" if bold else "0",
            )
            self._solid_fill(props, color)
            etree.SubElement(props, q(A_NS, "latin"), typeface="Arial")
            etree.SubElement(props, q(A_NS, "ea"), typeface="Arial")
            etree.SubElement(props, q(A_NS, "cs"), typeface="Arial")
            text_node = etree.SubElement(run, q(A_NS, "t"))
            text_node.set(q(XML_NS, "space"), "preserve")
            text_node.text = line_text
            etree.SubElement(para, q(A_NS, "endParaRPr"), lang="ru-RU", sz=str(round(size * 100)))
        return sp

    def picture(self, rel_id, filename, x, y, max_w, max_h, name):
        with Image.open(ROOT / filename) as im:
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
        etree.SubElement(self.root, q(P_NS, "clrMapOvr"))
        self.root[-1].append(etree.Element(q(A_NS, "masterClrMapping")))
        return etree.tostring(self.root, xml_declaration=True, encoding="UTF-8", standalone=True)


def add_brand(slide, page, section, title, subtitle):
    slide.rect(0, 0, 0.86, 7.5, NAVY, name="University blue sidebar")
    slide.text(0.08, 0.20, 0.70, 0.42, "КФУ", 16, WHITE, True, "ctr", name="KFU mark")
    slide.rect(0.16, 0.78, 0.54, 0.025, ACCENT, name="Sidebar separator")
    slide.text(0.10, 6.95, 0.65, 0.32, f"{page:02d}", 11, WHITE, True, "ctr", name="Slide number")
    slide.text(1.25, 0.22, 11.55, 0.28, section.upper(), 10, BLUE, True, name="Section")
    slide.text(1.25, 0.52, 11.55, 0.57, title, 25, INK, True, name="Slide title")
    slide.text(1.25, 1.04, 11.55, 0.29, subtitle, 12, MUTED, name="Slide subtitle")
    slide.rect(1.25, 1.39, 11.55, 0.035, BLUE, name="Title rule")


def add_metric(slide, x, value, label, w=2.55):
    slide.rect(x, 1.58, w, 0.80, PALE_BLUE, rounded=True, name="Data card")
    slide.text(x + 0.08, 1.61, w - 0.16, 0.38, value, 21, NAVY, True, "ctr", name="Metric")
    slide.text(x + 0.08, 1.99, w - 0.16, 0.29, label, 10.5, MUTED, False, "ctr", name="Metric label")


def create_slides():
    slides = []

    # 1. Cover
    s = Slide(NAVY)
    s.text(1.10, 0.58, 11.1, 0.34, "КАЗАНСКИЙ ФЕДЕРАЛЬНЫЙ УНИВЕРСИТЕТ", 15, WHITE, True, name="University")
    s.text(1.10, 0.94, 11.1, 0.32, "Институт математики и механики им. Н.И. Лобачевского", 12, ACCENT, name="Institute")
    s.rect(1.10, 1.48, 10.9, 0.045, ACCENT, name="Cover rule")
    s.text(1.10, 2.05, 11.0, 1.55,
           "Линейная регрессия для анализа факторов,\nсвязанных с ценой товара",
           32, WHITE, True, valign="ctr", name="Presentation title")
    s.text(1.12, 3.85, 10.7, 0.80,
           "Сравнение трёх цен конкурентов отдельно\nи в одной множественной модели",
           19, ACCENT, name="Research question")
    s.text(1.12, 6.23, 10.8, 0.44,
           "Максим Кибардин  ·  группа 05-308  ·  Казань, 2026",
           14, WHITE, name="Author")
    slides.append((s, []))

    # 2. Data and distribution graph
    s = Slide()
    add_brand(s, 2, "Данные", "Набор Retail Price", "676 наблюдений по товарам за 2017–2018 годы")
    add_metric(s, 1.25, "676", "наблюдений", 2.45)
    add_metric(s, 3.88, "52", "товара", 2.45)
    add_metric(s, 6.51, "2017–2018", "период данных", 2.55)
    add_metric(s, 9.24, "1 423 / 808", "средняя / медиана общей цены", 3.56)
    s.text(1.32, 2.48, 11.35, 0.34,
           "Отклик — total_price; факторы — число покупателей, вес и цены трёх конкурентов.",
           14, INK, name="Data variables")
    s.picture("rId2", "price_distribution_simple.png", 1.34, 2.86, 11.35, 3.94, "Price distribution")
    s.text(1.48, 6.84, 10.95, 0.27,
           "Логарифмирование сжимает длинный правый хвост общей цены.",
           11, MUTED, align="ctr", name="Histogram caption")
    slides.append((s, [("rId2", "image_price_distribution.png")]))

    # 3. Method: separate and joint specifications
    s = Slide()
    add_brand(s, 3, "Метод", "Две постановки одного вопроса", "Все модели оценены на одних и тех же 676 наблюдениях")
    s.rect(1.30, 1.62, 5.52, 1.08, PALE_BLUE, rounded=True, name="Separate models panel")
    s.text(1.47, 1.72, 5.18, 0.34, "1. По одному конкуренту", 17, NAVY, True, name="Separate models heading")
    s.text(1.47, 2.09, 5.18, 0.48,
           "Три модели: покупатели + вес + цена одного comp_j.", 14, INK, name="Separate models description")
    s.rect(7.06, 1.62, 5.70, 1.08, PALE_BLUE, rounded=True, name="Multiple model panel")
    s.text(7.23, 1.72, 5.34, 0.34, "2. Все три цены вместе", 17, NAVY, True, name="Multiple model heading")
    s.text(7.23, 2.09, 5.34, 0.48,
           "Одна множественная модель со всеми конкурентами.", 14, INK, name="Multiple model description")
    s.rect(1.30, 2.95, 11.46, 1.10, PALE, rounded=True, name="Model formulas panel")
    s.text(1.50, 3.04, 11.05, 0.89,
           "Отдельно: ln(total_price) ~ ln(customers) + ln(comp_j) + ln(weight)\n"
           "Вместе: ln(total_price) ~ ln(customers) + ln(comp_1) + ln(comp_2) + ln(comp_3) + ln(weight)",
           13, INK, name="Model formulas")
    card_y, card_h, card_w = 4.42, 1.48, 3.62
    for x, head, body in [
        (1.30, "Сравнение", "Для трёх отдельных моделей — скорректированный R²."),
        (5.22, "Коэффициенты", "p-value и 95%-ные интервалы; ошибки сгруппированы по товару."),
        (9.14, "Совместный тест", "F-тест проверяет общий вклад трёх цен конкурентов."),
    ]:
        s.rect(x, card_y, card_w, card_h, PALE_BLUE, rounded=True, name="Method card")
        s.text(x + 0.13, card_y + 0.10, card_w - 0.26, 0.34, head, 15, NAVY, True, name="Method card heading")
        s.text(x + 0.13, card_y + 0.50, card_w - 0.26, 0.82, body, 13, INK, name="Method card body")
    s.text(1.42, 6.20, 11.05, 0.45,
           "Кластеризация по 52 товарам учитывает повторные наблюдения одного товара.",
           13, MUTED, align="ctr", name="Cluster note")
    slides.append((s, []))

    # 4. Three one-competitor models
    s = Slide()
    add_brand(s, 4, "Сравнение моделей", "Каждый конкурент — сначала отдельно", "В каждой модели также учтены число покупателей и вес товара")
    col_x = 1.25
    widths = [2.55, 1.72, 1.74, 3.04, 2.30]
    headers = ["Цена конкурента", "Коэффициент", "p-value", "95%-ный интервал", "Скорр. R²"]
    y, h = 1.78, 0.67
    x = col_x
    for label, w in zip(headers, widths):
        s.text(x, y, w, h, label, 12.5, WHITE, True, "ctr", fill=NAVY, rounded=True, name="Comparison table header")
        x += w + 0.04
    rows = [
        ("comp_1", "0,364", "0,0134", "[0,079; 0,649]", "0,236"),
        ("comp_2", "0,669", "0,000028", "[0,377; 0,961]", "0,286"),
        ("comp_3", "0,526", "0,00048", "[0,243; 0,809]", "0,254"),
    ]
    for ri, row in enumerate(rows):
        y = 2.50 + ri * 0.84
        x = col_x
        fill = PALE_BLUE if ri % 2 == 0 else PALE
        for value, w in zip(row, widths):
            s.text(x, y, w, 0.72, value, 15, INK, ri == 1 and value == "comp_2", "ctr",
                   fill=fill, rounded=True, name="Comparison table cell")
            x += w + 0.04
    s.rect(1.36, 5.35, 11.31, 0.98, PALE_BLUE, rounded=True, name="Comparison takeaway panel")
    s.text(1.57, 5.46, 10.88, 0.72,
           "Во всех трёх моделях коэффициент положителен и значим на уровне 5%.\n"
           "Наибольший скорректированный R² — у модели с comp_2: 0,286.",
           16, NAVY, True, name="Comparison takeaway")
    s.text(1.50, 6.54, 10.98, 0.38,
           "Это сравнение подгонки на данной выборке, а не проверка точности прогноза на новых данных.",
           11.5, MUTED, align="ctr", name="Comparison caveat")
    slides.append((s, []))

    # 5. Multiple regression and coefficient plot
    s = Slide()
    add_brand(s, 5, "Множественная регрессия", "Все три цены конкурентов — вместе", "Каждый коэффициент показывает условную связь при фиксированных остальных факторах")
    s.picture("rId2", "coefficients_ci_simple.png", 1.18, 1.55, 7.12, 4.82, "Multiple regression coefficients")
    s.text(8.46, 1.55, 4.20, 0.42, "Индивидуально значимы", 16, WHITE, True, "ctr", fill=NAVY, rounded=True, name="Significance heading")
    s.text(8.46, 2.02, 4.20, 1.12,
           "Покупатели: β=0,543; p<0,001\ncomp_2: β=0,532; p=0,011\nВес: β=0,135; p=0,037",
           14, INK, fill=PALE_BLUE, rounded=True, name="Significant coefficients")
    s.text(8.46, 3.27, 4.20, 0.84,
           "comp_1 (p=0,802) и comp_3 (p=0,253): индивидуальная связь не подтверждена.",
           13, INK, fill=PALE, rounded=True, name="Not individually significant")
    s.text(8.46, 4.22, 4.20, 0.86,
           "Три цены конкурентов совместно:\nF(3, 51)=10,58; p<0,001",
           14, NAVY, True, fill=PALE_BLUE, rounded=True, name="Joint competitor test")
    s.text(8.46, 5.19, 4.20, 0.98,
           "Вся модель: F(5, 51)=28,73; p<0,001\nR²=0,298; скорректированный R²=0,293",
           13, INK, fill=PALE, rounded=True, name="Overall model test")
    s.text(1.40, 6.48, 6.90, 0.40,
           "Точки — оценки; линии — кластерные 95%-ные доверительные интервалы.",
           11, MUTED, align="ctr", name="Coefficient plot caption")
    slides.append((s, [("rId2", "image_coefficients.png")]))

    # 6. Practical interpretation and limitations with residual plot
    s = Slide()
    add_brand(s, 6, "Интерпретация", "Что можно заключить — и где границы", "Оценки описывают связи в данных, а не причинное влияние")
    s.picture("rId2", "residuals_simple.png", 1.14, 1.58, 6.88, 4.20, "Residual plot")
    s.text(1.35, 5.82, 6.48, 0.58,
           "Разброс остатков неодинаков; график служит визуальной диагностикой, а не формальным тестом.",
           11.5, MUTED, align="ctr", name="Residual plot caption")
    s.text(8.24, 1.58, 4.48, 0.42, "Ограничения", 17, NAVY, True, name="Limitations heading")
    limitations = [
        "Данные наблюдательные: причинность не устанавливается.",
        "В выборке 52 товара за 2017–2018 годы.",
        "Не учтены сезонность, категория и часть характеристик.",
        "Нет проверки на новых наблюдениях.",
    ]
    for i, line in enumerate(limitations):
        s.text(8.24, 2.12 + i * 0.72, 4.48, 0.62, "• " + line, 12.5, INK,
               fill=PALE if i % 2 else PALE_BLUE, rounded=True, name="Limitation")
    s.text(8.24, 5.20, 4.48, 1.18,
           "При росте на 10% модельная оценка цены меняется примерно на: покупатели +5,3%, comp_2 +5,2%, вес +1,3% (при прочих равных).",
           12.5, NAVY, True, fill=PALE_BLUE, rounded=True, name="Ten percent interpretation")
    slides.append((s, [("rId2", "image_residuals.png")]))

    # 7. Conclusion
    s = Slide(NAVY)
    s.text(1.10, 0.70, 11.1, 0.38, "ИТОГ ИССЛЕДОВАНИЯ", 12, ACCENT, True, name="Conclusion section")
    s.text(1.10, 1.15, 11.0, 0.65, "Главный вывод", 30, WHITE, True, name="Conclusion title")
    s.rect(1.10, 1.95, 10.9, 0.04, ACCENT, name="Conclusion rule")
    s.text(1.12, 2.28, 10.8, 0.78,
           "По отдельности положительная связь обнаружена для всех трёх конкурентов.",
           21, WHITE, name="Conclusion point one")
    s.text(1.12, 3.20, 10.8, 1.10,
           "В общей модели индивидуально значим comp_2, а три цены конкурентов значимы совместно.",
           21, WHITE, name="Conclusion point two")
    s.text(1.12, 4.42, 10.8, 0.80,
           "Число покупателей и вес также положительно связаны с общей ценой.",
           20, WHITE, name="Conclusion point three")
    s.text(1.12, 5.44, 10.8, 0.60,
           "Это статистические связи; причинное влияние работа не устанавливает.",
           16, ACCENT, True, name="Conclusion limitation")
    s.text(1.12, 6.48, 10.8, 0.52, "Спасибо за внимание!", 27, WHITE, True, name="Thank you")
    slides.append((s, []))

    return slides


def slide_rels(images):
    root = etree.Element(q(PKG_REL_NS, "Relationships"), nsmap={None: PKG_REL_NS})
    for rel_id, target in images:
        etree.SubElement(root, q(PKG_REL_NS, "Relationship"),
                         Id=rel_id,
                         Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                         Target="../media/" + target)
    etree.SubElement(root, q(PKG_REL_NS, "Relationship"),
                     Id="rId1" if not images else "rId3",
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
        etree.SubElement(pres_rels, q(PKG_REL_NS, "Relationship"),
                         Id=f"rId{i+1}",
                         Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide",
                         Target=f"slides/slide{i}.xml")
    entries["ppt/_rels/presentation.xml.rels"] = etree.tostring(pres_rels, xml_declaration=True, encoding="UTF-8", standalone=True)

    content_types = etree.fromstring(entries["[Content_Types].xml"])
    existing_overrides = {el.get("PartName") for el in content_types.findall(q(CT_NS, "Override"))}
    for i in range(1, len(slides) + 1):
        part = f"/ppt/slides/slide{i}.xml"
        if part not in existing_overrides:
            etree.SubElement(content_types, q(CT_NS, "Override"),
                             PartName=part,
                             ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml")
    entries["[Content_Types].xml"] = etree.tostring(content_types, xml_declaration=True, encoding="UTF-8", standalone=True)

    for i, (slide, images) in enumerate(slides, start=1):
        entries[f"ppt/slides/slide{i}.xml"] = slide.bytes()
        entries[f"ppt/slides/_rels/slide{i}.xml.rels"] = slide_rels(images)

    entries["ppt/media/image_price_distribution.png"] = CHART_PRICE.read_bytes()
    entries["ppt/media/image_coefficients.png"] = CHART_COEFFICIENTS.read_bytes()
    entries["ppt/media/image_residuals.png"] = CHART_RESIDUALS.read_bytes()

    core_path = "docProps/core.xml"
    if core_path in entries:
        core = etree.fromstring(entries[core_path])
        for el in core:
            if el.tag.endswith("}title"):
                el.text = "Анализ розничных цен с помощью множественной регрессии"
            elif el.tag.endswith("}subject"):
                el.text = "Презентация к курсовой работе"
        entries[core_path] = etree.tostring(core, xml_declaration=True, encoding="UTF-8", standalone=True)

    with ZipFile(TMP_PPTX, "w", ZIP_DEFLATED) as target:
        for name, data in entries.items():
            target.writestr(name, data)
    os.replace(TMP_PPTX, PPTX)


def main():
    for path in (PPTX, CHART_PRICE, CHART_COEFFICIENTS, CHART_RESIDUALS):
        if not path.exists():
            raise FileNotFoundError(path)
    rebuild_package(create_slides())
    print(f"Updated {PPTX.name} with 7 slides.")


if __name__ == "__main__":
    main()
