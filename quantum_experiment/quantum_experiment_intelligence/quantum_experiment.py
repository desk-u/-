import multiprocessing
import sys
import tkinter as tk
from tkinter import ttk
from noise_impact import run
from quantum_experiment_intelligence.quantum_correction.color_Interactable_visualization import HexagonalColorInteractableCodeUI
from quantum_experiment_intelligence.quantum_correction.shor_Interactable_visualization import ShorInteractableCodeUI
from quantum_experiment_intelligence.quantum_correction.surface_Interactable_visualization import SurfaceCodeInteractableUI
from quantum_experiment_intelligence.intandtun_Interactable_visualization import ClickableQuantumExperimentGUI

COLOR_ACCENT = "#0078d4"
COLOR_TEXT = "#333333"

try:
    from OpenGL import GL, GLU, GLUT
    from OpenGL.GL import *
    from OpenGL.GLU import *
    from OpenGL.GLUT import *

    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False
    print("警告: OpenGL模块未安装，3D量子隧穿可视化将不可用")
    print("提示: 可以使用 pip install PyOpenGL PyOpenGL_accelerate 安装")

# class ModifiedHexagonalUI(HexagonalColorCodeUI):
class ModifiedHexagonalUI(HexagonalColorInteractableCodeUI):
    def __init__(self, root):
        super().__init__(root)
        self.main_frame.pack_forget()
        self.create_selector()
        self.create_experiment_selector()

    def create_experiment_selector(self):
        existing_children = self.left_frame.pack_slaves()

        self.experiment_selector_frame = ttk.Frame(self.left_frame)
        if existing_children:
            self.experiment_selector_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10,
                                                before=existing_children[0])
        else:
            self.experiment_selector_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        style = ttk.Style()
        style.configure('Header.TLabel',
                        font=('Segoe UI', 11, 'bold'),
                        foreground=COLOR_ACCENT)
        style.configure('TCombobox',
                        fieldbackground='white',
                        foreground=COLOR_TEXT,
                        selectbackground=COLOR_ACCENT,
                        selectforeground='white',
                        padding=5)
        ttk.Label(self.experiment_selector_frame, text="实验类型:", style='Header.TLabel').pack(anchor=tk.W, pady=(5, 0))
        self.experiment_type_combobox = ttk.Combobox(self.experiment_selector_frame,
                                            values=["量子隧穿", "双缝干涉", "量子纠错"], state="readonly", style='TCombobox')
        self.experiment_type_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.experiment_type_combobox.current(0)

    def create_selector(self):
        existing_children = self.left_frame.pack_slaves()

        self.selector_frame = ttk.Frame(self.left_frame)
        if existing_children:
            self.selector_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10,
                                     before=existing_children[0])
        else:
            self.selector_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(self.selector_frame, text="选择方式:").pack(side=tk.LEFT)
        self.selector = ttk.Combobox(
            self.selector_frame,
            values=["六边形颜色码", "Shor码", "表面码"],
            state="readonly"
        )
        self.selector.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.selector.current(0)


# class ModifiedQuantumUI(ShorCodeUI):
class ModifiedQuantumUI(ShorInteractableCodeUI):
    def __init__(self, root):
        super().__init__(root)
        self.main_frame.pack_forget()
        self.create_selector()
        self.create_experiment_selector()

    def create_experiment_selector(self):
        existing_children = self.left_frame.pack_slaves()

        self.experiment_selector_frame = ttk.Frame(self.left_frame)
        if existing_children:
            self.experiment_selector_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10,
                                                before=existing_children[0])
        else:
            self.experiment_selector_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        style = ttk.Style()
        style.configure('Header.TLabel',
                        font=('Segoe UI', 11, 'bold'),
                        foreground=COLOR_ACCENT)
        ttk.Label(self.experiment_selector_frame, text="实验类型:", style='Header.TLabel').pack(anchor=tk.W, pady=(5, 0))
        self.experiment_type_combobox = ttk.Combobox(self.experiment_selector_frame,
                                            values=["量子隧穿", "双缝干涉", "量子纠错"], state="readonly", style='TCombobox')
        self.experiment_type_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.experiment_type_combobox.current(0)



    def create_selector(self):
        existing_children = self.left_frame.pack_slaves()

        self.selector_frame = ttk.Frame(self.left_frame)
        if existing_children:
            self.selector_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10,
                                     before=existing_children[0])
        else:
            self.selector_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(self.selector_frame, text="选择方式:").pack(side=tk.LEFT)
        self.selector = ttk.Combobox(
            self.selector_frame,
            values=["六边形颜色码", "Shor码", "表面码"],
            state="readonly"
        )
        self.selector.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.selector.current(0)


# class ModifiedSurfaceUI(SurfaceCodeUI):
class ModifiedSurfaceUI(SurfaceCodeInteractableUI):
    def __init__(self, root):
        super().__init__(root)
        self.main_frame.pack_forget()
        self.create_selector()
        self.create_experiment_selector()

    def create_experiment_selector(self):
        existing_children = self.left_frame.pack_slaves()

        self.experiment_selector_frame = ttk.Frame(self.left_frame)
        if existing_children:
            self.experiment_selector_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10,
                                     before=existing_children[0])
        else:
            self.experiment_selector_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        style = ttk.Style()
        style.configure('Header.TLabel',
                        font=('Segoe UI', 11, 'bold'),
                        foreground=COLOR_ACCENT)
        ttk.Label(self.experiment_selector_frame, text="实验类型:", style='Header.TLabel').pack(anchor=tk.W, pady=(5, 0))
        self.experiment_type_combobox = ttk.Combobox(self.experiment_selector_frame,
                     values=["量子隧穿", "双缝干涉", "量子纠错"], state="readonly", style='TCombobox')
        self.experiment_type_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.experiment_type_combobox.current(0)

    def create_selector(self):
        existing_children = self.left_frame.pack_slaves()

        self.selector_frame = ttk.Frame(self.left_frame)
        if existing_children:
            self.selector_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10,
                                     before=existing_children[0])
        else:
            self.selector_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(self.selector_frame, text="选择方式:").pack(side=tk.LEFT)
        self.selector = ttk.Combobox(
            self.selector_frame,
            values=["六边形颜色码", "Shor码", "表面码"],
            state="readonly"
        )
        self.selector.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.selector.current(0)


class MainApplication:
    def __init__(self, root):
        self.root = root
        # self.root.title("量子纠错模拟器")
        # self.root.geometry("1400x800")

        self.pygame_process = None

        self.hex_ui = ModifiedHexagonalUI(root)
        self.shor_ui = ModifiedQuantumUI(root)
        self.surface_ui = ModifiedSurfaceUI(root)

        self.uis = {
            "六边形颜色码": self.hex_ui.main_frame,
            "Shor码": self.shor_ui.main_frame,
            "表面码": self.surface_ui.main_frame
        }

        for ui in [self.hex_ui, self.shor_ui, self.surface_ui]:
            ui.selector.bind("<<ComboboxSelected>>", self.on_selector_changed)

        self.current_ui = "六边形颜色码"
        self.uis[self.current_ui].pack(fill=tk.BOTH, expand=True)

        for ui in [self.hex_ui, self.shor_ui, self.surface_ui]:
            btn = ttk.Button(ui.left_frame, text="噪声模拟器", command=self.start_pygame_once)
            btn.place(relx=0.0, rely=1.0, anchor='sw', x=20, y=-20)

        # self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_selector_changed(self, event):
        selected_ui = event.widget.get()
        if selected_ui == self.current_ui:
            return

        for frame in self.uis.values():
            frame.pack_forget()

        self.uis[selected_ui].pack(fill=tk.BOTH, expand=True)
        self.current_ui = selected_ui

        for ui in [self.hex_ui, self.shor_ui, self.surface_ui]:
            ui.selector.set(selected_ui)

    def start_pygame_once(self):
        if self.pygame_process and self.pygame_process.is_alive():
            return

        self.pygame_process = multiprocessing.Process(target=run)
        self.pygame_process.start()

    def on_close(self):
        if self.pygame_process and self.pygame_process.is_alive():
            self.pygame_process.terminate()
            self.pygame_process.join()
        self.root.destroy()

class UnifiedQuantumInterface:
    def __init__(self, root):
        self.root = root
        # self.root.title("量子实验")
        # self.root.geometry("1400x800")

        # 初始化两个界面
        self.quantum_ui = ClickableQuantumExperimentGUI(root)
        self.qec_ui = MainApplication(root)

        self.qec_ui.hex_ui.main_frame.pack_forget()
        self.qec_ui.shor_ui.main_frame.pack_forget()
        self.qec_ui.surface_ui.main_frame.pack_forget()

        self.quantum_ui.experiment_type_combobox.bind("<<ComboboxSelected>>", self.switch_interface)
        self.qec_ui.hex_ui.experiment_type_combobox.bind("<<ComboboxSelected>>", self.switch_interface)
        self.qec_ui.surface_ui.experiment_type_combobox.bind("<<ComboboxSelected>>", self.switch_interface)
        self.qec_ui.shor_ui.experiment_type_combobox.bind("<<ComboboxSelected>>", self.switch_interface)

        self.current_ui = "量子隧穿"
        self.quantum_ui.main_frame.pack(fill=tk.BOTH, expand=True)

        # self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def switch_interface(self, event=None):
        selected_type = event.widget.get()
        if selected_type == self.current_ui:
            return

        self.quantum_ui.main_frame.pack_forget()
        self.qec_ui.hex_ui.main_frame.pack_forget()
        self.qec_ui.surface_ui.main_frame.pack_forget()
        self.qec_ui.shor_ui.main_frame.pack_forget()

        if selected_type == "量子隧穿":
            self.current_ui = "量子隧穿"
            self.quantum_ui.experiment_type_combobox.set(self.current_ui)
            self.quantum_ui.main_frame.pack(fill=tk.BOTH, expand=True)
            self.quantum_ui.update_controls()
        elif selected_type == "双缝干涉":
            self.current_ui = "双缝干涉"
            self.quantum_ui.experiment_type_combobox.set(self.current_ui)
            self.quantum_ui.main_frame.pack(fill=tk.BOTH, expand=True)
            self.quantum_ui.update_controls()
        else:
            self.current_ui = "量子纠错"
            self.qec_ui.hex_ui.experiment_type_combobox.set(self.current_ui)
            self.qec_ui.surface_ui.experiment_type_combobox.set(self.current_ui)
            self.qec_ui.shor_ui.experiment_type_combobox.set(self.current_ui)
            self.qec_ui.hex_ui.main_frame.pack(fill=tk.BOTH, expand=True)

    def on_close(self):
        if self.qec_ui.pygame_process and self.qec_ui.pygame_process.is_alive():
            self.qec_ui.pygame_process.terminate()
            self.qec_ui.pygame_process.join()
        self.root.destroy()
        sys.exit(0)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    if OPENGL_AVAILABLE:
        try:
            glutInit(sys.argv)
        except Exception as e:
            print(f"GLUT初始化失败: {str(e)}")
            OPENGL_AVAILABLE = False

    root = tk.Tk()
    app = UnifiedQuantumInterface(root)
    root.mainloop()

