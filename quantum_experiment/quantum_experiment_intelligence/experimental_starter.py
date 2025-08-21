import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os

class QuantumExperimentLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("量子实验启动器")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)

        # 设置主题和样式
        self.setup_style()

        # 创建界面
        self.create_widgets()

        # 实验选项
        self.experiments = {
            "量子实验与智能助手": {
                "file": "quantum_intelligence.py",
                "desc": "综合量子实验平台，结合量子实验界面和智能助手功能。左侧是量子实验界面，右侧是智能助手，可以分析实验数据。",
                "icon": "🔬"
            },
            "单缝衍射实验": {
                "file": "other_experiments/quantum_diffraction.py",
                "desc": "模拟单缝衍射现象的实验界面。可以调整缝宽、波长等参数，观察衍射图样的变化。",
                "icon": "📊"
            },
            "自由粒子模拟": {
                "file": "other_experiments/quantum_particle.py",
                "desc": "模拟自由粒子在不同量子环境下的行为，包括经典物理、量子物理、无限深势阱、有限高势垒和量子塌缩等模式。",
                "icon": "⚛️"
            },
            "量子力学概率函数": {
                "file": "other_experiments/quantum_wave_function.py",
                "desc": "演示量子力学中的概率函数，通过小球在直线上的出现频率展示量子概率分布。",
                "icon": "📈"
            }
        }

        # 填充实验列表
        self.populate_experiment_list()

        # 默认选择第一个实验
        if len(self.experiment_list.get_children()) > 0:
            self.experiment_list.selection_set(self.experiment_list.get_children()[0])
            self.show_experiment_details(0)

    def setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')

        # 配置颜色
        self.bg_color = "#f8f9fa"
        self.card_bg = "#ffffff"
        self.primary_color = "#4a6baf"
        self.secondary_color = "#6c757d"
        self.highlight_color = "#e1e5eb"
        self.text_color = "#212529"
        self.accent_color = "#20c997"

        # 自定义颜色
        style.configure('TFrame', background=self.bg_color)
        style.configure('Card.TFrame', background=self.card_bg, relief=tk.RAISED, borderwidth=1)
        style.configure('Title.TLabel',
                      font=('Segoe UI', 24, 'bold'),
                      background=self.bg_color,
                      foreground=self.text_color)
        style.configure('Subtitle.TLabel',
                      font=('Segoe UI', 12),
                      background=self.bg_color,
                      foreground=self.secondary_color)
        style.configure('Experiment.TLabel',
                      font=('Segoe UI', 14),
                      background=self.card_bg,
                      foreground=self.text_color)
        style.configure('Desc.TLabel',
                      font=('Segoe UI', 12),
                      background=self.card_bg,
                      foreground=self.secondary_color,
                      wraplength=380)  # 调整描述文本宽度
        style.configure('Icon.TLabel',
                      font=('Segoe UI', 24),
                      background=self.card_bg)

        # 按钮样式
        style.configure('Primary.TButton',
                      font=('Segoe UI', 12, 'bold'),
                      background=self.primary_color,
                      foreground="white",
                      borderwidth=0,
                      padding=10)
        style.map('Primary.TButton',
                background=[('active', '#3a5a8f'), ('disabled', '#cccccc')],
                foreground=[('active', 'white')])

        # 列表样式
        style.configure('Experiment.Treeview',
                      font=('Segoe UI', 12),
                      rowheight=40,
                      background=self.card_bg,
                      fieldbackground=self.card_bg,
                      foreground=self.text_color,
                      bordercolor=self.highlight_color,
                      borderwidth=0)
        style.map('Experiment.Treeview',
                background=[('selected', self.primary_color)],
                foreground=[('selected', 'white')])

    def create_widgets(self):
        # 主框架
        self.main_frame = ttk.Frame(self.root, padding=(20, 20, 20, 10))
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题区域
        self.create_header()

        # 内容区域
        self.create_content()

        # 底部区域
        self.create_footer()

    def create_header(self):
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = ttk.Label(header_frame,
                              text="量子实验启动器",
                              style='Title.TLabel')
        title_label.pack(side=tk.LEFT)

        subtitle_label = ttk.Label(header_frame,
                                 text="探索量子世界的奇妙现象",
                                 style='Subtitle.TLabel')
        subtitle_label.pack(side=tk.LEFT, padx=10, pady=(8, 0))

    def create_content(self):
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        self.create_experiment_list(content_frame)

        self.create_experiment_details(content_frame)

    def create_experiment_list(self, parent):
        list_frame = ttk.Frame(parent, style='Card.TFrame')
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 15), expand=True)

        list_title = ttk.Label(list_frame,
                             text="可用实验",
                             font=('Segoe UI', 14, 'bold'),
                             background=self.card_bg,
                             foreground=self.text_color)
        list_title.pack(pady=(15, 10), padx=15, anchor=tk.W)

        self.experiment_list = ttk.Treeview(
            list_frame,
            style='Experiment.Treeview',
            columns=('icon', 'name'),
            show='tree',
            selectmode='browse',
            height=4
        )
        self.experiment_list.column('#0', width=0, stretch=tk.NO)
        self.experiment_list.column('icon', width=50, anchor=tk.CENTER)
        self.experiment_list.column('name', width=200, anchor=tk.W)

        self.experiment_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.experiment_list.bind('<<TreeviewSelect>>', self.on_experiment_select)

    def create_experiment_details(self, parent):
        detail_frame = ttk.Frame(parent, style='Card.TFrame')
        detail_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.detail_title = ttk.Label(
            detail_frame,
            text="实验详情",
            font=('Segoe UI', 16, 'bold'),
            background=self.card_bg,
            foreground=self.text_color
        )
        self.detail_title.pack(pady=(20, 10), padx=20, anchor=tk.W)

        # 图标和名称
        icon_name_frame = ttk.Frame(detail_frame, style='Card.TFrame')
        icon_name_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        self.icon_label = ttk.Label(icon_name_frame, style='Icon.TLabel')
        self.icon_label.pack(side=tk.LEFT, padx=(0, 15))

        self.name_label = ttk.Label(
            icon_name_frame,
            font=('Segoe UI', 18, 'bold'),
            background=self.card_bg,
            foreground=self.text_color
        )
        self.name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 分隔线
        separator = ttk.Separator(detail_frame, orient='horizontal')
        separator.pack(fill=tk.X, padx=20, pady=5)

        # 描述
        self.desc_label = ttk.Label(
            detail_frame,
            style='Desc.TLabel',
            justify=tk.LEFT
        )
        self.desc_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 启动按钮
        button_frame = ttk.Frame(detail_frame, style='Card.TFrame')
        button_frame.pack(fill=tk.X, padx=20, pady=(10, 20))

        self.launch_button = ttk.Button(
            button_frame,
            text="启动实验",
            style='Primary.TButton',
            command=self.launch_experiment
        )
        self.launch_button.pack(fill=tk.X, ipady=8)

    def create_footer(self):
        # 底部框架
        footer_frame = ttk.Frame(self.main_frame)
        footer_frame.pack(fill=tk.X, pady=(10, 0))

        # 版权信息
        copyright_label = ttk.Label(
            footer_frame,
            text="© 量子实验室 | 版本 1.0.0",
            font=('Segoe UI', 10),
            background=self.bg_color,
            foreground=self.secondary_color
        )
        copyright_label.pack(side=tk.RIGHT)

    def populate_experiment_list(self):
        for name, info in self.experiments.items():
            self.experiment_list.insert(
                '',
                tk.END,
                values=(info['icon'], name),
                tags=(name,)
            )

    def on_experiment_select(self, event):
        selected_item = self.experiment_list.selection()
        if selected_item:
            index = self.experiment_list.index(selected_item[0])
            self.show_experiment_details(index)

    def show_experiment_details(self, index):
        item = self.experiment_list.item(self.experiment_list.get_children()[index])
        exp_name = item['values'][1]
        exp_info = self.experiments.get(exp_name, {})

        # 更新详情
        self.icon_label.config(text=exp_info.get('icon', '⚛️'))
        self.name_label.config(text=exp_name)
        self.desc_label.config(text=exp_info.get('desc', '暂无描述'))

    def launch_experiment(self):
        selected_item = self.experiment_list.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择一个实验")
            return

        item = self.experiment_list.item(selected_item[0])
        exp_name = item['values'][1]
        exp_info = self.experiments.get(exp_name, {})
        script_name = exp_info.get('file')

        if not script_name:
            messagebox.showerror("错误", "找不到实验脚本")
            return

        # 检查文件是否存在
        if not os.path.exists(script_name):
            messagebox.showerror("错误", f"找不到实验文件: {script_name}")
            return

        # 启动选中的实验
        try:
            python = sys.executable
            subprocess.Popen([python, script_name])
        except Exception as e:
            messagebox.showerror("错误", f"无法启动实验: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = QuantumExperimentLauncher(root)
    root.mainloop()