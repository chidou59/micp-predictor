# MICP Predictor · 科研级加固效果预测软件

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![scikit--learn](https://img.shields.io/badge/ML-scikit--learn-F7931E?logo=scikitlearn&logoColor=white)
![CI](https://github.com/chidou59/micp-predictor/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

这是一个 Python + CustomTkinter 桌面程序，用于从 `数据表.xlsx` 训练 MICP 加固效果预测模型，并预测 `UCS/kpa` 与 `CCC`。

## 快速开始

需要 Python 3.11 或更高版本。

```powershell
git clone https://github.com/chidou59/micp-predictor.git
cd micp-predictor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Windows 用户也可以先运行 `install_deps.bat`，再运行 `run_app.bat`。在“数据”页导入符合字段规范的 Excel，在“建模”页训练并选择 UCS/CCC 模型，最后进入“预测”页输入参数。

## 新版能力

- 数据质量：字段缺失率、异常值、目标跨度、论文分组画像。
- 清洗预览：显示原始值、清洗值、区间取均值、缺失和自动计算体积。
- 特征工程：自动生成高径比、单位体积用量、总 CaCl2 指标、总尿素指标、钙尿素比和胶结处理强度。
- 算法比较：Ridge-log、Huber-log、ElasticNet-log、SVR-log、KernelRidge-log、GradientBoosting-log、RandomForest、ExtraTrees、GaussianProcess-log。
- 验证诊断：随机 K 折、重复 K 折、按论文分组、重复论文分组、论文误差、特征重要性、原始输入影响分析。
- 模型选择台：按验证指标自动选择最佳模型，或为 UCS/CCC 手动指定已训练算法后再预测。
- 粒子进度：训练、可信预测和批量预测均使用动态粒子进度浮层，避免长任务像卡死。
- 可信预测：输出预测值、log 分位数提升树 + 残差校准参考区间、训练范围诊断、最近训练样本和可信度等级。
- 批量预测：导入 Excel 批量输出 UCS/CCC 预测和诊断提示。
- 模型管理：自动保存模型版本历史，可导出训练报告和验证图。

## 科研使用建议

当前数据量较小且跨论文差异明显。随机 K 折分数只能说明数据内部插值能力，科研解释时应优先查看“按论文分组”和“重复论文分组”验证结果。软件输出的是辅助预测和风险提示，不等同于工程设计保证值。

## 数据与隐私

真实研究数据、训练模型和生成报告不会进入 Git。仓库只提供程序和字段说明。请确认你有权使用导入的数据，并在分享结果前去除论文作者之外的个人或机构敏感信息。

输入字段见 [`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md)，模型边界和完整数据流见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

## 项目结构

```text
micp-predictor/
├─ app.py                    CustomTkinter 桌面界面
├─ micp_model.py             数据、训练、验证与预测核心
├─ docs/                     架构与输入字段说明
└─ requirements.txt         运行依赖
```

## 许可证

本项目采用 [MIT License](LICENSE)。
