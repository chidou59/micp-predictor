from __future__ import annotations

import json
import math
import os
import queue
import threading
import time
from pathlib import Path
import textwrap
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import customtkinter as ctk
except ImportError as exc:
    raise SystemExit("缺少 customtkinter。请先运行：install_deps.bat") from exc

try:
    from PIL import Image
except ImportError:
    Image = None

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).with_name(".matplotlib_cache")))
Path(os.environ["MPLCONFIGDIR"]).mkdir(exist_ok=True)

try:
    from matplotlib import rcParams
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    rcParams["axes.unicode_minus"] = False
    HAS_MATPLOTLIB = True
except ImportError:
    FigureCanvasTkAgg = None
    Figure = None
    HAS_MATPLOTLIB = False

from micp_model import (
    ALL_FEATURES,
    ENGINEERED_FEATURES,
    FEATURES,
    TARGETS,
    USER_INPUT_FEATURES,
    DataValidationError,
    available_algorithm_options,
    available_feature_modes,
    build_prediction_frame,
    calculate_volume,
    export_training_report,
    load_dataset,
    load_model_bundle,
    make_import_template,
    parse_numeric,
    predict_many,
    predict_with_diagnostics,
    train_models,
)

APP_TITLE = "MICP 科研级加固效果预测软件"
DEFAULT_EXCEL = Path("数据表.xlsx")
MODEL_PATH = Path("models") / "micp_research_predictor.joblib"
HISTORY_PATH = Path("models") / "training_history.json"
ASSET_DIR = Path(__file__).with_name("assets")
ICON_PATH = ASSET_DIR / "micp_icon.ico"
ICON_PNG_PATH = ASSET_DIR / "micp_icon.png"
MARK_PATH = ASSET_DIR / "micp_mark.ico"
MARK_PNG_PATH = ASSET_DIR / "micp_mark.png"
DECOR_PATH = ASSET_DIR / "micp_decor.png"
DECOR_FAINT_PATH = ASSET_DIR / "micp_decor_faint.png"

COLORS = {
    "bg": "#eef4f1",
    "bg_deep": "#dce8e3",
    "panel": "#fbfdfc",
    "panel_alt": "#f3f8f6",
    "panel_tint": "#e7f1ee",
    "ink": "#071f1b",
    "muted": "#60736f",
    "soft": "#89a09a",
    "line": "#cfddd8",
    "line_light": "#e3ece8",
    "green": "#0d2c25",
    "green_2": "#153a32",
    "teal": "#2f7f82",
    "teal_dark": "#25696c",
    "blue": "#4c6f85",
    "blue_dark": "#3f5e72",
    "amber": "#a66d22",
    "amber_soft": "#f5eadb",
    "red": "#a64235",
    "red_soft": "#f7e8e4",
    "white": "#ffffff",
    "seg_selected": "#cfe5df",
    "seg_unselected": "#f5f9f7",
    "seg_hover": "#dbece7",
}

FONTS = {
    "display": ("Microsoft YaHei UI", 31, "bold"),
    "title": ("Microsoft YaHei UI", 27, "bold"),
    "section": ("Microsoft YaHei UI", 18, "bold"),
    "body": ("Microsoft YaHei UI", 12),
    "body_bold": ("Microsoft YaHei UI", 12, "bold"),
    "small": ("Microsoft YaHei UI", 11),
    "metric": ("Microsoft YaHei UI", 22, "bold"),
}
HELP_TEXT = {
    "缺失值": "中位数补全会保留更多样本；只用完整行更严格，但你当前完整输入行较少。",
    "特征模式": "原始特征使用实验参数和体积；增强特征使用高径比、单位体积用量等组合指标；全部特征默认推荐。",
    "算法模式": "自动推荐按数据画像选择少量算法；手动选择只训练勾选算法；全部比较会训练全部候选算法。",
    "主排序": "决定最佳模型的排序依据。数据内预测看随机 K 折，跨论文泛化优先看按论文分组或重复论文分组。",
    "随机K折": "随机拆分数据做交叉验证，样本利用充分，但同一篇论文可能同时出现在训练和验证中。",
    "重复K折": "多次随机 K 折后取平均，减少一次随机划分带来的偶然性。",
    "按论文分组": "同一篇论文整组留出，更接近预测新论文体系的风险。",
    "重复论文分组": "多轮按论文整组划分验证集，让不同论文组合轮流作为验证，用于降低单次分组划分的偶然性。",
    "RMSE": "均方根误差，越小越好，对大误差更敏感。",
    "MAE": "平均绝对误差，越小越好，可理解为平均差多少。",
    "R2": "决定系数，越接近 1 越好；小于 0 表示泛化表现很差。",
    "可信度": "综合训练范围、最近样本距离、跨论文验证风险和残差区间给出的参考等级。",
    "增强特征": "由原始实验参数自动推导的组合指标，不需要用户额外填写。",
}


class Tooltip:
    def __init__(self, widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)
        widget.bind("<ButtonPress>", self.hide)

    def show(self, _event=None) -> None:
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tip_window, text=self.text, justify="left", background="#122c26", foreground="#ecf7f4", relief="flat", borderwidth=0, padx=12, pady=8, wraplength=340, font=("Microsoft YaHei UI", 10))
        label.pack()

    def hide(self, _event=None) -> None:
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None



class ParticleProgressDialog:
    def __init__(self, master, title: str, subtitle: str, steps: list[tuple[float, str]] | None = None) -> None:
        self.master = master
        self.steps = steps or []
        self.target_progress = 0.04
        self.display_progress = 0.0
        self.phase = 0.0
        self.running = True
        self.window = ctk.CTkToplevel(master)
        self.window.title(title)
        self.window.geometry("560x280")
        self.window.resizable(False, False)
        self.window.transient(master)
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", lambda: None)
        self.window.configure(fg_color="#09211d")
        self.window.attributes("-topmost", True)

        card = ctk.CTkFrame(self.window, corner_radius=18, fg_color="#0d2c25", border_width=1, border_color="#3c776b")
        card.pack(fill="both", expand=True, padx=14, pady=14)
        ctk.CTkLabel(card, text=title, text_color="#f1fffb", font=("Microsoft YaHei UI", 23, "bold")).pack(anchor="w", padx=22, pady=(18, 3))
        ctk.CTkLabel(card, text=subtitle, text_color="#a9cec4", font=("Microsoft YaHei UI", 12), wraplength=500, justify="left").pack(anchor="w", padx=22, pady=(0, 12))
        self.canvas = tk.Canvas(card, height=128, bg="#0d2c25", highlightthickness=0)
        self.canvas.pack(fill="x", padx=20, pady=(0, 4))
        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.pack(fill="x", padx=22, pady=(0, 16))
        footer.grid_columnconfigure(0, weight=1)
        self.stage_label = ctk.CTkLabel(footer, text="准备计算", text_color="#d7ebe5", font=("Microsoft YaHei UI", 12, "bold"))
        self.stage_label.grid(row=0, column=0, sticky="w")
        self.percent_label = ctk.CTkLabel(footer, text=f"{int(self.target_progress * 100):d}%", text_color="#f5d59b", font=("Microsoft YaHei UI", 19, "bold"))
        self.percent_label.grid(row=0, column=1, sticky="e")
        self._center()
        self._animate()

    def _center(self) -> None:
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        root_x = self.master.winfo_rootx()
        root_y = self.master.winfo_rooty()
        root_w = max(self.master.winfo_width(), width)
        root_h = max(self.master.winfo_height(), height)
        x = root_x + (root_w - width) // 2
        y = root_y + (root_h - height) // 2
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def set_progress(self, value: float, stage: str | None = None) -> None:
        self.target_progress = max(0.0, min(1.0, value))
        if stage is None:
            for threshold, text in self.steps:
                if self.target_progress >= threshold:
                    stage = text
        if stage:
            self.stage_label.configure(text=stage)
        self.percent_label.configure(text=f"{int(self.target_progress * 100):d}%")

    def close(self) -> None:
        self.running = False
        try:
            self.window.grab_release()
        except Exception:
            pass
        try:
            self.window.destroy()
        except Exception:
            pass

    def _animate(self) -> None:
        if not self.running or not self.window.winfo_exists():
            return
        self.display_progress += (self.target_progress - self.display_progress) * 0.16
        self.phase += 1.0
        self._draw()
        self.window.after(30, self._animate)

    def _draw(self) -> None:
        canvas = self.canvas
        canvas.delete("anim")
        width = max(canvas.winfo_width(), 520)
        height = 126
        for i in range(12):
            x = 24 + i * (width - 48) / 11
            canvas.create_line(x, 8, x, height - 18, fill="#173d35", width=1, tags="anim")
        for i in range(5):
            y = 18 + i * 20
            canvas.create_line(24, y, width - 24, y, fill="#12342d", width=1, tags="anim")

        bar_x, bar_y = 34, 76
        bar_w, bar_h = width - 68, 18
        fill_w = int(bar_w * self.display_progress)
        canvas.create_rectangle(bar_x, bar_y, bar_x + bar_w, bar_y + bar_h, fill="#08201c", outline="#315f55", width=1, tags="anim")
        if fill_w > 0:
            canvas.create_rectangle(bar_x, bar_y, bar_x + fill_w, bar_y + bar_h, fill="#2f7f82", outline="", tags="anim")
            canvas.create_rectangle(max(bar_x, bar_x + fill_w - 44), bar_y, bar_x + fill_w, bar_y + bar_h, fill="#f5d59b", outline="", tags="anim")

        limit = bar_x + fill_w
        for i in range(46):
            speed = 1.8 + (i % 7) * 0.28
            x = bar_x + ((i * 37 + self.phase * speed) % max(bar_w, 1))
            if x > limit:
                continue
            wave = math.sin(self.phase * 0.11 + i * 0.9)
            y = bar_y + bar_h / 2 + wave * (12 + i % 5)
            radius = 1.8 + (i % 4) * 0.65
            color = "#d7fff4" if i % 3 else "#f5d59b"
            canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=color, outline="", tags="anim")
            if i % 5 == 0:
                canvas.create_line(max(bar_x, x - 18), y, x, y, fill="#8ee9db", width=1, tags="anim")
        head_x = min(limit, bar_x + bar_w)
        pulse = 5 + math.sin(self.phase * 0.22) * 2
        canvas.create_oval(head_x - pulse, bar_y + bar_h / 2 - pulse, head_x + pulse, bar_y + bar_h / 2 + pulse, outline="#f5d59b", width=2, tags="anim")


class MicpApp(ctk.CTk):
    def load_ui_image(self, path: Path, size: tuple[int, int]):
        if Image is None or not path.exists():
            return None
        try:
            image = Image.open(path).convert("RGBA")
            return ctk.CTkImage(light_image=image, dark_image=image, size=size)
        except Exception:
            return None

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        app_icon_path = MARK_PATH if MARK_PATH.exists() else ICON_PATH
        if app_icon_path.exists():
            try:
                self.iconbitmap(str(app_icon_path))
            except tk.TclError:
                pass
        self.geometry("1440x880")
        self.minsize(1180, 760)
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.raw_df = None
        self.prepared_df = None
        self.dataset_info = None
        self.model_bundle = None
        self.training_report = None
        self.input_vars = {}
        self.algorithm_checks = {}
        self.scenarios: list[dict[str, str]] = []
        self.last_figure = None
        self.active_page = "data"
        brand_icon_path = MARK_PNG_PATH if MARK_PNG_PATH.exists() else ICON_PNG_PATH
        self.brand_icon_image = self.load_ui_image(brand_icon_path, (46, 46))
        self.sidebar_decor_image = self.load_ui_image(DECOR_FAINT_PATH, (162, 108))
        self.empty_decor_image = None
        self._style()
        self._shell()
        if DEFAULT_EXCEL.exists():
            self.load_excel(DEFAULT_EXCEL, quiet=True)
        self.show_page("data")

    def _style(self) -> None:
        self.configure(fg_color=COLORS["bg"])
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", background=COLORS["panel"], foreground=COLORS["ink"], rowheight=31, fieldbackground=COLORS["panel"], borderwidth=0, font=("Microsoft YaHei UI", 10))
        style.configure("Treeview.Heading", background=COLORS["panel_tint"], foreground=COLORS["ink"], relief="flat", font=("Microsoft YaHei UI", 10, "bold"), padding=(8, 8))
        style.configure("Vertical.TScrollbar", background=COLORS["line"], troughcolor=COLORS["panel_alt"], bordercolor=COLORS["panel_alt"], arrowcolor=COLORS["muted"])
        style.configure("Horizontal.TScrollbar", background=COLORS["line"], troughcolor=COLORS["panel_alt"], bordercolor=COLORS["panel_alt"], arrowcolor=COLORS["muted"])
        style.map("Treeview", background=[("selected", COLORS["teal"])], foreground=[("selected", "#ffffff")])
    def _shell(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        sidebar = ctk.CTkFrame(self, width=286, corner_radius=0, fg_color=COLORS["green"])
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, padx=22, pady=(30, 18), sticky="ew")
        badge = ctk.CTkFrame(brand, width=58, height=58, corner_radius=16, fg_color="#123a32", border_width=1, border_color="#3c776b")
        badge.grid(row=0, column=0, rowspan=2, sticky="nw")
        badge.grid_propagate(False)
        if self.brand_icon_image:
            ctk.CTkLabel(badge, image=self.brand_icon_image, text="").place(relx=0.5, rely=0.5, anchor="center")
        else:
            ctk.CTkLabel(badge, text="Ca", text_color="white", font=("Microsoft YaHei UI", 16, "bold")).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(brand, text="MICP", justify="left", text_color="white", font=FONTS["display"]).grid(row=0, column=1, padx=(14, 0), sticky="w")
        ctk.CTkLabel(brand, text="Research Console", justify="left", text_color="#d7ebe5", font=("Microsoft YaHei UI", 15, "bold")).grid(row=1, column=1, padx=(14, 0), sticky="w")
        ctk.CTkLabel(sidebar, text="Data -> Model -> Validate -> Select -> Predict", text_color="#a9cec4", wraplength=225, justify="left", font=("Microsoft YaHei UI", 12)).grid(row=1, column=0, padx=24, pady=(0, 28), sticky="w")

        self.nav_buttons = {}
        nav_items = [("data", "数据管理"), ("modeling", "建模控制"), ("validation", "验证诊断"), ("selector", "模型选择台"), ("prediction", "可信预测"), ("management", "模型版本")]
        for row, (key, label) in enumerate(nav_items, start=2):
            button = ctk.CTkButton(sidebar, text=label, height=48, anchor="w", corner_radius=12, fg_color="transparent", text_color="#e8f5f1", hover_color=COLORS["green_2"], font=("Microsoft YaHei UI", 15, "bold"), command=lambda k=key: self.show_page(k))
            button.grid(row=row, column=0, padx=18, pady=5, sticky="ew")
            self.nav_buttons[key] = button
        if self.sidebar_decor_image:
            self.sidebar_decor_label = ctk.CTkLabel(sidebar, image=self.sidebar_decor_image, text="")
            self.sidebar_decor_label.grid(row=8, column=0, padx=18, pady=(10, 0), sticky="e")
        sidebar.grid_rowconfigure(9, weight=1)

        status_card = ctk.CTkFrame(sidebar, corner_radius=14, fg_color="#143a32", border_width=1, border_color="#28554b")
        status_card.grid(row=10, column=0, padx=18, pady=24, sticky="sew")
        ctk.CTkLabel(status_card, text="当前状态", text_color="#9fc6bd", font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        self.status_label = ctk.CTkLabel(status_card, text="未加载数据", text_color="#eef8f5", justify="left", font=("Microsoft YaHei UI", 12))
        self.status_label.pack(anchor="w", padx=14, pady=(0, 12))

        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=COLORS["bg"])
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.grid(row=0, column=0, padx=34, pady=(24, 12), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)
        self.header_title = ctk.CTkLabel(header, text="", font=FONTS["title"], text_color=COLORS["ink"])
        self.header_title.grid(row=0, column=0, sticky="w")
        self.header_subtitle = ctk.CTkLabel(header, text="", font=FONTS["body"], text_color=COLORS["muted"])
        self.header_subtitle.grid(row=1, column=0, pady=(4, 0), sticky="w")
        self.page_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.page_frame.grid(row=1, column=0, padx=34, pady=(0, 30), sticky="nsew")
        self.page_frame.grid_columnconfigure(0, weight=1)
        self.page_frame.grid_rowconfigure(0, weight=1)
    def panel(self, parent, **kwargs):
        options = {"corner_radius": 14, "fg_color": COLORS["panel"], "border_width": 1, "border_color": COLORS["line_light"]}
        options.update(kwargs)
        return ctk.CTkFrame(parent, **options)

    def button(self, parent, text: str, command, kind: str = "primary", **kwargs):
        palette = {
            "primary": (COLORS["teal"], COLORS["teal_dark"]),
            "secondary": (COLORS["blue"], COLORS["blue_dark"]),
            "ghost": (COLORS["panel_tint"], COLORS["line"]),
        }
        fg, hover = palette.get(kind, palette["primary"])
        text_color = COLORS["ink"] if kind == "ghost" else "white"
        options = {"height": 40, "corner_radius": 10, "fg_color": fg, "hover_color": hover, "text_color": text_color, "font": FONTS["body_bold"], "command": command}
        options.update(kwargs)
        return ctk.CTkButton(parent, text=text, **options)

    def section_title(self, parent, text: str, subtitle: str | None = None, help_key: str | None = None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        title = ctk.CTkLabel(frame, text=text, font=FONTS["section"], text_color=COLORS["ink"])
        title.pack(anchor="w")
        if help_key:
            Tooltip(title, HELP_TEXT[help_key])
        if subtitle:
            ctk.CTkLabel(frame, text=subtitle, font=FONTS["small"], text_color=COLORS["muted"], wraplength=560, justify="left").pack(anchor="w", pady=(3, 0))
        return frame

    def stat_card(self, parent, label: str, value: str, hint: str, accent: str = "teal"):
        card = ctk.CTkFrame(parent, height=86, corner_radius=10, fg_color=COLORS["white"], border_width=1, border_color=COLORS["line_light"])
        card.grid_propagate(False)
        card.pack_propagate(False)
        strip = ctk.CTkFrame(card, width=3, corner_radius=2, fg_color=COLORS.get(accent, COLORS["teal"]))
        strip.pack(side="left", fill="y", padx=(0, 10))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=(7, 6))
        ctk.CTkLabel(body, text=label, text_color=COLORS["muted"], font=("Microsoft YaHei UI", 10)).pack(anchor="w")
        ctk.CTkLabel(body, text=value, text_color=COLORS["ink"], font=("Microsoft YaHei UI", 20, "bold")).pack(anchor="w", pady=(1, 0))
        ctk.CTkLabel(body, text=hint, text_color=COLORS["soft"], font=("Microsoft YaHei UI", 9), wraplength=210, justify="left").pack(anchor="w")
        return card

    def term_label(self, parent, text: str, help_key: str, font_size: int = 13):
        label = ctk.CTkLabel(parent, text=text, font=("Microsoft YaHei UI", font_size, "bold"), text_color=COLORS["ink"])
        Tooltip(label, HELP_TEXT[help_key])
        return label

    def show_page(self, page: str) -> None:
        self.active_page = page
        for widget in self.page_frame.winfo_children():
            widget.destroy()
        for key, button in self.nav_buttons.items():
            if key == page:
                button.configure(fg_color=COLORS["teal"], hover_color=COLORS["teal_dark"], text_color="white")
            else:
                button.configure(fg_color="transparent", hover_color=COLORS["green_2"], text_color="#e8f5f1")
        titles = {"data": "数据质量与预处理", "modeling": "建模与算法训练", "validation": "交叉验证与泛化诊断", "selector": "模型选择台", "prediction": "可信预测与方案对比", "management": "模型版本与导出"}
        subtitles = {
            "data": "检查数据完整性、清洗痕迹、论文分组与目标跨度。",
            "modeling": "选择缺失值策略、特征模式和算法比较方式，训练可解释的双目标模型。",
            "validation": "用图表同时观察数据内表现与跨论文外推风险。",
            "selector": "根据验证结果选择自动最佳模型，或为 UCS / CCC 手动指定预测算法。",
            "prediction": "使用模型选择台确认的算法，输出 UCS / CCC 预测值、参考区间与可信度诊断。",
            "management": "加载历史模型，导出训练报告，追踪模型版本。",
        }
        self.header_title.configure(text=titles[page])
        self.header_subtitle.configure(text=subtitles[page])
        {"data": self.data_page, "modeling": self.modeling_page, "validation": self.validation_page, "selector": self.model_selection_page, "prediction": self.prediction_page, "management": self.management_page}[page]()
    def data_page(self) -> None:
        frame = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        actions = self.panel(frame, fg_color=COLORS["panel"], border_color=COLORS["line_light"])
        actions.grid(row=0, column=0, sticky="ew")
        actions.grid_columnconfigure(3, weight=1)
        self.button(actions, "导入 Excel", self.choose_excel, "primary", width=132).grid(row=0, column=0, padx=(16, 8), pady=14, sticky="w")
        self.button(actions, "读取默认数据表", lambda: self.load_excel(DEFAULT_EXCEL), "secondary", width=154).grid(row=0, column=1, padx=8, pady=14, sticky="w")
        self.button(actions, "生成导入模板", self.export_template, "ghost", width=146).grid(row=0, column=2, padx=8, pady=14, sticky="w")
        file_text = str(self.dataset_info.file_path) if self.dataset_info else "未选择文件"
        ctk.CTkLabel(actions, text=file_text, text_color=COLORS["muted"], font=FONTS["body"]).grid(row=0, column=3, padx=16, pady=14, sticky="e")

        summary = ctk.CTkFrame(frame, height=94, fg_color="transparent")
        summary.grid(row=1, column=0, pady=(10, 8), sticky="ew")
        summary.grid_propagate(False)
        summary.grid_rowconfigure(0, weight=1)
        values = self.summary_values()
        summary.grid_columnconfigure(tuple(range(len(values))), weight=1)
        accents = ["teal", "blue", "amber", "teal", "blue", "red"]
        for col, (label, value, hint) in enumerate(values):
            card = self.stat_card(summary, label, value, hint, accents[col % len(accents)])
            card.grid(row=0, column=col, padx=(0 if col == 0 else 7, 0 if col == len(values) - 1 else 7), sticky="nsew")

        tabs = ctk.CTkTabview(frame, fg_color=COLORS["panel"], border_width=1, border_color=COLORS["line_light"], segmented_button_selected_color=COLORS["seg_selected"], segmented_button_selected_hover_color=COLORS["seg_hover"], segmented_button_unselected_color=COLORS["seg_unselected"], segmented_button_unselected_hover_color=COLORS["seg_hover"], text_color=COLORS["ink"], text_color_disabled=COLORS["muted"])
        tabs.grid(row=2, column=0, sticky="nsew", pady=(4, 0))
        for name in ["清洗预览", "字段质量", "论文分组"]:
            tabs.add(name)
        self.cleaning_table(tabs.tab("清洗预览"))
        self.quality_table(tabs.tab("字段质量"))
        self.paper_table(tabs.tab("论文分组"))
    def modeling_page(self) -> None:
        frame = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        controls = self.panel(frame)
        controls.grid(row=0, column=0, sticky="ew")
        controls.grid_columnconfigure(3, weight=1)
        self.strategy_var = ctk.StringVar(value="中位数补全")
        self.mode_var = ctk.StringVar(value="全部比较")
        self.feature_mode_var = ctk.StringVar(value="全部特征")
        self.algorithm_checks = {}
        control_items = [
            ("缺失值", "缺失值", ["中位数补全", "只用完整行"], self.strategy_var),
            ("特征模式", "特征模式", ["原始特征", "增强特征", "全部特征"], self.feature_mode_var),
            ("算法模式", "算法模式", ["自动推荐", "手动选择", "全部比较"], self.mode_var),
        ]
        for col, (title, help_key, values, variable) in enumerate(control_items):
            box = ctk.CTkFrame(controls, fg_color="transparent")
            box.grid(row=0, column=col, padx=(16 if col == 0 else 8, 8), pady=14, sticky="w")
            self.term_label(box, title, help_key).pack(anchor="w", pady=(0, 6))
            ctk.CTkSegmentedButton(box, values=values, variable=variable, selected_color=COLORS["seg_selected"], selected_hover_color=COLORS["seg_hover"], unselected_color=COLORS["seg_unselected"], unselected_hover_color=COLORS["seg_hover"], text_color=COLORS["ink"], text_color_disabled=COLORS["muted"]).pack(anchor="w")
        self.button(controls, "训练并验证", self.train_current_data, "primary", width=142, height=44).grid(row=0, column=3, padx=16, pady=14, sticky="e")

        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        algo_panel = self.panel(body)
        algo_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.section_title(algo_panel, "候选算法", "勾选后可在手动选择模式中训练；自动推荐和全部比较会按模式处理。", "算法模式").pack(anchor="w", padx=18, pady=(18, 10))
        recommended = set(self.dataset_info.profile.recommended_algorithms) if self.dataset_info else {"svr_log", "gbr_log", "kernel_ridge_log"}
        scroller = ctk.CTkScrollableFrame(algo_panel, fg_color="transparent", scrollbar_button_color=COLORS["line"], scrollbar_button_hover_color=COLORS["soft"])
        scroller.pack(fill="both", expand=True, padx=12, pady=(0, 14))
        for name, label, desc in available_algorithm_options():
            var = ctk.BooleanVar(value=name in recommended)
            self.algorithm_checks[name] = var
            row = ctk.CTkFrame(scroller, corner_radius=11, fg_color=COLORS["panel_alt"], border_width=1, border_color=COLORS["line_light"])
            row.pack(fill="x", padx=4, pady=6)
            ctk.CTkCheckBox(row, text=label, variable=var, text_color=COLORS["ink"], font=("Microsoft YaHei UI", 13, "bold"), fg_color=COLORS["teal"], hover_color=COLORS["teal_dark"], border_color=COLORS["soft"]).pack(anchor="w", padx=12, pady=(10, 2))
            ctk.CTkLabel(row, text=desc, wraplength=560, justify="left", text_color=COLORS["muted"], font=FONTS["small"]).pack(anchor="w", padx=40, pady=(0, 10))

        report_panel = self.panel(body)
        report_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.report_container = ctk.CTkScrollableFrame(report_panel, fg_color="transparent", scrollbar_button_color=COLORS["line"], scrollbar_button_hover_color=COLORS["soft"])
        self.report_container.pack(fill="both", expand=True, padx=12, pady=12)
        self.render_modeling_report()
    def validation_kind_label(self, kind: str) -> str:
        return {"random_kfold": "随机K折", "repeated_kfold": "重复K折", "group_kfold": "按论文分组", "repeated_group_kfold": "重复论文分组"}.get(kind, kind)

    def validation_kind_from_label(self, label: str) -> str:
        return {"随机 K 折": "random_kfold", "按论文分组": "group_kfold", "重复论文分组": "repeated_group_kfold"}.get(label, "repeated_group_kfold")

    def ensure_model_selection(self) -> dict[str, str]:
        if not self.model_bundle or not self.training_report:
            return {}
        current = self.model_bundle.setdefault("model_selection", {})
        all_models = self.model_bundle.get("all_models", {}) or {}
        active_models = self.model_bundle.setdefault("models", {})
        for target, result in self.training_report.results.items():
            algorithm = current.get(target) or result.best_algorithm
            if target in all_models and algorithm not in all_models[target]:
                algorithm = result.best_algorithm
            current[target] = algorithm
            if target in all_models and algorithm in all_models[target]:
                active_models[target] = all_models[target][algorithm]
        return current

    def auto_best_algorithm(self, result, validation_kind: str) -> str:
        candidates = [v for v in result.validation_results if v.validation_kind == validation_kind]
        if not candidates:
            candidates = [v for v in result.validation_results if v.validation_kind == "group_kfold"]
        if not candidates:
            candidates = [v for v in result.validation_results if v.validation_kind == "random_kfold"]
        order = self.training_report.selected_algorithms if self.training_report else []
        return sorted(candidates, key=lambda item: (item.metrics.rmse, order.index(item.algorithm_name) if item.algorithm_name in order else 999))[0].algorithm_name

    def apply_model_selection(self, target: str, algorithm_name: str, mode: str) -> None:
        if not self.model_bundle:
            return
        self.model_selection_modes[target] = mode
        selection = self.model_bundle.setdefault("model_selection", {})
        selection[target] = algorithm_name
        all_models = self.model_bundle.get("all_models", {}) or {}
        if target in all_models and algorithm_name in all_models[target]:
            self.model_bundle.setdefault("models", {})[target] = all_models[target][algorithm_name]
        self.status_label.configure(text="已选择预测模型\n" + self.selection_summary_text())

    def selection_summary_text(self) -> str:
        if not self.training_report or not self.model_bundle:
            return "未选择模型"
        selection = self.ensure_model_selection()
        labels = []
        for target in TARGETS:
            result = self.training_report.results.get(target)
            if not result:
                continue
            labels.append(f"{target}: {self.algorithm_label(selection.get(target, result.best_algorithm))}")
        return " | ".join(labels) if labels else "未选择模型"

    def current_model_selection(self) -> dict[str, str]:
        return dict(self.ensure_model_selection())

    def on_selector_sort_change(self, _value=None) -> None:
        if not self.training_report:
            return
        validation_kind = self.validation_kind_from_label(self.selector_sort_var.get())
        for target, result in self.training_report.results.items():
            if self.model_selection_modes.get(target, "auto") == "auto":
                self.apply_model_selection(target, self.auto_best_algorithm(result, validation_kind), "auto")
        self.show_page("selector")

    def model_selection_page(self) -> None:
        frame = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        if not hasattr(self, "selector_sort_var"):
            self.selector_sort_var = ctk.StringVar(value="重复论文分组")

        top = self.panel(frame)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(top, text="自动最佳模型排序", text_color=COLORS["ink"], font=FONTS["body_bold"]).grid(row=0, column=0, padx=(18, 10), pady=16, sticky="w")
        sorter = ctk.CTkSegmentedButton(top, values=["随机 K 折", "按论文分组", "重复论文分组"], variable=self.selector_sort_var, selected_color=COLORS["seg_selected"], selected_hover_color=COLORS["seg_hover"], unselected_color=COLORS["seg_unselected"], unselected_hover_color=COLORS["seg_hover"], text_color=COLORS["ink"], text_color_disabled=COLORS["muted"], command=self.on_selector_sort_change)
        sorter.grid(row=0, column=1, padx=8, pady=14, sticky="w")
        ctk.CTkLabel(top, text="自动模式会按所选验证指标选择 RMSE 最低的算法；手动模式会覆盖自动选择。", text_color=COLORS["muted"], font=FONTS["body"]).grid(row=0, column=2, padx=16, pady=14, sticky="w")

        body = ctk.CTkScrollableFrame(frame, fg_color="transparent", scrollbar_button_color=COLORS["line"], scrollbar_button_hover_color=COLORS["soft"])
        body.grid(row=1, column=0, pady=(14, 0), sticky="nsew")
        body.grid_columnconfigure((0, 1), weight=1)
        if not self.training_report or not self.model_bundle:
            empty = self.panel(body, fg_color=COLORS["panel_tint"])
            empty.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
            ctk.CTkLabel(empty, text="尚未训练模型", text_color=COLORS["ink"], font=FONTS["section"]).pack(anchor="w", padx=18, pady=(18, 5))
            ctk.CTkLabel(empty, text="请先在建模控制页完成训练，再回到这里选择用于可信预测的算法。", text_color=COLORS["muted"], font=FONTS["body"]).pack(anchor="w", padx=18, pady=(0, 18))
            return

        selection = self.ensure_model_selection()
        validation_kind = self.validation_kind_from_label(self.selector_sort_var.get())
        all_models = self.model_bundle.get("all_models", {}) or {}
        for index, target in enumerate(TARGETS):
            result = self.training_report.results.get(target)
            if not result:
                continue
            card = self.panel(body)
            card.grid(row=index // 2, column=index % 2, padx=6, pady=6, sticky="nsew")
            card.grid_columnconfigure(0, weight=1)
            auto_algorithm = self.auto_best_algorithm(result, validation_kind)
            current_algorithm = selection.get(target, auto_algorithm)
            if self.model_selection_modes.get(target, "auto") == "auto":
                current_algorithm = auto_algorithm
                self.apply_model_selection(target, current_algorithm, "auto")
            mode_text = "自动最佳模型" if self.model_selection_modes.get(target, "auto") == "auto" else "手动指定模型"
            ctk.CTkLabel(card, text=f"{target}  |  {mode_text}", text_color=COLORS["ink"], font=("Microsoft YaHei UI", 20, "bold")).grid(row=0, column=0, padx=18, pady=(18, 4), sticky="w")
            ctk.CTkLabel(card, text=f"当前用于预测：{self.algorithm_label(current_algorithm)}", text_color=COLORS["teal"], font=FONTS["body_bold"]).grid(row=1, column=0, padx=18, pady=(0, 10), sticky="w")

            target_models = all_models.get(target, {}) if isinstance(all_models, dict) else {}
            algorithm_names = list(target_models.keys()) if target_models else [result.best_algorithm]
            display_to_algorithm = {self.algorithm_label(name): name for name in algorithm_names}
            auto_display = f"自动最佳模型：{self.algorithm_label(auto_algorithm)}"
            values = [auto_display] + list(display_to_algorithm.keys())
            selected_display = auto_display if self.model_selection_modes.get(target, "auto") == "auto" else self.algorithm_label(current_algorithm)
            menu_var = ctk.StringVar(value=selected_display)

            def choose(value, current_target=target, current_auto=auto_algorithm, current_map=display_to_algorithm):
                if value.startswith("自动最佳模型"):
                    self.apply_model_selection(current_target, current_auto, "auto")
                else:
                    self.apply_model_selection(current_target, current_map.get(value, current_auto), "manual")
                self.show_page("selector")

            menu = ctk.CTkOptionMenu(card, values=values, variable=menu_var, command=choose, fg_color=COLORS["panel_tint"], button_color=COLORS["teal"], button_hover_color=COLORS["teal_dark"], text_color=COLORS["ink"], dropdown_fg_color=COLORS["white"], dropdown_text_color=COLORS["ink"], dropdown_hover_color=COLORS["panel_tint"], height=38)
            menu.grid(row=2, column=0, padx=18, pady=(0, 12), sticky="ew")
            if not target_models:
                ctk.CTkLabel(card, text="当前加载的是旧模型文件，只包含自动最佳模型，需重新训练后才能手动选择其他算法。", text_color=COLORS["amber"], font=FONTS["small"], wraplength=520, justify="left").grid(row=3, column=0, padx=18, pady=(0, 8), sticky="w")

            selected_validations = [v for v in result.validation_results if v.algorithm_name == current_algorithm]
            rows = [[self.validation_kind_label(v.validation_kind), format_number(v.metrics.rmse, 2), format_number(v.metrics.mae, 2), f"{v.metrics.r2:.3f}", str(v.fold_count)] for v in selected_validations]
            table_holder = ctk.CTkFrame(card, fg_color="transparent")
            table_holder.grid(row=4, column=0, padx=18, pady=(0, 18), sticky="nsew")
            self.tree(table_holder, ["验证方式", "RMSE", "MAE", "R²", "折数"], rows, 5, {"验证方式": 2, "RMSE": 1, "MAE": 1, "R²": 1, "折数": 1})
    def validation_page(self) -> None:
        frame = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        top = self.panel(frame)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(1, weight=1)
        self.validation_target_var = ctk.StringVar(value=TARGETS[0])
        ctk.CTkSegmentedButton(top, values=TARGETS, variable=self.validation_target_var, selected_color=COLORS["seg_selected"], selected_hover_color=COLORS["seg_hover"], unselected_color=COLORS["seg_unselected"], unselected_hover_color=COLORS["seg_hover"], text_color=COLORS["ink"], text_color_disabled=COLORS["muted"], command=lambda _: self.redraw_validation_chart()).grid(row=0, column=0, padx=16, pady=14, sticky="w")
        hint = ctk.CTkLabel(top, text="诊断中心会同时展示算法排名、预测-实测、残差、原始输入影响、论文误差和泛化风险。", text_color=COLORS["muted"], font=FONTS["body"])
        hint.grid(row=0, column=1, padx=10, pady=14, sticky="w")
        Tooltip(hint, HELP_TEXT["随机K折"] + "\n\n" + HELP_TEXT["按论文分组"] + "\n\n" + HELP_TEXT["重复论文分组"])
        self.button(top, "导出当前图", self.export_current_chart, "secondary", width=124, height=38).grid(row=0, column=2, padx=16, pady=14, sticky="e")

        self.chart_panel = self.panel(frame, fg_color=COLORS["panel"])
        self.chart_panel.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        self.chart_panel.grid_columnconfigure(0, weight=1)
        self.chart_panel.grid_rowconfigure(0, weight=1)
        self.chart_scroll = ctk.CTkScrollableFrame(self.chart_panel, fg_color="transparent", scrollbar_button_color=COLORS["line"], scrollbar_button_hover_color=COLORS["soft"])
        self.chart_scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.chart_scroll.grid_columnconfigure(0, weight=1)
        self.redraw_validation_chart()
    def prediction_page(self) -> None:
        frame = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=2)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        form_panel = self.panel(frame)
        form_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        form_panel.grid_columnconfigure(0, weight=1)
        form_panel.grid_rowconfigure(1, weight=1)
        self.section_title(form_panel, "实验输入", "只填写原始实验参数，体积和增强特征由系统自动计算。", None).grid(row=0, column=0, padx=18, pady=(18, 10), sticky="w")
        form_body = ctk.CTkScrollableFrame(form_panel, fg_color="transparent", scrollbar_button_color=COLORS["line"], scrollbar_button_hover_color=COLORS["soft"])
        form_body.grid(row=1, column=0, padx=12, pady=(0, 4), sticky="nsew")
        form_body.grid_columnconfigure((0, 1), weight=1)
        self.input_vars = {}
        for index, feature in enumerate(USER_INPUT_FEATURES):
            grid_row = index // 2
            grid_col = index % 2
            cell = ctk.CTkFrame(form_body, corner_radius=11, fg_color=COLORS["panel_alt"], border_width=1, border_color=COLORS["line_light"])
            cell.grid(row=grid_row, column=grid_col, padx=6, pady=6, sticky="ew")
            cell.grid_columnconfigure(0, weight=1)
            unit = f"  {feature.unit}" if feature.unit else ""
            ctk.CTkLabel(cell, text=f"{feature.label}{unit}", text_color="#2d4740", font=FONTS["body_bold"]).grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")
            var = ctk.StringVar()
            var.trace_add("write", lambda *_: self.update_derived_panel())
            self.input_vars[feature.key] = var
            ctk.CTkEntry(cell, textvariable=var, height=36, corner_radius=9, fg_color=COLORS["white"], border_color=COLORS["line"], text_color=COLORS["ink"], placeholder_text="输入数值或区间").grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
        action_bar = ctk.CTkFrame(form_panel, fg_color="transparent")
        action_bar.grid(row=2, column=0, padx=18, pady=(8, 16), sticky="ew")
        action_bar.grid_columnconfigure((0, 1), weight=1)
        self.button(action_bar, "生成可信预测", self.predict_current_input, "primary", height=44).grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.button(action_bar, "加入方案对比", self.add_scenario, "secondary", height=44).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        derived_panel = self.panel(frame)
        derived_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        derived_panel.grid_columnconfigure(0, weight=1)
        derived_panel.grid_rowconfigure(4, weight=1)
        self.section_title(derived_panel, "自动计算", "实时生成体积和科研增强特征。", "增强特征").grid(row=0, column=0, padx=18, pady=(18, 10), sticky="w")
        feature_box = ctk.CTkFrame(derived_panel, corner_radius=12, fg_color=COLORS["panel_tint"], border_width=1, border_color=COLORS["line_light"])
        feature_box.grid(row=1, column=0, padx=18, pady=(0, 12), sticky="ew")
        feature_box.grid_columnconfigure(0, weight=1)
        self.derived_text = ctk.CTkLabel(feature_box, text="填写高度和内径后自动计算体积。", wraplength=315, justify="left", text_color=COLORS["muted"], font=FONTS["body"])
        self.derived_text.grid(row=0, column=0, padx=14, pady=14, sticky="w")
        self.button(derived_panel, "批量预测 Excel", self.batch_predict, "secondary", height=40).grid(row=2, column=0, padx=18, pady=(0, 12), sticky="ew")
        ctk.CTkLabel(derived_panel, text="方案对比", font=FONTS["section"], text_color=COLORS["ink"]).grid(row=3, column=0, padx=18, pady=(4, 8), sticky="w")
        self.scenario_table_holder = ctk.CTkFrame(derived_panel, fg_color="transparent")
        self.scenario_table_holder.grid(row=4, column=0, padx=18, pady=(0, 14), sticky="nsew")
        self.render_scenarios()

        result_panel = self.panel(frame)
        result_panel.grid(row=0, column=2, sticky="nsew")
        result_panel.grid_columnconfigure(0, weight=1)
        result_panel.grid_rowconfigure(4, weight=1)
        self.section_title(result_panel, "预测结果", "区分预测值、参考区间与可信度提示。", None).grid(row=0, column=0, padx=18, pady=(18, 10), sticky="w")
        ucs_card = ctk.CTkFrame(result_panel, corner_radius=14, fg_color=COLORS["white"], border_width=1, border_color=COLORS["line_light"])
        ucs_card.grid(row=1, column=0, padx=18, pady=(0, 10), sticky="ew")
        self.ucs_value = ctk.CTkLabel(ucs_card, text="UCS/kpa\n--", justify="left", text_color=COLORS["ink"], font=("Microsoft YaHei UI", 25, "bold"))
        self.ucs_value.pack(anchor="w", padx=16, pady=14)
        ccc_card = ctk.CTkFrame(result_panel, corner_radius=14, fg_color=COLORS["white"], border_width=1, border_color=COLORS["line_light"])
        ccc_card.grid(row=2, column=0, padx=18, pady=(0, 12), sticky="ew")
        self.ccc_value = ctk.CTkLabel(ccc_card, text="CCC\n--", justify="left", text_color=COLORS["ink"], font=("Microsoft YaHei UI", 25, "bold"))
        self.ccc_value.pack(anchor="w", padx=16, pady=14)
        diag = ctk.CTkFrame(result_panel, corner_radius=14, fg_color=COLORS["panel_tint"], border_width=1, border_color=COLORS["line_light"])
        diag.grid(row=3, column=0, padx=18, pady=(0, 12), sticky="ew")
        self.term_label(diag, "可信度诊断", "可信度", 15).pack(anchor="w", padx=14, pady=(12, 5))
        note = ("模型已就绪：" + self.selection_summary_text()) if self.model_bundle else "训练模型后即可预测。结果用于科研辅助判断。"
        self.prediction_note = ctk.CTkLabel(diag, text=note, wraplength=340, justify="left", text_color=COLORS["muted"], font=FONTS["body"])
        self.prediction_note.pack(anchor="w", padx=14, pady=(0, 12))
        self.similar_note = ctk.CTkLabel(result_panel, text="", wraplength=350, justify="left", text_color=COLORS["muted"], font=FONTS["small"])
        self.similar_note.grid(row=4, column=0, padx=18, pady=(0, 14), sticky="nw")
        self.update_derived_panel()
    def management_page(self) -> None:
        frame = ctk.CTkFrame(self.page_frame, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        actions = self.panel(frame)
        actions.grid(row=0, column=0, sticky="ew")
        actions.grid_columnconfigure(2, weight=1)
        self.button(actions, "加载模型", self.choose_model, "primary", width=116).grid(row=0, column=0, padx=(16, 8), pady=14, sticky="w")
        self.button(actions, "导出训练报告", self.export_report, "secondary", width=132).grid(row=0, column=1, padx=8, pady=14, sticky="w")
        ctk.CTkLabel(actions, text="模型保存后会自动写入训练历史，用于追踪不同数据和算法版本。", text_color=COLORS["muted"], font=FONTS["body"]).grid(row=0, column=2, padx=16, pady=14, sticky="e")
        table_panel = self.panel(frame)
        table_panel.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        table_panel.grid_columnconfigure(0, weight=1)
        table_panel.grid_rowconfigure(1, weight=1)
        self.section_title(table_panel, "训练历史", "用于回溯不同算法、特征模式和泛化风险。", None).grid(row=0, column=0, padx=18, pady=(18, 8), sticky="w")
        self.history_table(table_panel)
    def run_progress_task(self, title: str, subtitle: str, steps: list[tuple[float, str]], estimate_seconds: float, work, on_success, on_error=None, min_visible_ms: int = 650, progress_events=None) -> None:
        if getattr(self, "active_progress", None):
            messagebox.showwarning("任务进行中", "当前已有计算任务正在运行，请稍候。")
            return
        dialog = ParticleProgressDialog(self, title, subtitle, steps)
        self.active_progress = dialog
        dialog.set_progress(0.04, "准备启动后台任务")
        started = time.perf_counter()
        state: dict[str, object] = {"done": False, "ok": False}

        def worker() -> None:
            try:
                state["result"] = work()
                state["ok"] = True
            except Exception as exc:
                state["exc"] = exc
                state["ok"] = False
            finally:
                state["done"] = True

        threading.Thread(target=worker, daemon=True).start()

        def poll() -> None:
            elapsed = time.perf_counter() - started
            latest_progress = None
            if progress_events is not None:
                while True:
                    try:
                        latest_progress = progress_events.get_nowait()
                    except queue.Empty:
                        break
            if state.get("done"):
                dialog.set_progress(1.0, "计算完成，正在刷新界面")
                wait_ms = max(0, min_visible_ms - int(elapsed * 1000)) + 320

                def finish() -> None:
                    self.active_progress = None
                    dialog.close()
                    if state.get("ok"):
                        on_success(state.get("result"))
                    elif on_error:
                        on_error(state.get("exc"))
                    else:
                        messagebox.showerror("任务失败", str(state.get("exc")))

                self.after(wait_ms, finish)
                return
            if latest_progress:
                value, stage = latest_progress
                dialog.set_progress(float(value), str(stage))
            else:
                value = min(0.94, 0.05 + (1 - math.exp(-elapsed / max(estimate_seconds, 0.5))) * 0.88)
                dialog.set_progress(value)
            self.after(80, poll)

        poll()

    def choose_excel(self) -> None:
        path = filedialog.askopenfilename(title="选择数据表", filetypes=[("Excel 文件", "*.xlsx *.xls"), ("所有文件", "*.*")])
        if path:
            self.load_excel(Path(path))

    def load_excel(self, path: Path, quiet: bool = False) -> None:
        try:
            self.raw_df, self.prepared_df, self.dataset_info = load_dataset(path)
            self.status_label.configure(text=f"已读取：{path.name}\n{self.dataset_info.row_count} 行 | {self.dataset_info.profile.group_count} 组")
            if not quiet:
                self.show_page(self.active_page)
        except Exception as exc:
            if not quiet:
                messagebox.showerror("读取失败", str(exc))

    def train_current_data(self) -> None:
        if self.prepared_df is None:
            messagebox.showwarning("缺少数据", "请先导入 Excel 数据表。")
            return
        strategy = "median" if self.strategy_var.get() == "中位数补全" else "complete"
        mode_map = {"自动推荐": "auto", "手动选择": "manual", "全部比较": "all"}
        feature_map = {"原始特征": "original", "增强特征": "engineered", "全部特征": "all"}
        selected = [name for name, var in self.algorithm_checks.items() if var.get()]
        steps = [
            (0.08, "锁定训练配置"),
            (0.18, "清洗样本并构造特征"),
            (0.36, "候选算法交叉验证"),
            (0.58, "跨论文泛化诊断"),
            (0.76, "拟合最终模型"),
            (0.90, "写入模型版本"),
        ]

        progress_events: queue.Queue[tuple[float, str]] = queue.Queue()

        def report_progress(value: float, stage: str) -> None:
            progress_events.put((value, stage))

        def work():
            return train_models(self.prepared_df, self.raw_df, strategy, mode_map[self.mode_var.get()], selected, "repeated_group_kfold", MODEL_PATH, feature_map[self.feature_mode_var.get()], str(self.dataset_info.file_path) if self.dataset_info else None, report_progress)

        def success(payload) -> None:
            self.model_bundle, self.training_report = payload
            self.model_selection_modes = {target: "auto" for target in TARGETS}
            self.ensure_model_selection()
            self.status_label.configure(text=f"模型已训练\n保存到 {MODEL_PATH}")
            self.render_modeling_report()
            messagebox.showinfo("训练完成", "UCS 与 CCC 已完成算法比较、交叉验证和风险诊断。")

        def failure(exc) -> None:
            if isinstance(exc, RuntimeError):
                messagebox.showerror("缺少依赖", str(exc))
            elif isinstance(exc, DataValidationError):
                messagebox.showerror("训练失败", str(exc))
            else:
                messagebox.showerror("训练失败", f"{type(exc).__name__}: {exc}")

        self.status_label.configure(text="正在训练模型...\n粒子进度已启动")
        self.run_progress_task("模型训练中", "正在比较候选算法、执行交叉验证并生成可解释诊断。", steps, 7.0, work, success, failure, min_visible_ms=1200, progress_events=progress_events)
    def choose_model(self) -> None:
        path = filedialog.askopenfilename(title="选择模型文件", filetypes=[("Joblib 模型", "*.joblib"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            self.model_bundle = load_model_bundle(path)
            self.training_report = self.model_bundle.get("training_report")
            self.model_selection_modes = {target: "auto" for target in TARGETS}
            self.ensure_model_selection()
            self.status_label.configure(text=f"已加载模型\n{Path(path).name}")
            self.show_page(self.active_page)
        except Exception as exc:
            messagebox.showerror("加载失败", str(exc))

    def predict_current_input(self) -> None:
        if not self.model_bundle:
            messagebox.showwarning("模型未就绪", "请先训练模型或加载已有模型。")
            return
        values = {key: var.get() for key, var in self.input_vars.items()}
        frame = build_prediction_frame(values, self.model_bundle.get("feature_mode", "all"))
        if frame.isna().any(axis=None):
            messagebox.showwarning("输入不完整", "请填写所有输入参数，且必须为数字或数字区间。")
            return
        selection = self.current_model_selection()
        steps = [(0.18, "解析实验输入"), (0.36, "生成体积与增强特征"), (0.62, "调用所选模型"), (0.82, "校准参考区间"), (0.93, "生成可信度诊断")]

        def work():
            return predict_with_diagnostics(self.model_bundle, values, selection)

        def success(result) -> None:
            self.ucs_value.configure(text=self.prediction_text("UCS/kpa", result))
            self.ccc_value.configure(text=self.prediction_text("CCC", result))
            lines = [f"可信度：{result.confidence_level}", "预测模型：" + self.selection_summary_text(), f"自动计算体积：{format_number(result.specimen_volume_mm3, 2)} mm3"]
            if math.isfinite(result.nearest_distance):
                lines.append(f"最近训练样本距离：{result.nearest_distance:.2f}")
            lines.extend(result.messages)
            self.prediction_note.configure(text="\n".join(lines), text_color=COLORS["red"] if result.confidence_level == "低" else COLORS["muted"])
            if result.similar_samples:
                sims = [f"相似样本：行 {s.row_number} | {s.target} 实测 {format_number(s.observed, 2)} | 距离 {s.distance:.2f}" for s in result.similar_samples]
                self.similar_note.configure(text="\n".join(sims))
            else:
                self.similar_note.configure(text="")
            self.update_derived_panel(result.engineered_values)

        self.run_progress_task("可信预测计算中", "正在把实验方案映射到所选模型，并生成区间与风险提示。", steps, 1.2, work, success, lambda exc: messagebox.showerror("预测失败", str(exc)), min_visible_ms=850)
    def prediction_text(self, target: str, result) -> str:
        value = result.predictions.get(target, float("nan"))
        line = f"{target}\n{format_number(value, 2 if target == 'UCS/kpa' else 4)}"
        if target in result.intervals:
            low, high = result.intervals[target]
            line += f"\n参考区间 {format_number(low, 2)} - {format_number(high, 2)}"
        return line

    def update_derived_panel(self, engineered_values: dict[str, float] | None = None) -> None:
        if not hasattr(self, "derived_text"):
            return
        try:
            values = {key: var.get() for key, var in self.input_vars.items()}
            if engineered_values is None:
                row = {feature.key: parse_numeric(values.get(feature.key)) for feature in USER_INPUT_FEATURES}
                row["specimen_volume_mm3"] = calculate_volume(row["height_mm"], row["inner_diameter_mm"])
                engineered_values = {"specimen_volume_mm3": row["specimen_volume_mm3"]}
        except Exception:
            engineered_values = {}
        lines = []
        label_map = {feature.key: feature.label for feature in FEATURES + ENGINEERED_FEATURES}
        for key in ["specimen_volume_mm3", "aspect_ratio", "bacteria_per_volume", "cementation_per_volume", "cacl2_total_index", "urea_total_index", "ca_urea_ratio", "cementation_intensity"]:
            value = engineered_values.get(key, float("nan")) if engineered_values else float("nan")
            lines.append(f"{label_map.get(key, key)}：{format_number(value, 6 if 'per_volume' in key else 3)}")
        self.derived_text.configure(text="\n".join(lines))

    def add_scenario(self) -> None:
        if not self.model_bundle:
            messagebox.showwarning("模型未就绪", "请先训练模型或加载已有模型。")
            return
        values = {key: var.get() for key, var in self.input_vars.items()}
        selection = self.current_model_selection()
        steps = [(0.22, "读取方案输入"), (0.52, "执行双目标预测"), (0.78, "写入方案对比"), (0.92, "刷新表格")]

        def work():
            return predict_with_diagnostics(self.model_bundle, values, selection)

        def success(result) -> None:
            self.scenarios.append({"方案": f"方案 {len(self.scenarios) + 1}", "UCS/kpa": format_number(result.predictions.get("UCS/kpa"), 2), "CCC": format_number(result.predictions.get("CCC"), 4), "可信度": result.confidence_level})
            self.render_scenarios()

        self.run_progress_task("方案写入中", "正在使用当前模型组合计算该方案并加入对比表。", steps, 0.9, work, success, lambda exc: messagebox.showerror("加入失败", str(exc)), min_visible_ms=650)
    def batch_predict(self) -> None:
        if not self.model_bundle:
            messagebox.showwarning("模型未就绪", "请先训练模型或加载已有模型。")
            return
        path = filedialog.askopenfilename(title="选择批量预测 Excel", filetypes=[("Excel 文件", "*.xlsx *.xls")])
        if not path:
            return
        save_path = filedialog.asksaveasfilename(title="保存预测结果", defaultextension=".xlsx", filetypes=[("Excel 文件", "*.xlsx")])
        if not save_path:
            return
        selection = self.current_model_selection()
        steps = [(0.16, "读取批量表格"), (0.38, "清洗输入字段"), (0.62, "逐行执行预测"), (0.82, "生成诊断提示"), (0.94, "写入 Excel 结果")]

        def work():
            import pandas as pd
            raw = pd.read_excel(path, sheet_name="Sheet1")
            output = predict_many(self.model_bundle, raw, selection)
            output.to_excel(save_path, index=False)
            return save_path

        def success(result_path) -> None:
            messagebox.showinfo("批量预测完成", f"已保存：{result_path}")

        self.run_progress_task("批量预测处理中", "正在批量计算 UCS/CCC、可信度与诊断提示。", steps, 3.0, work, success, lambda exc: messagebox.showerror("批量预测失败", str(exc)), min_visible_ms=1000)
    def export_template(self) -> None:
        path = filedialog.asksaveasfilename(title="保存导入模板", defaultextension=".xlsx", initialfile="MICP数据导入模板.xlsx", filetypes=[("Excel 文件", "*.xlsx")])
        if not path:
            return
        try:
            make_import_template(path)
            messagebox.showinfo("模板已生成", f"已保存：{path}")
        except Exception as exc:
            messagebox.showerror("生成失败", str(exc))

    def export_report(self) -> None:
        if not self.training_report:
            messagebox.showwarning("缺少报告", "请先训练模型或加载包含报告的模型。")
            return
        path = filedialog.asksaveasfilename(title="保存训练报告", defaultextension=".xlsx", initialfile="MICP训练报告.xlsx", filetypes=[("Excel 文件", "*.xlsx")])
        if not path:
            return
        try:
            export_training_report(self.training_report, path)
            messagebox.showinfo("导出完成", f"已保存：{path}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def export_current_chart(self) -> None:
        if not self.last_figure:
            messagebox.showwarning("没有图表", "训练后进入验证页再导出图表。")
            return
        path = filedialog.asksaveasfilename(title="保存验证图", defaultextension=".png", initialfile="MICP验证诊断.png", filetypes=[("PNG 图片", "*.png")])
        if path:
            self.last_figure.savefig(path, dpi=180, bbox_inches="tight")
            messagebox.showinfo("导出完成", f"已保存：{path}")

    def render_modeling_report(self) -> None:
        for widget in self.report_container.winfo_children():
            widget.destroy()
        if not self.training_report:
            empty = ctk.CTkFrame(self.report_container, corner_radius=16, fg_color=COLORS["panel_tint"], border_width=1, border_color=COLORS["line_light"])
            empty.pack(fill="x", padx=4, pady=4)
            empty.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(empty, text="尚未训练模型", text_color=COLORS["ink"], font=FONTS["section"]).grid(row=0, column=0, padx=16, pady=(16, 5), sticky="w")
            ctk.CTkLabel(empty, text="建议使用“全部比较 + 全部特征”先获得完整算法排名，再结合验证页判断科研可用性。", wraplength=520, justify="left", text_color=COLORS["muted"], font=FONTS["body"]).grid(row=1, column=0, padx=16, pady=(0, 16), sticky="w")
            if self.empty_decor_image:
                ctk.CTkLabel(empty, image=self.empty_decor_image, text="").grid(row=0, column=1, rowspan=2, padx=(6, 16), pady=10, sticky="e")
            return
        meta = ctk.CTkFrame(self.report_container, corner_radius=12, fg_color=COLORS["panel_alt"], border_width=1, border_color=COLORS["line_light"])
        meta.pack(fill="x", padx=4, pady=(4, 10))
        ctk.CTkLabel(meta, text=f"训练时间：{self.training_report.trained_at}", text_color=COLORS["ink"], font=FONTS["body_bold"]).pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(meta, text=f"特征模式：{self.feature_mode_label(self.training_report.feature_mode)} | 已比较算法：{', '.join(self.algorithm_label(x) for x in self.training_report.selected_algorithms)}", wraplength=620, justify="left", text_color=COLORS["muted"], font=FONTS["small"]).pack(anchor="w", padx=14, pady=(0, 12))
        for target, result in self.training_report.results.items():
            card = ctk.CTkFrame(self.report_container, corner_radius=14, fg_color=COLORS["white"], border_width=1, border_color=COLORS["line_light"])
            card.pack(fill="x", padx=4, pady=8)
            risk_color = COLORS["red"] if result.generalization_risk == "高" else COLORS["amber"] if result.generalization_risk == "中" else COLORS["teal"]
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.grid(row=0, column=0, columnspan=2, padx=16, pady=(14, 5), sticky="ew")
            header.grid_columnconfigure(0, weight=1)
            header.grid_columnconfigure(1, weight=0)
            ctk.CTkLabel(header, text=f"{target}  |  {result.best_algorithm_label}", text_color=COLORS["ink"], font=("Microsoft YaHei UI", 20, "bold"), wraplength=430, justify="left").grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(header, text=f"泛化风险 {result.generalization_risk}", text_color="white", fg_color=risk_color, corner_radius=9, width=92, height=28, font=FONTS["small"]).grid(row=0, column=1, sticky="e")
            detail = f"样本 {result.sample_count} | 论文组 {result.group_count} | 目标变换 {'log1p' if result.uses_log_target else '原始值'} | 参数 {result.best_params}"
            ctk.CTkLabel(card, text=detail, text_color=COLORS["muted"], font=FONTS["small"]).grid(row=1, column=0, columnspan=2, padx=16, sticky="w")
            repeated_group_metrics = getattr(result, "repeated_group_metrics", None)
            rows = [("随机K折", result.random_metrics, "随机K折"), ("重复K折", result.repeated_metrics, "重复K折"), ("按论文分组", result.group_metrics, "按论文分组"), ("重复论文分组", repeated_group_metrics, "重复论文分组")]
            metric_grid = ctk.CTkFrame(card, fg_color="transparent")
            metric_grid.grid(row=2, column=0, columnspan=2, padx=12, pady=(10, 4), sticky="ew")
            metric_grid.grid_columnconfigure((0, 1), weight=1)
            for i, (name, metrics, help_key) in enumerate(rows):
                tile = ctk.CTkFrame(metric_grid, corner_radius=11, fg_color=COLORS["panel_alt"], border_width=1, border_color=COLORS["line_light"])
                tile.grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky="ew")
                label = ctk.CTkLabel(tile, text=name, text_color=COLORS["muted"], font=FONTS["small"])
                label.pack(anchor="w", padx=12, pady=(9, 1))
                Tooltip(label, HELP_TEXT[help_key])
                ctk.CTkLabel(tile, text=metrics_text(metrics), text_color=COLORS["ink"], font=FONTS["body_bold"], wraplength=250, justify="left").pack(anchor="w", padx=12, pady=(0, 9))
            residual = ctk.CTkLabel(card, text=f"残差参考：P80={format_number(result.residual_p80, 2)}，P95={format_number(result.residual_p95, 2)}", text_color=COLORS["muted"], font=FONTS["body"])
            residual.grid(row=3, column=0, columnspan=2, padx=16, pady=(4, 3), sticky="w")
            impacts = [item for item in getattr(result, "input_impacts", []) if float(item.get("normalized_impact") or 0.0) > 0][:3]
            if impacts:
                impact_text = " | ".join(f"{item.get('feature')} {float(item.get('normalized_impact') or 0.0):.0%}（{item.get('direction')}）" for item in impacts)
                ctk.CTkLabel(card, text=f"输入影响Top3：{impact_text}", wraplength=620, justify="left", text_color=COLORS["muted"], font=FONTS["body"]).grid(row=4, column=0, columnspan=2, padx=16, pady=(0, 5), sticky="w")
            ctk.CTkLabel(card, text=result.risk_reason, wraplength=620, justify="left", text_color=risk_color, font=FONTS["body_bold"]).grid(row=5, column=0, columnspan=2, padx=16, pady=(0, 14), sticky="w")
            card.grid_columnconfigure(0, weight=1)

    def redraw_validation_chart(self) -> None:
        if not hasattr(self, "chart_panel"):
            return
        container = self.chart_scroll if hasattr(self, "chart_scroll") else self.chart_panel
        for widget in container.winfo_children():
            widget.destroy()
        if not self.training_report:
            empty = ctk.CTkFrame(container, corner_radius=18, fg_color=COLORS["panel_tint"], border_width=1, border_color=COLORS["line_light"])
            empty.grid(row=0, column=0, padx=18, pady=18, sticky="ew")
            empty.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(empty, text="诊断中心等待训练结果", text_color=COLORS["ink"], font=("Microsoft YaHei UI", 20, "bold")).grid(row=0, column=0, padx=18, pady=(18, 5), sticky="w")
            ctk.CTkLabel(empty, text="完成训练后，这里会显示算法排名、预测-实测、残差分布、原始输入影响、论文误差和 R² 泛化对比。", text_color=COLORS["muted"], font=FONTS["body"], wraplength=620, justify="left").grid(row=1, column=0, padx=18, pady=(0, 18), sticky="w")
            if self.empty_decor_image:
                ctk.CTkLabel(empty, image=self.empty_decor_image, text="").grid(row=0, column=1, rowspan=2, padx=(8, 20), pady=12, sticky="e")
            return
        if not HAS_MATPLOTLIB:
            ctk.CTkLabel(container, text="缺少 matplotlib，请运行 install_deps.bat 后重启软件。", text_color=COLORS["amber"], font=("Microsoft YaHei UI", 16, "bold")).grid(row=0, column=0, padx=18, pady=18, sticky="w")
            return
        target = self.validation_target_var.get()
        result = self.training_report.results[target]
        paper_count = max(4, len(self.paper_error_rows(result)))
        lower_row_ratio = max(1.15, min(1.75, paper_count * 0.12))
        figure_height = max(14.8, 12.2 + paper_count * 0.22)
        figure = Figure(figsize=(13.0, figure_height), dpi=100, facecolor=COLORS["panel"], constrained_layout=True)
        axes = figure.subplots(3, 2, gridspec_kw={"height_ratios": [1.04, 1.0, lower_row_ratio], "wspace": 0.12, "hspace": 0.18})
        self.plot_algorithm_rank(axes[0][0], result)
        self.plot_predicted_observed(axes[0][1], result)
        self.plot_residuals(axes[1][0], result)
        self.plot_input_impact(axes[1][1], result)
        self.plot_paper_errors(axes[2][0], result)
        self.plot_metric_compare(axes[2][1], result)
        for ax in axes.ravel():
            self.style_axis(ax)
        self.last_figure = figure
        canvas = FigureCanvasTkAgg(figure, master=container)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="ew", padx=14, pady=14)

    def style_axis(self, ax) -> None:
        ax.set_facecolor(COLORS["panel"])
        ax.title.set_fontsize(13)
        ax.title.set_fontweight("bold")
        ax.title.set_color(COLORS["ink"])
        ax.title.set_position((0.5, 1.02))
        ax.tick_params(colors=COLORS["ink"], labelsize=9, pad=4)
        ax.xaxis.label.set_color(COLORS["muted"])
        ax.yaxis.label.set_color(COLORS["muted"])
        ax.xaxis.label.set_size(10)
        ax.yaxis.label.set_size(10)
        for spine in ax.spines.values():
            spine.set_color(COLORS["line"])
            spine.set_linewidth(0.8)
        ax.grid(color=COLORS["line"], alpha=0.34, linewidth=0.7)
        ax.margins(x=0.025, y=0.08)

    def plot_algorithm_rank(self, ax, result) -> None:
        random = [v for v in result.validation_results if v.validation_kind == "random_kfold"]
        group = [v for v in result.validation_results if v.validation_kind == "group_kfold"]
        labels = [v.algorithm_label.replace("GradientBoosting", "GBR").replace("GaussianProcess", "GPR") for v in random]
        labels = [textwrap.fill(label, 13) for label in labels]
        x = range(len(labels))
        random_values = [max(v.metrics.rmse, 1e-6) for v in random]
        ax.bar([i - 0.18 for i in x], random_values, width=0.36, label="随机K折", color=COLORS["teal"])
        if group:
            by_name = {v.algorithm_name: max(v.metrics.rmse, 1e-6) for v in group}
            ax.bar([i + 0.18 for i in x], [by_name.get(v.algorithm_name, 1e-6) for v in random], width=0.36, label="按论文分组", color=COLORS["blue"])
        ax.set_yscale("log")
        ax.set_title("算法 RMSE 排名（原始尺度）")
        ax.set_ylabel("RMSE（log，越低越好）")
        ax.set_xlabel("候选算法")
        ax.set_xticks(list(x), labels, rotation=0, ha="center")
        ax.legend(fontsize=9, frameon=False, loc="upper right")
        ax.grid(axis="y", alpha=0.25, which="both")

    def best_validation(self, result, kind="random_kfold"):
        return next(v for v in result.validation_results if v.algorithm_name == result.best_algorithm and v.validation_kind == kind)

    def paper_error_rows(self, result) -> list[dict[str, object]]:
        for kind in ["repeated_group_kfold", "group_kfold"]:
            for validation in result.validation_results:
                if validation.algorithm_name == result.best_algorithm and validation.validation_kind == kind and validation.paper_errors:
                    return validation.paper_errors
        return []

    def plot_predicted_observed(self, ax, result) -> None:
        val = self.best_validation(result, "random_kfold")
        ax.scatter(val.y_true, val.y_pred, color=COLORS["teal"], s=34, alpha=0.82, edgecolors=COLORS["green"], linewidths=0.3)
        low = min(min(val.y_true), min(val.y_pred))
        high = max(max(val.y_true), max(val.y_pred))
        padding = (high - low) * 0.04 if high > low else max(abs(high), 1.0) * 0.04
        low -= padding
        high += padding
        ax.plot([low, high], [low, high], color=COLORS["amber"], linestyle="--", linewidth=1.1, label="理想预测线")
        ax.set_xlim(low, high)
        ax.set_ylim(low, high)
        ax.set_title(f"预测-实测对照（{val.fold_count} 折随机K折）")
        ax.set_xlabel(f"实测 {result.target}")
        ax.set_ylabel(f"预测 {result.target}")
        ax.legend(fontsize=9, frameon=False, loc="upper left")
        ax.grid(alpha=0.25)

    def plot_residuals(self, ax, result) -> None:
        val = self.best_validation(result, "random_kfold")
        residuals = [pred - true for true, pred in zip(val.y_true, val.y_pred, strict=False)]
        bins = min(14, max(5, len(residuals) // 3))
        ax.hist(residuals, bins=bins, color=COLORS["blue"], alpha=0.82, edgecolor=COLORS["panel"], linewidth=0.7)
        ax.axvline(0, color=COLORS["amber"], linestyle="--", linewidth=1.2, label="零误差")
        ax.set_title("残差分布（预测 - 实测）")
        ax.set_xlabel(f"残差：预测值 - 实测值（{result.target}）")
        ax.set_ylabel("样本数")
        ax.legend(fontsize=9, frameon=False, loc="upper left")
        ax.grid(axis="y", alpha=0.25)

    def plot_input_impact(self, ax, result) -> None:
        items = getattr(result, "input_impacts", [])[:10]
        if not items:
            ax.set_title("原始输入影响程度")
            ax.text(0.5, 0.5, "旧模型缺少输入影响分析\n请重新训练模型", ha="center", va="center", color=COLORS["muted"])
            return
        labels = [textwrap.fill(str(item.get("feature", "")), 16) for item in items][::-1]
        values = [float(item.get("normalized_impact") or 0.0) for item in items][::-1]
        directions = [item.get("direction", "") for item in items][::-1]
        colors = [COLORS["teal"] if direction == "正向" else COLORS["red"] if direction == "负向" else COLORS["blue"] for direction in directions]
        ax.barh(labels, values, color=colors, alpha=0.94)
        max_value = max(values) if values else 0.0
        ax.set_title("原始输入影响程度")
        ax.set_xlabel("归一化影响程度（P10 -> P90，越大表示该输入对预测改变越明显）")
        ax.set_ylabel("原始输入量")
        ax.set_xlim(0, max_value * 1.34 if max_value > 0 else 1)
        for index, (value, direction) in enumerate(zip(values, directions, strict=False)):
            if value > 0:
                ax.text(value + max_value * 0.025, index, direction, va="center", fontsize=9, color=COLORS["muted"])
        ax.grid(axis="x", alpha=0.25)

    def plot_importance(self, ax, result) -> None:
        items = result.feature_importance[:8]
        labels = [x[0] for x in items][::-1]
        values = [x[1] for x in items][::-1]
        ax.barh(labels, values, color=COLORS["teal"])
        ax.set_title("Permutation 特征重要性")
        ax.set_xlim(0, max(values) * 1.2 if values else 1)
        ax.grid(axis="x", alpha=0.25)

    def plot_paper_errors(self, ax, result) -> None:
        errors = self.paper_error_rows(result)
        if not errors:
            ax.set_title("每篇论文 MAE")
            ax.text(0.5, 0.5, "无论文分组结果", ha="center", va="center", color=COLORS["muted"])
            return
        labels = [textwrap.fill(str(e["paper"]), 24) for e in errors][::-1]
        values = [e["mae"] for e in errors][::-1]
        ax.barh(labels, values, color=COLORS["blue"], alpha=0.9)
        ax.set_title(f"每篇论文 MAE（共 {len(errors)} 篇，按误差从高到低排序）")
        ax.set_xlabel(f"{result.target} 平均绝对误差 MAE（越低越好）")
        ax.set_ylabel("论文来源")
        ax.tick_params(axis="y", labelsize=8 if len(errors) <= 14 else 7)
        ax.grid(axis="x", alpha=0.25)

    def plot_metric_compare(self, ax, result) -> None:
        labels, values = [], []
        repeated_group_metrics = getattr(result, "repeated_group_metrics", None)
        for name, metrics in [("随机K折", result.random_metrics), ("重复K折", result.repeated_metrics), ("按论文分组", result.group_metrics), ("重复论文分组", repeated_group_metrics)]:
            if metrics:
                labels.append(name)
                values.append(metrics.r2)
        ax.bar(labels, values, color=[COLORS["teal"], COLORS["blue"], COLORS["amber"], COLORS["red"]][:len(values)], alpha=0.9)
        ax.axhline(0, color="#333333", linewidth=0.8)
        ax.set_title("R² 泛化对比")
        ax.set_xlabel("验证方式")
        ax.set_ylabel("R²（越高越好，低于 0 表示泛化风险高）")
        ax.set_ylim(min(-1, min(values) - 0.1), max(1, max(values) + 0.1))
        ax.grid(axis="y", alpha=0.25)
    def tree(self, parent, columns: list[str], rows: list[list[str]], height: int = 12, column_weights: dict[str, int] | None = None) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        table = ttk.Treeview(parent, columns=columns, show="headings", height=height)
        table.tag_configure("odd", background=COLORS["panel"])
        table.tag_configure("even", background=COLORS["panel_alt"])
        y_scroll = ttk.Scrollbar(parent, orient="vertical", command=table.yview)
        x_scroll = ttk.Scrollbar(parent, orient="horizontal", command=table.xview)
        table.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        table.grid(row=0, column=0, sticky="nsew", padx=(20, 0), pady=(18, 8))
        y_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 18), pady=(18, 8))
        x_scroll.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 18))

        weights = column_weights or {}
        min_widths = {}
        for column in columns:
            table.heading(column, text=column)
            min_width = max(74, min(180, len(column) * 18 + 42))
            min_widths[column] = min_width
            anchor = "w" if column in {"论文", "字段", "原始值", "清洗值", "说明", "数据文件", "训练时间"} else "center"
            table.column(column, width=min_width, minwidth=min_width, anchor=anchor, stretch=True)

        def resize_columns(_event=None) -> None:
            available = table.winfo_width() - 8
            if available <= 1 or not columns:
                return
            total_min = sum(min_widths.values())
            extra = max(0, available - total_min)
            total_weight = sum(max(1, weights.get(column, 1)) for column in columns)
            for column in columns:
                share = extra * max(1, weights.get(column, 1)) / total_weight if total_weight else 0
                table.column(column, width=int(min_widths[column] + share))

        table.bind("<Configure>", resize_columns, add="+")
        table.after_idle(resize_columns)
        for index, row in enumerate(rows):
            table.insert("", "end", values=row, tags=("even" if index % 2 else "odd",))
    def cleaning_table(self, parent) -> None:
        columns = ["行号", "论文", "字段", "原始值", "清洗值", "状态"]
        rows = []
        if self.dataset_info:
            for item in self.dataset_info.cleaning_preview[:12]:
                for feature in USER_INPUT_FEATURES:
                    rows.append([item.get("行号"), item.get("论文"), feature.label, item.get(feature.label), self.format_value(item.get(f"{feature.label} 清洗值")), item.get(f"{feature.label} 状态")])
                rows.append([item.get("行号"), item.get("论文"), "试样体积", "高度+内径", self.format_value(item.get("试样体积 清洗值"), 2), item.get("试样体积 状态")])
        self.tree(parent, columns, rows, 13, {"行号": 1, "论文": 3, "字段": 3, "原始值": 2, "清洗值": 2, "状态": 2})

    def quality_table(self, parent) -> None:
        columns = ["字段", "有效数", "缺失率", "异常值", "说明"]
        rows = []
        if self.dataset_info:
            profile = self.dataset_info.profile
            for feature in ALL_FEATURES:
                rows.append([feature.label, self.dataset_info.numeric_counts.get(feature.label, 0), f"{profile.missing_rates.get(feature.label, 0):.1%}", profile.outlier_counts.get(feature.label, 0), "增强特征" if feature.source == "engineered" else "自动计算" if feature.source == "computed" else "原始输入"])
        self.tree(parent, columns, rows, 14, {"字段": 3, "有效数": 1, "缺失率": 1, "异常值": 1, "说明": 2})

    def paper_table(self, parent) -> None:
        columns = ["论文", "行数", "UCS样本", "CCC样本", "完整输入", "最高缺失率", "UCS范围", "CCC范围"]
        rows = []
        if self.dataset_info:
            for item in self.dataset_info.profile.paper_summaries:
                rows.append([item.paper, item.rows, item.ucs_count, item.ccc_count, item.complete_inputs, f"{item.max_missing_rate:.1%}", self.range_text(item.ucs_range), self.range_text(item.ccc_range)])
        self.tree(parent, columns, rows, 14, {"论文": 4, "行数": 1, "UCS样本": 1, "CCC样本": 1, "完整输入": 1, "最高缺失率": 1, "UCS范围": 2, "CCC范围": 2})

    def history_table(self, parent) -> None:
        columns = ["训练时间", "数据文件", "特征模式", "缺失策略", "UCS模型", "UCS风险", "CCC模型", "CCC风险"]
        rows = []
        if HISTORY_PATH.exists():
            try:
                history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
                for item in history[::-1]:
                    targets = item.get("targets", {})
                    rows.append([item.get("trained_at"), Path(item.get("data_file", "")).name, item.get("feature_mode"), item.get("missing_strategy"), targets.get("UCS/kpa", {}).get("best_algorithm"), targets.get("UCS/kpa", {}).get("risk"), targets.get("CCC", {}).get("best_algorithm"), targets.get("CCC", {}).get("risk")])
            except Exception:
                rows = []
        self.tree(parent, columns, rows, 14, {"训练时间": 3, "数据文件": 3, "特征模式": 2, "缺失策略": 2, "UCS模型": 2, "UCS风险": 1, "CCC模型": 2, "CCC风险": 1})

    def render_scenarios(self) -> None:
        if not hasattr(self, "scenario_table_holder"):
            return
        for widget in self.scenario_table_holder.winfo_children():
            widget.destroy()
        columns = ["方案", "UCS/kpa", "CCC", "可信度"]
        rows = [[s.get(c, "") for c in columns] for s in self.scenarios]
        self.tree(self.scenario_table_holder, columns, rows, 7, {"方案": 2, "UCS/kpa": 2, "CCC": 2, "可信度": 1})

    def summary_values(self) -> list[tuple[str, str, str]]:
        if not self.dataset_info:
            return [("数据行数", "--", ""), ("UCS 样本", "--", ""), ("CCC 样本", "--", ""), ("完整输入行", "--", ""), ("论文组", "--", ""), ("最高缺失", "--", "")]
        profile = self.dataset_info.profile
        missing = max(profile.missing_rates.values()) if profile.missing_rates else 0
        return [("数据行数", str(self.dataset_info.row_count), "Sheet1"), ("UCS 样本", str(self.dataset_info.target_counts["UCS/kpa"]), self.range_hint("UCS/kpa")), ("CCC 样本", str(self.dataset_info.target_counts["CCC"]), self.range_hint("CCC")), ("完整输入行", str(profile.feature_complete_rows), "原始输入+体积"), ("论文组", str(profile.group_count), "分组验证依据"), ("最高缺失", f"{missing:.0%}", "字段质量")]

    def range_hint(self, target: str) -> str:
        if not self.dataset_info:
            return ""
        low, med, high = self.dataset_info.profile.target_ranges[target]
        span = self.dataset_info.profile.target_spans[target]
        return f"{format_number(low, 2)} - {format_number(high, 2)} | 跨度 {format_number(span, 1)}x"

    def range_text(self, value) -> str:
        if not value:
            return "--"
        return f"{format_number(value[0], 2)} - {format_number(value[1], 2)}"

    def format_value(self, value, decimals: int = 3) -> str:
        if value is None:
            return "--"
        if isinstance(value, (int, float)):
            return format_number(float(value), decimals).rstrip("0").rstrip(".")
        return str(value)

    def algorithm_label(self, name: str) -> str:
        for opt_name, label, _ in available_algorithm_options():
            if opt_name == name:
                return label
        return name

    def feature_mode_label(self, name: str) -> str:
        return {"original": "原始特征", "engineered": "增强特征", "all": "全部特征"}.get(name, name)


def format_number(value: float | None, decimals: int = 2) -> str:
    try:
        if value is None or not math.isfinite(float(value)):
            return "--"
        return f"{float(value):,.{decimals}f}"
    except Exception:
        return "--"


def metrics_text(metrics) -> str:
    if not metrics:
        return "--"
    return f"RMSE {format_number(metrics.rmse, 1)}   MAE {format_number(metrics.mae, 1)}\nR² {metrics.r2:.3f}"


if __name__ == "__main__":
    MicpApp().mainloop()
