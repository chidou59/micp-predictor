from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    FrameBreak,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "MICP预测器使用教程.pdf"

PAGE_W, PAGE_H = A4

PALETTE = {
    "ink": colors.HexColor("#07211d"),
    "muted": colors.HexColor("#506961"),
    "soft": colors.HexColor("#7f9991"),
    "green": colors.HexColor("#0d2c25"),
    "teal": colors.HexColor("#2f7f82"),
    "blue": colors.HexColor("#4c6f85"),
    "amber": colors.HexColor("#a66d22"),
    "red": colors.HexColor("#a64235"),
    "bg": colors.HexColor("#eef4f1"),
    "panel": colors.HexColor("#fbfdfc"),
    "tint": colors.HexColor("#e7f1ee"),
    "line": colors.HexColor("#d6e3df"),
    "line_light": colors.HexColor("#e7eeeb"),
    "white": colors.white,
}


def register_fonts() -> tuple[str, str]:
    candidates = [
        (Path("C:/Windows/Fonts/Deng.ttf"), Path("C:/Windows/Fonts/Dengb.ttf")),
        (Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"), Path("C:/Windows/Fonts/NotoSansSC-VF.ttf")),
        (Path("C:/Windows/Fonts/simhei.ttf"), Path("C:/Windows/Fonts/simhei.ttf")),
    ]
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("CN-Regular", str(regular)))
            pdfmetrics.registerFont(TTFont("CN-Bold", str(bold)))
            return "CN-Regular", "CN-Bold"
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light", "STSong-Light"


FONT, FONT_BOLD = register_fonts()


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName=FONT_BOLD,
            fontSize=29,
            leading=37,
            textColor=PALETTE["ink"],
            alignment=TA_LEFT,
            wordWrap="CJK",
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=12.5,
            leading=19,
            textColor=PALETTE["muted"],
            wordWrap="CJK",
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName=FONT_BOLD,
            fontSize=19,
            leading=25,
            textColor=PALETTE["ink"],
            spaceBefore=10,
            spaceAfter=8,
            wordWrap="CJK",
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName=FONT_BOLD,
            fontSize=14.5,
            leading=20,
            textColor=PALETTE["ink"],
            spaceBefore=8,
            spaceAfter=6,
            wordWrap="CJK",
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=10.6,
            leading=16.2,
            textColor=PALETTE["ink"],
            wordWrap="CJK",
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=9.1,
            leading=13.2,
            textColor=PALETTE["muted"],
            wordWrap="CJK",
        ),
        "tiny": ParagraphStyle(
            "tiny",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=7.8,
            leading=10.5,
            textColor=PALETTE["muted"],
            wordWrap="CJK",
        ),
        "white": ParagraphStyle(
            "white",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=10.4,
            leading=15.5,
            textColor=colors.white,
            wordWrap="CJK",
        ),
        "white_bold": ParagraphStyle(
            "white_bold",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=16,
            leading=21,
            textColor=colors.white,
            wordWrap="CJK",
        ),
        "card_title": ParagraphStyle(
            "card_title",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=12.1,
            leading=16,
            textColor=PALETTE["ink"],
            wordWrap="CJK",
        ),
        "center": ParagraphStyle(
            "center",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=9.5,
            leading=13.2,
            textColor=PALETTE["ink"],
            alignment=TA_CENTER,
            wordWrap="CJK",
        ),
        "toc": ParagraphStyle(
            "toc",
            parent=base["Normal"],
            fontName=FONT,
            fontSize=11,
            leading=17,
            textColor=PALETTE["ink"],
            wordWrap="CJK",
        ),
    }


S = make_styles()


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


def bullet(items: list[str], style: str = "body") -> ListFlowable:
    return ListFlowable(
        [ListItem(p(item, style), leftIndent=0) for item in items],
        bulletType="bullet",
        leftIndent=15,
        bulletFontName=FONT,
        bulletFontSize=8,
        bulletColor=PALETTE["teal"],
        spaceBefore=2,
        spaceAfter=5,
    )


def number_list(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(p(item), leftIndent=0) for item in items],
        bulletType="1",
        leftIndent=18,
        bulletFontName=FONT_BOLD,
        bulletFontSize=9,
        bulletColor=PALETTE["teal"],
        spaceBefore=2,
        spaceAfter=6,
    )


def card(title: str, body: str, tone: str = "teal") -> Table:
    color = PALETTE.get(tone, PALETTE["teal"])
    data = [[p(title, "card_title")], [p(body, "body")]]
    table = Table(data, colWidths=[162 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALETTE["panel"]),
                ("BOX", (0, 0), (-1, -1), 0.65, PALETTE["line"]),
                ("LINEBEFORE", (0, 0), (0, -1), 3.0, color),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                ("TOPPADDING", (0, 1), (-1, 1), 0),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
            ]
        )
    )
    return table


def mini_cards(items: list[tuple[str, str, str]], col_width: float = 51 * mm) -> Table:
    cells = []
    for title, value, note in items:
        cells.append(
            [
                p(title, "tiny"),
                Paragraph(f"<font name='{FONT_BOLD}' size='18'>{value}</font>", S["body"]),
                p(note, "tiny"),
            ]
        )
    row = [Table([[cell[0]], [cell[1]], [cell[2]]], colWidths=[col_width - 7 * mm]) for cell in cells]
    table = Table([row], colWidths=[col_width] * len(items), hAlign="LEFT")
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), PALETTE["white"]),
        ("BOX", (0, 0), (-1, -1), 0.55, PALETTE["line"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.55, PALETTE["line_light"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    table.setStyle(TableStyle(style))
    return table


def simple_table(headers: list[str], rows: list[list[str]], widths: list[float] | None = None) -> Table:
    data = [[p(h, "small") for h in headers]]
    data.extend([[p(str(cell), "tiny") for cell in row] for row in rows])
    if widths is None:
        widths = [162 * mm / len(headers)] * len(headers)
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PALETTE["tint"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), PALETTE["ink"]),
                ("BOX", (0, 0), (-1, -1), 0.55, PALETTE["line"]),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, PALETTE["line_light"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PALETTE["white"], colors.HexColor("#f7fbf9")]),
            ]
        )
    )
    return table


def workflow_table() -> Table:
    steps = [
        ("1", "准备 Excel", "把实验数据放进 Sheet1，列名要对。"),
        ("2", "导入数据", "进入数据管理页，点导入或读取默认表。"),
        ("3", "训练模型", "进入建模控制页，点训练并验证。"),
        ("4", "看验证图", "进入验证诊断页，看模型是否可靠。"),
        ("5", "做预测", "进入可信预测页，填参数，生成结果。"),
    ]
    data = []
    for num, title, note in steps:
        data.append([p(num, "center"), p(f"<b>{title}</b><br/>{note}", "small")])
    table = Table(data, colWidths=[13 * mm, 149 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), PALETTE["teal"]),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                ("BACKGROUND", (1, 0), (1, -1), PALETTE["panel"]),
                ("BOX", (0, 0), (-1, -1), 0.65, PALETTE["line"]),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, PALETTE["line_light"]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


class TutorialDoc(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=22 * mm,
            rightMargin=22 * mm,
            topMargin=20 * mm,
            bottomMargin=18 * mm,
            title="MICP预测器使用教程",
            author="Codex",
            subject="MICP科研级预测软件零基础使用教程",
        )
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal")
        cover_frame = Frame(0, 0, PAGE_W, PAGE_H, id="cover")
        self.addPageTemplates(
            [
                PageTemplate(id="cover", frames=[cover_frame], onPage=draw_cover_bg),
                PageTemplate(id="normal", frames=[frame], onPage=draw_page),
            ]
        )


def draw_cover_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PALETTE["bg"])
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(PALETTE["green"])
    canvas.rect(0, 0, 70 * mm, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(PALETTE["teal"])
    canvas.roundRect(22 * mm, PAGE_H - 52 * mm, 18 * mm, 18 * mm, 5 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont(FONT_BOLD, 16)
    canvas.drawCentredString(31 * mm, PAGE_H - 45.5 * mm, "M")
    canvas.setFillColor(PALETTE["teal"])
    canvas.roundRect(86 * mm, 31 * mm, 92 * mm, 36 * mm, 6 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont(FONT_BOLD, 15)
    canvas.drawString(93 * mm, 52 * mm, "给完全零基础使用者的路线图")
    canvas.setFont(FONT, 9.5)
    canvas.drawString(93 * mm, 43 * mm, "从 Excel 到模型训练，再到验证图和可信预测")
    canvas.restoreState()


def draw_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PALETTE["bg"])
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(PALETTE["panel"])
    canvas.roundRect(13 * mm, 11 * mm, PAGE_W - 26 * mm, PAGE_H - 22 * mm, 5 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(PALETTE["line"])
    canvas.setLineWidth(0.45)
    canvas.line(22 * mm, PAGE_H - 16 * mm, PAGE_W - 22 * mm, PAGE_H - 16 * mm)
    canvas.setFillColor(PALETTE["muted"])
    canvas.setFont(FONT, 8.2)
    canvas.drawString(22 * mm, PAGE_H - 11 * mm, "MICP Research Console - 使用教程")
    canvas.drawRightString(PAGE_W - 22 * mm, 10 * mm, f"{doc.page}")
    canvas.restoreState()


def add_cover(story: list):
    story.append(NextPageTemplate("normal"))
    story.append(Spacer(78 * mm, 83 * mm))
    story.append(
        Table(
            [
                [p("MICP预测器使用教程", "title")],
                [p("完全零基础版：高中生也能跟着完成数据导入、模型训练、验证图解读和可信预测。", "subtitle")],
                [p(f"适用软件：MICP 科研级加固效果预测软件<br/>生成日期：{datetime.now().strftime('%Y-%m-%d')}", "small")],
            ],
            colWidths=[101 * mm],
        )
    )
    story.append(PageBreak())


def add_preface(story: list):
    story.append(p("先看这里：这份教程怎么用", "h1"))
    story.append(
        p(
            "你不需要先学会机器学习，也不需要看懂每个公式。你只要把这个软件当成一台“科研计算工作台”：先把实验数据交给它，让它学习过去论文里的规律，再让它帮你估计新方案可能得到的 UCS 和 CCC。",
        )
    )
    story.append(
        card(
            "一句话理解 MICP 预测器",
            "它不是魔法，也不是工程保证书。它做的事情是：根据已导入论文数据，寻找“菌液参数、试样尺寸、胶结方案”和“加固结果”之间的统计关系，然后给新方案一个有风险提示的预测。",
            "teal",
        )
    )
    story.append(Spacer(1, 6))
    story.append(p("教程规划", "h2"))
    story.append(
        number_list(
            [
                "先跑通最短流程：导入数据 -> 训练并验证 -> 输入参数 -> 生成预测。",
                "再认识五个页面：数据管理、建模控制、验证诊断、可信预测、模型版本。",
                "最后学会看图：知道什么时候模型可信，什么时候只是“看起来分数高”。",
            ]
        )
    )
    story.append(p("目录", "h2"))
    story.append(
        simple_table(
            ["章节", "你会学到什么"],
            [
                ["1. 1分钟快速上手", "最少点几个按钮就能完成一次训练和预测。"],
                ["2. 数据准备", "Excel 表格必须有哪些列，区间值和缺失值怎么处理。"],
                ["3. 数据管理页", "看数据行数、样本数、缺失率、清洗预览和论文分组。"],
                ["4. 建模控制页", "缺失值策略、特征模式、算法模式和最佳模型排序怎么选。"],
                ["5. 验证诊断页", "6 张图分别怎么看，如何判断模型能不能用于科研分析。"],
                ["6. 可信预测页", "手动输入、自动体积、参考区间、可信度、相似样本和批量预测。"],
                ["7. 模型版本页", "加载模型、导出训练报告、追踪历史版本。"],
                ["8. 专属名词小词典", "MICP、OD600、UCS、CCC、RMSE、R²、log 等术语的白话解释。"],
                ["9. 常见问题", "打不开、训练失败、预测不可信、图看不懂时怎么办。"],
            ],
            [38 * mm, 124 * mm],
        )
    )
    story.append(PageBreak())


def add_quick_start(story: list):
    story.append(p("1. 1分钟快速上手", "h1"))
    story.append(
        p(
            "如果你只想先确认软件能用，照着下面 5 步做。第一次成功跑通之后，再慢慢看后面的解释。",
        )
    )
    story.append(workflow_table())
    story.append(Spacer(1, 8))
    story.append(
        mini_cards(
            [
                ("建议默认设置", "全部比较", "先让软件把所有算法都比一遍"),
                ("缺失值", "中位数补全", "保留更多小样本"),
                ("特征模式", "全部特征", "原始参数+自动增强特征"),
            ]
        )
    )
    story.append(Spacer(1, 8))
    story.append(p("第一次操作步骤", "h2"))
    story.append(
        number_list(
            [
                "双击 run_app.bat 打开软件。如果提示缺少依赖，先双击 install_deps.bat。",
                "进入“数据管理”，点击“读取默认数据表”。如果你有新表，就点“导入 Excel”。",
                "进入“建模控制”，保持默认：中位数补全、全部特征、全部比较、按论文分组。点击“训练并验证”。",
                "训练结束后进入“验证诊断”，先看 UCS/kpa，再切到 CCC。重点看蓝色的按论文分组结果和 R² 泛化对比。",
                "进入“可信预测”，填入 10 个原始实验参数，点击“生成可信预测”。",
            ]
        )
    )
    story.append(
        card(
            "新手最重要的判断",
            "如果软件给出“可信度低”或提示“超出训练数据范围”，不要把预测值当作定论。它的意思是：你的新方案和训练数据差得比较远，模型只能提供参考，最好补充相近实验数据后重新训练。",
            "red",
        )
    )
    story.append(PageBreak())


def add_data_prep(story: list):
    story.append(p("2. 准备 Excel 数据", "h1"))
    story.append(
        p(
            "软件默认读取 Excel 的 Sheet1。你可以直接使用当前文件夹里的“数据表.xlsx”，也可以自己整理新数据。列名一定要保持一致，因为软件靠列名找到输入和输出。",
        )
    )
    story.append(p("必须准备的输入列", "h2"))
    story.append(
        simple_table(
            ["列名", "白话含义", "填写提示"],
            [
                ["OD600", "菌液浑浊程度，可粗略理解为菌浓度指标。", "填数字，例如 0.9；区间 0.8-1.0 会取均值。"],
                ["脲酶活性U/ml", "细菌分解尿素的能力。", "单位沿用原表 U/ml。"],
                ["中值粒径D50", "土颗粒有一半比它小、一半比它大的粒径。", "通常填 mm。"],
                ["试样高度mm", "圆柱试样的高度。", "必须为数字，单位 mm。"],
                ["试样内径mm", "圆柱试样的内径。", "软件会用高度和内径自动算体积。"],
                ["菌液用量", "实验中加入的菌液量。", "单位沿用你的数据表。"],
                ["胶结液浓度-氯化钙", "胶结液中的 CaCl2 浓度。", "通常 mol/L。"],
                ["胶结液浓度-尿素", "胶结液中的尿素浓度。", "通常 mol/L。"],
                ["胶结液处理次数", "胶结液处理了几次。", "填 1、2、3 这类次数。"],
                ["胶结液总用量", "所有胶结液加起来的总量。", "单位沿用你的数据表。"],
            ],
            [38 * mm, 69 * mm, 55 * mm],
        )
    )
    story.append(p("输出列", "h2"))
    story.append(
        simple_table(
            ["列名", "含义", "说明"],
            [
                ["UCS/kpa", "无侧限抗压强度", "越大通常代表试样更抗压；单位沿用 kPa。"],
                ["CCC", "碳酸钙生成量或含量指标", "MICP 产生的胶结物相关结果，单位沿用原表。"],
            ],
            [38 * mm, 55 * mm, 69 * mm],
        )
    )
    story.append(p("软件会自动做的清洗", "h2"))
    story.append(
        bullet(
            [
                "区间值：例如 0.8-1.0、3-3.5，软件默认取中间值。0.8-1.0 会变成 0.9。",
                "试样体积：不用手填。公式是 pi x (试样内径 / 2)^2 x 试样高度。",
                "空白值：训练时可以选择“中位数补全”或“只用完整行”。",
                "论文分组：软件读取第 2 列“文章”，并向下填充空白，用来做跨论文验证。",
            ]
        )
    )
    story.append(
        card(
            "为什么要有论文分组？",
            "同一篇论文里的数据往往来自相似材料、相似设备和相似实验习惯。如果随机拆分，同一篇论文可能同时出现在训练集和验证集里，分数会好看一些。按论文分组更像是在问：如果遇到一篇新论文体系，模型还能不能预测？",
            "blue",
        )
    )
    story.append(PageBreak())


def add_data_page(story: list):
    story.append(p("3. 数据管理页：先检查数据健康程度", "h1"))
    story.append(
        p(
            "数据管理页像体检报告。不要急着训练，先看数据是不是完整、有没有很多空白、目标值范围是不是特别大。",
        )
    )
    story.append(p("顶部按钮", "h2"))
    story.append(
        simple_table(
            ["按钮", "什么时候点", "结果"],
            [
                ["导入 Excel", "你有自己的数据表时。", "选择 .xlsx 文件，软件读取 Sheet1。"],
                ["读取默认数据表", "使用当前文件夹的“数据表.xlsx”。", "快速加载已有数据。"],
                ["生成导入模板", "你要整理新实验数据时。", "导出一个列名已经写好的空 Excel。"],
            ],
            [38 * mm, 62 * mm, 62 * mm],
        )
    )
    story.append(p("6 张小卡片怎么看", "h2"))
    story.append(
        simple_table(
            ["卡片", "小白解释", "怎么看"],
            [
                ["数据行数", "Excel 里共有多少行实验记录。", "行数越多，模型学习材料越多。"],
                ["UCS 样本", "有 UCS 结果的行数。", "训练 UCS 模型只用这些行。"],
                ["CCC 样本", "有 CCC 结果的行数。", "训练 CCC 模型只用这些行。"],
                ["完整输入行", "所有输入参数都不缺的行数。", "如果太少，建议先用中位数补全。"],
                ["论文组", "数据来自多少篇论文或实验体系。", "越多越有利于判断跨论文泛化。"],
                ["最高缺失", "缺得最严重的字段有多严重。", "超过 40% 时要格外小心。"],
            ],
            [33 * mm, 68 * mm, 61 * mm],
        )
    )
    story.append(p("下方三个表格", "h2"))
    story.append(
        simple_table(
            ["标签页", "看什么", "有什么用"],
            [
                ["清洗预览", "原始值、清洗值、状态。", "确认区间取均值、体积自动计算是否正常。"],
                ["字段质量", "每个字段的有效数、缺失率、异常值。", "找出最拖模型后腿的字段。"],
                ["论文分组", "每篇论文的样本数、目标范围、最高缺失率。", "判断某些论文是否特别难预测。"],
            ],
            [34 * mm, 60 * mm, 68 * mm],
        )
    )
    story.append(
        card(
            "当前数据的典型特点",
            "你的数据来自多篇论文，但完整输入行比较少，且 UCS 与 CCC 的数值跨度较大。所以不要只看随机 K 折的漂亮分数，更要看按论文分组和留一论文验证。",
            "amber",
        )
    )
    story.append(PageBreak())


def add_modeling_page(story: list):
    story.append(p("4. 建模控制页：让软件学习规律", "h1"))
    story.append(
        p(
            "建模就是让电脑从已有实验中学习关系。你可以把它想成：以前做过很多题，现在让软件总结“什么条件容易得到更高 UCS 或 CCC”。",
        )
    )
    story.append(p("推荐新手设置", "h2"))
    story.append(
        mini_cards(
            [
                ("缺失值", "中位数补全", "保留更多样本"),
                ("特征模式", "全部特征", "原始+增强都用"),
                ("算法模式", "全部比较", "让软件自动选优"),
            ]
        )
    )
    story.append(Spacer(1, 5))
    story.append(
        mini_cards(
            [
                ("最佳模型排序", "按论文分组", "科研泛化更严格"),
                ("训练按钮", "训练并验证", "同时训练 UCS 和 CCC"),
                ("结果位置", "右侧报告", "看最佳算法和风险"),
            ]
        )
    )
    story.append(p("四个控制项怎么理解", "h2"))
    story.append(
        simple_table(
            ["控制项", "选项", "小白解释"],
            [
                ["缺失值", "中位数补全", "把空白值用这一列的中间水平补上，适合样本少时先用。"],
                ["缺失值", "只用完整行", "只保留没有空白的记录，更严格，但你的可用行数会变少。"],
                ["特征模式", "原始特征", "只用你输入的实验参数和自动体积。"],
                ["特征模式", "增强特征", "只用软件推导出的组合指标，例如高径比、单位体积用量。"],
                ["特征模式", "全部特征", "原始和增强一起用，新手默认推荐。"],
                ["算法模式", "自动推荐", "软件按数据特点挑 1-2 类适合算法。"],
                ["算法模式", "手动选择", "只训练你勾选的算法。"],
                ["算法模式", "全部比较", "训练所有候选算法，再按指标选最佳。"],
                ["最佳模型排序", "随机 K 折", "更看重数据内部预测能力。"],
                ["最佳模型排序", "按论文分组", "更看重跨论文泛化能力，科研解释更稳妥。"],
                ["最佳模型排序", "留一论文", "最严格，每次拿一整篇论文出来测试。"],
            ],
            [28 * mm, 35 * mm, 99 * mm],
        )
    )
    story.append(PageBreak())


def add_algorithms(story: list):
    story.append(p("算法不是越复杂越好", "h1"))
    story.append(
        p(
            "软件会比较多种算法。你不需要记住数学公式，只要知道它们像不同性格的“解题同学”：有的稳，有的擅长曲线关系，有的适合小样本，有的能给参考上下界。",
        )
    )
    story.append(
        simple_table(
            ["算法", "白话理解", "什么时候值得关注"],
            [
                ["Ridge-log", "稳健的线性基准，像“先画一条大趋势线”。", "用来当对照：复杂模型至少要比它好。"],
                ["ElasticNet-log", "带一点特征筛选倾向的线性模型。", "特征很多、可能重复时可参考。"],
                ["SVR-log", "适合小样本的非线性模型。", "你的数据小、目标跨度大时很常用。"],
                ["KernelRidge-log", "另一种小样本核回归，可补充 SVR。", "SVR 不稳定时可看它。"],
                ["GradientBoosting-log", "一棵树接一棵树改错，擅长数据内插值。", "随机 K 折表现常较好。"],
                ["QuantileGradientBoosting", "重点帮助估计参考上下界。", "看预测区间时有用。"],
                ["RandomForest", "很多树投票，稳定且可看特征重要性。", "做非线性对照。"],
                ["ExtraTrees", "更随机的树模型。", "用来检验关系是否稳定。"],
                ["GaussianProcess-log", "小样本友好，可辅助不确定性判断。", "数据很少时可参考，但可能较敏感。"],
            ],
            [42 * mm, 67 * mm, 53 * mm],
        )
    )
    story.append(
        card(
            "为什么很多算法带 log？",
            "当 UCS 或 CCC 从很小到很大，差距可能是几十倍甚至几百倍。log 变换像把过大的尺子压缩一下，让模型既能看小数值，也不被特别大的数值完全带偏。最后软件会再把结果换回原单位显示。",
            "teal",
        )
    )
    story.append(PageBreak())


def add_validation_page(story: list):
    story.append(p("5. 验证诊断页：教你看图", "h1"))
    story.append(
        p(
            "验证图不是装饰，它是在回答一个核心问题：模型到底是在学规律，还是只是在背数据？科研使用时，这一页比单个预测值更重要。",
        )
    )
    story.append(p("先认识三个指标", "h2"))
    story.append(
        simple_table(
            ["指标", "像什么", "怎么看"],
            [
                ["RMSE", "模型预测和真实结果之间的“重罚版平均差距”。", "越小越好；大错会被惩罚得更厉害。"],
                ["MAE", "平均差多少。", "越小越好；比 RMSE 更直观。"],
                ["R²", "模型解释规律的程度。", "越接近 1 越好；低于 0 说明外推表现很差。"],
            ],
            [28 * mm, 77 * mm, 57 * mm],
        )
    )
    story.append(p("6 张图逐张看", "h2"))
    story.append(
        simple_table(
            ["图", "看图方法", "危险信号"],
            [
                ["算法 RMSE 排名", "柱子越低越好。随机 K 折看数据内部能力；按论文分组看跨论文能力。图中用 log 尺度时，差一格可能差很多倍。", "蓝色按论文分组柱子远高于随机 K 折，说明换论文后风险大。"],
                ["预测-实测", "点越贴近斜虚线越好。虚线代表“预测=真实”。", "很多点远离虚线，或大值总被低估。"],
                ["残差分布", "残差=预测值-真实值。最好围绕 0 分布。", "大部分在 0 的一侧，说明系统性高估或低估。"],
                ["Permutation 特征重要性", "柱子越长，模型越依赖这个特征。", "不能直接证明因果，只能说明模型预测时很看重。"],
                ["每篇论文 MAE", "哪篇论文误差最大，哪篇就最难预测。", "某一篇特别高，说明该论文实验体系可能和别人不同。"],
                ["R² 泛化对比", "比较随机、重复、分组、留一的 R²。", "随机高、分组低或为负，说明模型可能只适合数据内部插值。"],
            ],
            [34 * mm, 76 * mm, 52 * mm],
        )
    )
    story.append(PageBreak())
    story.append(p("怎么判断模型能不能用？", "h1"))
    story.append(
        simple_table(
            ["情况", "可以怎么理解", "建议"],
            [
                ["随机 K 折好，按论文分组也还可以", "模型既能在已有数据附近预测，也有一定跨论文能力。", "可以谨慎用于科研辅助预测。"],
                ["随机 K 折好，按论文分组很差", "模型可能学到了同一论文内部规律，但对新论文体系不稳。", "只在训练数据范围附近使用，并明确说明外推风险。"],
                ["随机 K 折和分组都差", "当前数据不足以支持稳定预测。", "补数据、清理缺失、检查单位和异常值。"],
                ["R² 小于 0", "还不如用平均值猜，说明外推很危险。", "不要把该结果当强结论。"],
            ],
            [42 * mm, 70 * mm, 50 * mm],
        )
    )
    story.append(
        card(
            "科研写作建议",
            "如果要在论文、开题或报告中使用预测结果，建议同时报告：样本量、最佳算法、RMSE、MAE、R²、按论文分组表现、泛化风险等级。不要只写“准确率很高”。回归问题里更专业的说法是误差指标和验证方式。",
            "blue",
        )
    )
    story.append(PageBreak())


def add_prediction_page(story: list):
    story.append(p("6. 可信预测页：输入新方案，看结果和风险", "h1"))
    story.append(
        p(
            "预测页分三块：左边填实验参数，中间看自动计算的体积和增强特征，右边看 UCS/CCC 预测值、参考区间和可信度诊断。",
        )
    )
    story.append(p("手动预测步骤", "h2"))
    story.append(
        number_list(
            [
                "确认已经训练模型，或在模型版本页加载已有模型。",
                "在左侧输入 10 个原始参数。可以填单个数字，也可以填区间，例如 0.8-1.0。",
                "高度和内径填好后，中间会自动显示试样体积。体积不用自己填。",
                "点击“生成可信预测”。右侧会同时显示 UCS/kpa 和 CCC。",
                "先看可信度，再看预测值。可信度低时，数值只能作为粗略参考。",
            ]
        )
    )
    story.append(p("预测结果怎么读", "h2"))
    story.append(
        simple_table(
            ["结果", "白话解释", "怎么用"],
            [
                ["预测值", "模型根据已有数据估计的新方案结果。", "可用于方案初筛，不等于真实实验值。"],
                ["参考区间", "结合分位数模型或交叉验证残差给出的上下范围。", "区间越宽，说明不确定性越大。"],
                ["可信度", "高/中/低三个等级。", "低可信度时应补充相近实验或重新训练。"],
                ["训练范围诊断", "检查输入是否超过训练数据的最小-最大范围。", "超范围就是外推，风险明显增大。"],
                ["最近训练样本距离", "新方案离已有实验有多近。", "越小越像已有样本，越大越像陌生方案。"],
                ["相似样本", "列出最接近的几条训练记录。", "帮助你判断预测是不是有现实参考对象。"],
            ],
            [38 * mm, 67 * mm, 57 * mm],
        )
    )
    story.append(
        card(
            "先看风险，再看数值",
            "小白最容易犯的错误是只看 UCS=多少、CCC=多少。更专业的顺序是：先看是否超训练范围，再看可信度，再看参考区间，最后才看预测值。",
            "red",
        )
    )
    story.append(PageBreak())
    story.append(p("批量预测与方案对比", "h1"))
    story.append(p("当你有很多组实验方案时，不需要一组一组手动输入。可以用“批量预测 Excel”。", "body"))
    story.append(
        simple_table(
            ["功能", "怎么操作", "适用场景"],
            [
                ["批量预测 Excel", "准备一个包含 10 个输入列的 Excel，UCS/CCC 可以为空。点击按钮后选择输入表，再选择保存位置。", "一次比较几十组方案。"],
                ["加入方案对比", "手动预测一组方案后，点击加入方案对比。", "临时比较 2-5 个候选实验方案。"],
                ["自动计算", "中间面板实时显示体积、高径比、单位体积用量等。", "检查输入是否合理。"],
            ],
            [38 * mm, 82 * mm, 42 * mm],
        )
    )
    story.append(
        card(
            "批量预测文件小提醒",
            "批量预测时，输入列名必须和模板一致。最稳妥的方法是在数据管理页点击“生成导入模板”，然后把你的方案填进去。",
            "teal",
        )
    )
    story.append(PageBreak())


def add_management_page(story: list):
    story.append(p("7. 模型版本与导出", "h1"))
    story.append(
        p(
            "模型训练完成后，软件会把模型保存到 models 文件夹，并记录训练历史。这样你下次不一定要重新训练，也可以回看某次训练用了什么算法和数据。",
        )
    )
    story.append(
        simple_table(
            ["功能", "在哪里", "用途"],
            [
                ["加载模型", "模型版本页", "打开以前训练好的 .joblib 模型。"],
                ["导出训练报告", "模型版本页", "导出 Excel，里面包含训练摘要、算法验证和特征重要性。"],
                ["导出当前图", "验证诊断页", "把当前验证图保存为 PNG，用于报告或组会。"],
                ["训练历史", "模型版本页下方表格", "比较不同训练时间、算法、风险等级。"],
            ],
            [38 * mm, 46 * mm, 78 * mm],
        )
    )
    story.append(p("建议保存的科研记录", "h2"))
    story.append(
        bullet(
            [
                "数据文件名和日期：例如 数据表.xlsx，2026-07-06。",
                "训练设置：缺失值策略、特征模式、算法模式、最佳模型排序。",
                "UCS 和 CCC 各自的最佳算法。",
                "随机 K 折、重复 K 折、按论文分组、留一论文的 RMSE/MAE/R²。",
                "泛化风险等级和软件给出的风险说明。",
                "预测时的输入参数、预测值、参考区间、可信度。",
            ]
        )
    )
    story.append(PageBreak())


def add_glossary(story: list):
    story.append(p("8. 专属名词小词典", "h1"))
    story.append(
        simple_table(
            ["名词", "通俗解释"],
            [
                ["MICP", "微生物诱导碳酸钙沉淀。可以理解为让细菌帮忙生成碳酸钙，把松散颗粒胶结得更结实。"],
                ["OD600", "用 600 nm 光测出来的菌液浑浊程度，常用来估计菌液浓度。"],
                ["脲酶活性", "细菌分解尿素的能力。能力越强，通常越有利于碳酸钙沉淀反应。"],
                ["D50", "中值粒径，一半颗粒比它小，一半颗粒比它大。"],
                ["试样体积", "圆柱试样占的空间大小。软件由高度和内径自动计算。"],
                ["胶结液", "含氯化钙和尿素的溶液，是 MICP 反应的重要原料。"],
                ["UCS/kpa", "无侧限抗压强度。可以理解为试样被压坏前能承受多大压力。"],
                ["CCC", "碳酸钙生成量或含量相关指标，用来反映胶结产物多少。"],
                ["缺失值", "表格里空着或无法读成数字的位置。"],
                ["中位数补全", "用这一列的中间水平填补空白，避免样本大量丢失。"],
                ["增强特征", "软件根据原始参数自动算出的新指标，例如高径比、单位体积胶结液用量。"],
                ["交叉验证", "把数据反复分成训练部分和验证部分，测试模型是否真的会预测。"],
                ["随机 K 折", "随机分组验证，适合看数据内部预测能力。"],
                ["按论文分组", "同一篇论文整组留出，更适合看新论文体系的风险。"],
                ["留一论文", "每次拿一整篇论文出来当考试题，是更严格的泛化检查。"],
                ["RMSE", "预测和真实差距的重罚版平均值，越小越好。"],
                ["MAE", "预测平均差多少，越小越好。"],
                ["R²", "模型解释规律的程度，越接近 1 越好；小于 0 说明很不稳。"],
                ["残差", "预测值减真实值。正数表示高估，负数表示低估。"],
                ["外推", "新方案超出了训练数据范围，相当于让模型猜没见过的情况。"],
                ["可信度", "软件综合范围、距离、验证风险给出的高/中/低提示。"],
            ],
            [38 * mm, 124 * mm],
        )
    )
    story.append(PageBreak())


def add_faq(story: list):
    story.append(p("9. 常见问题与排错", "h1"))
    story.append(
        simple_table(
            ["问题", "可能原因", "解决办法"],
            [
                ["软件打不开", "依赖没有安装或启动脚本路径异常。", "先运行 install_deps.bat，再运行 run_app.bat。"],
                ["导入 Excel 失败", "Sheet1 不存在、列名不一致、文件被 Excel 占用。", "关闭 Excel，检查列名，或用“生成导入模板”重新整理。"],
                ["训练失败", "可用样本太少，或目标列几乎为空。", "检查 UCS/CCC 是否有足够数字，优先用中位数补全。"],
                ["图里 R² 为负", "跨论文外推能力差，不一定是程序错误。", "补充更多论文或相近实验，解释时写明风险。"],
                ["预测提示超出训练范围", "输入的新方案比过去数据更大或更小。", "把它当高风险外推，最好补做相近实验。"],
                ["参考区间很宽", "模型不确定性较大。", "不要只看中间预测值，报告时一起写区间。"],
                ["特征重要性看不懂", "它只说明模型预测时依赖哪些变量。", "不要直接写成因果结论，除非有实验机理支持。"],
            ],
            [38 * mm, 58 * mm, 66 * mm],
        )
    )
    story.append(p("给完全新手的最后检查清单", "h2"))
    story.append(
        bullet(
            [
                "我是否确认 Excel 列名正确？",
                "我是否看过数据管理页的缺失率和完整输入行？",
                "我是否至少训练过一次“全部比较 + 全部特征”？",
                "我是否查看了按论文分组和留一论文验证？",
                "我是否在预测结果里先看了可信度和参考区间？",
                "如果要写报告，我是否导出了训练报告和验证图？",
            ]
        )
    )
    story.append(
        card(
            "最重要的一句话",
            "这个软件的专业价值，不是给出一个看似精确的小数，而是告诉你：预测值是多少、误差可能多大、为什么可信或为什么不可信。",
            "teal",
        )
    )


def build_pdf():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = TutorialDoc(str(OUTPUT))
    story: list = []
    add_cover(story)
    add_preface(story)
    add_quick_start(story)
    add_data_prep(story)
    add_data_page(story)
    add_modeling_page(story)
    add_algorithms(story)
    add_validation_page(story)
    add_prediction_page(story)
    add_management_page(story)
    add_glossary(story)
    add_faq(story)
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build_pdf()
