from __future__ import annotations

import json
import math
import re
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal

import numpy as np
import pandas as pd

MissingStrategy = Literal["median", "complete"]
AlgorithmMode = Literal["auto", "all", "manual"]
ValidationKind = Literal["random_kfold", "repeated_kfold", "group_kfold", "repeated_group_kfold"]
FeatureMode = Literal["original", "engineered", "all"]
SHEET_NAME = "Sheet1"
TARGETS = ["UCS/kpa", "CCC"]
GROUP_COLUMN_INDEX = 1


@dataclass(frozen=True)
class FeatureSpec:
    key: str
    label: str
    column: str | None
    unit: str = ""
    source: Literal["input", "computed", "engineered"] = "input"


@dataclass
class PaperSummary:
    paper: str
    rows: int
    ucs_count: int
    ccc_count: int
    complete_inputs: int
    max_missing_rate: float
    ucs_range: tuple[float, float] | None
    ccc_range: tuple[float, float] | None


@dataclass
class DatasetProfile:
    row_count: int
    feature_complete_rows: int
    group_count: int
    group_column: str | None
    missing_rates: dict[str, float]
    target_ranges: dict[str, tuple[float, float, float]]
    target_spans: dict[str, float]
    recommended_algorithms: list[str]
    recommendation_reason: str
    warnings: list[str] = field(default_factory=list)
    data_issues: list[str] = field(default_factory=list)
    paper_summaries: list[PaperSummary] = field(default_factory=list)
    outlier_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class DatasetInfo:
    file_path: Path
    sheet_name: str
    row_count: int
    column_count: int
    numeric_counts: dict[str, int]
    target_counts: dict[str, int]
    preview: list[dict[str, Any]]
    cleaning_preview: list[dict[str, Any]]
    profile: DatasetProfile


@dataclass(frozen=True)
class AlgorithmSpec:
    name: str
    label: str
    uses_log_target: bool
    description: str
    factory: Callable[[str | None, dict[str, Any], dict[str, Any] | None], Any]
    candidate_params: tuple[dict[str, Any], ...] = ({},)


@dataclass
class Metrics:
    rmse: float
    mae: float
    r2: float


@dataclass
class ValidationResult:
    algorithm_name: str
    algorithm_label: str
    target: str
    validation_kind: ValidationKind
    sample_count: int
    fold_count: int
    metrics: Metrics
    y_true: list[float]
    y_pred: list[float]
    paper_errors: list[dict[str, Any]] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class TargetTrainingResult:
    target: str
    sample_count: int
    group_count: int
    best_algorithm: str
    best_algorithm_label: str
    best_params: dict[str, Any]
    selected_validation: ValidationKind
    uses_log_target: bool
    random_metrics: Metrics
    repeated_metrics: Metrics | None
    group_metrics: Metrics | None
    repeated_group_metrics: Metrics | None
    validation_results: list[ValidationResult]
    feature_importance: list[tuple[str, float]]
    input_impacts: list[dict[str, Any]]
    residual_p80: float
    residual_p95: float
    generalization_risk: str
    risk_reason: str
    warning: str | None


@dataclass
class TrainingReport:
    missing_strategy: MissingStrategy
    algorithm_mode: AlgorithmMode
    feature_mode: FeatureMode
    selected_algorithms: list[str]
    primary_validation: ValidationKind
    results: dict[str, TargetTrainingResult]
    data_file: str | None = None
    trained_at: str = ""
    model_path: Path | None = None


@dataclass
class SimilarSample:
    target: str
    distance: float
    row_number: int
    observed: float
    feature_summary: str


@dataclass
class PredictionDiagnostics:
    predictions: dict[str, float]
    intervals: dict[str, tuple[float, float]]
    nearest_distance: float
    out_of_range_features: list[str]
    messages: list[str]
    specimen_volume_mm3: float
    engineered_values: dict[str, float]
    similar_samples: list[SimilarSample]
    confidence_level: str


INPUT_FEATURES: list[FeatureSpec] = [
    FeatureSpec("od600", "OD600", "OD600"),
    FeatureSpec("urease_activity", "脲酶活性", "脲酶活性U/ml", "U/ml"),
    FeatureSpec("d50", "中值粒径 D50", "中值粒径D50", "mm"),
    FeatureSpec("height_mm", "试样高度", "试样高度mm", "mm"),
    FeatureSpec("inner_diameter_mm", "试样内径", "试样内径mm", "mm"),
    FeatureSpec("bacteria_solution_amount", "菌液用量", "菌液用量"),
    FeatureSpec("cacl2_concentration", "胶结液浓度-氯化钙", "胶结液浓度-氯化钙", "mol/L"),
    FeatureSpec("urea_concentration", "胶结液浓度-尿素", "胶结液浓度-尿素", "mol/L"),
    FeatureSpec("cementation_treatments", "胶结液处理次数", "胶结液处理次数", "次"),
    FeatureSpec("cementation_total_amount", "胶结液总用量", "胶结液总用量"),
]
COMPUTED_FEATURES = [FeatureSpec("specimen_volume_mm3", "试样体积", None, "mm3", "computed")]
ENGINEERED_FEATURES: list[FeatureSpec] = [
    FeatureSpec("aspect_ratio", "高径比", None, "", "engineered"),
    FeatureSpec("bacteria_per_volume", "单位体积菌液用量", None, "", "engineered"),
    FeatureSpec("cementation_per_volume", "单位体积胶结液用量", None, "", "engineered"),
    FeatureSpec("cacl2_total_index", "总 CaCl2 用量指标", None, "", "engineered"),
    FeatureSpec("urea_total_index", "总尿素用量指标", None, "", "engineered"),
    FeatureSpec("ca_urea_ratio", "钙尿素比", None, "", "engineered"),
    FeatureSpec("cementation_intensity", "胶结处理强度", None, "", "engineered"),
]
FEATURES = INPUT_FEATURES + COMPUTED_FEATURES
ALL_FEATURES = INPUT_FEATURES + COMPUTED_FEATURES + ENGINEERED_FEATURES
USER_INPUT_FEATURES = INPUT_FEATURES
BASE_MODEL_FEATURES = [f.key for f in INPUT_FEATURES + COMPUTED_FEATURES]
ENGINEERED_MODEL_FEATURES = [f.key for f in ENGINEERED_FEATURES]


class DataValidationError(ValueError):
    pass


def parse_numeric(value: Any) -> float:
    if value is None or pd.isna(value):
        return float("nan")
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip()
    if not text:
        return float("nan")
    normalized = text.replace("～", "-").replace("~", "-").replace("—", "-").replace("–", "-").replace("至", "-").replace("－", "-")
    numbers = re.findall(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", normalized)
    if not numbers:
        return float("nan")
    return float(np.mean([float(number) for number in numbers]))


def parse_status(value: Any, parsed: float, computed: bool = False) -> str:
    if computed:
        return "自动计算"
    if value is None or pd.isna(value) or str(value).strip() == "":
        return "缺失"
    text = str(value)
    if any(mark in text for mark in ["-", "～", "~", "—", "–", "至", "－"]) and len(re.findall(r"\d", text)) >= 2:
        return "区间取均值"
    if not np.isfinite(parsed):
        return "无法解析"
    return "原始数值"


def calculate_volume(height_mm: float, inner_diameter_mm: float) -> float:
    if not np.isfinite(height_mm) or not np.isfinite(inner_diameter_mm):
        return float("nan")
    return math.pi * (inner_diameter_mm / 2.0) ** 2 * height_mm


def safe_divide(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return float("nan")
    return float(numerator / denominator)


def add_engineered_features(df: pd.DataFrame) -> None:
    df["aspect_ratio"] = [safe_divide(h, d) for h, d in zip(df["height_mm"], df["inner_diameter_mm"], strict=False)]
    df["bacteria_per_volume"] = [safe_divide(v, vol) for v, vol in zip(df["bacteria_solution_amount"], df["specimen_volume_mm3"], strict=False)]
    df["cementation_per_volume"] = [safe_divide(v, vol) for v, vol in zip(df["cementation_total_amount"], df["specimen_volume_mm3"], strict=False)]
    df["cacl2_total_index"] = df["cacl2_concentration"] * df["cementation_total_amount"]
    df["urea_total_index"] = df["urea_concentration"] * df["cementation_total_amount"]
    df["ca_urea_ratio"] = [safe_divide(ca, urea) for ca, urea in zip(df["cacl2_concentration"], df["urea_concentration"], strict=False)]
    df["cementation_intensity"] = ((df["cacl2_concentration"] + df["urea_concentration"]) / 2.0) * df["cementation_treatments"]


def prepare_features(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame(index=raw_df.index)
    for feature in USER_INPUT_FEATURES:
        df[feature.key] = raw_df[feature.column].map(parse_numeric)
    df["specimen_volume_mm3"] = [calculate_volume(h, d) for h, d in zip(df["height_mm"], df["inner_diameter_mm"], strict=False)]
    add_engineered_features(df)
    for target in TARGETS:
        df[target] = raw_df[target].map(parse_numeric)
    return df


def extract_groups(raw_df: pd.DataFrame | None, index: pd.Index | None = None) -> pd.Series:
    if raw_df is None:
        return pd.Series(["unknown"] * (0 if index is None else len(index)), index=index)
    if raw_df.shape[1] <= GROUP_COLUMN_INDEX:
        groups = pd.Series(["unknown"] * len(raw_df), index=raw_df.index)
    else:
        groups = raw_df.iloc[:, GROUP_COLUMN_INDEX].ffill().fillna("unknown").astype(str)
    return groups.loc[index] if index is not None else groups


def load_dataset(file_path: str | Path, sheet_name: str = SHEET_NAME) -> tuple[pd.DataFrame, pd.DataFrame, DatasetInfo]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{path}")
    raw_df = pd.read_excel(path, sheet_name=sheet_name)
    if raw_df.empty:
        raise DataValidationError(f"{sheet_name} 中没有可用于训练的数据。")
    required_columns = [feature.column for feature in USER_INPUT_FEATURES] + TARGETS
    missing_columns = [str(column) for column in required_columns if column not in raw_df.columns]
    if missing_columns:
        raise DataValidationError("Excel 缺少必要列：" + "、".join(missing_columns))
    prepared_df = prepare_features(raw_df)
    profile = build_dataset_profile(raw_df, prepared_df)
    numeric_counts = {feature.label: int(prepared_df[feature.key].notna().sum()) for feature in ALL_FEATURES}
    target_counts = {target: int(prepared_df[target].notna().sum()) for target in TARGETS}
    preview_columns = [feature.key for feature in ALL_FEATURES] + TARGETS
    preview = prepared_df[preview_columns].head(30).replace({np.nan: None}).to_dict(orient="records")
    return raw_df, prepared_df, DatasetInfo(path, sheet_name, int(raw_df.shape[0]), int(raw_df.shape[1]), numeric_counts, target_counts, preview, build_cleaning_preview(raw_df, prepared_df), profile)


def build_cleaning_preview(raw_df: pd.DataFrame, prepared_df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    groups = extract_groups(raw_df)
    for idx in raw_df.index[:30]:
        row: dict[str, Any] = {"行号": int(idx) + 2, "论文": groups.loc[idx]}
        for feature in USER_INPUT_FEATURES:
            raw_value = raw_df.at[idx, feature.column]
            parsed = prepared_df.at[idx, feature.key]
            row[feature.label] = raw_value
            row[f"{feature.label} 清洗值"] = None if not np.isfinite(parsed) else float(parsed)
            row[f"{feature.label} 状态"] = parse_status(raw_value, parsed)
        volume = prepared_df.at[idx, "specimen_volume_mm3"]
        row["试样体积 清洗值"] = None if not np.isfinite(volume) else float(volume)
        row["试样体积 状态"] = parse_status(None, volume, True)
        rows.append(row)
    return rows


def build_dataset_profile(raw_df: pd.DataFrame, prepared_df: pd.DataFrame) -> DatasetProfile:
    feature_keys = [feature.key for feature in FEATURES]
    complete_rows = int(prepared_df[feature_keys].dropna().shape[0])
    missing_rates = {feature.label: float(prepared_df[feature.key].isna().mean()) for feature in ALL_FEATURES}
    target_ranges: dict[str, tuple[float, float, float]] = {}
    target_spans: dict[str, float] = {}
    for target in TARGETS:
        series = prepared_df[target].dropna()
        target_ranges[target] = (float(series.min()) if not series.empty else float("nan"), float(series.median()) if not series.empty else float("nan"), float(series.max()) if not series.empty else float("nan"))
        positive = series[series > 0]
        target_spans[target] = float(positive.max() / positive.min()) if not positive.empty else float("nan")
    groups = extract_groups(raw_df)
    group_count = int(groups[prepared_df[TARGETS].notna().any(axis=1)].nunique())
    max_missing = max(missing_rates.values()) if missing_rates else 0.0
    warnings: list[str] = []
    issues: list[str] = []
    if group_count < 5:
        warnings.append("论文分组数量较少，跨论文泛化评估会有较高不确定性。")
    if complete_rows < 25:
        warnings.append("完整输入样本偏少，建议优先使用中位数补全并补充实验数据。")
    if max_missing > 0.4:
        warnings.append("部分关键输入缺失率较高，模型结论应结合数据来源审查。")
    for target, span in target_spans.items():
        if np.isfinite(span) and span > 100:
            issues.append(f"{target} 跨度约 {span:.0f} 倍，推荐使用 log 目标变换并重点查看残差。")
    reason = "当前数据小样本、目标跨度大且缺失较多，推荐 Huber-log、SVR-log、KernelRidge-log 与 GradientBoosting-log，并用树模型对照非线性关系。"
    group_column = str(raw_df.columns[GROUP_COLUMN_INDEX]) if raw_df.shape[1] > GROUP_COLUMN_INDEX else None
    return DatasetProfile(int(raw_df.shape[0]), complete_rows, group_count, group_column, missing_rates, target_ranges, target_spans, recommend_algorithms(prepared_df, group_count, max_missing), reason, warnings, issues, build_paper_summaries(raw_df, prepared_df, groups), detect_outliers(prepared_df))


def build_paper_summaries(raw_df: pd.DataFrame, prepared_df: pd.DataFrame, groups: pd.Series) -> list[PaperSummary]:
    summaries: list[PaperSummary] = []
    feature_keys = [feature.key for feature in FEATURES]
    for paper, idx in groups.groupby(groups).groups.items():
        part = prepared_df.loc[list(idx)]
        def rng(target: str) -> tuple[float, float] | None:
            series = part[target].dropna()
            return None if series.empty else (float(series.min()), float(series.max()))
        summaries.append(PaperSummary(str(paper), int(part.shape[0]), int(part["UCS/kpa"].notna().sum()), int(part["CCC"].notna().sum()), int(part[feature_keys].notna().all(axis=1).sum()), float(part[feature_keys].isna().mean().max()), rng("UCS/kpa"), rng("CCC")))
    return sorted(summaries, key=lambda item: item.paper)


def detect_outliers(prepared_df: pd.DataFrame) -> dict[str, int]:
    outliers: dict[str, int] = {}
    for feature in ALL_FEATURES:
        series = prepared_df[feature.key].dropna()
        if len(series) < 8:
            outliers[feature.label] = 0
            continue
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        outliers[feature.label] = 0 if iqr == 0 else int(((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).sum())
    return outliers


def recommend_algorithms(prepared_df: pd.DataFrame, group_count: int, max_missing: float) -> list[str]:
    spans = []
    for target in TARGETS:
        positive = prepared_df[target].dropna()
        positive = positive[positive > 0]
        if len(positive):
            spans.append(float(positive.max() / positive.min()))
    if any(span > 20 for span in spans):
        return ["huber_log", "svr_log", "kernel_ridge_log", "gbr_log"]
    if group_count >= 5 and max_missing < 0.25:
        return ["huber_log", "gbr_log", "extra_trees", "gaussian_process_log"]
    return ["ridge_log", "huber_log", "elasticnet_log", "svr_log"]


def feature_keys_for_mode(feature_mode: FeatureMode) -> list[str]:
    if feature_mode == "original":
        return BASE_MODEL_FEATURES
    if feature_mode == "engineered":
        return ENGINEERED_MODEL_FEATURES
    return BASE_MODEL_FEATURES + ENGINEERED_MODEL_FEATURES


def require_sklearn() -> dict[str, Any]:
    try:
        from joblib import dump, load
        from sklearn.compose import TransformedTargetRegressor
        from sklearn.exceptions import ConvergenceWarning
        from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel
        from sklearn.impute import SimpleImputer
        from sklearn.inspection import permutation_importance
        from sklearn.kernel_ridge import KernelRidge
        from sklearn.linear_model import ElasticNet, HuberRegressor, Ridge
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        from sklearn.base import clone
        from sklearn.model_selection import GroupKFold, KFold, cross_val_predict
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import SVR
    except ImportError as exc:
        raise RuntimeError("缺少机器学习依赖。请先运行：install_deps.bat") from exc
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    return locals()


def algorithm_registry(sklearn: dict[str, Any] | None = None) -> dict[str, AlgorithmSpec]:
    if sklearn is None:
        sklearn = require_sklearn()
    Pipeline = sklearn["Pipeline"]
    SimpleImputer = sklearn["SimpleImputer"]
    StandardScaler = sklearn["StandardScaler"]
    Ridge = sklearn["Ridge"]
    ElasticNet = sklearn["ElasticNet"]
    HuberRegressor = sklearn["HuberRegressor"]
    SVR = sklearn["SVR"]
    KernelRidge = sklearn["KernelRidge"]
    RandomForestRegressor = sklearn["RandomForestRegressor"]
    ExtraTreesRegressor = sklearn["ExtraTreesRegressor"]
    GradientBoostingRegressor = sklearn["GradientBoostingRegressor"]
    GaussianProcessRegressor = sklearn["GaussianProcessRegressor"]
    ConstantKernel = sklearn["ConstantKernel"]
    RBF = sklearn["RBF"]
    WhiteKernel = sklearn["WhiteKernel"]
    TransformedTargetRegressor = sklearn["TransformedTargetRegressor"]

    def steps(estimator: Any, imputer_strategy: str | None, scaled: bool = False) -> list[tuple[str, Any]]:
        pipeline_steps: list[tuple[str, Any]] = []
        if imputer_strategy:
            pipeline_steps.append(("imputer", SimpleImputer(strategy=imputer_strategy)))
        if scaled:
            pipeline_steps.append(("scaler", StandardScaler()))
        pipeline_steps.append(("model", estimator))
        return pipeline_steps

    def log_target(regressor: Any) -> Any:
        return TransformedTargetRegressor(regressor=regressor, func=np.log1p, inverse_func=np.expm1)

    def gpr_model(params: dict[str, Any]) -> Any:
        kernel = ConstantKernel(1.0, constant_value_bounds="fixed") * RBF(length_scale=params.get("length_scale", 1.0)) + WhiteKernel(noise_level=params.get("alpha", 1e-5))
        return GaussianProcessRegressor(kernel=kernel, normalize_y=True, random_state=42, n_restarts_optimizer=0)

    return {
        "ridge_log": AlgorithmSpec("ridge_log", "Ridge-log", True, "线性基准模型，适合小样本稳定对照。", lambda imputer, sk, p=None: Pipeline(steps(log_target(Ridge(alpha=(p or {}).get("alpha", 1.0))), imputer, True)), ({"alpha": 0.3}, {"alpha": 1.0}, {"alpha": 3.0})),
        "huber_log": AlgorithmSpec("huber_log", "Huber-log", True, "稳健线性模型，适合小样本且目标中存在极端强度值时作为保守预测器。", lambda imputer, sk, p=None: Pipeline(steps(log_target(HuberRegressor(alpha=(p or {}).get("alpha", 0.0001), epsilon=(p or {}).get("epsilon", 1.35), max_iter=1000)), imputer, True)), ({"alpha": 0.0001, "epsilon": 1.25}, {"alpha": 0.0001, "epsilon": 1.35}, {"alpha": 0.001, "epsilon": 1.5})),
        "elasticnet_log": AlgorithmSpec("elasticnet_log", "ElasticNet-log", True, "带特征筛选倾向的线性模型，用于处理冗余特征。", lambda imputer, sk, p=None: Pipeline(steps(log_target(ElasticNet(alpha=(p or {}).get("alpha", 0.01), l1_ratio=(p or {}).get("l1_ratio", 0.25), max_iter=20000)), imputer, True)), ({"alpha": 0.001, "l1_ratio": 0.2}, {"alpha": 0.01, "l1_ratio": 0.25}, {"alpha": 0.03, "l1_ratio": 0.5})),
        "svr_log": AlgorithmSpec("svr_log", "SVR-log", True, "适合小样本非线性回归，对目标跨度较大的数据较稳健。", lambda imputer, sk, p=None: Pipeline(steps(log_target(SVR(C=(p or {}).get("C", 10.0), epsilon=(p or {}).get("epsilon", 0.1), gamma="scale")), imputer, True)), ({"C": 3.0, "epsilon": 0.05}, {"C": 10.0, "epsilon": 0.1}, {"C": 30.0, "epsilon": 0.1})),
        "kernel_ridge_log": AlgorithmSpec("kernel_ridge_log", "KernelRidge-log", True, "小样本核回归模型，可作为 SVR 的稳定补充。", lambda imputer, sk, p=None: Pipeline(steps(log_target(KernelRidge(kernel="rbf", alpha=(p or {}).get("alpha", 1.0), gamma=(p or {}).get("gamma", 0.1))), imputer, True)), ({"alpha": 0.3, "gamma": 0.05}, {"alpha": 1.0, "gamma": 0.1}, {"alpha": 3.0, "gamma": 0.2})),
        "gbr_log": AlgorithmSpec("gbr_log", "GradientBoosting-log", True, "非线性提升树，对数据内插值表现通常较好。", lambda imputer, sk, p=None: Pipeline(steps(log_target(GradientBoostingRegressor(random_state=42, max_depth=(p or {}).get("max_depth", 2), n_estimators=(p or {}).get("n_estimators", 120), learning_rate=(p or {}).get("learning_rate", 0.05), min_samples_leaf=2)), imputer)), ({"max_depth": 2, "n_estimators": 100, "learning_rate": 0.05}, {"max_depth": 2, "n_estimators": 160, "learning_rate": 0.04}, {"max_depth": 3, "n_estimators": 100, "learning_rate": 0.04})),
        "random_forest": AlgorithmSpec("random_forest", "RandomForest", False, "稳健树模型，可解释特征重要性，适合作为非线性基线。", lambda imputer, sk, p=None: Pipeline(steps(RandomForestRegressor(n_estimators=(p or {}).get("n_estimators", 240), random_state=42, min_samples_leaf=(p or {}).get("min_samples_leaf", 2)), imputer)), ({"n_estimators": 220, "min_samples_leaf": 2}, {"n_estimators": 320, "min_samples_leaf": 3})),
        "extra_trees": AlgorithmSpec("extra_trees", "ExtraTrees", False, "高随机性树模型，用于检验特征关系是否稳定。", lambda imputer, sk, p=None: Pipeline(steps(ExtraTreesRegressor(n_estimators=(p or {}).get("n_estimators", 260), random_state=42, min_samples_leaf=(p or {}).get("min_samples_leaf", 2)), imputer)), ({"n_estimators": 260, "min_samples_leaf": 2}, {"n_estimators": 360, "min_samples_leaf": 3})),
        "gaussian_process_log": AlgorithmSpec("gaussian_process_log", "GaussianProcess-log", True, "高斯过程适合小样本，并能作为不确定性判断的补充。", lambda imputer, sk, p=None: Pipeline(steps(log_target(gpr_model(p or {})), imputer, True)), ({"length_scale": 0.8, "alpha": 1e-5}, {"length_scale": 1.6, "alpha": 1e-4})),
    }


def train_models(prepared_df: pd.DataFrame, raw_df: pd.DataFrame | None = None, missing_strategy: MissingStrategy = "median", algorithm_mode: AlgorithmMode = "all", selected_algorithms: list[str] | None = None, primary_validation: ValidationKind = "random_kfold", save_path: str | Path | None = None, feature_mode: FeatureMode = "all", data_file: str | None = None, progress_callback: Callable[[float, str], None] | None = None) -> tuple[dict[str, Any], TrainingReport]:
    def emit_progress(value: float, stage: str) -> None:
        if progress_callback:
            try:
                progress_callback(max(0.0, min(0.99, value)), stage)
            except Exception:
                pass

    emit_progress(0.06, "载入训练依赖")
    sklearn = require_sklearn()
    registry = algorithm_registry(sklearn)
    feature_keys = feature_keys_for_mode(feature_mode)
    imputer_strategy = "median" if missing_strategy == "median" else None
    if algorithm_mode == "manual" and selected_algorithms:
        algorithm_names = [name for name in selected_algorithms if name in registry]
    elif algorithm_mode == "auto":
        profile = build_dataset_profile(raw_df, prepared_df) if raw_df is not None else None
        algorithm_names = profile.recommended_algorithms if profile else ["svr_log", "gbr_log", "kernel_ridge_log"]
    else:
        algorithm_names = list(registry.keys())
    if not algorithm_names:
        algorithm_names = ["svr_log", "gbr_log", "kernel_ridge_log"]

    emit_progress(0.10, "锁定训练配置")
    total_algorithm_units = max(1, len(TARGETS) * len(algorithm_names))
    completed_algorithm_units = 0

    groups_all = extract_groups(raw_df) if raw_df is not None else pd.Series(["unknown"] * len(prepared_df), index=prepared_df.index)
    trained_targets: dict[str, Any] = {}
    all_trained_targets: dict[str, dict[str, Any]] = {}
    report_results: dict[str, TargetTrainingResult] = {}
    diagnostics: dict[str, Any] = {}
    quantile_models: dict[str, dict[str, Any]] = {}

    for target_index, target in enumerate(TARGETS):
        emit_progress(0.12 + 0.70 * (completed_algorithm_units / total_algorithm_units), f"准备训练 {target}")
        target_df = prepared_df[feature_keys + [target]].dropna(subset=[target]).copy()
        if missing_strategy == "complete":
            target_df = target_df.dropna(subset=feature_keys)
        if target_df.shape[0] < 6:
            raise DataValidationError(f"{target} 可用于训练的样本少于 6 条，无法稳定训练。")
        target_groups = groups_all.loc[target_df.index]
        validations: list[ValidationResult] = []
        fitted_candidates: dict[str, Any] = {}
        best_params_by_algorithm: dict[str, dict[str, Any]] = {}
        for algorithm_name in algorithm_names:
            spec = registry[algorithm_name]
            emit_progress(0.14 + 0.68 * (completed_algorithm_units / total_algorithm_units), f"{target}: {spec.label} 调参与交叉验证")
            best_params = choose_algorithm_params(spec, target, target_df[feature_keys], target_df[target], imputer_strategy, sklearn, target_groups, primary_validation)
            best_params_by_algorithm[algorithm_name] = best_params
            validations.append(_cross_validate_algorithm(spec.factory(imputer_strategy, sklearn, best_params), spec, target, target_df[feature_keys], target_df[target], None, "random_kfold", sklearn, best_params))
            validations.append(_cross_validate_algorithm(spec.factory(imputer_strategy, sklearn, best_params), spec, target, target_df[feature_keys], target_df[target], None, "repeated_kfold", sklearn, best_params))
            if target_groups.nunique() >= 2:
                validations.append(_cross_validate_algorithm(spec.factory(imputer_strategy, sklearn, best_params), spec, target, target_df[feature_keys], target_df[target], target_groups, "group_kfold", sklearn, best_params))
                validations.append(_cross_validate_algorithm(spec.factory(imputer_strategy, sklearn, best_params), spec, target, target_df[feature_keys], target_df[target], target_groups, "repeated_group_kfold", sklearn, best_params))
            emit_progress(0.14 + 0.68 * ((completed_algorithm_units + 0.75) / total_algorithm_units), f"{target}: 拟合 {spec.label}")
            fitted = spec.factory(imputer_strategy, sklearn, best_params)
            fitted.fit(target_df[feature_keys], target_df[target])
            fitted_candidates[algorithm_name] = fitted
            completed_algorithm_units += 1
            emit_progress(0.14 + 0.68 * (completed_algorithm_units / total_algorithm_units), f"{target}: {spec.label} 完成")

        emit_progress(0.82 + 0.04 * ((target_index + 1) / len(TARGETS)), f"{target}: 选择最佳算法")
        best_name = _choose_best_algorithm(validations, algorithm_names, primary_validation)
        best_spec = registry[best_name]
        best_model = fitted_candidates[best_name]
        trained_targets[target] = best_model
        random_best = _find_validation(validations, best_name, "random_kfold")
        repeated_best = _find_validation(validations, best_name, "repeated_kfold")
        group_best = _find_validation(validations, best_name, "group_kfold")
        repeated_group_best = _find_validation(validations, best_name, "repeated_group_kfold")
        assert random_best is not None
        residuals = np.abs(np.asarray(random_best.y_true) - np.asarray(random_best.y_pred))
        risk, risk_reason = assess_risk(target_df.shape[0], target_groups.nunique(), group_best.metrics if group_best else None, repeated_best.metrics if repeated_best else random_best.metrics, repeated_group_best.metrics if repeated_group_best else None)
        warning = None
        if len(target_df) < 25:
            warning = "样本量较小，建议结合跨论文验证和残差区间判断预测可信度。"
        if group_best and group_best.metrics.r2 < 0:
            warning = "按论文分组泛化 R² 为负，说明模型对未见论文体系的外推风险较高。"
        elif repeated_group_best and repeated_group_best.metrics.r2 < 0:
            warning = "重复论文分组验证 R² 为负，说明模型对未见论文体系的外推风险较高。"
        report_results[target] = TargetTrainingResult(target, int(target_df.shape[0]), int(target_groups.nunique()), best_name, best_spec.label, best_params_by_algorithm[best_name], primary_validation, best_spec.uses_log_target, random_best.metrics, repeated_best.metrics if repeated_best else None, group_best.metrics if group_best else None, repeated_group_best.metrics if repeated_group_best else None, validations, feature_importance(best_model, target_df[feature_keys], target_df[target], feature_keys, sklearn), input_sensitivity_impacts(best_model, prepared_df.loc[target_df.index], feature_mode), float(np.percentile(residuals, 80)), float(np.percentile(residuals, 95)), risk, risk_reason, warning)
        all_trained_targets[target] = fitted_candidates
        train_numeric = target_df[feature_keys].apply(pd.to_numeric, errors="coerce")
        target_numeric = pd.to_numeric(target_df[target], errors="coerce")
        diagnostics[target] = {
            "train_X": {key: [None if pd.isna(value) else float(value) for value in train_numeric[key].tolist()] for key in feature_keys},
            "train_y": [None if pd.isna(value) else float(value) for value in target_numeric.tolist()],
            "row_numbers": [int(idx) + 2 if isinstance(idx, (int, np.integer)) else pos + 2 for pos, idx in enumerate(target_df.index)],
            "feature_min": {key: None if pd.isna(value) else float(value) for key, value in train_numeric.min().to_dict().items()},
            "feature_max": {key: None if pd.isna(value) else float(value) for key, value in train_numeric.max().to_dict().items()},
        }
        emit_progress(0.88 + 0.04 * (target_index / len(TARGETS)), f"{target}: 计算预测区间")
        quantile_models[target] = fit_quantile_models(target_df[feature_keys], target_df[target], imputer_strategy, sklearn)
        emit_progress(0.90 + 0.04 * ((target_index + 1) / len(TARGETS)), f"{target}: 诊断完成")

    model_path = Path(save_path) if save_path else None
    training_report = TrainingReport(missing_strategy, algorithm_mode, feature_mode, algorithm_names, primary_validation, report_results, data_file, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), model_path)
    bundle = {"feature_specs": ALL_FEATURES, "feature_keys": feature_keys, "feature_mode": feature_mode, "targets": TARGETS, "missing_strategy": missing_strategy, "algorithm_mode": algorithm_mode, "selected_algorithms": algorithm_names, "primary_validation": primary_validation, "models": trained_targets, "all_models": all_trained_targets, "model_selection": {target: report_results[target].best_algorithm for target in TARGETS if target in report_results}, "quantile_models": quantile_models, "report": report_results, "training_report": training_report, "diagnostics": diagnostics, "trained_at": training_report.trained_at, "data_file": data_file}
    if model_path:
        emit_progress(0.95, "写入模型版本")
        model_path.parent.mkdir(parents=True, exist_ok=True)
        sklearn["dump"](bundle, model_path)
        append_training_history(model_path, training_report)
    emit_progress(0.98, "训练完成，准备刷新界面")
    return bundle, training_report

def choose_algorithm_params(spec: AlgorithmSpec, target: str, x: pd.DataFrame, y: pd.Series, imputer_strategy: str | None, sklearn: dict[str, Any], groups: pd.Series | None = None, primary_validation: ValidationKind = "random_kfold") -> dict[str, Any]:
    tuning_kinds: list[ValidationKind] = []
    if primary_validation in {"group_kfold", "repeated_group_kfold"} and groups is not None and groups.nunique() >= 2:
        tuning_kinds.append(primary_validation)
        if primary_validation == "repeated_group_kfold":
            tuning_kinds.append("group_kfold")
    elif primary_validation == "repeated_kfold":
        tuning_kinds.append("repeated_kfold")
    tuning_kinds.append("random_kfold")

    seen: set[ValidationKind] = set()
    for validation_kind in tuning_kinds:
        if validation_kind in seen:
            continue
        seen.add(validation_kind)
        validation_groups = groups if validation_kind in {"group_kfold", "repeated_group_kfold"} else None
        if validation_kind in {"group_kfold", "repeated_group_kfold"} and (validation_groups is None or validation_groups.nunique() < 2):
            continue
        best_params: dict[str, Any] = {}
        best_rmse = float("inf")
        for params in spec.candidate_params:
            try:
                result = _cross_validate_algorithm(spec.factory(imputer_strategy, sklearn, params), spec, target, x, y, validation_groups, validation_kind, sklearn, params)
            except Exception:
                continue
            if result.metrics.rmse < best_rmse:
                best_rmse = result.metrics.rmse
                best_params = dict(params)
        if np.isfinite(best_rmse):
            return best_params
    return dict(spec.candidate_params[0]) if spec.candidate_params else {}


def fit_quantile_models(x: pd.DataFrame, y: pd.Series, imputer_strategy: str | None, sklearn: dict[str, Any]) -> dict[str, Any]:
    Pipeline = sklearn["Pipeline"]
    SimpleImputer = sklearn["SimpleImputer"]
    GradientBoostingRegressor = sklearn["GradientBoostingRegressor"]
    TransformedTargetRegressor = sklearn["TransformedTargetRegressor"]
    min_leaf = max(2, min(5, int(max(2, len(y) // 10))))

    def build(alpha: float) -> Any:
        steps: list[tuple[str, Any]] = []
        if imputer_strategy:
            steps.append(("imputer", SimpleImputer(strategy=imputer_strategy)))
        base = GradientBoostingRegressor(loss="quantile", alpha=alpha, random_state=42, max_depth=2, n_estimators=160, learning_rate=0.04, min_samples_leaf=min_leaf)
        steps.append(("model", TransformedTargetRegressor(regressor=base, func=np.log1p, inverse_func=np.expm1)))
        return Pipeline(steps)

    models = {"low": build(0.1), "high": build(0.9)}
    for model in models.values():
        model.fit(x, y)
    return models


def repeated_group_split_indices(groups: pd.Series, folds: int, seed: int):
    group_values = groups.to_numpy()
    unique_groups = np.asarray(pd.unique(group_values))
    rng = np.random.default_rng(seed)
    shuffled_groups = unique_groups.copy()
    rng.shuffle(shuffled_groups)
    row_indices = np.arange(len(group_values))
    for heldout_groups in np.array_split(shuffled_groups, folds):
        if len(heldout_groups) == 0:
            continue
        test_mask = np.isin(group_values, heldout_groups)
        if not test_mask.any() or test_mask.all():
            continue
        yield row_indices[~test_mask], row_indices[test_mask]

def _cross_validate_algorithm(model: Any, spec: AlgorithmSpec, target: str, x: pd.DataFrame, y: pd.Series, groups: pd.Series | None, validation_kind: ValidationKind, sklearn: dict[str, Any], params: dict[str, Any] | None = None) -> ValidationResult:
    y_values = np.asarray(y, dtype=float)
    paper_errors: list[dict[str, Any]] = []
    if validation_kind == "group_kfold" and groups is not None and groups.nunique() >= 2:
        folds = min(5, int(groups.nunique()))
        cv = sklearn["GroupKFold"](n_splits=folds)
        pred = sklearn["cross_val_predict"](model, x, y, cv=cv, groups=groups)
        paper_errors = build_paper_errors(groups, y_values, pred)
    elif validation_kind == "repeated_group_kfold" and groups is not None and groups.nunique() >= 2:
        folds = min(5, int(groups.nunique()))
        predictions = []
        metrics = []
        for seed in [11, 42, 73]:
            current = np.full(len(y_values), np.nan, dtype=float)
            for train_idx, test_idx in repeated_group_split_indices(groups, folds, seed):
                current_model = sklearn["clone"](model)
                current_model.fit(x.iloc[train_idx], y.iloc[train_idx])
                current[test_idx] = current_model.predict(x.iloc[test_idx])
            current = np.maximum(np.asarray(current, dtype=float), 0.0)
            predictions.append(current)
            metrics.append(calculate_metrics(y_values, current, sklearn))
        pred = np.mean(np.vstack(predictions), axis=0)
        avg = Metrics(float(np.mean([m.rmse for m in metrics])), float(np.mean([m.mae for m in metrics])), float(np.mean([m.r2 for m in metrics])))
        paper_errors = build_paper_errors(groups, y_values, pred)
        return ValidationResult(spec.name, spec.label, target, validation_kind, int(len(y_values)), int(folds * 3), avg, y_values.tolist(), pred.tolist(), paper_errors, params or {})
    elif validation_kind == "repeated_kfold":
        folds = min(5, max(2, int(len(x) // 4)))
        predictions = []
        metrics = []
        for seed in [11, 42, 73]:
            cv = sklearn["KFold"](n_splits=folds, shuffle=True, random_state=seed)
            current = sklearn["cross_val_predict"](model, x, y, cv=cv)
            current = np.maximum(np.asarray(current, dtype=float), 0.0)
            predictions.append(current)
            metrics.append(calculate_metrics(y_values, current, sklearn))
        pred = np.mean(np.vstack(predictions), axis=0)
        avg = Metrics(float(np.mean([m.rmse for m in metrics])), float(np.mean([m.mae for m in metrics])), float(np.mean([m.r2 for m in metrics])))
        return ValidationResult(spec.name, spec.label, target, validation_kind, int(len(y_values)), int(folds * 3), avg, y_values.tolist(), pred.tolist(), params=params or {})
    else:
        folds = min(5, max(2, int(len(x) // 4)))
        cv = sklearn["KFold"](n_splits=folds, shuffle=True, random_state=42)
        pred = sklearn["cross_val_predict"](model, x, y, cv=cv)
    pred = np.maximum(np.asarray(pred, dtype=float), 0.0)
    return ValidationResult(spec.name, spec.label, target, validation_kind, int(len(y_values)), int(folds), calculate_metrics(y_values, pred, sklearn), y_values.tolist(), pred.tolist(), paper_errors, params or {})


def calculate_metrics(y_values: np.ndarray, pred: np.ndarray, sklearn: dict[str, Any]) -> Metrics:
    return Metrics(float(np.sqrt(sklearn["mean_squared_error"](y_values, pred))), float(sklearn["mean_absolute_error"](y_values, pred)), float(sklearn["r2_score"](y_values, pred)) if len(y_values) > 1 else float("nan"))


def build_paper_errors(groups: pd.Series, y_values: np.ndarray, pred: np.ndarray) -> list[dict[str, Any]]:
    frame = pd.DataFrame({"paper": groups.to_numpy(), "true": y_values, "pred": pred})
    frame["abs_error"] = (frame["pred"] - frame["true"]).abs()
    rows = []
    for paper, part in frame.groupby("paper"):
        rows.append({"paper": str(paper), "n": int(part.shape[0]), "mae": float(part["abs_error"].mean()), "bias": float((part["pred"] - part["true"]).mean())})
    return sorted(rows, key=lambda item: item["mae"], reverse=True)


def _choose_best_algorithm(validations: list[ValidationResult], algorithm_names: list[str], primary: ValidationKind) -> str:
    preferred = [result for result in validations if result.validation_kind == primary]
    if not preferred:
        preferred = [result for result in validations if result.validation_kind == "group_kfold"]
    if not preferred:
        preferred = [result for result in validations if result.validation_kind == "random_kfold"]
    return sorted(preferred, key=lambda result: (result.metrics.rmse, algorithm_names.index(result.algorithm_name)))[0].algorithm_name


def _find_validation(validations: list[ValidationResult], algorithm_name: str, kind: ValidationKind) -> ValidationResult | None:
    for result in validations:
        if result.algorithm_name == algorithm_name and result.validation_kind == kind:
            return result
    return None


def assess_risk(sample_count: int, group_count: int, group_metrics: Metrics | None, repeated_metrics: Metrics | None, repeated_group_metrics: Metrics | None = None) -> tuple[str, str]:
    if sample_count < 25:
        return "高", "目标样本量偏少，预测更依赖少量论文数据。"
    if group_count < 5:
        return "高", "论文分组数量少，难以稳定判断跨论文泛化能力。"
    if repeated_group_metrics and np.isfinite(repeated_group_metrics.r2):
        if repeated_group_metrics.r2 < 0:
            return "高", "重复论文分组验证 R² 为负，说明外推到新论文体系风险高。"
        if repeated_group_metrics.r2 < 0.2:
            return "中", "重复论文分组验证较弱，建议只在训练范围附近使用。"
    if group_metrics and np.isfinite(group_metrics.r2):
        if group_metrics.r2 < 0:
            return "高", "按论文分组验证 R² 为负，说明外推到新论文体系风险高。"
        if group_metrics.r2 < 0.35:
            return "中", "跨论文验证有一定误差，建议只在训练范围附近使用。"
    if repeated_metrics and repeated_metrics.r2 < 0.5:
        return "中", "重复 K 折表现一般，预测值应结合参考区间。"
    return "低", "当前验证结果相对稳定，但仍需结合训练范围解释。"


def feature_importance(model: Any, x: pd.DataFrame, y: pd.Series, feature_keys: list[str], sklearn: dict[str, Any]) -> list[tuple[str, float]]:
    try:
        result = sklearn["permutation_importance"](model, x, y, n_repeats=8, random_state=42, scoring="neg_root_mean_squared_error")
        values = np.maximum(np.asarray(result.importances_mean, dtype=float), 0.0)
    except Exception:
        values = np.zeros(len(feature_keys), dtype=float)
        estimator = model.named_steps.get("model") if hasattr(model, "named_steps") else model
        if hasattr(estimator, "regressor_"):
            estimator = estimator.regressor_
        if hasattr(estimator, "feature_importances_"):
            values = np.asarray(estimator.feature_importances_, dtype=float)
        elif hasattr(estimator, "coef_"):
            values = np.abs(np.asarray(estimator.coef_, dtype=float)).reshape(-1)
    total = float(values.sum())
    if total > 0:
        values = values / total
    labels = [_label_for_key(key) for key in feature_keys]
    return sorted(zip(labels, values.tolist(), strict=False), key=lambda item: item[1], reverse=True)


def input_sensitivity_impacts(model: Any, training_rows: pd.DataFrame, feature_mode: FeatureMode) -> list[dict[str, Any]]:
    input_keys = [feature.key for feature in USER_INPUT_FEATURES]
    numeric = training_rows[input_keys].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    baseline = {key: float(numeric[key].median()) if numeric[key].notna().any() else float("nan") for key in input_keys}

    def model_prediction(values: dict[str, float]) -> float:
        x = build_prediction_frame(values, feature_mode)
        return max(float(model.predict(x)[0]), 0.0)

    try:
        baseline_prediction = model_prediction(baseline)
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    for feature in USER_INPUT_FEATURES:
        series = numeric[feature.key].dropna()
        if series.shape[0] < 2:
            rows.append({"feature_key": feature.key, "feature": feature.label, "unit": feature.unit, "baseline": baseline.get(feature.key), "low": None, "high": None, "prediction_low": None, "prediction_high": None, "delta": 0.0, "abs_delta": 0.0, "relative_to_baseline": 0.0, "normalized_impact": 0.0, "direction": "数据不足"})
            continue
        low = float(series.quantile(0.1))
        high = float(series.quantile(0.9))
        if not np.isfinite(low) or not np.isfinite(high) or math.isclose(low, high):
            low = float(series.min())
            high = float(series.max())
        if not np.isfinite(low) or not np.isfinite(high) or math.isclose(low, high):
            rows.append({"feature_key": feature.key, "feature": feature.label, "unit": feature.unit, "baseline": baseline.get(feature.key), "low": low, "high": high, "prediction_low": None, "prediction_high": None, "delta": 0.0, "abs_delta": 0.0, "relative_to_baseline": 0.0, "normalized_impact": 0.0, "direction": "变化不足"})
            continue
        low_values = dict(baseline)
        high_values = dict(baseline)
        low_values[feature.key] = low
        high_values[feature.key] = high
        try:
            pred_low = model_prediction(low_values)
            pred_high = model_prediction(high_values)
        except Exception:
            pred_low = pred_high = float("nan")
        delta = float(pred_high - pred_low) if np.isfinite(pred_low) and np.isfinite(pred_high) else 0.0
        abs_delta = abs(delta)
        scale = max(abs(baseline_prediction), 1e-9)
        if abs_delta <= scale * 1e-6:
            direction = "影响不明显"
        else:
            direction = "正向" if delta > 0 else "负向"
        rows.append({"feature_key": feature.key, "feature": feature.label, "unit": feature.unit, "baseline": baseline.get(feature.key), "low": low, "high": high, "prediction_low": pred_low if np.isfinite(pred_low) else None, "prediction_high": pred_high if np.isfinite(pred_high) else None, "delta": delta, "abs_delta": abs_delta, "relative_to_baseline": float(delta / scale), "normalized_impact": 0.0, "direction": direction})
    total = sum(float(row["abs_delta"]) for row in rows)
    if total > 0:
        for row in rows:
            row["normalized_impact"] = float(row["abs_delta"] / total)
    return sorted(rows, key=lambda item: item["normalized_impact"], reverse=True)


def load_model_bundle(model_path: str | Path) -> dict[str, Any]:
    try:
        return require_sklearn()["load"](model_path)
    except (AttributeError, ModuleNotFoundError, NotImplementedError, ValueError) as exc:
        raise DataValidationError(
            "模型文件无法在当前环境加载，可能是由旧版 pandas/scikit-learn 保存的模型包。"
            "请用当前数据重新训练，或选择与该模型兼容的软件环境。"
            f"原始错误：{type(exc).__name__}: {exc}"
        ) from exc


def build_prediction_frame(values: dict[str, Any], feature_mode: FeatureMode = "all") -> pd.DataFrame:
    row = {feature.key: parse_numeric(values.get(feature.key)) for feature in USER_INPUT_FEATURES}
    row["specimen_volume_mm3"] = calculate_volume(row["height_mm"], row["inner_diameter_mm"])
    df = pd.DataFrame([row])
    add_engineered_features(df)
    return df.reindex(columns=feature_keys_for_mode(feature_mode))


def predict(bundle: dict[str, Any], values: dict[str, Any]) -> dict[str, float]:
    return predict_with_diagnostics(bundle, values).predictions


def prediction_models(bundle: dict[str, Any], model_selection: dict[str, str] | None = None) -> dict[str, Any]:
    selected = model_selection or bundle.get("model_selection", {}) or {}
    all_models = bundle.get("all_models", {}) or {}
    default_models = bundle.get("models", {}) or {}
    models: dict[str, Any] = {}
    for target in bundle.get("targets", TARGETS):
        algorithm_name = selected.get(target) if isinstance(selected, dict) else None
        target_models = all_models.get(target, {}) if isinstance(all_models, dict) else {}
        if algorithm_name and algorithm_name in target_models:
            models[target] = target_models[algorithm_name]
        elif target in default_models:
            models[target] = default_models[target]
    return models


def selected_validation_for_report(report: TargetTrainingResult | None, algorithm_name: str | None) -> ValidationResult | None:
    if not report or not algorithm_name:
        return None
    preferred_kinds = [report.selected_validation, "repeated_group_kfold", "group_kfold", "repeated_kfold", "random_kfold"]
    seen: set[str] = set()
    for kind in preferred_kinds:
        if kind in seen:
            continue
        seen.add(kind)
        for validation in report.validation_results:
            if validation.algorithm_name == algorithm_name and validation.validation_kind == kind:
                return validation
    return None


def predict_with_diagnostics(bundle: dict[str, Any], values: dict[str, Any], model_selection: dict[str, str] | None = None) -> PredictionDiagnostics:
    feature_mode = bundle.get("feature_mode", "all")
    all_values = pd.DataFrame([{feature.key: parse_numeric(values.get(feature.key)) for feature in USER_INPUT_FEATURES}])
    all_values["specimen_volume_mm3"] = calculate_volume(all_values.at[0, "height_mm"], all_values.at[0, "inner_diameter_mm"])
    add_engineered_features(all_values)
    feature_keys = bundle.get("feature_keys", feature_keys_for_mode(feature_mode))
    x = all_values.reindex(columns=feature_keys)
    missing_input_features = [_label_for_key(key) for key in feature_keys if key in x.columns and not np.isfinite(float(x[key].iloc[0]))]
    active_models = prediction_models(bundle, model_selection)
    if not active_models:
        raise DataValidationError("模型包中没有可用于预测的模型，请重新训练或加载完整模型。")
    predictions = {target: max(float(model.predict(x)[0]), 0.0) for target, model in active_models.items()}
    report: dict[str, TargetTrainingResult] = bundle.get("report", {})
    diagnostics = bundle.get("diagnostics", {})
    quantile_models = bundle.get("quantile_models", {})
    out_of_range: list[str] = []
    nearest_distances: list[float] = []
    intervals: dict[str, tuple[float, float]] = {}
    messages: list[str] = []
    similar_samples: list[SimilarSample] = []
    confidence = "高"
    active_selection = model_selection or bundle.get("model_selection", {}) or {}
    for target, pred in predictions.items():
        target_diag = diagnostics.get(target, {})
        mins = target_diag.get("feature_min", {})
        maxs = target_diag.get("feature_max", {})
        for key in feature_keys:
            value = float(x[key].iloc[0])
            if key in mins and np.isfinite(value) and (value < mins[key] or value > maxs[key]):
                out_of_range.append(_label_for_key(key))
        train_x_raw = target_diag.get("train_X")
        train_y_raw = target_diag.get("train_y")
        if isinstance(train_x_raw, pd.DataFrame):
            train_frame = train_x_raw.copy()
        elif isinstance(train_x_raw, dict):
            train_frame = pd.DataFrame(train_x_raw)
        elif isinstance(train_x_raw, list):
            train_frame = pd.DataFrame(train_x_raw)
        else:
            train_frame = pd.DataFrame()
        if not train_frame.empty:
            train_numeric = train_frame.reindex(columns=feature_keys).apply(pd.to_numeric, errors="coerce")
            if isinstance(train_y_raw, pd.Series):
                train_y = pd.to_numeric(train_y_raw, errors="coerce")
            else:
                train_y_values = [] if train_y_raw is None else list(train_y_raw)
                train_y = pd.Series(pd.to_numeric(pd.Series(train_y_values), errors="coerce").to_numpy(), index=train_numeric.index[:len(train_y_values)])
                if len(train_y) != len(train_numeric):
                    train_y = train_y.reindex(train_numeric.index)
            med = train_numeric.median(numeric_only=True).fillna(0.0)
            train_filled = train_numeric.fillna(med)
            x_numeric = pd.to_numeric(x[feature_keys].iloc[0], errors="coerce").fillna(med)
            scale = train_filled.std(numeric_only=True).replace(0, 1).fillna(1)
            x_scaled = (x_numeric - med) / scale
            train_scaled = (train_filled - med) / scale
            dist = np.sqrt(((train_scaled - x_scaled) ** 2).sum(axis=1))
            nearest_distances.append(float(dist.min()))
            row_numbers = target_diag.get("row_numbers") or []
            for idx, distance in dist.sort_values().head(3).items():
                try:
                    position = int(train_numeric.index.get_loc(idx))
                except Exception:
                    position = 0
                observed = float(train_y.loc[idx]) if idx in train_y.index and np.isfinite(train_y.loc[idx]) else float("nan")
                if row_numbers and position < len(row_numbers):
                    row_number = int(row_numbers[position])
                elif isinstance(idx, (int, np.integer)):
                    row_number = int(idx) + 2
                else:
                    row_number = position + 2
                if {"od600", "d50"}.issubset(train_frame.columns):
                    od600 = pd.to_numeric(pd.Series([train_frame.at[idx, "od600"]]), errors="coerce").iloc[0]
                    d50 = pd.to_numeric(pd.Series([train_frame.at[idx, "d50"]]), errors="coerce").iloc[0]
                    summary = f"OD600={od600:.3g}, D50={d50:.3g}" if np.isfinite(od600) and np.isfinite(d50) else f"样本行 {row_number}"
                else:
                    summary = f"样本行 {row_number}"
                similar_samples.append(SimilarSample(target, float(distance), row_number, observed, summary))
        target_report = report.get(target)
        selected_algorithm = active_selection.get(target) if isinstance(active_selection, dict) else None
        selected_validation = selected_validation_for_report(target_report, selected_algorithm)
        if selected_validation:
            residual_values = np.abs(np.asarray(selected_validation.y_true, dtype=float) - np.asarray(selected_validation.y_pred, dtype=float))
            residual = float(np.percentile(residual_values, 80))
        else:
            residual = target_report.residual_p80 if target_report else float("nan")
        q_models = quantile_models.get(target, {})
        if q_models:
            try:
                low = float(q_models["low"].predict(x)[0])
                high = float(q_models["high"].predict(x)[0])
                if low > high:
                    low, high = high, low
                lower_candidates = [low, pred]
                upper_candidates = [high, pred]
                if np.isfinite(residual):
                    lower_candidates.append(pred - residual)
                    upper_candidates.append(pred + residual)
                intervals[target] = (max(0.0, min(lower_candidates)), max(upper_candidates))
            except Exception:
                pass
        if target not in intervals and np.isfinite(residual):
            intervals[target] = (max(0.0, pred - residual), pred + residual)
        if target_report and target_report.generalization_risk == "高":
            confidence = "低"
        elif target_report and target_report.generalization_risk == "中" and confidence == "高":
            confidence = "中"
    unique_missing = sorted(set(missing_input_features))
    if unique_missing:
        shown_missing = "、".join(unique_missing[:8]) + ("等" if len(unique_missing) > 8 else "")
        messages.append("以下输入或派生特征缺失，模型已按训练中位数补全：" + shown_missing)
        if len(unique_missing) > max(2, len(feature_keys) // 3):
            confidence = "低"
        elif confidence == "高":
            confidence = "中"
    unique_out = sorted(set(out_of_range))
    if unique_out:
        messages.append("以下输入超出训练数据范围：" + "、".join(unique_out))
        confidence = "低"
    nearest = float(min(nearest_distances)) if nearest_distances else float("nan")
    if np.isfinite(nearest):
        if nearest < 1.5:
            messages.append("输入点与训练样本较接近，属于相对稳妥的插值预测。")
        elif nearest < 3.0:
            messages.append("输入点与训练样本有一定距离，请结合误差区间使用。")
            if confidence == "高":
                confidence = "中"
        else:
            messages.append("输入点距离训练样本较远，预测可能属于外推。")
            confidence = "低"
    if not messages:
        messages.append("预测诊断正常，请结合验证页指标解释结果。")
    engineered = {feature.key: float(all_values.at[0, feature.key]) for feature in COMPUTED_FEATURES + ENGINEERED_FEATURES}
    return PredictionDiagnostics(predictions, intervals, nearest, unique_out, messages, float(all_values.at[0, "specimen_volume_mm3"]), engineered, sorted(similar_samples, key=lambda item: item.distance)[:3], confidence)


def predict_many(bundle: dict[str, Any], raw_df: pd.DataFrame, model_selection: dict[str, str] | None = None) -> pd.DataFrame:
    row_data = pd.DataFrame(index=raw_df.index)
    missing = [feature.column for feature in USER_INPUT_FEATURES if feature.column not in raw_df.columns]
    if missing:
        raise DataValidationError("批量预测文件缺少输入列：" + "、".join(missing))
    for feature in USER_INPUT_FEATURES:
        row_data[feature.key] = raw_df[feature.column].map(parse_numeric)
    row_data["specimen_volume_mm3"] = [calculate_volume(h, d) for h, d in zip(row_data["height_mm"], row_data["inner_diameter_mm"], strict=False)]
    add_engineered_features(row_data)
    output = raw_df.copy()
    for idx in raw_df.index:
        values = {feature.key: row_data.at[idx, feature.key] for feature in USER_INPUT_FEATURES}
        result = predict_with_diagnostics(bundle, values, model_selection)
        for target in TARGETS:
            output.at[idx, f"预测_{target}"] = result.predictions.get(target)
            if target in result.intervals:
                low, high = result.intervals[target]
                output.at[idx, f"{target}_参考下限"] = low
                output.at[idx, f"{target}_参考上限"] = high
        output.at[idx, "可信度"] = result.confidence_level
        output.at[idx, "诊断提示"] = "；".join(result.messages)
    return output


def append_training_history(model_path: Path, report: TrainingReport) -> None:
    history_path = model_path.parent / "training_history.json"
    rows: list[dict[str, Any]] = []
    if history_path.exists():
        try:
            rows = json.loads(history_path.read_text(encoding="utf-8"))
        except Exception:
            rows = []
    rows.append(training_report_summary(report))
    history_path.write_text(json.dumps(rows[-50:], ensure_ascii=False, indent=2), encoding="utf-8")


def training_report_summary(report: TrainingReport) -> dict[str, Any]:
    return {"trained_at": report.trained_at, "data_file": report.data_file, "model_path": str(report.model_path) if report.model_path else "", "feature_mode": report.feature_mode, "missing_strategy": report.missing_strategy, "primary_validation": report.primary_validation, "targets": {target: {"best_algorithm": result.best_algorithm_label, "sample_count": result.sample_count, "random_rmse": result.random_metrics.rmse, "group_rmse": result.group_metrics.rmse if result.group_metrics else None, "risk": result.generalization_risk} for target, result in report.results.items()}}


def export_training_report(report: TrainingReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for target, result in report.results.items():
        rows.append({"目标": target, "最佳算法": result.best_algorithm_label, "样本量": result.sample_count, "论文组": result.group_count, "随机K折_RMSE": result.random_metrics.rmse, "随机K折_MAE": result.random_metrics.mae, "随机K折_R2": result.random_metrics.r2, "重复K折_RMSE": result.repeated_metrics.rmse if result.repeated_metrics else None, "按论文分组_RMSE": result.group_metrics.rmse if result.group_metrics else None, "按论文分组_R2": result.group_metrics.r2 if result.group_metrics else None, "重复论文分组_RMSE": getattr(result, "repeated_group_metrics", None).rmse if getattr(result, "repeated_group_metrics", None) else None, "泛化风险": result.generalization_risk, "风险说明": result.risk_reason})
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name="训练摘要", index=False)
        pd.DataFrame([{"目标": t, "特征": f, "重要性": v} for t, r in report.results.items() for f, v in r.feature_importance]).to_excel(writer, sheet_name="特征重要性", index=False)
        pd.DataFrame([{"目标": t, "输入量": item.get("feature"), "单位": item.get("unit"), "训练典型值": item.get("baseline"), "低位值P10": item.get("low"), "高位值P90": item.get("high"), "低位预测": item.get("prediction_low"), "高位预测": item.get("prediction_high"), "影响方向": item.get("direction"), "预测变化量": item.get("delta"), "相对基准变化": item.get("relative_to_baseline"), "归一化影响程度": item.get("normalized_impact")} for t, r in report.results.items() for item in getattr(r, "input_impacts", [])]).to_excel(writer, sheet_name="输入影响分析", index=False)
        pd.DataFrame([{"目标": t, "算法": v.algorithm_label, "验证": v.validation_kind, "RMSE": v.metrics.rmse, "MAE": v.metrics.mae, "R2": v.metrics.r2, "折数": v.fold_count, "参数": json.dumps(v.params, ensure_ascii=False)} for t, r in report.results.items() for v in r.validation_results]).to_excel(writer, sheet_name="算法验证", index=False)
    return path


def make_import_template(output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [feature.column for feature in USER_INPUT_FEATURES] + TARGETS
    pd.DataFrame(columns=columns).to_excel(path, index=False)
    return path


def _label_for_key(key: str) -> str:
    return next((feature.label for feature in ALL_FEATURES if feature.key == key), key)


def available_algorithm_options() -> list[tuple[str, str, str]]:
    return [(name, spec.label, spec.description) for name, spec in algorithm_registry().items()]


def available_feature_modes() -> list[tuple[str, str, str]]:
    return [("original", "原始特征", "只使用用户输入参数和自动计算体积。"), ("engineered", "增强特征", "只使用由实验参数推导出的科研组合指标。"), ("all", "全部特征", "同时使用原始特征和增强特征，默认推荐。")]
