"""受控词表：档案未枚举，本地落一份可用的权威术语集。

TerraLID Metadata Profile 声明「能控则控」，但仓库内并未枚举词表 —— 绝大多数字段只写
``controlled vocabulary``，权威来源指向外部（Nomisma 钱币、IMA/Mindat 矿物、ORCID、ROR、
PIDinst、DataCite）。``introduction.md`` 明确写道词表可能未覆盖使用者的需求并鼓励补充，
因此本模块的每个词表默认 ``open_ended=True``（允许自由文本，Excel 下拉须配「允许其他值」）。
真正由档案穷举的只有 ``B3.2`` / ``B3.3.4`` / ``B4.6`` / ``B6.1`` / ``B6.4`` / ``B6.7`` /
``OO8.1``，以及 A15.1 的年龄模型名，这些取 ``open_ended=False``。

内容约定（供后续维护）：

- ``terms`` 只放**规范写法**，一物一写法：标样用官方全称（``NIST SRM 981``）、仪器型号用
  「厂商 型号」（``Thermo Scientific Neptune Plus``）、矿物用 IMA 小写规范名（``galena``）。
  同一实体的多种写法不重复收录，选定的规范形式写在 ``source`` 里。
- ``source`` 逐条写明依据：档案已枚举 / 本地补充 + 具体出处或推断依据；凡无法核实的一律
  不收（例如检索不到认证编号的 ``Pb-1`` 未收录，理由写在 A9.1 的 ``source``）。
- 词表定义集中在 ``_VOCAB_SPECS``：新增/修改词表只需改那一行（含它命中的 ``oids``），
  ``_OID_VOCAB`` 与 ``VOCABULARIES`` 都由该表推导，不存在第二份需要同步维护的映射。
  该表为了守住「单文件 ≤800 行」刻意排得较密，追加词表时注意行数预算。

本模块是纯数据 + 纯函数：不导入 PyQt5 / pandas / openpyxl，不做任何文件 IO，也不解析
markdown（解析是 ``parse.py`` 的职责），以免形成循环依赖。
"""
from __future__ import annotations

from dataclasses import dataclass

from .spec import (
    AGE_MODEL_NAMES,
    DATE_TYPES,
    DATE_UNITS,
    LIA_RATIO_NAMES,
    RATIO_SOURCES,
    SIGMA_LEVELS,
    YES_NO_UNCLEAR,
    FieldSpec,
)


@dataclass(frozen=True)
class Vocabulary:
    """一条受控词表。

    Attributes:
        id: 词表标识，小写 snake_case，同时是 ``VOCABULARIES`` 的键。
        label_en: 词表英文名（一般取档案字段名）。
        label_zh: 词表中文名。
        terms: 规范候选值；顺序即下拉展示顺序，不重复、不含空串。
        source: 依据/出处；档案未枚举的写清「本地补充」及具体推断依据。
        open_ended: 是否允许自由文本。``True`` 表示词表外取值是正常的（Excel 下拉须配
            「允许其他值」，校验层应降级为 WARNING）；``False`` 表示档案已穷举该字段
            允许值，词表外取值应视为错误。
    """

    id: str
    label_en: str
    label_zh: str
    terms: tuple[str, ...]
    source: str
    open_ended: bool = True


#: 档案原文已穷举允许值的字段。
_S_ARCHIVE = "档案已枚举：TerraLID Metadata Profile v0.3.4 的 Allowed values 原文即穷举"
#: 档案只写 ``controlled vocabulary``、未给候选值的字段。
_S_LOCAL = (
    "本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充"
)


#: 词表定义表，每行 ``(id, label_en, label_zh, open_ended, oids, terms, source)``。
#: oids 是本词表命中的档案字段 OID，放在同一行以保证「一个词表一处定义」。
#: 用「表 + 推导」而不是逐条 ``dict`` 字面量，是为了在 800 行上限内完整保留
#: 每条词表的收词依据与 OID 归属。
_VocabRow = tuple[str, str, str, bool, tuple[str, ...], tuple[str, ...], str]
_VOCAB_SPECS: tuple[_VocabRow, ...] = (
    # ── Analyses（分析）────────────────────────────────────────────────────
    ('analysis_type', 'Analysis type', '分析类型', True, ('A2',), ('bulk solution analysis',
     'mineral separate analysis', 'in situ laser ablation'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：由 A3 前处理 / A4 '
     '被测材料 / A5 分离流程 / A6 仪器 的字段链，把「分析类型」理解为取样与进样方式，只放三种通行做法，其余走自由文本。'),
    ('instrument_type', 'Instrument type', '仪器类型', True, ('A6.1',), ('TIMS', 'MC-TIMS', 'MC-ICP-MS',
     'ICP-MS', 'Q-ICP-MS', 'HR-ICP-MS', 'LA-ICP-MS', 'LA-MC-ICP-MS', 'SIMS'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：铅同位素实验室通行的质谱仪器分类。'
     '收词口径：只放规范写法，一物一写法，同义缩写不重复收录（HR-ICP-MS 与 SF-ICP-MS 指同一类扇形磁场高分辨仪器，只收 HR-ICP-MS；本项目历史数据里的 '
     'HR-ICP-SFMS 视为其变体写法）。'),
    ('instrument_model', 'Instrument model', '仪器型号', True, ('A6.2',),
     ('Thermo Scientific TRITON Plus', 'Thermo Finnigan TRITON TI', 'Thermo Finnigan MAT 261',
     'Thermo Finnigan MAT 262', 'Thermo Finnigan Neptune', 'Thermo Scientific Neptune Plus',
     'Thermo Scientific Neptune XT', 'Thermo Scientific Element 2', 'Thermo Scientific Element XR',
     'Thermo Finnigan Element', 'Nu Instruments Nu Plasma', 'Nu Instruments Nu Plasma HR',
     'Nu Instruments Nu Plasma II', 'Nu Instruments Nu Plasma 1700', 'Nu Instruments Sapphire',
     'Nu Instruments Attom', 'GV Instruments IsoProbe', 'Micromass Isoprobe-T',
     'VG Instruments Sector 54', 'VG Instruments VG 354', 'Isotopx Phoenix', 'Isotopx NGX',
     'Agilent 7500', 'Agilent 7700', 'Agilent 7900', 'Agilent 8800', 'Agilent 8900',
     'PerkinElmer ELAN 6100', 'PerkinElmer NexION 300', 'PerkinElmer NexION 2000',
     'Thermo Scientific XSeries II', 'Thermo Scientific iCAP Q', 'New Wave Research UP193',
     'ESI NWR 193', 'Photon Machines Analyte G2', 'Photon Machines Excite', 'Cetac LSX-213',
     'ASI RESOlution M-50', 'ASI RESOlution S-155'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：各厂商公开的 TIMS / '
     'MC-ICP-MS / 四极杆与高分辨 ICP-MS / 激光剥蚀进样系统机型，并对照本项目 数据/地质铅.xlsx「Instrument」列真实取值（MAT261 / '
     'MAT262 / VG354 / Isoprobe-T / Triton TI / Neptune Plus / Nu Plasma HR）。收词口径：只放规范写法，'
     '一物一写法，同义缩写不重复收录（统一「厂商 型号」全称；不收 Trition TI 等拼写错误）。'),
    ('intensity_unit', 'Intensity unit', '信号强度单位', True, ('A8.2',), ('V', 'mV', 'A', 'mA', 'pA',
     'nA', 'cps', 'kcps', 'Mcps'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「平均总信号强度的 SI '
     '单位」，故以 V / A 系（法拉第杯经放大器输出）为主，另收离子计数器惯用的计数率 cps 系列。'),
    ('pb_reference_material', 'Name of lead isotope reference material', '铅同位素标准物质名称', True,
     ('A9.1',), ('NIST SRM 981', 'NIST SRM 982', 'NIST SRM 983', 'NIST SRM 984', 'NIST SRM 610',
     'NIST SRM 612', 'NIST SRM 614', 'NRC HIPB-1', 'ERM-EB400', 'ERM-AE142', 'BCR-1', 'BCR-2',
     'AGV-1', 'AGV-2', 'BHVO-1', 'BHVO-2', 'G-2', 'GSP-1', 'JB-1', 'JB-2', 'JB-3', 'TILL-1',
     'TILL-2', 'TILL-3', 'TILL-4', 'MRG-1', 'SCo-1', 'MAG-1', 'NOD-A-1', 'NOD-P-1', 'RGM-1', 'W-2',
     'BIR-1', 'DNC-1', 'STM-1'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：NIST SRM '
     '981/982/983 分别是 common / equal-atom / radiogenic lead 同位素标准（SRM 984 为放射性成因铅补充），SRM '
     '610/612/614 为玻璃标样（激光剥蚀用）；NRC HIPB-1 为高纯铅认证标准物质；ERM-EB400 / ERM-AE142 为铅同位素基体与溶液标样；'
     'BCR-1/2、AGV-1/2、BHVO-1/2、G-2、GSP-1、JB-1/2/3、TILL-1~4、MRG-1、SCo-1、MAG-1、NOD-A-1/P-1、'
     'RGM-1、W-2、BIR-1、DNC-1、STM-1 为铅同位素实验室常用比对岩石标样。收词口径：只放规范写法，一物一写法，同义缩写不重复收录（统一「NIST SRM '
     '981」全称；`Pb-1` 检索不到对应认证标样，疑为实验室内部代号，故未收 —— 若确有其事请补充出处）。'),
    ('tl_reference_material', 'Name of thallium isotope reference material', '铊同位素标准物质名称', True,
     ('A9.4',), ('NIST SRM 997', 'Alfa Aesar Specpure Tl', 'in-house Tl standard solution'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：NIST SRM 997 即 '
     'Thallium Isotopic Standard，是 Tl 归一化法校正质量歧视最通行的标样；另收文献常见的商品 Tl 溶液与实验室自配 Tl 标准溶液。'),
    ('mass_bias_model', 'Mass bias correction model', '质量歧视校正模型', True, ('A10',),
     ('exponential law', 'power law', 'Russell law', 'linear law',
     'Tl normalization (external normalization with Tl)', 'sample-standard bracketing (SSB)',
     'double spike (DS)', 'none'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：TIMS / MC-ICP-MS '
     '质量歧视校正的经典模型（指数律、幂律、Russell 1978、线性律）与外部归一化（Tl 归一化）、样品-标样交替（SSB）、双稀释剂等通行策略；`none` 表示未做校正。'
     "收词口径：只放规范写法，一物一写法，同义缩写不重复收录（Russell law 不写成 Russell's law）。"),
    ('age_model_name', 'Age model name', '年龄模型名称', False, ('A15.1',), ('SK75', 'CR75', 'AJ84'),
     '档案已枚举：TerraLID Metadata Profile v0.3.4 的 Allowed values 原文即穷举：A15.1 的 Allowed values '
     '原文即 SK75 / CR75 / AJ84，对应 Stacey & Kramers (1975)、Cumming & Richards (1975)、Albarède & '
     'Juteau (1984)，三者已在 data/geochemistry/engine.py::PRESET_MODELS 实现。'),

    # ── Assemblages（堆积单位）─────────────────────────────────────────────
    ('assemblage_type', 'Assemblage type', '堆积单位类型', True, ('AS1',), ('finds complex', 'hoard',
     'grave', 'workshop', 'mining gallery', 'smelting workshop', 'gossan', 'alteration zone',
     'fault zone', 'stratigraphic layer', 'surface scatter'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义给出两类 —— 考古 '
     'finds complex（hoard / workshop / mining gallery）与地质体（gossan / alteration zone / fault '
     'zone），术语按该口径展开。'),
    ('investigation_type', 'Investigation type', '发现/调查方式', True, ('AS2',), ('excavation',
     'archaeological survey', 'geological field survey', 'mining prospection', 'surface collection',
     'chance find', 'museum/legacy collection'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「导致堆积单位被发现的调查类型」。'),
    ('stratigraphy_context', 'Context', '埋藏/扰动状况', True, ('AS4.3',), ('undisturbed (in situ)',
     'disturbed', 'redeposited', 'residual', 'uncertain'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充。**字段名虽为 '
     'Context（stratigraphy_context，易误读为「地层背景」），档案定义实为「堆积时或后期事件中材料是否受到扰动」**，故按扰动状态收词。'),
    ('depth_unit', 'Unit', '深度单位', True, ('AS5.3',), ('m', 'cm', 'mm'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案要求深度的 SI 单位，故只收 '
     'm / cm / mm；基准面由 AS5.1 Reference point 自由文本记录。'),

    # ── Glass（玻璃）──────────────────────────────────────────────────────
    ('glass_production_context', 'Production context', '玻璃生产背景', True, ('OG1',),
     ('primary production (raw glass)', 'secondary production (vessel working)',
     'local workshop production', 'industrial production', 'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：玻璃考古学通行的生产链划分（初级熔制生玻璃 / 次级成型加工）与作坊、工业化生产背景。'),
    ('recycling_indicator', 'Indication for recycling', '回收/回用迹象', True, ('OG2.1', 'OP8.1'), ('yes',
     'no', 'unclear'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「是否显示回收（玻璃）/ '
     '回收或回用（颜料）迹象」，按 OO8.1 在 v0.3.4 新增 unclear 的同一口径给出 yes / no / unclear。仍取 '
     'open_ended=True：档案未枚举该字段，不应把自由描述判为硬错。'),
    ('glass_group', 'Glass group', '玻璃类型群', True, ('OG4',), ('natron glass', 'plant ash glass',
     'soda-lime glass', 'potash glass', 'mixed-alkali glass', 'lead glass', 'high-lead glass',
     'HIMT', 'Levantine I', 'Levantine II', 'Egyptian I', 'Egyptian II', 'Jalame',
     'Roman blue-green', 'Sb-decolourised Roman glass', 'Mn-decolourised Roman glass',
     'Foy Série 2.1', 'Foy Série 3.2'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：玻璃考古学通行的助熔剂体系与化学群名（natron 与植物灰两大体系，以及 HIMT、Levantine I/II、Egyptian I/II、Jalame、Foy '
     'Série 2.1/3.2 等文献稳定出现的群名）；只收有明确化学定义的群，地区性新群名走自由文本。'),
    ('glass_colour', 'Glass colour', '玻璃颜色', True, ('OG5',), ('colourless', 'white', 'grey',
     'black', 'brown', 'amber', 'yellow', 'yellow-green', 'green', 'olive', 'blue', 'turquoise',
     'purple', 'red', 'pink', 'orange'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：考古玻璃报告中通行的描述性颜色名；'
     '若使用 Munsell / CIELAB 等体系，请改填 OP6.2 颜色体系字段。'),
    ('glass_colourant', 'Colourant', '着色剂', True, ('OG6',), ('Fe (iron)', 'Cu (copper)',
     'Co (cobalt)', 'Mn (manganese)', 'Cr (chromium)', 'Au (gold)', 'U (uranium)', 'Ni (nickel)',
     'none detected'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：玻璃着色元素的地球化学常识（Fe '
     '蓝绿/黄绿、Cu 蓝绿与铜红、Co 深蓝、Mn 紫、Cr 绿、Au 红宝石玻璃、U 荧光黄绿）。'),
    ('glass_decolourant', 'Decolourant', '脱色剂', True, ('OG7',), ('Mn (manganese)', 'Sb (antimony)',
     'As (arsenic)', 'Ce (cerium)', 'Se (selenium)', 'none detected'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：玻璃脱色剂通行清单（古代玻璃以 '
     'Mn / Sb 为主，现代玻璃用 As / Ce / Se）。'),
    ('glass_lead_source', 'Lead source', '铅来源', True, ('OG8',), ('lead oxide (PbO) flux',
     'litharge', 'lead metal', 'galena (PbS)', 'lead slag', 'lead-bearing sand',
     'cullet (recycled glass)', 'not applicable', 'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「玻璃中作为铅来源的组分」，按玻璃配方原料与冶金中间产物列常见含铅物料。'),
    ('corrosion_extent', 'Extent', '腐蚀程度', True, ('OG13.1', 'OM2.1'), ('none', 'slight', 'moderate',
     'severe', 'localised (pitted)', 'through-going (complete)', 'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「腐蚀程度」，'
     '同时用于玻璃（OG13.1）与金属（OM2.1）；程度分级按文物保护与腐蚀学通行写法。'),

    # ── Metal（金属器）────────────────────────────────────────────────────
    ('metal_major_elements', 'Major elements', '主量元素（>1 wt%）', True, ('OM1.2',), ('Cu', 'Sn', 'Pb',
     'Zn', 'Fe', 'As', 'Sb', 'Ag', 'Au', 'Ni', 'Co', 'Bi'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案把该字段限定为金属中 >1 '
     'wt% 的主量元素，即铜合金 / 铅锡合金体系的主成分与常见伴生元素；元素符号按 IUPAC。'),

    # ── Metal: Coins（钱币，Nomisma 术语体系）─────────────────────────────
    ('coin_type_series', 'Type series', '钱币类型系列', True, ('OM.C1',), ('RIC', 'RRC', 'RPC',
     'HN Italy', 'SNG', 'BMC', 'DOC', 'MEC', 'LRBC', 'Cohen'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案 Allowed values '
     '指向 Nomisma nmo:TypeSeries 受控词表；此处收钱币学最通行的类型系列：RIC（罗马帝国钱币）、RRC（Crawford 罗马共和钱币）、'
     'RPC（罗马行省钱币）、HN Italy、SNG、BMC、DOC（拜占庭）、MEC（中世纪欧洲）、LRBC（晚期罗马铜币）、Cohen。收词口径：只放规范写法，一物一写法，'
     '同义缩写不重复收录（沿用各系列通用缩写，如 RIC 不写成 R.I.C.）。'),
    ('coin_deposition_type', 'Deposition type', '埋藏/出土情境', True, ('OM.C3',), ('hoard',
     'single find', 'votive deposit', 'grave deposit', 'chance loss', 'stray find',
     'excavation find', 'river find', 'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：Nomisma '
     'nmo:DepositionType 语义，档案定义原文以 hoard、votive deposit、chance loss 为例。'),
    ('coin_authority', 'Authority', '发行权威', True, ('OM.C4',), ('Roman Republic', 'Roman Empire',
     'Roman Senate', 'Augustus', 'Tiberius', 'Nero', 'Vespasian', 'Trajan', 'Hadrian',
     'Marcus Aurelius', 'Septimius Severus', 'Diocletian', 'Constantine I', 'Julian',
     'Byzantine Empire', 'Justinian I', 'Seleucid Empire', 'Ptolemaic Kingdom',
     'Kingdom of Macedon', 'Alexander III of Macedon', 'Philip II of Macedon', 'Athens',
     'Achaemenid Empire', 'Carthage'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「以其名义（显式或隐含）'
     '发行的权威」，对应 Nomisma foaf:Organization / foaf:Person + role authority；'
     '收地中海—近东钱币学最常出现的发行权威（政权、王朝与君主）。收词口径：只放规范写法，一物一写法，同义缩写不重复收录（君主用「通行英文名 + 世数」，如 Alexander '
     'III of Macedon）。'),
    ('coin_mint', 'Mint', '造币厂', True, ('OM.C5',), ('Rome', 'Alexandria', 'Antioch', 'Carthage',
     'Lugdunum', 'Trier', 'Constantinople', 'Thessalonica', 'Nicomedia', 'Cyzicus', 'Aquileia',
     'Siscia', 'Sirmium', 'Serdica', 'Heraclea', 'Athens', 'Corinth', 'Ephesus', 'Tarsus',
     'Seleucia on the Tigris', 'Pella', 'Amphipolis', 'Mediolanum', 'Ravenna', 'Arelate',
     'Londinium', 'Ostia'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：Nomisma nmo:Mint；'
     '收罗马共和—帝国与希腊化世界的主要造币厂。收词口径：只放规范写法，一物一写法，同义缩写不重复收录（地名用古代通行英文形式，如 Lugdunum / Mediolanum / '
     'Arelate / Londinium，不混用现代城市名）。'),
    ('coin_denomination', 'Denomination', '面值', True, ('OM.C6',), ('aureus', 'denarius',
     'quinarius', 'sestertius', 'dupondius', 'as', 'semis', 'quadrans', 'antoninianus', 'nummus',
     'follis', 'solidus', 'semissis', 'tremissis', 'siliqua', 'miliarense', 'stater', 'tetradrachm',
     'didrachm', 'drachm', 'obol', 'hemiobol', 'uncertain'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：Nomisma '
     'nmo:Denomination；收希腊—罗马—拜占庭主要面值，拉丁名用小写（denarius / solidus / follis）。'),
    ('coin_manufacture', 'Manufacture', '制造工艺', True, ('OM.C8',), ('struck', 'cast',
     'struck on cast flan', 'overstruck', 'milled (machine struck)', 'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：Nomisma '
     'nmo:Manufacture；档案把 double-struck 等归入 C9 生产特征，故此处只放成型工艺。'),
    ('coin_peculiarity', 'Peculiarity of Production', '生产特征', True, ('OM.C9',), ('double-struck',
     'off-centre strike', 'weak strike', 'brockage', 'die crack', 'die break', 'overstruck',
     'plated (fourrée)', 'serrated edge', 'edge test cut', 'countermark', "banker's mark", 'holed',
     'clipped', 'chipped'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：Nomisma '
     'nmo:PeculiarityOfProduction；double-struck 为档案原文示例，其余为钱币学通行的生产缺陷与加工痕迹术语。'),

    # ── Objects（器物）────────────────────────────────────────────────────
    ('object_pid_type', 'Type of persistent identifier', '持久标识符类型', True, ('O5.1.2',), ('DOI',
     'ARK', 'Handle', 'Wikidata QID', 'TerraLID ID', 'URI'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「赋予器物的持久标识符类型」；收通行 PID 体系与 TerraLID 自身编号（馆藏登录号不是持久标识符，不入表）。'),
    ('collection_method', 'Collection method', '采集/获取方式', True, ('O7',), ('excavation',
     'surface collection', 'chance find', 'metal-detecting find', 'purchase', 'gift', 'bequest',
     'museum/legacy collection', 'loan', 'seizure', 'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「器物如何被采集或获得」，'
     '覆盖考古发掘、地表采集、偶然发现、金属探测发现、购买、捐赠、遗赠、博物馆旧藏、借展与查扣等来源。'),
    ('housing_material', 'Housing material', '存放材料', True, ('O8.1',), ('none', 'polyethylene bag',
     'polypropylene container', 'glass vial', 'acid-free paper', 'paper envelope', 'cardboard box',
     'wooden box', 'aluminium foil', 'gelatine capsule', 'resin mount', 'epoxy mount'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「器物在 O8.2 '
     '所记阶段中存放于何种材料」，按样品保存与制样的通行材料列。'),
    ('housing_stage', 'Stage of Storage', '存放阶段', True, ('O8.2',), ('field storage',
     'post-excavation storage', 'museum storage', 'laboratory storage', 'transport', 'loan',
     'exhibition'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「器物生命史中被存放的阶段」，按野外、发掘后、库房、实验室、运输、借出、展陈等环节列。'),
    ('weight_unit', 'Unit', '重量单位', True, ('O10.2', 'S6.2'), ('g', 'mg', 'kg', 'µg', 'ct'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案要求质量 SI 单位（g / '
     'mg / kg / µg）；另收珠饰与宝石称重惯用的 ct（carat）以兼容历史记录。'),
    ('dimension_unit', 'Unit of Dimensions', '尺寸单位', True, ('O11.4',), ('mm', 'cm', 'm', 'µm'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：长度 SI 单位及其十进倍数；'
     '器物测量以 mm / cm 最常用，µm 用于微区观察。'),
    ('material', 'Material', '材质', True, ('O12',), ('metal', 'ore', 'glass', 'pigment', 'ceramic',
     'stone', 'organic', 'composite', 'other', 'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案说明该字段决定后续追加哪个材料专属模块；metal / ore / glass / pigment 与现有材料模块一一对应（钱币属 metal 的专门分支），'
     '其余为可扩展的通用材质。'),
    ('authenticity_type', 'Authenticity type', '真伪判定', True, ('O18.1',), ('authentic',
     'probably authentic', 'questionable', 'modern forgery', 'reproduction', 'not assessed'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「器物真伪的类型」；'
     '分档按古代金属器真伪鉴定的通行表述。'),

    # ── Ore（矿石）────────────────────────────────────────────────────────
    ('mineral_name', 'Mineral name', '矿物名称', True, ('OO1.1.1', 'OP4.3.1'), ('galena', 'cerussite',
     'anglesite', 'hydrocerussite', 'pyromorphite', 'mimetite', 'vanadinite', 'wulfenite',
     'crocoite', 'phosgenite', 'litharge', 'massicot', 'sphalerite', 'wurtzite', 'pyrite',
     'marcasite', 'pyrrhotite', 'chalcopyrite', 'bornite', 'chalcocite', 'covellite', 'enargite',
     'tennantite', 'tetrahedrite', 'arsenopyrite', 'molybdenite', 'cassiterite', 'magnetite',
     'hematite', 'goethite', 'cuprite', 'malachite', 'azurite', 'tenorite', 'ilmenite', 'rutile',
     'zircon', 'quartz', 'calcite', 'dolomite', 'barite', 'fluorite', 'gypsum', 'anhydrite',
     'siderite', 'rhodochrosite', 'apatite', 'muscovite', 'phlogopite', 'epidote', 'spinel'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案 Allowed values '
     '指向 IMA 矿物列表（rruff.info/ima）并经 Mindat API 取值；此处只收 IMA 认可、且铅同位素与考古冶金研究常用的硫化物 / 碳酸盐 / 氧化物 '
     '/ 硫酸盐矿物与常见脉石矿物。收词口径：只放规范写法，一物一写法，同义缩写不重复收录（全部小写 IMA 规范名；**不含** limonite、biotite 等非 IMA '
     '认可名）。'),
    ('ore_part', 'Mineral–hosting ore part', '矿物赋存部位', True, ('OO1.2',), ('bulk ore',
     'ore mineral separate', 'gangue', 'matrix', 'host rock', 'vein fill', 'inclusion',
     'oxidation zone', 'not specified'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「矿物所赋存的矿石部位」。'),
    ('targeted_metal', 'Targeted metals', '目标金属', True, ('OO2.1',), ('Pb', 'Ag', 'Cu', 'Zn', 'Au',
     'Sn', 'Fe', 'Sb', 'Bi', 'Hg', 'As', 'Mo', 'W', 'Co', 'Ni', 'U'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「采矿活动的目标金属」；'
     '元素符号按 IUPAC，覆盖历史采矿涉及的金属与半金属。'),
    ('ore_texture', 'Mineralisation type', '矿石结构构造', True, ('OO3.1',), ('massive', 'disseminated',
     'vein/veinlet', 'stockwork', 'breccia', 'banded/laminated', 'colloform', 'nodular',
     'framboidal', 'replacement', 'residual', 'euhedral', 'anhedral'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充。**字段名虽为 '
     'Mineralisation type（易误读为「矿化类型」），档案定义实为「矿石矿物的结构构造（texture of the ore mineral）」**，'
     '故按结构构造的通行分类收词（massive / disseminated / vein / stockwork / breccia / colloform / '
     'framboidal / replacement 等）；矿床类型另见 OO6 Deposit type。'),
    ('abundance_category', 'Abundance category', '含量级别', True, ('OO4.2',), ('major', 'minor',
     'trace', 'ultra-trace', 'below detection limit', 'not detected'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「由化学组成推断的元素含量级别」；分档口径与 OM1.2 的 major（>1 wt%）相容：major >1 wt%、minor 0.1–1 wt%、'
     'trace 0.01–0.1 wt%、ultra-trace <0.01 wt%。阈值只写在 source、不写进 terms，便于按级别检索。'),
    ('alteration_extent', 'Alteration', '蚀变程度', True, ('OO5',), ('none', 'slight', 'moderate',
     'strong', 'pervasive (complete)'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充。**字段名虽为 '
     'Alteration（易误读为「蚀变类型」），档案定义实为「蚀变程度（extent of alteration）」**，故按程度分级收词；蚀变类型请用自由文本或后续新增字段。'),
    ('deposit_type', 'Deposit type', '矿床类型', True, ('OO6',), ('Mississippi Valley-type (MVT)',
     'SEDEX', 'volcanogenic massive sulfide (VMS)', 'sandstone-hosted Pb-Zn',
     'carbonate-hosted Pb-Zn', 'skarn', 'porphyry', 'epithermal', 'orogenic (mesothermal)',
     'vein-type', 'unconformity-related', 'iron oxide-copper-gold (IOCG)', 'magmatic Ni-Cu',
     'placer', 'residual/supergene'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：矿床学通行分类（USGS '
     '矿床模型体系常用的端元类型）；地区性名称与过渡类型走自由文本。'),
    ('ore_accessibility', 'Accessibility', '目标金属可获取性', False, ('OO8.1',), ('yes', 'no', 'unclear'),
     '档案已枚举：TerraLID Metadata Profile v0.3.4 的 Allowed values 原文即穷举：Allowed values 原文即 yes / '
     'no / unclear（v0.3.4 changelog 记录 unclear 为新增值）。'),

    # ── Pigments（颜料）───────────────────────────────────────────────────
    ('pigment_name', 'Pigment name', '颜料名称', True, ('OP1',), ('lead white', 'cerussite',
     'hydrocerussite', 'litharge', 'massicot', 'red lead (minium)', 'galena', 'Egyptian blue',
     'Han blue', 'Han purple', 'Maya blue', 'azurite', 'malachite', 'verdigris', 'cinnabar',
     'vermilion', 'orpiment', 'realgar', 'hematite (red ochre)', 'goethite (yellow ochre)',
     'carbon black', 'bone black', 'chalk', 'gypsum', 'kaolinite', 'Tyrian purple'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：含铅颜料（铅白、铅丹、密陀僧、黄丹、'
     '方铅矿）与考古常见颜料（埃及蓝、中国蓝、中国紫、玛雅蓝、石青、石绿、铜绿、朱砂、雌黄、雄黄、赭石、炭黑等）的通行名称。收词口径：只放规范写法，一物一写法，'
     '同义缩写不重复收录（英文通行名小写；矿物相名与 mineral_name 一致）。'),
    ('pigment_chemistry_type', 'Type', '化学类型', True, ('OP3.1',), ('inorganic', 'organic',
     'organometallic', 'mixed', 'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义原文「有机还是无机颜料」。'),
    ('pigment_origin', 'Occurrence', '成因（天然/合成）', True, ('OP3.2',), ('natural', 'synthetic', 'both',
     'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义原文「天然还是合成颜料」。'),
    ('pigment_production_context', 'Production context', '生产背景', True, ('OP5.1',),
     ('primary production (raw material processing)', 'secondary production (pigment making)',
     'workshop production', 'industrial production', 'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「颜料相关的生产背景」；'
     '与 OG1 玻璃语境对齐，分为初级原料处理与次级颜料制作。'),
    ('pigment_treatment', 'Treatment', '原料处理方式', True, ('OP5.2',), ('grinding',
     'levigation (washing)', 'sieving', 'roasting/calcination', 'heating', 'mixing', 'none',
     'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「为制得颜料对原料做了哪些处理」；按颜料工艺通行步骤收词（研磨、淘洗、过筛、焙烧/煅烧、加热、混合）。'),
    ('colour_system', 'Colour system', '颜色体系', True, ('OP6.2',), ('Munsell', 'CIE L*a*b*',
     'CIE XYZ', 'RGB', 'hex triplet', 'descriptive name'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「测定颜色所用的颜色体系」；收色彩学通行体系（Munsell 文物/土壤色卡、CIE Lab 与 XYZ、RGB、十六进制、描述性色名）。'),
    ('pigment_alteration_type', 'Alteration type', '变质类型', True, ('OP7.1',), ('discolouration',
     'darkening/blackening', 'oxidation', 'hydration', 'degradation', 'efflorescence',
     'none observed'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「观察到的变质过程类型」；'
     '含铅颜料最常见的是铅白/铅丹转变为方铅矿（PbS）导致的变黑，故 darkening/blackening 单列。'),
    ('pigment_lead_source', 'Lead source', '铅来源', True, ('OP9',), ('galena (PbS)',
     'cerussite (PbCO3)', 'lead metal', 'litharge (PbO)', 'lead white', 'lead slag', 'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「颜料中铅的来源」；'
     '按古代含铅颜料的原料矿物与冶金中间产物列。'),

    # ── Samples（样品）────────────────────────────────────────────────────
    ('sample_pid_type', 'Type of persistent identifier', '持久标识符类型', True, ('S1.2.2',), ('IGSN',
     'DOI', 'ARK', 'Handle', 'TerraLID ID'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「赋予样品的持久标识符类型」；样品级 PID 以 IGSN（国际通用样品编号）为首选。'),
    ('sampled_material', 'Sampled material', '取样材质', True, ('S3',), ('metal', 'ore',
     'mineral separate', 'glass', 'pigment', 'ceramic', 'rock', 'sediment/soil', 'slag',
     'crucible material', 'corrosion product', 'organic'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义强调该字段可与 O12 '
     '材质不同（异质材料取样）；故在 O12 词表基础上补入单矿物、炉渣、坩埚材料、腐蚀产物等取样专门对象。'),
    ('sample_type', 'Sample type', '样品类型', True, ('S5',), ('bulk sample', 'micro-sample',
     'drill core', 'cut fragment', 'chip', 'powder', 'solution', 'mineral separate',
     'polished section', 'thin section'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「所取材料的类型」，'
     '按取样形态收词（块样、微样、钻芯、切块、碎屑、粉末、溶液、单矿物、光片/薄片）。'),
    ('sampling_method', 'Sampling method', '取样方法', True, ('S7',), ('drilling', 'micro-drilling',
     'cutting/sawing', 'chipping', 'scraping', 'coring', 'grab sampling', 'channel sampling',
     'bulk sampling', 'surface sampling'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「取样所用方法」；'
     '覆盖文物微损取样与矿山/冶炼遗址常规取样方式。'),
    ('sample_condition', 'Sample condition', '样品分析后状态', True, ('S8',), ('intact',
     'partially consumed', 'consumed', 'residual material archived', 'not recoverable', 'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充。**字段名虽为 Sample '
     'condition（易误读为「样品风化/腐蚀状态」），档案定义实为「分析之后样品的状态（state of the sample after analysis）」**，'
     '故按消耗程度与留存状态收词；风化/腐蚀状态请填 S11 描述或材料专属模块。'),

    # ── Sites（遗址/矿区）─────────────────────────────────────────────────
    ('site_pid_type', 'Type', '遗址标识符类型', True, ('SI4.2',), ('GeoNames', 'Pleiades',
     'iDAI.gazetteer', 'Wikidata QID', 'TerraLID ID', 'DOI'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「数据基础设施名称」（B3.1.2 为同义表述）；收考古与地质地名通行 gazetteer：GeoNames、Pleiades（古典世界）、'
     'iDAI.gazetteer（德国考古研究院）与 Wikidata / DOI / TerraLID 自身编号。'),
    ('site_type', 'Site type', '遗址类型', True, ('SI8',), ('mine', 'ore deposit', 'mineral occurrence',
     'smelting site', 'workshop', 'settlement', 'burial/cemetery', 'hoard find spot', 'quarry',
     'kiln', 'harbour/port', 'shipwreck', 'cave', 'tell', 'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「遗址类型：地质成因或人类用途」，故矿区类与考古遗址类并收。'),

    # ── Block B1 Person（人员/机构）───────────────────────────────────────
    ('person_role', 'Role', '角色', True, ('B1.1',), ('author', 'contributor', 'editor', 'collector',
     'excavator', 'curator', 'analyst', 'data provider', 'contact person', 'photographer',
     'supervisor', 'reviewer', 'funder'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案示例为 Author；'
     '角色集参照 CASRAI CRediT 贡献者角色分类，并补入博物馆与实验室岗位（collector / excavator / curator / analyst / '
     'data provider）。'),
    ('person_pid_type', 'Type of persistent identifier', '持久标识符类型', True, ('B1.4.2',), ('ORCID',
     'ISNI', 'VIAF', 'GND', 'Wikidata QID', 'Scopus Author ID', 'ResearcherID'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：人员持久标识符的通行体系；档案 '
     'Provided by 一栏明确提到 API (ORCID ID)，故 ORCID 为首选。'),

    # ── Block B2 Status（保存与可获取性）──────────────────────────────────
    ('accessibility', 'Accessibility', '可获取性', True, ('B2.2',), ('openly accessible',
     'accessible with restrictions', 'accessible on request', 'not accessible', 'unknown'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「材料是否可供其他研究者获取、是否有限制」；注意与 OO8.1（目标金属是否可获取，yes/no/unclear）不是同一字段。'),

    # ── Block B3 Dating（年代）────────────────────────────────────────────
    ('period_pid_type', 'Type', '年代标识符类型', True, ('B3.1.2',), ('PeriodO', 'ChronOntology',
     'Wikidata QID', 'TerraLID ID', 'DOI'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「数据基础设施名称」，'
     '该字段挂在年代/时期标识符上；收时期本体库 PeriodO（perio.do）、ChronOntology（iDAI）与 Wikidata / DOI / TerraLID '
     '自身编号。'),
    ('date_type', 'Date type', '年代类型', False, ('B3.2',), ('geological', 'archaeological'),
     '档案已枚举：TerraLID Metadata Profile v0.3.4 的 Allowed values 原文即穷举：Allowed values 原文即 '
     'geological, archaeological；该字段控制 B3.3.4 单位与 B3.5 / B3.6 的可用性。'),
    ('absolute_dating_method', 'Dating method', '绝对年代测定方法', True, ('B3.3.3',), ('radiocarbon (14C)',
     'dendrochronology', 'U-series', 'U-Pb', 'Pb-Pb', 'K-Ar', 'Ar-Ar', 'Rb-Sr', 'Sm-Nd', 'Lu-Hf',
     'Re-Os', 'fission track', 'OSL', 'TL', 'tephrochronology', 'historical record'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「确定绝对年代所用的方法」；同时覆盖考古定年（14C、树木年轮、OSL/TL、历史记载）与地质定年（U-Pb、Ar-Ar、裂变径迹等）。'),
    ('date_unit', 'Unit of date', '年代单位', False, ('B3.3.4',), ('a', 'Ma'),
     '档案已枚举：TerraLID Metadata Profile v0.3.4 的 Allowed values 原文即穷举：Allowed values 原文即 a, Ma；'
     '且由 B3.2 派生（geological → Ma，archaeological → a，BCE 为负值）。'),
    ('chronological_unit', 'Chronological unit', '年代单元', True, ('B3.4.1',), ('Holocene',
     'Pleistocene', 'Pliocene', 'Miocene', 'Oligocene', 'Eocene', 'Paleocene', 'Cretaceous',
     'Jurassic', 'Triassic', 'Permian', 'Carboniferous', 'Devonian', 'Silurian', 'Ordovician',
     'Cambrian', 'Neoproterozoic', 'Mesoproterozoic', 'Paleoproterozoic', 'Archean', 'Palaeolithic',
     'Mesolithic', 'Neolithic', 'Chalcolithic', 'Early Bronze Age', 'Middle Bronze Age',
     'Late Bronze Age', 'Iron Age', 'Roman', 'Late Antique', 'Byzantine', 'Medieval',
     'Early Modern'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「以年代单元表述的相对年代」，该字段同时服务地质与考古两类日期（由 B3.2 控制）。地质部分采用国际年代地层表（ICS）的统/系名，'
     '考古部分只收跨区域通用的时代名；地区性考古学文化请填 B3.5（自由文本）。'),
    ('relative_dating_method', 'Dating method', '相对年代判定方法', True, ('B3.4.2',), ('stratigraphy',
     'lithostratigraphy', 'biostratigraphy', 'chronostratigraphy', 'chemostratigraphy',
     'magnetostratigraphy', 'tephrochronology', 'typology', 'seriation', 'cross-dating',
     'stylistic comparison', 'historical record'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「确定相对年代所用的方法」；按地质地层学与考古类型学两组收词。'),
    ('orogeny', 'Orogenesis', '造山事件', True, ('B3.6',), ('Alpine', 'Variscan', 'Caledonian',
     'Cadomian', 'Pan-African', 'Grenvillian', 'Baikalian', 'Uralian', 'Cimmerian', 'Indosinian',
     'Yanshanian', 'Laramide', 'Andean', 'Himalayan'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「以造山事件表述的相对年代」，仅 B3.2 = geological 时可用；收全球与东亚（Indosinian 印支期、Yanshanian 燕山期）'
     '通行的造山期名称。收词口径：只放规范写法，一物一写法，同义缩写不重复收录（Variscan 与 Hercynian 指同一造山期，只收 Variscan）。'),

    # ── Block B4 Chemistry（化学组成）─────────────────────────────────────
    ('chemistry_method', 'Analytical method', '化学成分分析方法', True, ('B4.1',), ('XRF', 'pXRF',
     'ICP-OES', 'ICP-MS', 'LA-ICP-MS', 'AAS', 'INAA', 'EPMA', 'SEM-EDS', 'wet chemical analysis',
     'titration', 'gravimetry'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「测定化学组成的方法」；'
     '收无机成分分析通行手段，含文物无损/微损的 pXRF 与微区 EPMA / SEM-EDS。'),
    ('analysed_compound', 'Analysed compound', '被测化合物', True, ('B4.2',), ('Al', 'Si', 'Ca', 'Mg',
     'Na', 'K', 'Fe', 'Mn', 'Ti', 'P', 'Cu', 'Sn', 'Pb', 'Zn', 'Ag', 'Au', 'As', 'Sb', 'Ni', 'Co',
     'Bi', 'S', 'Mo', 'W', 'U', 'Th', 'Zr', 'Nb', 'Ba', 'Sr', 'Cr', 'V', 'Cl', 'C', 'SiO2', 'TiO2',
     'Al2O3', 'Fe2O3', 'FeO', 'MnO', 'MgO', 'CaO', 'Na2O', 'K2O', 'P2O5', 'PbO', 'CuO', 'SnO2',
     'ZnO', 'SO3', 'CO2', 'LOI', '206Pb', '207Pb', '208Pb', '204Pb', '205Tl', '203Tl', '87Sr',
     '86Sr', '143Nd', '144Nd', '176Hf', '177Hf', '18O', '16O'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「被测化学化合物（元素、'
     '氧化物、同位素）」，并要求尽量报实际测量对象（质谱测的是同位素而非元素）；元素与氧化物按 IUPAC 符号与惯用氧化物写法，同位素用「质量数 + 元素符号」。'
     '收词口径：只放规范写法，一物一写法，同义缩写不重复收录（氧化物不写 Unicode 下标；比值请改用 B6 铅同位素比值字段）。'),
    ('chemistry_unit', 'Unit', '含量单位', True, ('B4.4',), ('wt%', 'ppm', 'ppb', 'µg/g', 'mg/kg',
     'ng/g', 'mol%', 'at%', 'vol%', 'g/L', 'mg/L', 'µg/mL'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「浓度单位」；'
     '氧化物与主量用 wt%，微量元素用 ppm / ppb；ppm 与 µg/g、mg/kg 数值等价但都是领域惯用写法，为兼容历史数据并存。未收 % （与 wt% 重复）与 '
     'ppt（千分/万亿分之一歧义）。'),
    ('chemistry_uncertainty_type', 'Uncertainty type', '不确定度类型', True, ('B4.5',),
     ('standard deviation', 'standard error of the mean', 'relative standard deviation',
     'expanded uncertainty', 'confidence interval', 'limit of detection', 'limit of quantification',
     'estimated', 'not specified'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「分析不确定度的类型」，'
     '其 B4.6 记录 σ 倍数、B4.7 记录绝对不确定度值、B4.8 记录定性值，故此处只列不确定度的性质。'),
    ('confidence_level', 'Confidence level', '置信水平（σ 倍数）', False, ('B4.6', 'B6.4'), ('1', '2', '3'),
     '档案已枚举：TerraLID Metadata Profile v0.3.4 的 Allowed values 原文即穷举：Allowed values 原文即 1, 2, '
     '3（标准差 σ 的倍数）；B4.6（化学组成）与 B6.4（铅同位素比值）共用本词表。'),

    # ── Block B5 Relation（关联资源）──────────────────────────────────────
    ('relation_pid_type', 'Type', '关联标识符类型', True, ('B5.1.2',), ('DOI', 'Handle', 'ARK', 'ISBN',
     'ISSN', 'PMID', 'arXiv ID', 'ORCID', 'ROR', 'IGSN', 'TerraLID ID', 'URL'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：档案定义为「标识符类型」，'
     '并明确「若指向 TerraLID 库内实体必须使用 TerraLID 标识符」；收文献、数据集、人员、机构、样品与链接各常用标识符。'),
    ('relation_kind', 'Kind of relation', '关联关系类型', True, ('B5.3',), ('IsCitedBy', 'Cites',
     'IsSupplementTo', 'IsSupplementedBy', 'IsPartOf', 'HasPart', 'IsReferencedBy', 'References',
     'IsDerivedFrom', 'IsSourceOf', 'Describes', 'IsDescribedBy', 'HasMetadata', 'IsMetadataFor',
     'IsDocumentedBy', 'Documents', 'IsIdenticalTo', 'IsNewVersionOf', 'IsPreviousVersionOf'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「条目与研究产出之间的关系」；直接采用 DataCite Metadata Schema 4.4 的 relationType 受控词表。'
     '收词口径：只放规范写法，一物一写法，同义缩写不重复收录（大小写照 DataCite 原文的 IsXxx 形式），便于日后与 DOI 元数据对接。'),
    ('resource_type', 'Type of resource', '资源类型', True, ('B5.4',), ('Audiovisual', 'Book',
     'BookChapter', 'Collection', 'ConferencePaper', 'ConferenceProceeding', 'DataPaper', 'Dataset',
     'Dissertation', 'Event', 'Image', 'Journal', 'JournalArticle', 'Model', 'PhysicalObject',
     'Preprint', 'Report', 'Service', 'Software', 'Standard', 'Text', 'Workflow', 'Other'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；依据：采用 DataCite '
     'Metadata Schema 4.4 的 resourceTypeGeneral 受控词表（大小写照原文）；PhysicalObject 覆盖器物/样品这一 '
     'TerraLID 特有情形。'),

    # ── Block B6 Lead isotope ratio（铅同位素比值）────────────────────────
    ('lia_ratio_name', 'Name', '比值名称', False, ('B6.1',), ('206Pb/204Pb', '207Pb/204Pb',
     '208Pb/204Pb', '204Pb/206Pb', '207Pb/206Pb', '208Pb/206Pb', '207Pb/208Pb', '206Pb/208Pb'),
     '档案已枚举：TerraLID Metadata Profile v0.3.4 的 Allowed values 原文即穷举：Allowed values 原文即 8 个比值，'
     '与 spec.LIA_RATIO_NAMES 逐项一致（含顺序）；前三个为主比值，其余 5 个由系统推导。'),
    ('lia_uncertainty_type', 'Uncertainty', '比值不确定度类型', True, ('B6.3',), ('standard deviation',
     'standard error of the mean', 'relative standard deviation', 'internal reproducibility',
     'external reproducibility', 'long-term reproducibility', 'within-run precision',
     'propagated uncertainty', 'expanded uncertainty', 'not specified'),
     '本地补充：档案仅标注 controlled vocabulary 未枚举；introduction.md 明确词表可能不全并鼓励补充；'
     '依据：档案定义为「铅同位素比值的分析不确定度类型」；除通用统计量外，收同位素比值测量报告惯用的内部/外部/长期重现性与传播不确定度。'),
    ('ratio_source', 'Source', '比值来源', False, ('B6.7',), ('original', 'calculated'),
     '档案已枚举：TerraLID Metadata Profile v0.3.4 的 Allowed values 原文即穷举：Allowed values 原文即 '
     'original, calculated；系统会依据三个主比值自动补齐 calculated 行。'),
)

#: 受控词表注册表：id（小写 snake_case）→ `Vocabulary`；键与 `Vocabulary.id` 恒等。
#: 传参顺序 id / label_en / label_zh / terms / source / open_ended，对应表列 0,1,2,5,6,3。
VOCABULARIES: dict[str, Vocabulary] = {
    spec[0]: Vocabulary(spec[0], spec[1], spec[2], spec[5], spec[6], spec[3])
    for spec in _VOCAB_SPECS
}


#: OID → 词表 id，由 `_VOCAB_SPECS` 的 oids 列反查得到，不手工维护第二份映射。
_OID_VOCAB: dict[str, str] = {
    oid: spec[0] for spec in _VOCAB_SPECS for oid in spec[4]
}


def vocab_id_for(spec: FieldSpec) -> str | None:
    """按字段 OID 取受控词表 id。

    只依赖 ``spec.oid``：块字段（B1–B6）被不同模块内联时 OID 相同、词表也相同，因此无需
    区分宿主模块。**不读** ``spec.vocab_id`` —— 那个字段正是本函数的输出（由 ``profile.py``
    回填），若在此读取会形成自引用。

    Args:
        spec: 档案字段定义。

    Returns:
        词表 id；该字段没有受控词表（自由文本、数值、日期等）时返回 ``None``。
    """
    return _OID_VOCAB.get(spec.oid)


def vocabulary(vocab_id: str) -> Vocabulary | None:
    """按 id 取词表对象。

    Args:
        vocab_id: 词表 id。

    Returns:
        对应词表；id 不存在时返回 ``None``（不抛异常，便于调用方按“无词表”继续）。
    """
    return VOCABULARIES.get(vocab_id)


def terms(vocab_id: str) -> tuple[str, ...]:
    """取词表的候选值元组。

    Args:
        vocab_id: 词表 id。

    Returns:
        规范候选值；id 不存在时返回空元组。
    """
    found = VOCABULARIES.get(vocab_id)
    return found.terms if found is not None else ()


def open_ended(vocab_id: str) -> bool:
    """判断词表是否允许自由文本（词表外取值应降级为 WARNING）。

    不存在的 id 一律返回 ``True``，这是刻意的保守默认：档案明确说词表可能不覆盖全部
    需求并鼓励补充，因此宁可不报硬错，也不要把未知词表当成封闭集。

    Args:
        vocab_id: 词表 id。

    Returns:
        ``True`` = 允许自由文本（词表外取值只是提示）；``False`` = 档案已穷举允许值
        （词表外取值应视为错误）。
    """
    found = VOCABULARIES.get(vocab_id)
    return True if found is None else found.open_ended


def _normalize(value: str) -> str:
    """生成比较键：折叠空白 + 大小写不敏感。"""
    return " ".join(str(value).split()).casefold()


def contains(vocab_id: str, value: str | None) -> bool:
    """判断取值是否属于某个词表（大小写与空白不敏感）。

    比较规则：去掉前后空白、把内部连续空白折叠为单个空格、再做 ``casefold()``，然后与
    ``terms`` 逐项**全等**比较。不做前缀、子串或别名匹配 —— 词表本身只收规范写法，
    别名问题在词表内容层解决。

    Args:
        vocab_id: 词表 id。
        value: 待判断的取值；``None`` 或纯空白视为未提供。

    Returns:
        属于该词表返回 ``True``；``vocab_id`` 不存在、``value`` 为空、或取值不在词表内
        均返回 ``False``（不抛异常）。
    """
    if value is None:
        return False
    target = _normalize(value)
    if not target:
        return False
    found = VOCABULARIES.get(vocab_id)
    if found is None:
        return False
    return any(_normalize(term) == target for term in found.terms)


__all__ = [
    # 数据结构
    "Vocabulary",
    # 词表注册表
    "VOCABULARIES",
    # 查询
    "contains",
    "open_ended",
    "terms",
    "vocab_id_for",
    "vocabulary",
]
