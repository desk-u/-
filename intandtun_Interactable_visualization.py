import tkinter as tk

from quantum_experiment_intelligence.Interference_and_tunneling import QuantumExperimentGUI


class ClickableQuantumExperimentGUI(QuantumExperimentGUI):
    def __init__(self, root):
        super().__init__(root)
        self._setup_click_handlers()
        self.active_borders = {}  # 存储当前活动的边框
        self.is_enable_selection_mode = False
        self.select_images = []
        self.fal_select = 15
        self.ture_select_images = []
        self.obtain_para = []
        self._original_start_experiment = super().start_experiment
        self._original_analyze_parameter_effect = super().analyze_parameter_effect
        self._original_analyze_double_slit_effect = super().analyze_double_slit_effect

    def get_obtain_para(self):
        self.obtain_para = []
        if self.fal_select == 15:
            self.obtain_para = [self.barrier_height_var.get(),
                                self.barrier_width_var.get(),
                                self.particle_energy_var.get()]
        elif self.fal_select == 18:
            self.obtain_para = [self.slit_distance_var.get(),
                                self.slit_width_var.get(),
                                self.screen_distance_var.get(),
                                self.wavelength_var.get()]

        elif self.fal_select == 21:
            self.obtain_para = [self.barrier_height_var.get(),
                                self.barrier_width_var.get(),
                                self.particle_energy_var.get(),
                                self.analysis_type_var.get(),
                                self.range_start_var.get(),
                                self.range_end_var.get()]
        else:
            self.obtain_para = [self.slit_distance_var.get(),
                                self.slit_width_var.get(),
                                self.screen_distance_var.get(),
                                self.wavelength_var.get(),
                                self.double_slit_analysis_type_var.get(),
                                self.double_slit_range_start_var.get(),
                                self.double_slit_range_end_var.get()]
        return self.obtain_para

    def get_ture_select_images(self):
        self.ture_select_images = []
        if self.fal_select == (15 or 18):
            for i in self.select_images:
                if i == 'image00':
                    self.ture_select_images.append(i[:-2] + str(self.fal_select))
                elif i == 'image01':
                    self.ture_select_images.append(i[:-2] + str(self.fal_select + 1))
                elif i == 'image02':
                    self.ture_select_images.append(i[:-2] + str(self.fal_select + 2))
            return self.ture_select_images
        elif self.fal_select == 21:
            self.analysis_type = self.analysis_type_var.get()
            for i in self.select_images:
                if self.analysis_type == "势垒高度":
                    if i == 'image00':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select))
                    elif i == 'image01':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 1))
                    elif i == 'image02':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 2))
                elif self.analysis_type == "势垒宽度":
                    if i == 'image00':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 3))
                    elif i == 'image01':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 1 + 3))
                    elif i == 'image02':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 2 + 3))
                else:
                    if i == 'image00':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 6))
                    elif i == 'image01':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 1 + 6))
                    elif i == 'image02':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 2 + 6))
            return self.ture_select_images
        else:
            self.analysis_type = self.double_slit_analysis_type_var.get()
            for i in self.select_images:
                if self.analysis_type == "狭缝间距":
                    if i == 'image00':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select))
                    elif i == 'image01':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 1))
                    elif i == 'image02':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 2))
                elif self.analysis_type == "狭缝宽度":
                    if i == 'image00':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 3))
                    elif i == 'image01':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 1 + 3))
                    elif i == 'image02':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 2 + 3))
                elif self.analysis_type == "波长":
                    if i == 'image00':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 6))
                    elif i == 'image01':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 1 + 6))
                    elif i == 'image02':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 2 + 6))
                else:
                    if i == 'image00':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 9))
                    elif i == 'image01':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 1 + 9))
                    elif i == 'image02':
                        self.ture_select_images.append(i[:-2] + str(self.fal_select + 2 + 9))
            return self.ture_select_images


    def update_select_images(self):
        for i in self.select_images:
            if self.select_images.count(i) > 1:
                self.select_images.remove(i)
                self.select_images.remove(i)

    def _setup_click_handlers(self):
        """设置所有图表区域的点击事件处理"""
        # 等待主界面初始化完成
        self.root.after(100, self._bind_canvas_events)

    def _bind_canvas_events(self):
        """绑定画布点击事件"""
        if hasattr(self, 'canvas') and self.canvas:
            self._make_canvas_clickable(self.canvas)

        if hasattr(self, 'single_quantum_canvas') and self.single_quantum_canvas:
            self._make_canvas_clickable(self.single_quantum_canvas)

    def _make_canvas_clickable(self, canvas):
        """使画布可点击并添加透明覆盖层"""
        tk_canvas = canvas.get_tk_widget() if hasattr(canvas, 'get_tk_widget') else canvas

        if hasattr(tk_canvas, 'click_zones'):
            for zone_id in tk_canvas.click_zones:
                tk_canvas.delete(zone_id)
        else:
            tk_canvas.click_zones = []

        width = tk_canvas.winfo_width()
        height = tk_canvas.winfo_height()

        if width <= 1 or height <= 1:  # 防止无效尺寸
            self.root.after(100, lambda: self._make_canvas_clickable(canvas))
            return

        # 定义不同区域的点击处理函数
        def create_zone(x1, y1, x2, y2, callback):
            zone_id = tk_canvas.create_rectangle(
                x1, y1, x2, y2,
                outline="", fill="", tags="click_zone"
            )
            tk_canvas.tag_bind(zone_id, "<Button-1>", callback)
            tk_canvas.click_zones.append(zone_id)
            return zone_id

        fig_width, fig_height = self.figure.get_size_inches()
        dpi = self.figure.get_dpi()
        total_width = fig_width * dpi
        total_height = fig_height * dpi

        # 确保只在主画布上创建点击区域
        if canvas == self.canvas:
            # 左侧子图
            create_zone(
                0, 0, total_width * 0.4, total_height,
                lambda e: self._handle_plot_click(e, canvas, "left_plot")
            )
            # 中间子图
            create_zone(
                total_width * 0.4, 0, total_width * 0.75, total_height,
                lambda e: self._handle_plot_click(e, canvas, "mid_plot")
            )
            # 右侧子图
            create_zone(
                total_width * 0.75, 0, total_width, total_height,
                lambda e: self._handle_plot_click(e, canvas, "right_plot")
            )

        # 动态调整大小
        tk_canvas.bind("<Configure>", lambda e: self._resize_click_zones(tk_canvas))

    def _resize_click_zones(self, tk_canvas):
        """调整点击区域大小以适应画布变化"""
        if not hasattr(tk_canvas, 'click_zones'):
            return

        width = tk_canvas.winfo_width()
        height = tk_canvas.winfo_height()

        if width <= 1 or height <= 1:
            return

        # 重新计算区域位置（简化版，实际应根据子图位置计算）
        if len(tk_canvas.click_zones) == 3:  # 主图表3个子图
            tk_canvas.coords(tk_canvas.click_zones[0], 0, 0, width * 0.4, height)
            tk_canvas.coords(tk_canvas.click_zones[1], width * 0.4, 0, width * 0.75, height)
            tk_canvas.coords(tk_canvas.click_zones[2], width * 0.75, 0, width, height)
        else:  # 单个图表
            tk_canvas.coords(tk_canvas.click_zones[0], 0, 0, width, height)

    def _handle_plot_click(self, event, canvas, zone_id):
        """处理图表点击事件"""
        if not self.is_enable_selection_mode:
            return

        # 获取Tkinter画布对象
        tk_canvas = canvas.get_tk_widget() if hasattr(canvas, 'get_tk_widget') else canvas

        # 获取点击区域坐标
        if zone_id == "left_plot":
            x1, y1, x2, y2 = 0, 0, tk_canvas.winfo_width() * 0.4, tk_canvas.winfo_height()
            self.select_images.append('image00')
            self.update_select_images()
            self._toggle_border(tk_canvas, zone_id, (x1, y1, x2, y2))
        elif zone_id == "mid_plot":
            x1, y1, x2, y2 = tk_canvas.winfo_width() * 0.4, 0, tk_canvas.winfo_width() * 0.75, tk_canvas.winfo_height()
            self.select_images.append('image01')
            self.update_select_images()
            self._toggle_border(tk_canvas, zone_id, (x1, y1, x2, y2))
        elif zone_id == "right_plot":
            x1, y1, x2, y2 = tk_canvas.winfo_width() * 0.75, 0, tk_canvas.winfo_width(), tk_canvas.winfo_height()
            self.select_images.append('image02')
            self.update_select_images()
            self._toggle_border(tk_canvas, zone_id, (x1, y1, x2, y2))

    def _toggle_border(self, tk_canvas, zone_id, coords):
        """切换点击区域的边框显示"""
        border_tag = f"plot_border_{zone_id}"

        if border_tag in self.active_borders:
            tk_canvas.delete(self.active_borders[border_tag])
            del self.active_borders[border_tag]
            return

        x1, y1, x2, y2 = coords
        border_id = tk_canvas.create_rectangle(
            x1 + 2, y1 + 2, x2 - 2, y2 - 2,
            outline="#00AAFF", width=3,
            dash=(10, 5), tags=border_tag
        )

        tk_canvas.tag_raise(border_id)

        self.active_borders[border_tag] = border_id

    def reset_image_selection(self):
        if hasattr(self, 'canvas') and self.canvas:
            tk_canvas = self.canvas.get_tk_widget() if hasattr(self.canvas, 'get_tk_widget') else self.canvas
            if tk_canvas.winfo_exists():
                for border_tag, border_id in list(self.active_borders.items()):
                    if border_tag.startswith("plot_border_"):
                        tk_canvas.delete(border_id)
                        del self.active_borders[border_tag]

        if hasattr(self, 'single_quantum_canvas') and self.single_quantum_canvas:
            tk_canvas = self.single_quantum_canvas.get_tk_widget() if hasattr(self.single_quantum_canvas,
                                                                              'get_tk_widget') else self.single_quantum_canvas
            if tk_canvas.winfo_exists():
                for border_tag, border_id in list(self.active_borders.items()):
                    if border_tag.startswith("plot_border_"):
                        tk_canvas.delete(border_id)
                        del self.active_borders[border_tag]

        self.select_images = []
        self.obtain_para = []
        self.ture_select_images = []

    def start_experiment(self):
        self._original_start_experiment()
        self.reset_image_selection()
        if self.experiment_type_var.get() == "量子隧穿":
            self.fal_select = 15
        else:
            self.fal_select = 18

    def analyze_parameter_effect(self):
        self._original_analyze_parameter_effect()
        self.get_ture_select_images()
        self.reset_image_selection()
        self.fal_select = 21

    def analyze_double_slit_effect(self):
        self._original_analyze_double_slit_effect()
        self.get_ture_select_images()
        self.reset_image_selection()
        self.fal_select = 30


if __name__ == "__main__":
    root = tk.Tk()
    app = ClickableQuantumExperimentGUI(root)
    # app.is_enable_selection_mode = True
    root.mainloop()