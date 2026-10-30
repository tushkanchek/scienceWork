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
    "price": ROOT / "figures/distributions.png",
    "correlations": ROOT / "figures/correlations.png",
    "coefficients": ROOT / "figures/effects.png",
    "residuals": ROOT / "figures/diagnostics.png",
    "validation": ROOT / "figures/validation.png",
}
BRAND = {
    "sidebar_background": ASSETS / "reference_sidebar.png",
    "sidebar": ASSETS / "sidebar_with_kfu.png",
    "main_white": ASSETS / "kfu_main_white.png",
    "shield_white": ASSETS / "kfu_shield_white.png",
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
    slide.picture("rId2", BRAND["sidebar"], 0, 0, 1.21, 7.5, "Blue sidebar")
    slide.text(1.30, 0.03, 11.80, 0.62, title, 25, INK, True, valign="t", name="Slide title")


def add_rule(slide, x, y, w, color=GRAY, thickness=0.012):
    slide.rect(x, y, w, thickness, color, name="Table separator")


def create_slides():
    import pandas as pd
    import matplotlib.pyplot as plt
    data = ROOT / 'results'
    fit = pd.read_csv(data/'model_comparison.csv').set_index('model')
    tests = pd.read_csv(data/'joint_tests.csv').set_index('test')
    coef = pd.read_csv(data/'main_coefficients.csv').set_index('term')
    cv = pd.read_csv(data/'cv_metrics.csv').set_index('model')
    sensitivity = pd.read_csv(data/'sensitivity.csv').set_index('term')
    time_check = pd.read_csv(data/'time_sensitivity.csv').set_index('model')
    def num(x, digits=3):
        return f'{x:.{digits}f}'.replace('.', ',')

    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':13})
    terms=['ln_customers','ln_comp_1','ln_comp_2','ln_comp_3']
    labels=['Покупатели','Конкурент 1','Конкурент 2','Конкурент 3']
    fig,ax=plt.subplots(figsize=(8,4.5))
    for i,term in enumerate(terms):
        r=sensitivity.loc[term]
        ax.plot([r['min'],r['max']],[i,i],color='#00467C',lw=4)
        ax.scatter([r['full']],[i],s=80,color='#DA8D24',zorder=3)
    ax.set_yticks(range(4),labels);ax.invert_yaxis()
    ax.set(xlabel='Коэффициент: точка — вся выборка, линия — диапазон исключений',xlim=(0,.8))
    ax.grid(axis='x',alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.tight_layout();fig.savefig(ASSETS/'sensitivity_for_slides.png',dpi=180,bbox_inches='tight');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.4))
    names=['Среднее обучения','6 факторов','6 факторов + категория','9 факторов + категория']
    vals=cv.loc[['Mean','M1','M2','M3'],'rmse'].to_numpy()
    ax.barh(range(4),vals,color=['#A8B3BE','#6C9EC2','#00467C','#6C9EC2'],height=.58)
    for i,v in enumerate(vals):ax.text(v+.015,i,num(v),va='center',fontsize=14,fontweight='bold')
    ax.set_yticks(range(4),names);ax.invert_yaxis();ax.set_xlim(0,1.4)
    ax.set_xlabel('RMSE логарифма на исключённых товарах — меньше лучше')
    ax.spines[['top','right']].set_visible(False);fig.tight_layout()
    fig.savefig(ASSETS/'validation_for_slides.png',dpi=180,bbox_inches='tight');plt.close(fig)
    slides=[]
    def body(title):
        s=Slide();add_body_title(s,title);return s
    def finish(s,image=None,hidden=False):
        if hidden:s.root.set('show','0')
        rels=[('rId2','sidebar_with_kfu.png')]
        if image:rels.append(('rId3',image))
        slides.append((s,rels))
    def pair(s,y,heading,text):
        s.text(1.55,y,10.9,.40,heading,19,BLUE,True)
        s.text(1.55,y+.49,10.9,.80,text,17,INK,valign='t')
    def foot(s,text):s.text(1.55,6.62,10.95,.43,text,13,MUTED)

    s=Slide(NAVY)
    s.text(.4,1.4,5.4,5.5,'∫',400,'2479B7',alpha=25000,font='Times New Roman')
    s.text(7.3,1.65,5.2,4.8,'R²',250,'2479B7',alpha=26000,font='Times New Roman')
    s.picture('rId2',BRAND['main_white'],4.10,.54,5.15,.88,'KFU standard logo')
    s.rect(2.88,2.96,7.58,.025,WHITE)
    s.text(1.10,3.28,11.15,1.12,'Анализ данных розничной торговли\nс помощью множественной регрессии',25,WHITE,align='ctr',font='Times New Roman')
    s.text(1.3,4.72,10.7,.85,'Какие факторы связаны с суммой продаж\nи помогает ли расширение модели предсказывать её?',18,WHITE,align='ctr')
    s.text(1.2,6.24,10.9,.65,'Кибардин Максим Олегович · группа 05-308\nНаучный руководитель: Р. Ф. Салимов · Казань, 2026',14,WHITE,align='ctr')
    slides.append((s,[('rId2','kfu_main_white.png')]))

    s=body('1. Проверены данные и уточнён смысл отклика')
    s.text(1.5,.90,11.0,.48,'676 строк · 52 товара · 9 категорий · январь 2017 — август 2018',18,INK,True)
    s.picture('rId3',CHARTS['price'],1.40,1.62,7.65,3.66,'Sales distributions')
    s.text(9.30,1.70,3.4,.44,'Что проверено',20,BLUE,True)
    s.text(9.30,2.35,3.4,2.1,'Пропуски и дубли: 0.\nПроверены даты\nи ключ «товар–месяц».\n\nВсе строки сохранены.',17,INK,valign='t')
    s.text(1.55,5.55,10.95,.63,'total_price ≈ цена единицы × количество → изучаем сумму продаж за месяц.',18,BLUE,True)
    s.text(1.55,6.23,10.95,.48,'Логарифм сжимает правый хвост и позволяет описывать относительные связи.',16,INK)
    finish(s,'image_price_distribution.png')

    s=body('2. Исследованы связи и выбран набор факторов')
    s.picture('rId3',CHARTS['correlations'],1.45,1.15,5.55,5.22,'Correlation matrix')
    x=7.30;w=5.25
    s.text(x,1.13,w,.45,'Что показал предварительный анализ',18,BLUE,True)
    s.text(x,1.76,w,1.14,'Покупатели и сумма продаж: r = 0,43.\nВес и объём: r = 0,64.\nПарные связи требуют проверки в общей модели.',17,valign='t')
    s.text(x,3.12,w,.42,'Что включено в исследование',18,BLUE,True)
    s.text(x,3.75,w,1.34,'9 числовых факторов:\nпокупатели; 3 цены конкурентов;\nвес, объём, фотографии, рейтинг, доставка.\nДополнительно — категория товара.',16.5,valign='t')
    s.text(x,5.36,w,.95,'Цена единицы и количество исключены:\nони почти арифметически восстанавливают отклик.',16,INK,valign='t')
    foot(s,'Тепловая карта описывает парные корреляции, а не причинные эффекты и не значимость коэффициентов.')
    finish(s,'image_predictor_correlations.png')

    s=body('3. Сравнены три варианта множественной регрессии')
    s.text(1.5,.96,11.0,.45,'Одна выборка и один отклик. Меняем только состав объясняющих факторов.',18,BLUE,True)
    rows=[('Вариант','Что добавлено','R² скорр.'),
          ('Базовая (M1)','Покупатели, 3 цены, вес, фото',num(fit.loc['M1','adjusted_r2'])),
          ('С категориями (M2)','8 индикаторов категории',num(fit.loc['M2','adjusted_r2'])),
          ('Расширенная (M3)','Рейтинг, объём и доставка',num(fit.loc['M3','adjusted_r2']))]
    for i,row in enumerate(rows):
        y=1.84+i*.67
        for xx,ww,t in zip([1.5,5.5,10.7],[3.8,5.0,1.8],row):s.text(xx,y,ww,.49,t,17,INK,i==0)
        add_rule(s,1.5,y+.55,11)
    s.text(1.55,4.82,10.95,.78,'Категория улучшила подгонку: 0,305 → 0,361.\nТри новых признака повысили её до 0,379.',20,BLUE,True)
    s.text(1.55,5.84,10.95,.50,'ln(Y) = b₀ + b₁x₁ + … + b₉x₉ + эффекты категории + ε',19,BLUE,True)
    s.text(1.55,6.33,10.95,.30,'Y — сумма продаж; b — коэффициенты; x — факторы (шкалы на слайде 5); ε — ошибка.',13)
    foot(s,'Оценивание — МНК; ошибки по товару. R² описывает подгонку; проверка предсказаний — слайд 7.')
    finish(s)

    s=body('4. Проверено, какие связи сохраняются в общей модели')
    labelmap={'ln_customers':'ln покупателей','ln_comp_1':'ln цены конкурента 1','ln_comp_2':'ln цены конкурента 2',
              'ln_comp_3':'ln цены конкурента 3','ln_product_weight_g':'ln веса','product_photos_qty':'Фотографии',
              'product_score':'Рейтинг','ln_volume':'ln объёма','freight_price':'Доставка'}
    for xx,ww,t in [(1.5,3.1,'Фактор'),(4.7,1.3,'Коэфф.'),(6.15,1.6,'p Холма')]:s.text(xx,1.12,ww,.45,t,17,INK,True)
    add_rule(s,1.5,1.65,6.2)
    for i,(term,label) in enumerate(labelmap.items()):
        r=coef.loc[term];y=1.79+i*.43
        value=num(r.coef) if abs(r.coef)>=.0005 else '≈ 0'
        pv='< 0,001' if r.p_holm<.001 else num(r.p_holm)
        for xx,ww,t in [(1.5,3.1,label),(4.7,1.3,value),(6.15,1.6,pv)]:s.text(xx,y,ww,.37,t,16,BLUE if r.p_holm<.05 else INK,r.p_holm<.05)
    s.text(8.12,1.13,4.48,.80,'Цены конкурентов:\nсовместная связь есть',20,BLUE,True)
    s.text(8.12,2.15,4.48,.48,'F(3, 51) = '+num(tests.loc['competitors','F'],2)+'; p = '+num(tests.loc['competitors','p']),17)
    s.text(8.12,2.94,4.48,1.00,'Отдельный конкурент\nпосле 9 проверок с Холмом\nне выделяется.',18,valign='t')
    s.text(8.12,4.36,4.48,1.12,'Покупатели +10% →\nоценка суммы продаж +6,8%*\nВес: p Холма = '+num(coef.loc['ln_product_weight_g','p_holm'])+' — на границе.',17,valign='t')
    s.text(1.55,6.10,10.95,.79,'ln — натуральный логарифм; остальные факторы в исходной шкале. Результаты основной M3.\n* Геометрическое среднее при прочих равных. Чувствительность к времени — следующий слайд.',15,MUTED)
    finish(s)

    s=body('5. Проверена устойчивость к товарам и времени')
    s.picture('rId3',ASSETS/'sensitivity_for_slides.png',1.40,1.35,7.30,4.80,'Sensitivity to removing a product')
    x=8.95;w=3.78
    s.text(x,1.32,w,.58,'Добавлены 19 месяцев',19,BLUE,True)
    s.text(x,2.08,w,1.18,'Конкуренты совместно:\nM3: p = '+num(time_check.loc['M3','competitors_p'])+'\nС месяцами: p = '+num(time_check.loc['M3_time','competitors_p']),18,valign='t')
    s.text(x,3.63,w,1.08,'Вес: p после Холма\n'+num(time_check.loc['M3','weight_p_holm'])+' → '+num(time_check.loc['M3_time','weight_p_holm']),18,INK,True,valign='t')
    s.text(x,5.01,w,1.12,'При учёте времени\nвывод на уровне 5%\nне сохраняется.',18,BLUE,True,valign='t')
    s.text(1.55,6.44,10.95,.64,'Слева — диапазоны оценок при 52 исключениях товара, не доверительные интервалы.\nСправа — та же выборка с календарными эффектами; это не доказательство отсутствия связи.',14,MUTED)
    finish(s,'image_sensitivity_slides.png')

    s=body('6. Качество проверено на товарах вне обучения')
    s.text(1.55,.97,10.95,.47,'5 частей по товарам: ни одна строка проверяемого товара не участвует в обучении.',17,BLUE,True)
    s.picture('rId3',ASSETS/'validation_for_slides.png',1.38,1.82,7.55,4.29,'RMSE: '+', '.join(name+'='+num(cv.loc[name,'rmse']) for name in ['Mean','M1','M2','M3']))
    s.text(9.16,1.86,3.55,.48,'С чем сравнивали',19,BLUE,True)
    s.text(9.16,2.57,3.55,1.15,'Простой прогноз среднего\nи три регрессии —\nна одних и тех же\nисключённых товарах.',17,valign='t')
    s.text(9.16,4.13,3.55,1.25,'Модель с категориями\nимеет RMSE 1,030.\nРасширенная — 1,033:\nвыигрыша не получено.',18,INK,True,valign='t')
    s.text(1.55,6.15,10.95,.81,'Рост подгонки не перешёл в улучшение предсказания на выбранном разбиении.\nОшибки на шкале логарифма. Проверка не относится к будущим месяцам.',16,MUTED)
    finish(s,'image_validation_slides.png')

    s=body('Итоги: что сделано и что удалось установить')
    pair(s,1.04,'Подготовлена воспроизводимая модель розничных продаж','Проверены 30 столбцов; сохранены 676 строк.\nСравнены 6 факторов, добавление категории и расширение до 9 факторов.')
    pair(s,2.66,'Связь конкурентных цен чувствительна к учёту времени','Основная M3: p = '+num(time_check.loc['M3','competitors_p'])+'; с 19 месяцами: p = '+num(time_check.loc['M3_time','competitors_p'])+'.\nСовместная значимость на уровне 5% не сохраняется в календарном расширении.')
    pair(s,4.28,'Дополнительные признаки не улучшили предсказание','С рейтингом, объёмом и доставкой RMSE 1,033 против 1,030 без них.\nНа выбранном разбиении расширение модели себя не оправдало.')
    s.text(1.55,6.06,10.95,.55,'Ограничения: 52 товара; возможны общие ошибки категории и месяца. Выводы — о связях.',14,MUTED)
    s.text(1.55,6.79,10.95,.36,'Спасибо за внимание!',18,BLUE,True,align='r')
    finish(s)

    s=body('Резерв: как проверяются коэффициенты')
    pair(s,1.03,'Шкалы числовых факторов','Логарифмы: покупатели, 3 цены, вес, объём. В уровнях: фото, рейтинг, доставка.')
    pair(s,2.40,'Индивидуальная проверка','t = b / SEcluster; b — оценка коэффициента, SEcluster — её кластерная ошибка.')
    pair(s,3.77,'Почему поправка Холма?','9 индивидуальных проверок. Поправка учитывает риск хотя бы одного ложного отклонения.')
    pair(s,5.14,'Что проверяет совместный F-критерий?','Гипотезу о трёх одновременно нулевых коэффициентах, а не каждого отдельно.')
    finish(s,hidden=True)
    s=body('Резерв: диагностика и ограничения')
    s.picture('rId3',CHARTS['residuals'],1.35,1.18,11.25,3.37,'Residual diagnostics')
    s.text(1.55,4.86,10.95,.69,'VIF первого конкурента = 7,16: разделение индивидуальных связей затруднено.\nКвадрат логарифма покупателей: p = 0,202; конкретная кривизна не подтверждена.',16.5)
    s.text(1.55,5.95,10.95,.91,'Кластеризация по товару не покрывает все общие ошибки разных товаров.\nОстатки асимметричны; причинность, оптимальные цены и будущий прогноз не установлены.',16,MUTED)
    finish(s,'image_residuals.png',hidden=True)
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


def create_sidebar_asset():
    from PIL import ImageDraw

    bg = Image.open(BRAND["sidebar_background"]).convert("RGBA")
    shield = Image.open(BRAND["shield_white"]).convert("RGBA")
    shield.thumbnail((132, 156), Image.Resampling.LANCZOS)
    x = (bg.width - shield.width) // 2
    bg.alpha_composite(shield, (x, 34))
    draw = ImageDraw.Draw(bg)
    draw.line((46, 238, bg.width - 46, 238), fill=(183, 198, 212, 255), width=3)
    bg.convert("RGB").save(BRAND["sidebar"])


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
        "sidebar_with_kfu.png": BRAND["sidebar"],
        "kfu_main_white.png": BRAND["main_white"],
        "image_price_distribution.png": CHARTS["price"],
        "image_predictor_correlations.png": CHARTS["correlations"],
        "image_coefficients.png": CHARTS["coefficients"],
        "image_residuals.png": CHARTS["residuals"],
        "image_validation.png": CHARTS["validation"],
        "image_sensitivity_slides.png": ASSETS / "sensitivity_for_slides.png",
        "image_validation_slides.png": ASSETS / "validation_for_slides.png",
    }
    for name, path in media.items():
        entries[f"ppt/media/{name}"] = path.read_bytes()

    app_path = "docProps/app.xml"
    if app_path in entries:
        app = etree.fromstring(entries[app_path])
        for node in app:
            if node.tag.endswith("}Slides"):
                node.text = str(len(slides))
            elif node.tag.endswith("}HiddenSlides"):
                node.text = str(sum(slide.root.get("show") == "0" for slide, _ in slides))
        entries[app_path] = etree.tostring(app, xml_declaration=True, encoding="UTF-8", standalone=True)

    core_path = "docProps/core.xml"
    if core_path in entries:
        core = etree.fromstring(entries[core_path])
        for el in core:
            if el.tag.endswith("}title"):
                el.text = "Анализ данных розничной торговли с помощью множественной регрессии"
            elif el.tag.endswith("}subject"):
                el.text = "Презентация к курсовой работе"
        entries[core_path] = etree.tostring(core, xml_declaration=True, encoding="UTF-8", standalone=True)

    with ZipFile(TMP_PPTX, "w", ZIP_DEFLATED) as target:
        for name, data in entries.items():
            target.writestr(name, data)
    os.replace(TMP_PPTX, PPTX)


def main():
    required = [PPTX, *CHARTS.values(), BRAND["sidebar_background"], BRAND["main_white"], BRAND["shield_white"]]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
    create_sidebar_asset()
    rebuild_package(create_slides())
    print(f"Updated {PPTX.name} with 8 main slides and 2 hidden backup slides in the reference style.")


if __name__ == "__main__":
    main()
