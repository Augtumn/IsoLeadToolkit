# 地球化学计算原理文档

本文档详细说明 `data/geochemistry/` 模块的数学原理、公式推导及实现细节。

**算法来源:**
- Stacey, J.S. & Kramers, J.D. (1975). *EPSL*, 26, 207–221.
- Cumming, G.L. & Richards, J.R. (1975). *EPSL*, 28, 155–171.
- Maltese, A. & Mezger, K. (2020). *GCA*, 271, 70–87.
- Zhu, B.Q. (1993; 1995; 1998). 铅同位素三维拓扑投影方法.
- Jaffey, A.H. et al. (1971). *Phys. Rev. C*, 4, 1889. (衰变常数)
- Steiger, R.H. & Jäger, E. (1977). *EPSL*, 36, 359–362.
- Tatsumoto, M. et al. (1973). *Science*, 180, 1279–1283. (CDT 原始铅)
- Dausmann, V. et al. (2019). *PbIso* R 软件包文档.
- York, D. et al. (2004). *Am. J. Phys.*, 72, 367–375. (加权回归)

**源文件结构:**
```
data/geochemistry/
├── engine.py      → 常量、预设模型、GeochemistryEngine、模型曲线
├── age.py         → 模式年龄求解 (单阶段/两阶段/Pb-Pb)
├── delta.py       → Δ 值、V1-V2 投影
├── source.py      → 源区参数反演、初始比值
├── isochron.py    → 等时线、生长曲线、York 回归
└── __init__.py    → 集成入口 calculate_all_parameters()
```

---

## 1. 物理常数与参考值

### 1.1 衰变常数

| 符号 | 值 (yr⁻¹) | 来源 |
|------|-----------|------|
| λ₂₃₈ | 1.55125 × 10⁻¹⁰ | Jaffey et al. (1971) |
| λ₂₃₅ | 9.8485 × 10⁻¹⁰ | Jaffey et al. (1971) |
| λ₂₃₂ | 4.94752 × 10⁻¹¹ | Steiger & Jäger (1977) |

半衰期关系: T₁/₂ = ln(2) / λ

| 同位素 | 半衰期 |
|--------|-------|
| ²³⁸U → ²⁰⁶Pb | 44.68 亿年 |
| ²³⁵U → ²⁰⁷Pb | 7.04 亿年 |
| ²³²Th → ²⁰⁸Pb | 140.1 亿年 |

### 1.2 天然同位素比

²³⁵U/²³⁸U = 1/137.88 ≈ 0.0072527（天然铀同位素比值）

代码中记为 `U_RATIO_NATURAL`，其倒数 `U8U5 = 137.88` 在部分公式中使用。

### 1.3 原始铅同位素比值 (CDT)

Canyon Diablo Troilite (铁陨石) 的铅同位素组成，代表太阳系形成时的原始铅:

| 符号 | 比值 | 含义 |
|------|------|------|
| a₀ | 9.307 | ²⁰⁶Pb/²⁰⁴Pb |
| b₀ | 10.294 | ²⁰⁷Pb/²⁰⁴Pb |
| c₀ | 29.476 | ²⁰⁸Pb/²⁰⁴Pb |

来源: Tatsumoto et al. (1973)

### 1.4 Stacey-Kramers 第二阶段起始值

SK 模型两阶段过渡点 (3700 Ma) 的铅同位素组成:

| 符号 | 比值 | 含义 |
|------|------|------|
| a₁ | 11.152 | ²⁰⁶Pb/²⁰⁴Pb |
| b₁ | 12.998 | ²⁰⁷Pb/²⁰⁴Pb |
| c₁ | 31.23 | ²⁰⁸Pb/²⁰⁴Pb |

来源: Stacey & Kramers (1975)

### 1.5 时间参考

| 符号 | 值 (Ma) | 含义 |
|------|---------|------|
| T_EARTH_CANON | 4570 | 正则地球年龄 |
| T_EARTH_1ST | 4430 | SK 第一阶段近似地球年龄 |
| T_SK_STAGE2 | 3700 | SK 两阶段模型过渡时间 |

### 1.6 地幔参考参数 (默认)

| 符号 | 值 | 含义 |
|------|-----|------|
| μ_M | 9.74 | ²³⁸U/²⁰⁴Pb (地幔) |
| ω_M | 36.84 | ²³²Th/²⁰⁴Pb (地幔) |
| ν_M | μ_M × U_ratio | ²³⁵U/²⁰⁴Pb (衍生) |
| κ_M | ω_M / μ_M ≈ 3.78 | ²³²Th/²³⁸U (衍生) |

---

## 2. 预设模型库

系统内置 6 个预设模型，存储于 `PRESET_MODELS` 字典。

### 2.1 V1V2 (Geokit)

```
age_model  = single_stage
T1 = 4430 Ma,  T2 = 4570 Ma,  Tsec = 3700 Ma
a0/b0/c0   = CDT,  a1/b1/c1 = SK Stage2
μ = 7.8,  ω = 4.04 × 7.8 = 31.512,  κ = 4.04
E1 = 0,  E2 = 0
```

**特点:** 使用 T1=4430 Ma 作为单阶段年龄的起始时间（非标准 4570 Ma）。这是 Geokit 软件的默认约定。年龄计算使用 T1，但源区参数反演使用 T2=4570 Ma。

### 2.2 V1V2 (Zhu 1993)

```
age_model     = single_stage
T1 = T2       = 4570 Ma,  Tsec = 0
a0/b0/c0      = CDT,  a1/b1/c1 = CDT (同 a0/b0/c0)
μ = 7.8,  ω = 31.512,  κ = 4.04
v1v2_formula  = 'zhu1993'  (使用直接系数)
```

**特点:** V1-V2 坐标使用 Zhu (1993) 的直接投影系数而非平面投影公式。强制过原点 (Tsec=0)。

### 2.3 Stacey & Kramers 第二阶段 (默认模型)

```
age_model  = two_stage
T1 = 3700 Ma,  T2 = 4570 Ma,  Tsec = 3700 Ma
a0/b0/c0   = CDT,  a1/b1/c1 = (11.152, 12.998, 31.23)
μ = 9.74,  ω = 36.84,  κ ≈ 3.78
E1 = 0,  E2 = 0
```

**特点:** 两阶段模型——地球铅同位素演化分为两个阶段，以 3700 Ma 为界。第二阶段从 (a1, b1, c1) 开始，以更高的 μ 值演化至今。

### 2.4 Stacey & Kramers 第一阶段

```
age_model  = single_stage
T1 = T2    = 4570 Ma,  Tsec = 3700 Ma
a0/b0/c0   = CDT,  a1/b1/c1 = CDT
μ = 7.2,  ω = 33.2
E1 = 0,  E2 = 0
```

**特点:** 从太阳系形成 (CDT) 到 3700 Ma 的第一阶段演化，μ=7.2 较第二阶段低。

### 2.5 Cumming & Richards (Model III)

```
age_model  = single_stage
T1 = T2    = 4509 Ma,  Tsec = 0
a0/b0/c0   = CDT,  a1/b1/c1 = CDT
μ = 10.8,  ω = 41.2
E1 = 5.0 × 10⁻¹¹,  E2 = 3.7 × 10⁻¹¹
```

**特点:** 连续演化模型，μ 随时间变化 (由 E 参数控制)。E1/E2 非零使得演化项包含线性时间修正。

### 2.6 Maltese & Mezger (2020)

```
age_model  = single_stage
T1 = T2    = 4498 Ma,  Tsec = 0
a0/b0/c0   = CDT,  a1/b1/c1 = (9.345, 10.37, 29.51)
μ = 8.63,  ω = 34.8,  κ ≈ 4.03
E1 = 0,  E2 = 0
```

**特点:** BSE (Bulk Silicate Earth) 演化模型。起始于 4498 Ma 的分异组成 (a1 > a0)，表示地球核幔分异后 BSE 已积累了一定放射性成因铅。

### 2.7 模型参数对照表

| 参数 | Geokit | Zhu93 | SK-2nd | SK-1st | CR-III | MM2020 |
|------|--------|-------|--------|--------|--------|--------|
| age_model | single | single | **two** | single | single | single |
| T1 (Ma) | 4430 | 4570 | **3700** | 4570 | 4509 | 4498 |
| T2 (Ma) | 4570 | 4570 | 4570 | 4570 | 4509 | 4498 |
| μ_M | 7.8 | 7.8 | 9.74 | 7.2 | 10.8 | 8.63 |
| ω_M | 31.51 | 31.51 | 36.84 | 33.2 | 41.2 | 34.8 |
| E1 | 0 | 0 | 0 | 0 | **5e-11** | 0 |
| E2 | 0 | 0 | 0 | 0 | **3.7e-11** | 0 |

---

## 3. 铅同位素演化方程

### 3.1 基本生长方程 (标准指数模型)

放射性衰变使得母体同位素 (U, Th) 转变为子体同位素 (Pb)。对于封闭体系，从时间 T（向前计时，距今）到时间 t 的铅同位素积累为:

```
²⁰⁶Pb/²⁰⁴Pb(t) = X₁ + μ × [exp(λ₂₃₈ × T₁) − exp(λ₂₃₈ × t)]
²⁰⁷Pb/²⁰⁴Pb(t) = Y₁ + ν × [exp(λ₂₃₅ × T₁) − exp(λ₂₃₅ × t)]
²⁰⁸Pb/²⁰⁴Pb(t) = Z₁ + ω × [exp(λ₂₃₂ × T₁) − exp(λ₂₃₂ × t)]
```

其中:
- (X₁, Y₁, Z₁) = 时间 T₁ 时的初始铅同位素比值
- μ = ²³⁸U/²⁰⁴Pb (源区)
- ν = ²³⁵U/²⁰⁴Pb = μ / 137.88
- ω = ²³²Th/²⁰⁴Pb (源区)
- T₁ = 模型起始时间 (距今，单位: 年)
- t = 当前时间点 (距今，单位: 年)，t < T₁

**注意:** 所有时间均以"距今年数"表示，T₁ > t > 0，t=0 为现在。

### 3.2 E 参数修正 (PbIso 约定)

对于 Cumming & Richards 等 μ 随时间变化的模型，PbIso 引入演化修正项:

```
f(λ, t, E) = exp(λ × t) × [1 − E × (t − 1/λ)]     当 E ≠ 0
f(λ, t, 0) = exp(λ × t)                               当 E = 0
```

代码实现为 `_exp_evolution_term(lmbda, t_years, E)`。

修正后的生长方程:

```
²⁰⁶Pb/²⁰⁴Pb(t) = X₁ + μ × [f(λ₂₃₈, T₁, E₁) − f(λ₂₃₈, t, E₁)]
²⁰⁷Pb/²⁰⁴Pb(t) = Y₁ + ν × [f(λ₂₃₅, T₁, E₁) − f(λ₂₃₅, t, E₁)]
²⁰⁸Pb/²⁰⁴Pb(t) = Z₁ + ω × [f(λ₂₃₂, T₁, E₂) − f(λ₂₃₂, t, E₂)]
```

**物理意义:** E 参数使得等效 μ 随时间线性增长，近似表示地幔分异导致的 U/Pb 比随时间递增。注意 ²⁰⁶Pb 和 ²⁰⁷Pb 使用 E₁ (铀衰变系)，²⁰⁸Pb 使用 E₂ (钍衰变系)。

### 3.3 单阶段模型

铅同位素从 CDT (a₀, b₀, c₀) 以恒定 μ 演化至今:

```
²⁰⁶Pb/²⁰⁴Pb = a₀ + μ × [exp(λ₂₃₈ × T₂) − exp(λ₂₃₈ × t)]
²⁰⁷Pb/²⁰⁴Pb = b₀ + ν × [exp(λ₂₃₅ × T₂) − exp(λ₂₃₅ × t)]
²⁰⁸Pb/²⁰⁴Pb = c₀ + ω × [exp(λ₂₃₂ × T₂) − exp(λ₂₃₂ × t)]
```

其中 T₂ = 地球年龄 (通常 4570 Ma)，t = 样品年龄 (矿石形成时间)。

### 3.4 两阶段模型 (Stacey-Kramers)

```
第一阶段 (4570 → 3700 Ma): μ₁ = 7.2, 从 (a₀, b₀, c₀) 演化到 (a₁, b₁, c₁)
第二阶段 (3700 Ma → 今): μ₂ = 9.74, 从 (a₁, b₁, c₁) 继续演化
```

第二阶段方程:
```
²⁰⁶Pb/²⁰⁴Pb = a₁ + μ₂ × [exp(λ₂₃₈ × Tsec) − exp(λ₂₃₈ × t)]
²⁰⁷Pb/²⁰⁴Pb = b₁ + ν₂ × [exp(λ₂₃₅ × Tsec) − exp(λ₂₃₅ × t)]
```

其中 Tsec = 3700 Ma (第二阶段起始时间)。

### 3.5 模型曲线生成

`calculate_modelcurve(t_Ma, params)` 使用通用框架生成任何模型的演化曲线:

```python
x = X1 + μ × [f(λ₈, T1, E1) − f(λ₈, t, E1)]
y = Y1 + (μ/U8U5) × [f(λ₅, T1, E1) − f(λ₅, t, E1)]
z = Z1 + ω × [f(λ₂, T1, E2) − f(λ₂, t, E2)]
```

输入一组时间数组 `t_Ma`，输出对应的三组同位素比值数组，可直接绘制为模型演化曲线。

---

## 4. 模式年龄计算

### 4.1 单阶段模式年龄 (Holmes-Houtermans)

**物理意义:** 假设样品铅的源区从 CDT 原始组成开始，以恒定 μ 演化到年龄 t 时产出矿石铅。单阶段年龄 t 可从 207/206 关系直接求解（无需知道 μ）。

**方程:**
消除 μ，对两个生长方程取比:

```
(²⁰⁷Pb/²⁰⁴Pb − b₀)     1     exp(λ₂₃₅ × T) − exp(λ₂₃₅ × t)
─────────────────── = ────── × ─────────────────────────────────
(²⁰⁶Pb/²⁰⁴Pb − a₀)   137.88   exp(λ₂₃₈ × T) − exp(λ₂₃₈ × t)
```

整理为零点问题:

```
f(t) = R − U_ratio × [exp(λ₅T) − exp(λ₅t)] / [exp(λ₈T) − exp(λ₈t)] = 0
```

其中 R = (Pb207 − b₀) / (Pb206 − a₀)。

**求解方法:** `_solve_age_scipy()` 使用 Brent 方法:
1. 检查端点 [−4700 Ma, +4700 Ma] 是否异号
2. 若否，在区间内均匀采样 200 个点扫描变号区间
3. 找到变号区间后用 `scipy.optimize.brentq` 精确求根 (xtol=1e-6 年)

**实现:** `calculate_single_stage_age()` (`age.py:67`)

### 4.2 两阶段模式年龄 (Stacey-Kramers)

**方程:** 与单阶段相同，但以第二阶段参数替代:

```
(²⁰⁷Pb/²⁰⁴Pb − b₁)     1     exp(λ₂₃₅ × Tsec) − exp(λ₂₃₅ × t)
─────────────────── = ────── × ────────────────────────────────────
(²⁰⁶Pb/²⁰⁴Pb − a₁)   137.88   exp(λ₂₃₈ × Tsec) − exp(λ₂₃₈ × t)
```

使用 (a₁, b₁) 和 Tsec=3700 Ma 替代 (a₀, b₀) 和 T₂。

**实现:** `calculate_two_stage_age()` (`age.py:135`)

### 4.3 Pb-Pb 年龄 (放射性成因比值)

对于含铀矿物 (如锆石)，测量的 ²⁰⁷Pb*/²⁰⁶Pb* 比值 (放射性成因部分) 与年龄的关系:

```
²⁰⁷Pb*/²⁰⁶Pb* = (1/137.88) × [exp(λ₂₃₅ × t) − 1] / [exp(λ₂₃₈ × t) − 1]
```

对于等时线斜率 (207/204 vs 206/204 图中)，其数学形式相同:

```
Slope = (1/137.88) × [exp(λ₂₃₅ × t) − 1] / [exp(λ₂₃₈ × t) − 1]
```

**误差传播:**
```
σ_t = |dt/dR| × σ_R
```

其中:
```
dR/dt = U_ratio × [λ₅ × exp(λ₅t) × (exp(λ₈t)−1) − (exp(λ₅t)−1) × λ₈ × exp(λ₈t)]
        ─────────────────────────────────────────────────────────────────────────────────
                                    [exp(λ₈t) − 1]²
```

**实现:** `calculate_pbpb_age_from_ratio()` (`isochron.py:256`)

---

## 5. Delta 值计算 (Δα, Δβ, Δγ)

### 5.1 定义

Delta 值描述样品铅同位素组成相对于同期地幔参考组成的偏差，以千分比 (‰) 表示:

```
Δα = [(²⁰⁶Pb/²⁰⁴Pb)_样品 / (²⁰⁶Pb/²⁰⁴Pb)_参考 − 1] × 1000
Δβ = [(²⁰⁷Pb/²⁰⁴Pb)_样品 / (²⁰⁷Pb/²⁰⁴Pb)_参考 − 1] × 1000
Δγ = [(²⁰⁸Pb/²⁰⁴Pb)_样品 / (²⁰⁸Pb/²⁰⁴Pb)_参考 − 1] × 1000
```

### 5.2 参考值计算

参考值是模型演化曲线在样品年龄 t 处的同位素组成。

**单阶段参考 (use_two_stage=False):**
```
ref₂₀₆ = a₀ + μ_M × [f(λ₂₃₈, T₂, E₁) − f(λ₂₃₈, t, E₁)]
ref₂₀₇ = b₀ + ν_M × [f(λ₂₃₅, T₂, E₁) − f(λ₂₃₅, t, E₁)]
ref₂₀₈ = c₀ + ω_M × [f(λ₂₃₂, T₂, E₂) − f(λ₂₃₂, t, E₂)]
```

**两阶段参考 (use_two_stage=True):**
```
ref₂₀₆ = a₁ + μ_M × [f(λ₂₃₈, Tsec, E₁) − f(λ₂₃₈, t, E₁)]
ref₂₀₇ = b₁ + ν_M × [f(λ₂₃₅, Tsec, E₁) − f(λ₂₃₅, t, E₁)]
ref₂₀₈ = c₁ + ω_M × [f(λ₂₃₂, Tsec, E₂) − f(λ₂₃₂, t, E₂)]
```

其中 f(λ, t, E) 为 E 参数修正的演化项 (见 §3.2)。

### 5.3 年龄选择

Delta 值计算需要每个样品的"年龄" t 作为输入:

| 模型类型 | 使用年龄 | 说明 |
|---------|---------|------|
| 两阶段 (SK 2nd) | tSK | 两阶段模式年龄 |
| 单阶段 (Geokit) | tCDT (T1=4430 Ma) | Geokit 惯例 |
| 其他单阶段 | tCDT (T2) | 标准单阶段年龄 |

**重要约定:** 每个样品使用各自的模式年龄来计算 Delta 值。若 t 为标量，则所有样品使用同一参考值；若 t 为与样品等长的数组，则每个样品对应各自的参考值 (通过 numpy 广播实现)。

**实现:** `calculate_deltas()` (`delta.py:8`)

---

## 6. V1-V2 判别图投影

### 6.1 概述

V1-V2 判别图将三维 (Δα, Δβ, Δγ) 数据投影到二维平面，保留主要变化趋势，便于区分不同构造环境的铅同位素特征。

### 6.2 方法一: Zhu (1993) 直接系数法

当 `v1v2_formula == 'zhu1993'` 时使用:

```
V1 = 0.44073 × Δα + 0.89764 × Δγ
V2 = 0.84204 × Δα + 0.34648 × Δβ − 0.41343 × Δγ
```

这组系数来自 Zhu (1993) 对全球矿石铅数据的统计分析，直接给出从 (Δα, Δβ, Δγ) 到 (V1, V2) 的线性变换。

### 6.3 方法二: 回归平面投影法 (默认)

**步骤 1: 定义回归平面**

在 (Δα, Δβ, Δγ) 空间中拟合一个平面:

```
Δγ = a + b × Δα + c × Δβ
```

默认参数 (Zhu 1995/1998):
```
a = 0.0,  b = 2.0367,  c = −6.143
```

平面法向量: **n** = (−b, −c, 1)，|**n**|² = 1 + b² + c²

**步骤 2: 数据点投影到平面**

将每个数据点 (Δα, Δβ, Δγ) 正交投影到平面上:

```
                (1 + c²) × Δα + b × (Δγ − c × Δβ − a)
Δα' = ─────────────────────────────────────────────────
                         1 + b² + c²

                (1 + b²) × Δβ + c × (Δγ − b × Δα − a)
Δβ' = ─────────────────────────────────────────────────
                         1 + b² + c²

Δγ' = a + b × Δα' + c × Δβ'   (在平面上)
```

**推导:** 从点 P 到平面的投影 P' 满足 PP' ∥ **n**:
```
P' = P − [(P·n − d) / |n|²] × n
```
展开后得到上述公式。

**步骤 3: 平面内坐标变换**

在平面上定义两个正交方向:

- **e₁** = (1, 0, b) / √(1 + b²) ——沿 Δα 方向
- **e₂** = (−cb, 1+b², c) / √((1+b²)(1+b²+c²)) ——垂直于 e₁

V1, V2 为投影点在平面内的坐标:

```
V1 = (Δα' + b × Δγ') / √(1 + b²)

V2 = √(1 + b² + c²) / √(1 + b²) × Δβ'
```

**V1** 反映样品在 Δα-Δγ 平面内的变化（主要受 U/Pb 比控制）。
**V2** 反映样品偏离 Δα-Δγ 趋势的程度（主要受 Th/U 比控制）。

**注意:** V2 公式假定 a = 0（回归平面过原点）。当 a ≠ 0 时存在一个 c×a 量级的缺失项，但所有预设模型 a = 0。

**实现:** `calculate_v1v2_coordinates()` (`delta.py:81`)

---

## 7. 源区参数反演

### 7.1 统一反演架构

所有源区参数反演函数共享同一核心公式，仅**参考参数**不同:

| 核心函数 | 求解 | 公式特征 |
|---------|------|---------|
| `_invert_mu` | μ (²³⁸U/²⁰⁴Pb) | 等时线斜率投影, 联合 206+207 约束 |
| `_invert_omega` | ω (²³²Th/²⁰⁴Pb) | ²⁰⁸Pb 生长方程直接求解 |
| `_invert_kappa` | κ (²³²Th/²³⁸U) | ²⁰⁶/²⁰⁸ 比值法消去 μ |

公共 API 为薄委托层，从 params 中选取参考点后调用核心函数:

| 公共函数 | X_ref | Y/Z_ref | T_ref | 说明 |
|---------|-------|---------|-------|------|
| `calculate_source_mu` | a₀ | b₀ | T₂ | 单阶段 CDT 参考 |
| `calculate_model_mu` | a₁ | b₁ | T₁ | 模型参考 (PbIso CalcMu) |
| `calculate_source_omega` | — | c₀ | T₂ | 单阶段 CDT 参考 |
| `calculate_model_kappa` | a₁ | c₁ | T₁ | 模型参考 (PbIso CalcKa) |

`calculate_all_parameters()` 根据 `resolve_age_model()` 结果**自动选择**参考参数:
- **单阶段模型** → 使用 CDT 参考 (a₀, b₀, c₀, T₂)
- **两阶段模型** → 使用模型参考 (a₁, b₁, c₁, T₁)

### 7.2 μ 反演公式 (_invert_mu)

**目标:** 已知样品的 (²⁰⁶Pb/²⁰⁴Pb, ²⁰⁷Pb/²⁰⁴Pb) 和年龄 t，反推源区的 ²³⁸U/²⁰⁴Pb 比值。

**方法:** 利用 ²⁰⁶Pb 和 ²⁰⁷Pb 两个约束联合求解。统一公式使用 (X_ref, Y_ref, T_ref) 参数化:

定义当今等时线斜率:
```
slope_t = U_ratio × [exp(λ₂₃₅ × t) − 1] / [exp(λ₂₃₈ × t) − 1]
```

定义放射性成因增量:
```
G₂₀₆ = exp(λ₂₃₈ × T_ref) − exp(λ₂₃₈ × t)
G₂₀₇ = U_ratio × [exp(λ₂₃₅ × T_ref) − exp(λ₂₃₅ × t)]
```

则:
```
        (²⁰⁷Pb − Y_ref) − slope_t × (²⁰⁶Pb − X_ref)
μ = ──────────────────────────────────────────────────────
                 G₂₀₇ − slope_t × G₂₀₆
```

**几何意义:** 沿当今等时线方向将样品投影回生长曲线，找到对应的 μ 值。当样品恰好位于生长曲线上时，此公式等价于直接从任一同位素方程求解 μ。当样品偏离生长曲线时 (实际数据的常态)，此公式给出两个同位素约束的加权组合。

**实现:** `_invert_mu()` (`source.py`), 公共入口 `calculate_source_mu()` 和 `calculate_model_mu()`

### 7.3 ω 反演公式 (_invert_omega)

```
ω = (²⁰⁸Pb/²⁰⁴Pb − Z_ref) / [exp(λ₂₃₂ × T_ref) − exp(λ₂₃₂ × t)]
```

**ν (²³⁵U/²⁰⁴Pb):**
```
ν = μ × U_ratio = μ / 137.88
```

**实现:** `_invert_omega()` (`source.py`), 公共入口 `calculate_source_omega()`

### 7.4 ν 衍生参数

**ν (²³⁵U/²⁰⁴Pb):**
```
ν = μ × U_ratio = μ / 137.88
```

**实现:** `calculate_source_nu()` (`source.py`)

### 7.5 κ 反演公式 (_invert_kappa)

反演源区 ²³²Th/²³⁸U 比值。统一公式使用 (X_ref, Z_ref, T_ref) 参数化:

```
        (z − Z_ref)   exp(λ₂₃₈ × T_ref) − exp(λ₂₃₈ × t)
κ = ────────────── × ──────────────────────────────────────
        (x − X_ref)   exp(λ₂₃₂ × T_ref) − exp(λ₂₃₂ × t)
```

其中 z = ²⁰⁸Pb/²⁰⁴Pb, x = ²⁰⁶Pb/²⁰⁴Pb。

**推导:** 从生长方程:
```
z − Z_ref = κ × μ × [exp(λ₂₃₂T_ref) − exp(λ₂₃₂t)]   (因为 ω = κμ)
x − X_ref = μ × [exp(λ₂₃₈T_ref) − exp(λ₂₃₈t)]
```
两式相除消去 μ 得到上述公式。

**实现:** `_invert_kappa()` (`source.py`), 公共入口 `calculate_model_kappa()`

---

## 8. 初始比值反演

### 8.1 初始 ²⁰⁶Pb/²⁰⁴Pb (Calc64in)

计算样品形成时 (年龄 t) 源区的 ²⁰⁶Pb/²⁰⁴Pb:

```
(²⁰⁶Pb/²⁰⁴Pb)_初始 = X₁ + μ × [exp(λ₂₃₈ × T₁) − exp(λ₂₃₈ × t)]
```

其中 μ 先由 CalcMu 公式求得 (§7.3)。

**物理意义:** 这是模型预测的源区在时间 t 的 206Pb/204Pb 组成——并非样品的实测初始比值，而是模型框架下的计算值。

**实现:** `calculate_initial_ratio_64()` (`source.py:185`)

### 8.2 初始 ²⁰⁷Pb/²⁰⁴Pb (Calc74in)

```
(²⁰⁷Pb/²⁰⁴Pb)_初始 = Y₁ + (μ / U8U5) × [exp(λ₂₃₅ × T₁) − exp(λ₂₃₅ × t)]
```

**实现:** `calculate_initial_ratio_74()` (`source.py:220`)

### 8.3 初始 ²⁰⁸Pb/²⁰⁴Pb (Calc84in)

需要同时求解 μ 和 κ:

```
步骤 1: μ = CalcMu(x, y, t)           (同 §7.3)
步骤 2: κ = CalcKa(x, z, t)           (同 §7.4)
步骤 3: ω = κ × μ
步骤 4: (²⁰⁸Pb/²⁰⁴Pb)_初始 = Z₁ + ω × [exp(λ₂₃₂ × T₁) − exp(λ₂₃₂ × t)]
```

**实现:** `calculate_initial_ratio_84()` (`source.py:254`)

---

## 9. 等时线计算

### 9.1 古等时线 (Paleoisochron)

古等时线是在铅同位素演化图上连接具有相同年龄 t、不同源区 μ 的样品组成的直线。

#### 9.1.1 207Pb/204Pb vs 206Pb/204Pb 图 (PB_EVOL_76)

在这组坐标下，年龄为 t 的等时线斜率:

```
                exp(λ₂₃₅ × T₁) − exp(λ₂₃₅ × t)
slope₇₆ = ──────────────────────────────────────────
            U8U5 × [exp(λ₂₃₈ × T₁) − exp(λ₂₃₈ × t)]
```

截距 (等时线通过模型起始点 (X₁, Y₁)):
```
intercept₇₆ = Y₁ − slope₇₆ × X₁
```

**推导:** 对于不同 μ 的源区在时间 t 的组成:
```
x = X₁ + μ × [exp(λ₈T₁) − exp(λ₈t)]
y = Y₁ + (μ/U8U5) × [exp(λ₅T₁) − exp(λ₅t)]
```
消去 μ 即得斜率公式。等时线过 (X₁, Y₁) 是因为 μ=0 时 x=X₁, y=Y₁。

#### 9.1.2 208Pb/204Pb vs 206Pb/204Pb 图 (PB_EVOL_86)

```
                ω_M     exp(λ₂₃₂ × T₁) − exp(λ₂₃₂ × t)
slope₈₆ = ──── × ────────────────────────────────────────
                μ_M     exp(λ₂₃₈ × T₁) − exp(λ₂₃₈ × t)

           = κ × [exp(λ₂₃₂ × T₁) − exp(λ₂₃₂ × t)]
                  ────────────────────────────────────
                  [exp(λ₂₃₈ × T₁) − exp(λ₂₃₈ × t)]
```

其中 κ = ω_M / μ_M (模型的 Th/U 比)。

截距:
```
intercept₈₆ = Z₁ − slope₈₆ × X₁
```

**假设:** 208/206 等时线要求所有源区具有相同的 κ (Th/U 比)。这是一个强假设，实际地质过程中不同源区的 κ 可能不同。

**实现:** `calculate_paleoisochron_line()` (`isochron.py:32`)

### 9.2 等时线生长曲线

#### 9.2.1 207/206 生长曲线 (Isochron1)

已知等时线 (slope, intercept) 和年龄 t，反演源区 μ 并绘制该源区从 T₁ 到 0 的完整演化路径。

**步骤 1: 反演源区 μ**

等时线上的模型点满足:
```
y = slope × x + intercept
```

代入生长方程:
```
Y₁ + μ × C_β = slope × (X₁ + μ × C_α) + intercept
```

其中:
```
C_α = f(λ₈, T₁, E₁) − f(λ₈, t, E₁)    (206Pb 增量因子)
C_β = U_ratio × [f(λ₅, T₁, E₁) − f(λ₅, t, E₁)]  (207Pb 增量因子)
```

求解:
```
μ_source = (slope × X₁ + intercept − Y₁) / (C_β − slope × C_α)
```

**步骤 2: 生成生长曲线**

在时间网格 t_steps ∈ [0, T₁] 上:
```
x(t) = X₁ + μ_source × [f(λ₈, T₁, E₁) − f(λ₈, t, E₁)]
y(t) = Y₁ + μ_source × U_ratio × [f(λ₅, T₁, E₁) − f(λ₅, t, E₁)]
```

**实现:** `calculate_isochron1_growth_curve()` (`isochron.py:84`)

#### 9.2.2 208/206 生长曲线 (Isochron2)

需要同时利用 207/206 和 208/206 等时线信息:

1. 从 208/206 斜率反演 κ_source (§9.3.2)
2. 从 207/206 等时线反演 μ_source (§9.3.1)
3. 计算 ω_source = μ_source × κ_source
4. 生成 208/204 vs 206/204 演化曲线:

```
x(t) = X₁ + μ_source × [f(λ₈, T₁, E₁) − f(λ₈, t, E₁)]
z(t) = Z₁ + ω_source × [f(λ₂, T₁, E₂) − f(λ₂, t, E₂)]
```

**实现:** `calculate_isochron2_growth_curve()` (`isochron.py:133`)

### 9.3 从等时线参数反演源区特征

#### 9.3.1 从等时线反演 μ

```
            slope × a₁ + intercept − b₁
μ_source = ───────────────────────────────
            C₂ − slope × C₁
```

其中:
```
C₁ = exp(λ₂₃₈ × T₁) − exp(λ₂₃₈ × t)
C₂ = U_ratio × [exp(λ₂₃₅ × T₁) − exp(λ₂₃₅ × t)]
```

**实现:** `calculate_source_mu_from_isochron()` (`isochron.py:313`)

#### 9.3.2 从 208/206 斜率反演 κ

```
                      exp(λ₂₃₈ × T₁) − exp(λ₂₃₈ × t)
κ_source = slope₈₆ × ────────────────────────────────────
                      exp(λ₂₃₂ × T₁) − exp(λ₂₃₂ × t)
```

**实现:** `calculate_source_kappa_from_slope()` (`isochron.py:329`)

---

## 10. York 回归

### 10.1 算法概述

York (2004) 加权最小二乘回归，适用于 x 和 y 均有测量误差且可能存在相关性的情况。拟合模型: y = a + bx。

### 10.2 权重计算

每个数据点的权重:

```
ω_X_i = 1 / σ²_X_i
ω_Y_i = 1 / σ²_Y_i
α_i = √(ω_X_i × ω_Y_i)

W_i = (ω_X_i × ω_Y_i) / (ω_X_i + b² × ω_Y_i − 2b × r_i × α_i)
```

其中 r_i 为 x_i 和 y_i 测量误差的相关系数。

### 10.3 迭代求解

以普通最小二乘斜率为初始值，迭代直到收敛:

```
X̄ = Σ(W_i × x_i) / Σ(W_i)
Ȳ = Σ(W_i × y_i) / Σ(W_i)
U_i = x_i − X̄
V_i = y_i − Ȳ

β_i = W_i × [U_i/ω_Y_i + b × V_i/ω_X_i − (b × U_i + V_i) × r_i / α_i]

b_new = Σ(W_i × β_i × V_i) / Σ(W_i × β_i × U_i)
```

收敛条件: `(b_old/b_new − 1)² < 10⁻¹⁵`，最大迭代 50 次。

### 10.4 截距与误差

```
a = Ȳ − b × X̄

x̂_i = X̄ + β_i        (调整后 x 值)
x̄ = Σ(W_i × x̂_i) / Σ(W_i)
u_i = x̂_i − x̄

σ_b = √[1 / Σ(W_i × u_i²)]
σ_a = √[1/Σ(W_i) + (x̄ × σ_b)²]
cov(a, b) = −x̄ × σ_b²
```

### 10.5 MSWD (Mean Squared Weighted Deviation)

```
χ² = Σ W_i × (y_i − b × x_i − a)²
MSWD = χ² / (n − 2)
```

- MSWD ≈ 1: 数据散布与分析误差一致
- MSWD >> 1: 存在地质散布或模型不适用
- MSWD << 1: 误差可能被高估

p 值: `1 − CDF_χ²(χ², n−2)` (χ² 分布)

**实现:** `york_regression()` (`isochron.py:179`)

---

## 11. 计算流程集成

### 11.1 主入口: calculate_all_parameters()

`__init__.py` 中的集成函数按以下顺序编排所有计算:

```
输入: Pb206/204, Pb207/204, Pb208/204 (数组), 可选 t_Ma

┌─ 步骤 1: 确定年龄模型 (resolve_age_model)
│   ├─ 优先读取 params['age_model'] 标志
│   ├─ 回退: 根据模型名称推断 (Geokit→single, SK 2nd→two)
│   └─ 再回退: 检查 Tsec 和 a0/a1 差异
│
├─ 步骤 2: 计算模式年龄
│   ├─ tCDT: 单阶段年龄 (Geokit 用 T1, 其余用 T2)
│   ├─ tSK: 两阶段年龄 (使用 Tsec/a1/b1)
│   └─ t_model: 根据 age_model 选择 tCDT 或 tSK
│
├─ 步骤 3: 确定输入年龄 t_input
│   ├─ 若用户提供 t_Ma → 使用用户值 (NaN 回退到 t_model)
│   └─ 否则 → 使用 t_model
│
├─ 步骤 4: 计算 Delta 值
│   ├─ 两阶段: calculate_deltas(use_two_stage=True, t=tSK)
│   └─ 单阶段: calculate_deltas(use_two_stage=False, t=tCDT)
│
├─ 步骤 5: 计算 V1-V2 坐标
│   └─ calculate_v1v2_coordinates(Δα, Δβ, Δγ)
│
├─ 步骤 6: 源区参数反演 (使用 t_input)
│   ├─ 自动选择参考: single_stage → (a0/b0/c0, T2), two_stage → (a1/b1/c1, T1)
│   ├─ μ, ν, ω — 模型自动匹配参考
│   ├─ μ_model, κ_model — 始终使用模型参考 (a1/b1/c1, T1)
│   └─ ω_model = κ_model × μ_model
│
└─ 步骤 7: 初始比值反演 (使用 t_input)
    ├─ Init_206_204 — Calc64in
    ├─ Init_207_204 — Calc74in
    └─ Init_208_204 — Calc84in
```

### 11.2 输出字典

| 键 | 类型 | 说明 |
|----|------|------|
| `Pb206_204_S` | array | 输入数据 (回传) |
| `Pb207_204_S` | array | 输入数据 |
| `Pb208_204_S` | array | 输入数据 |
| `tCDT (Ma)` | array | 单阶段模式年龄 |
| `tSK (Ma)` | array | 两阶段模式年龄 |
| `Delta_alpha` | array | Δα (‰) |
| `Delta_beta` | array | Δβ (‰) |
| `Delta_gamma` | array | Δγ (‰) |
| `V1` | array | V1 判别坐标 |
| `V2` | array | V2 判别坐标 |
| `mu` | array | 单阶段源区 μ |
| `nu` | array | 单阶段源区 ν |
| `omega` | array | 单阶段源区 ω |
| `mu_model` | array | 模型源区 μ (CalcMu) |
| `kappa_model` | array | 模型源区 κ (CalcKa) |
| `omega_model` | array | 模型源区 ω (= κ × μ) |
| `Init_206_204` | array | 初始 ²⁰⁶Pb/²⁰⁴Pb |
| `Init_207_204` | array | 初始 ²⁰⁷Pb/²⁰⁴Pb |
| `Init_208_204` | array | 初始 ²⁰⁸Pb/²⁰⁴Pb |

---

## 12. 数值安全与实现细节

### 12.1 除零保护

所有涉及除法的位置均使用阈值 ε = 10⁻⁵⁰ 进行保护:

```python
denominator = np.where(np.abs(denominator) < 1e-50, 1e-50, denominator)
```

### 12.2 年龄求解稳定性

`_solve_age_scipy()` 的 Brent 算法要求函数在区间端点异号。当端点不异号时，自动在 [−4700 Ma, +4700 Ma] 范围内扫描 200 个等距点寻找变号子区间。允许负年龄以处理"超放射性成因"样品。

### 12.3 数组与标量兼容

所有函数支持标量和 numpy 数组输入。标量输入在内部转为 0-d 数组处理，结果保持对应形状。年龄函数中，标量使用优化的单次求解路径，数组逐元素循环求解。

### 12.4 E 参数注意事项

E 参数仅影响模型曲线 (`calculate_modelcurve`) 和 Delta 值 (`calculate_deltas`) 的参考曲线计算。模式年龄计算始终使用标准指数衰变方程 (E=0)，与 PbIso R 包的行为一致。

---

## 13. 已知约定与注意事项

### 13.1 时间约定

所有内部计算使用"距今年数" (年) 为单位。外部 API 接受/返回百万年 (Ma)。内部转换:
```
t_years = t_Ma × 10⁶
```

### 13.2 Geokit 模型的 T 不一致性

V1V2 (Geokit) 模型中:
- 年龄计算使用 T₁ = 4430 Ma
- 源区参数反演使用 T₂ = 4570 Ma
- Delta 参考曲线使用 T₂ = 4570 Ma

这是 Geokit 软件的原始设计约定。从物理角度看，年龄 t 是相对于 T₁ 的模式年龄，将其代入以 T₂ 为基准的方程存在概念上的混合。但这一做法被广泛采用并具有良好的经验效果。

### 13.3 tSK 在 Tsec=0 模型下的行为

对于 Zhu 1993、Cumming & Richards、Maltese & Mezger 等 Tsec=0 的模型，`calculate_two_stage_age()` 使用 T=0 求解，产生无物理意义的结果。`calculate_all_parameters()` 对这些模型不使用 tSK 进行后续计算，但 tSK 仍被导出到结果字典中。

### 13.4 投影方向选择

`calculate_source_mu()` 使用**当今等时线斜率** `u_ratio × (exp λ₅t − 1)/(exp λ₈t − 1)` 作为投影方向，而非**地球等时线 (geochron) 斜率** `u_ratio × (exp λ₅T − exp λ₅t)/(exp λ₈T − exp λ₈t)`。二者在数学上不等价 (除 t → 0 极限)。当今等时线斜率是 Geokit 和 PbIso 的共同约定。

### 13.5 源区参数的物理有效性

反演结果可能包含负值 (μ < 0, κ < 0)，这在物理上无意义，表明样品不符合所选模型的假设。代码不对结果进行截断或警告，用户需自行判断。

### 13.6 V2 公式的近似

当回归平面偏移量 a ≠ 0 时，V2 公式缺少 `c×a / √((1+b²)(1+b²+c²))` 修正项。所有预设模型 a=0，此近似无实际影响。自定义参数应避免设置 a≠0，或在分析中注意此限制。

---

## 14. API 速查表

### 14.1 年龄计算

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `calculate_single_stage_age` | 206, 207 | tCDT (Ma) | Holmes-Houtermans |
| `calculate_two_stage_age` | 206, 207 | tSK (Ma) | SK 两阶段 |
| `calculate_pbpb_age_from_ratio` | ²⁰⁷Pb*/²⁰⁶Pb* | age, σ_age | 放射性成因比值 |
| `calculate_isochron_age_from_slope` | slope | age (Ma) | 等时线斜率 |

### 14.2 Delta 与 V1V2

| 函数 | 输入 | 输出 |
|------|------|------|
| `calculate_deltas` | 206, 207, 208, t_Ma | (Δα, Δβ, Δγ) |
| `calculate_v1v2_coordinates` | Δα, Δβ, Δγ | (V1, V2) |

### 14.3 源区反演

| 函数 | 框架 | 输出 | PbIso 对应 |
|------|------|------|-----------|
| `calculate_source_mu` | 单阶段 (a₀/T₂) | μ | — |
| `calculate_source_omega` | 单阶段 (c₀/T₂) | ω | — |
| `calculate_source_nu` | 衍生 | ν = μ × U_ratio | — |
| `calculate_model_mu` | 模型 (a₁/T₁) | μ | CalcMu |
| `calculate_model_kappa` | 模型 (a₁c₁/T₁) | κ | CalcKa |

### 14.4 初始比值

| 函数 | 输出 | PbIso 对应 |
|------|------|-----------|
| `calculate_initial_ratio_64` | Init ²⁰⁶/²⁰⁴ | Calc64in |
| `calculate_initial_ratio_74` | Init ²⁰⁷/²⁰⁴ | Calc74in |
| `calculate_initial_ratio_84` | Init ²⁰⁸/²⁰⁴ | Calc84in |

### 14.5 等时线

| 函数 | 输入 | 输出 |
|------|------|------|
| `calculate_paleoisochron_line` | age, algorithm | (slope, intercept) |
| `calculate_isochron1_growth_curve` | slope, intercept, age | {x, y, μ_source, t_steps} |
| `calculate_isochron2_growth_curve` | slope₈, slope₇, int₇, age | {x, y, μ_source, κ_source, t_steps} |
| `york_regression` | x, σx, y, σy, rxy | {a, b, σa, σb, mswd, ...} |
| `calculate_source_mu_from_isochron` | slope, intercept, age | μ_source |
| `calculate_source_kappa_from_slope` | slope₈₆, age | κ_source |

### 14.6 集成入口

```python
calculate_all_parameters(Pb206, Pb207, Pb208, t_Ma=None, a=None, b=None, c=None)
→ dict  # 含 19 个键的完整结果集 (见 §11.2)
```
