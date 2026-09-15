from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from create_tutorial_pdf import (
    FONT,
    FONT_BOLD,
    PALETTE,
    ROOT,
    S,
    bullet,
    card,
    draw_page,
    mini_cards,
    number_list,
    p,
    simple_table,
)


OUTPUT = ROOT / "output" / "pdf" / "MICP预测器进阶教程_研究生版.pdf"
ICON = ROOT / "assets" / "micp_icon.png"
PAGE_W, PAGE_H = A4


class AdvancedDoc(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=22 * mm,
            rightMargin=22 * mm,
            topMargin=20 * mm,
            bottomMargin=18 * mm,
            title="MICP预测器进阶教程_研究生版",
            author="Codex",
            subject="MICP科研级预测软件进阶方法学教程",
        )
        normal = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal")
        cover = Frame(0, 0, PAGE_W, PAGE_H, id="cover")
        self.addPageTemplates(
            [
                PageTemplate(id="cover", frames=[cover], onPage=draw_cover),
                PageTemplate(id="normal", frames=[normal], onPage=draw_page),
            ]
        )


def draw_cover(canvas, _doc):
    canvas.saveState()
    canvas.setFillColor(PALETTE["bg"])
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(PALETTE["green"])
    canvas.rect(0, 0, 72 * mm, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(PALETTE["teal"])
    canvas.roundRect(23 * mm, PAGE_H - 54 * mm, 19 * mm, 19 * mm, 5 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont(FONT_BOLD, 16)
    canvas.drawCentredString(32.5 * mm, PAGE_H - 47 * mm, "M")
    canvas.setFillColor(PALETTE["teal"])
    canvas.roundRect(86 * mm, 30 * mm, 93 * mm, 37 * mm, 6 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont(FONT_BOLD, 14)
    canvas.drawString(93 * mm, 52 * mm, "研究生进阶方法学手册")
    canvas.setFont(FONT, 9.5)
    canvas.drawString(93 * mm, 43 * mm, "从数据审计、稳健建模到科研报告表达")
    canvas.restoreState()


def add_cover(story: list):
    story.append(NextPageTemplate("normal"))
    story.append(Spacer(1, 76 * mm))
    if ICON.exists():
        story.append(Image(str(ICON), width=31 * mm, height=31 * mm))
        story.append(Spacer(1, 6))
    story.append(p("MICP预测器进阶教程", "title"))
    story.append(p("研究生版：面向方法选择、验证诊断、误差解释、论文汇报和模型扩展。", "subtitle"))
    story.append(Spacer(1, 6))
    story.append(p(f"适用软件：MICP 科研级加固效果预测软件<br/>生成日期：{datetime.now().strftime('%Y-%m-%d')}", "small"))
    story.append(PageBreak())


def add_strategy(story: list):
    story.append(p("1. 进阶使用的核心目标", "h1"))
    story.append(
        p(
            "研究生使用这个软件，不应停留在“训练一个模型并得到预测值”。更重要的是建立一套可复核的建模证据链：数据是否可靠、模型是否稳定、泛化是否可接受、预测是否属于训练范围内插值、结果能否写进论文或报告。"
        )
    )
    story.append(
        mini_cards(
            [
                ("当前数据规模", "80 行", "来自多篇论文"),
                ("目标样本", "47 / 44", "UCS / CCC"),
                ("完整输入", "23 行", "缺失较明显"),
            ]
        )
    )
    story.append(Spacer(1, 7))
    story.append(
        mini_cards(
            [
                ("论文分组", "7 组", "可做跨论文验证"),
                ("最高缺失", "约 62%", "需谨慎解释"),
                ("建模重点", "透明诊断", "不制造虚高分数"),
            ]
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        card(
            "进阶版的判断顺序",
            "先看数据画像，再看验证设计；先看跨论文泛化，再看随机 K 折；先看可信度和区间，再看单个预测值。这个顺序比单纯追求高 R² 更适合科研场景。",
            "teal",
        )
    )
    story.append(p("建议工作流", "h2"))
    story.append(
        number_list(
            [
                "固定数据版本：记录 Excel 文件名、导入日期、Sheet1 和列名检查结果。",
                "完成数据审计：查看缺失率、论文分组、目标跨度、异常值和清洗预览。",
                "建立基线模型：使用 Ridge-log 或 ElasticNet-log 作为线性参考。",
                "比较非线性模型：使用 SVR-log、KernelRidge-log、GradientBoosting-log、树模型和 GaussianProcess-log。",
                "优先检验泛化：重点观察按论文分组和留一论文验证，而不是只看随机 K 折。",
                "做可信预测：检查训练范围、最近样本距离、参考区间和风险等级。",
                "导出证据：保存训练报告 Excel、验证图 PNG 和预测结果表。",
            ]
        )
    )
    story.append(PageBreak())


def add_data_audit(story: list):
    story.append(p("2. 数据审计：先判断数据能支撑什么结论", "h1"))
    story.append(
        p(
            "MICP 数据通常来自不同论文、土样、菌种、养护方式和测试条件。机器学习模型会把这些差异都当成数据模式学习，因此导入后的第一步不是训练，而是判断数据是否具有可比性。"
        )
    )
    story.append(
        simple_table(
            ["审计对象", "软件位置", "研究生要问的问题"],
            [
                ["字段缺失率", "数据管理 - 字段质量", "哪些关键变量缺失严重？缺失是否集中在某几篇论文？"],
                ["完整输入行", "数据管理 - 顶部卡片", "如果完整行太少，完整行策略是否会损失过多样本？"],
                ["论文分组", "数据管理 - 论文分组", "每篇论文的 UCS/CCC 样本数是否均衡？是否有单篇论文主导模型？"],
                ["目标跨度", "顶部 UCS/CCC 卡片", "目标是否跨越几十倍或几百倍？是否必须考虑 log 变换？"],
                ["异常值", "字段质量表", "异常值是单位错误、录入错误，还是真实极端实验？"],
                ["清洗状态", "清洗预览", "区间取均值、体积自动计算、无法解析值是否符合预期？"],
            ],
            [34 * mm, 44 * mm, 84 * mm],
        )
    )
    story.append(p("缺失值处理策略", "h2"))
    story.append(
        simple_table(
            ["策略", "优点", "风险", "适用建议"],
            [
                ["中位数补全", "保留更多样本，小数据下更容易训练。", "会弱化真实差异，可能引入补全偏差。", "当前数据默认推荐，报告中应说明。"],
                ["只用完整行", "更严格，不引入补充值。", "你的完整输入行较少，模型可能不稳定。", "适合做敏感性分析，不宜唯一依赖。"],
            ],
            [30 * mm, 43 * mm, 46 * mm, 43 * mm],
        )
    )
    story.append(
        card(
            "建议做敏感性分析",
            "同一数据分别用“中位数补全”和“只用完整行”训练。若最佳算法、关键特征和误差水平变化很大，说明结论对缺失值处理敏感，论文中需要谨慎表述。",
            "amber",
        )
    )
    story.append(PageBreak())


def add_features(story: list):
    story.append(p("3. 特征工程：让实验机理进入模型", "h1"))
    story.append(
        p(
            "软件不仅使用原始输入，还会自动生成增强特征。增强特征不是额外实验数据，而是对已有实验参数做组合，目的是让模型更容易捕捉与 MICP 机理相关的比例关系和剂量效应。"
        )
    )
    story.append(
        simple_table(
            ["特征", "计算思路", "可能对应的机理含义"],
            [
                ["试样体积", "pi x (内径 / 2)^2 x 高度", "把不同尺寸试样放到可比较尺度。"],
                ["高径比", "高度 / 内径", "反映试样几何形态，可能影响强度测试结果。"],
                ["单位体积菌液用量", "菌液用量 / 试样体积", "反映单位体积内菌液投加强度。"],
                ["单位体积胶结液用量", "胶结液总用量 / 试样体积", "反映单位体积内胶结液供给水平。"],
                ["总 CaCl2 用量指标", "CaCl2 浓度 x 胶结液总用量", "近似表示钙源投入强度。"],
                ["总尿素用量指标", "尿素浓度 x 胶结液总用量", "近似表示尿素供给强度。"],
                ["钙尿素比", "CaCl2 浓度 / 尿素浓度", "反映反应物配比关系。"],
                ["胶结处理强度", "平均浓度 x 处理次数", "近似表示处理强度或处理累积效应。"],
            ],
            [39 * mm, 56 * mm, 67 * mm],
        )
    )
    story.append(p("三种特征模式如何用于科研比较", "h2"))
    story.append(
        simple_table(
            ["模式", "用途", "建议解释"],
            [
                ["原始特征", "作为最直接、最少人为加工的模型。", "若表现接近全部特征，说明原始参数已包含主要信息。"],
                ["增强特征", "检验组合指标是否能单独表达规律。", "若增强特征表现更好，说明比例/剂量指标有解释价值。"],
                ["全部特征", "用于追求更完整的预测性能。", "报告时要结合特征重要性，避免过度解释冗余特征。"],
            ],
            [34 * mm, 64 * mm, 64 * mm],
        )
    )
    story.append(
        card(
            "不要把特征重要性直接写成因果",
            "Permutation 特征重要性表示模型预测时依赖哪些变量。它可以提出假设，但不能单独证明“某变量导致强度提升”。因果解释仍需要实验设计、机理分析和文献支持。",
            "red",
        )
    )
    story.append(PageBreak())


def add_algorithms(story: list):
    story.append(p("4. 算法比较：不是越复杂越科研", "h1"))
    story.append(
        p(
            "当前软件采用算法注册表，对 UCS 和 CCC 分别训练模型。研究生应把算法比较理解为“不同假设的竞争”：线性趋势、非线性平滑、小样本核方法、树模型分段关系和概率式小样本模型。"
        )
    )
    story.append(
        simple_table(
            ["算法类别", "代表算法", "建模假设与用途"],
            [
                ["线性基线", "Ridge-log, ElasticNet-log", "检查是否简单线性关系已足够，并作为复杂模型的最低参照。"],
                ["核方法", "SVR-log, KernelRidge-log", "适合小样本非线性，常作为当前数据的重要候选。"],
                ["提升树", "GradientBoosting-log", "擅长数据内插值，但要警惕跨论文外推下降。"],
                ["集成树", "RandomForest, ExtraTrees", "稳健、可解释特征重要性，适合非线性基线。"],
                ["高斯过程", "GaussianProcess-log", "小样本友好，但对尺度和噪声敏感，可作为不确定性补充。"],
                ["分位数树", "QuantileGradientBoosting", "用于参考上下界，不应只凭中位预测判断可靠性。"],
            ],
            [32 * mm, 48 * mm, 82 * mm],
        )
    )
    story.append(p("目标变换：为什么使用 log1p", "h2"))
    story.append(
        p(
            "当目标值跨度很大时，模型容易优先照顾大数值样本，导致小数值区域表现变差。log1p 变换会把大跨度压缩，使模型更关注倍数关系。软件训练后会自动反变换回 UCS/kpa 或 CCC 原始单位。"
        )
    )
    story.append(
        card(
            "推荐的建模比较组合",
            "第一轮：全部特征 + 全部比较 + 按论文分组排序。第二轮：只保留推荐算法做重复训练。第三轮：切换缺失策略和特征模式做敏感性分析。最终报告中说明为什么选择该模型，而不是只写软件自动选择。",
            "teal",
        )
    )
    story.append(PageBreak())


def add_validation(story: list):
    story.append(p("5. 验证设计：区分插值能力与外推能力", "h1"))
    story.append(
        simple_table(
            ["验证方式", "回答的问题", "适用解释"],
            [
                ["随机 K 折", "在当前数据分布内，模型能否预测类似样本？", "适合描述数据内部插值能力，但可能乐观。"],
                ["重复 K 折", "随机划分是否偶然影响结果？", "若重复 K 折比随机 K 折差很多，说明模型不稳定。"],
                ["按论文分组", "换到未见论文体系时还能否泛化？", "科研解释优先关注。"],
                ["留一论文", "每次完全留出一篇论文作为外部测试。", "最严格，也最能暴露跨体系风险。"],
            ],
            [36 * mm, 66 * mm, 60 * mm],
        )
    )
    story.append(p("指标解读", "h2"))
    story.append(
        simple_table(
            ["指标", "公式思路", "研究生解读重点"],
            [
                ["RMSE", "sqrt(mean((预测 - 实测)^2))", "对大误差敏感，适合发现严重失败案例。"],
                ["MAE", "mean(abs(预测 - 实测))", "直观表示平均误差，便于和实验量级比较。"],
                ["R²", "1 - 残差平方和 / 总离差平方和", "小于 0 表示比用均值猜还差，外推风险高。"],
                ["残差 P80/P95", "绝对残差的 80/95 分位", "用于给预测结果提供经验误差范围。"],
            ],
            [28 * mm, 58 * mm, 76 * mm],
        )
    )
    story.append(
        card(
            "为什么随机 K 折可能漂亮",
            "如果同一篇论文的相似样本同时进入训练和验证，模型会更容易猜对。这不一定作弊，但它回答的是“相似条件下能否插值”，不是“新论文体系能否泛化”。",
            "amber",
        )
    )
    story.append(PageBreak())


def add_plots(story: list):
    story.append(p("6. 验证图的高级读法", "h1"))
    story.append(
        simple_table(
            ["图", "高级读法", "报告建议"],
            [
                ["算法 RMSE 排名", "比较随机 K 折和按论文分组柱子的相对差距。若两者差距巨大，说明数据来源差异主导误差。", "说明主排序依据，并报告两个验证体系。"],
                ["预测-实测", "观察高值区是否系统低估、低值区是否系统高估，以及点云是否随目标值变宽。", "若存在异方差，建议报告 log 变换和残差区间。"],
                ["残差分布", "判断残差是否围绕 0，是否有长尾和极端错误。", "极端残差应回到原论文审查样本。"],
                ["特征重要性", "关注前几名是否符合 MICP 机理，也看是否被单一尺寸或剂量特征主导。", "写成“模型依赖”而非“因果证明”。"],
                ["每篇论文 MAE", "识别最难泛化的论文体系，可能对应土样、处理流程或测量口径差异。", "可作为后续补充数据和分组讨论依据。"],
                ["R² 泛化对比", "比较随机、重复、分组、留一的 R² 梯度下降。", "若分组或留一为负，应明确外推风险。"],
            ],
            [34 * mm, 80 * mm, 48 * mm],
        )
    )
    story.append(
        card(
            "图表结论模板",
            "可以这样写：模型在随机 K 折下表现较好，说明其对当前数据分布内样本具有一定插值能力；但按论文分组或留一论文验证下降明显，表明跨论文体系外推仍存在较高不确定性。",
            "blue",
        )
    )
    story.append(PageBreak())


def add_prediction(story: list):
    story.append(p("7. 可信预测：把模型输出变成科研判断", "h1"))
    story.append(
        p(
            "可信预测页输出的不只是两个数，而是一组诊断信息。研究生应把预测看成“带条件的假设”，而不是实验真值。"
        )
    )
    story.append(
        simple_table(
            ["诊断项", "含义", "如何用于决策"],
            [
                ["训练范围", "输入是否超出训练数据最小-最大范围。", "超范围时属于外推，应降低可信度。"],
                ["最近样本距离", "新方案在标准化特征空间中离训练样本多远。", "距离小更像插值；距离大需要补实验。"],
                ["相似样本", "最接近的训练记录和实测目标。", "检查预测是否有实际案例支撑。"],
                ["参考区间", "基于分位数模型或验证残差的上下范围。", "区间宽说明不确定性高。"],
                ["可信度等级", "综合范围、距离、泛化风险的高/中/低提示。", "论文中应和预测值一起报告。"],
            ],
            [34 * mm, 66 * mm, 62 * mm],
        )
    )
    story.append(p("方案比较建议", "h2"))
    story.append(
        bullet(
            [
                "优先比较相同土样、相同试样尺寸、相同处理框架下的方案，减少外推因素。",
                "不要只按预测 UCS 最大排序，还要同时查看 CCC、参考区间和可信度。",
                "如果两个方案预测值差异小于参考误差区间，不宜宣称一个显著优于另一个。",
                "批量预测后，筛选高可信度且参考区间较窄的方案进入真实实验验证。",
            ]
        )
    )
    story.append(
        card(
            "预测值的科研表达",
            "建议写“模型预测 UCS 为 X kPa，参考区间为 A-B kPa，可信度为中/高，输入参数位于训练数据范围内/部分超出训练范围”。这种写法比单独给出 X 更可靠。",
            "teal",
        )
    )
    story.append(PageBreak())


def add_reporting(story: list):
    story.append(p("8. 论文和组会报告怎么写", "h1"))
    story.append(
        simple_table(
            ["模块", "应报告内容", "示例措辞"],
            [
                ["数据来源", "论文数量、样本量、目标样本数、缺失情况。", "数据包含 7 个论文分组，UCS/CCC 有效样本分别为 47/44。"],
                ["预处理", "区间取均值、体积计算、缺失值策略。", "区间值按均值解析，试样体积由高度和内径计算，缺失值采用中位数补全。"],
                ["特征工程", "原始特征、增强特征和选择原因。", "增强特征包括高径比、单位体积用量和总反应物指标。"],
                ["算法比较", "候选算法、主排序依据、最佳模型。", "以按论文分组 RMSE 作为主排序，以控制跨论文泛化风险。"],
                ["验证结果", "随机/重复/分组/留一指标。", "随机 K 折用于插值能力，分组验证用于泛化能力。"],
                ["预测结果", "预测值、参考区间、可信度、范围诊断。", "预测结果仅作为实验方案筛选和科研辅助判断。"],
            ],
            [30 * mm, 63 * mm, 69 * mm],
        )
    )
    story.append(p("可直接复用的方法段落框架", "h2"))
    story.append(
        card(
            "方法描述模板",
            "本研究基于文献数据构建 MICP 加固效果预测模型。输入变量包括 OD600、脲酶活性、D50、试样尺寸、菌液用量、胶结液浓度与处理次数等，并由试样高度和内径计算体积。模型训练前对区间值取均值，对缺失值采用中位数补全，并构造高径比、单位体积投加量、总 CaCl2 和总尿素指标等增强特征。UCS 与 CCC 分别训练独立回归模型，候选算法包括线性基线、核方法、提升树、集成树和高斯过程。模型性能通过随机 K 折、重复 K 折、按论文分组和留一论文验证进行评估。",
            "blue",
        )
    )
    story.append(PageBreak())


def add_extensions(story: list):
    story.append(p("9. 后续优化路线", "h1"))
    story.append(
        simple_table(
            ["方向", "为什么重要", "具体建议"],
            [
                ["补充元数据", "论文差异可能来自菌种、砂土类型、养护温度、饱和度等未建模变量。", "新增菌种、土样类型、pH、温度、养护时间、注入方式等列。"],
                ["单位统一", "不同论文单位不一致会严重污染模型。", "建立单位字典和换算规则，不要混用 mL、L、g、%。"],
                ["外部验证集", "真正的科研泛化需要独立实验。", "保留一批本课题组实验作为最终测试集，不参与训练。"],
                ["不确定性建模", "单点预测不够支撑决策。", "继续完善分位数模型、bootstrap 或 conformal prediction。"],
                ["数据版本管理", "模型结果必须可复现。", "每次导入数据和训练报告都保留版本号。"],
                ["机理约束", "纯数据模型可能违反 MICP 机理。", "结合质量守恒、反应限值或物理约束做后续模型。"],
            ],
            [34 * mm, 60 * mm, 68 * mm],
        )
    )
    story.append(
        card(
            "进阶使用的底线",
            "当前软件适合做科研辅助、方案初筛、文献数据综合分析和方法学探索。若用于工程设计或关键结论，需要独立实验验证和更完整的数据字段支撑。",
            "red",
        )
    )
    story.append(PageBreak())


def add_checklists(story: list):
    story.append(p("10. 进阶检查清单", "h1"))
    story.append(p("训练前", "h2"))
    story.append(
        bullet(
            [
                "列名、单位、Sheet1 和论文分组列是否确认无误？",
                "是否查看了各字段缺失率和异常值？",
                "目标跨度是否很大，是否需要优先考虑 log 模型？",
                "是否识别出某些论文样本量过少或误差异常？",
            ]
        )
    )
    story.append(p("训练后", "h2"))
    story.append(
        bullet(
            [
                "最佳模型是否只在随机 K 折好看，分组验证却很差？",
                "重复 K 折是否稳定？留一论文是否暴露明显外推风险？",
                "特征重要性是否符合基本机理预期？",
                "残差是否有系统性高估或低估？",
            ]
        )
    )
    story.append(p("预测后", "h2"))
    story.append(
        bullet(
            [
                "输入参数是否超出训练范围？",
                "最近训练样本距离是否过大？",
                "参考区间是否宽到影响方案排序？",
                "预测结论是否写明可信度和风险？",
            ]
        )
    )
    story.append(
        card(
            "一句话总结",
            "研究生版使用重点不是让软件替你做结论，而是让软件把数据、模型、验证和预测风险透明化，帮助你做更有证据的科研判断。",
            "teal",
        )
    )


def build_pdf():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = AdvancedDoc(str(OUTPUT))
    story: list = []
    add_cover(story)
    add_strategy(story)
    add_data_audit(story)
    add_features(story)
    add_algorithms(story)
    add_validation(story)
    add_plots(story)
    add_prediction(story)
    add_reporting(story)
    add_extensions(story)
    add_checklists(story)
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build_pdf()
