import threading
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.gridspec import GridSpec
import warnings
import sys
import time
from qiskit import QuantumCircuit
from qiskit_aer import Aer
from qiskit.visualization import circuit_drawer, plot_state_qsphere

# 尝试导入OpenGL，如果不存在则设置标志变量
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

warnings.filterwarnings("ignore")
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

m_e = 9.10938356e-31  # 电子质量(kg)
hbar = 1.054571817e-34  # 约化普朗克常数(J·s)

COLOR_BG = "#f0f0f0"
COLOR_BG_SECONDARY = "#ffffff"
COLOR_ACCENT = "#0078d4"
COLOR_TEXT = "#333333"


class Quantum3DVisualization:
    def __init__(self):
        self.window = None
        self.control_panel = None
        self.running = False
        self.thread = None
        self.glut_initialized = False
        self.barrier_height = 1.0
        self.barrier_width = 1.0
        self.particle_energy = 0.5
        self.angle = 0.0
        self.time = 0
        self.rotation_speed = 0.5
        self.zoom = -8.0
        self.mouse_x = 0
        self.mouse_y = 0
        self.is_rotating = False
        self.glut_initialized = False
        self.control_panel = None
        self.running = False

        # 波包发射控制
        self.emission_interval = 4.0  # 减少发射间隔
        self.last_emission_time = 0
        self.wave_packets = []

        # 波包基本参数
        self.initial_position = -6.0
        self.wave_speed = 0.1  # 增加波包速度
        self.wave_width = 1.0
        self.wave_amplitude = 1.5
        self.spread_angle = 45
        self.reflection_coef = 0.9

        # 视觉效果参数
        self.light_position = [5.0, 10.0, 5.0, 1.0]
        self.ambient_light = [0.3, 0.3, 0.3, 1.0]
        self.diffuse_light = [0.8, 0.8, 0.8, 1.0]
        self.specular_light = [1.0, 1.0, 1.0, 1.0]
        self.current_tunneling_prob = 0.0  # 新增：用于同步概率

    def _init_control_panel(self):
        """创建控制面板，允许自由移动和独立关闭，主界面和3D窗口可同时操作"""
        self.control_panel = tk.Toplevel()
        self.control_panel.title("控制面板")
        self.control_panel.geometry("300x200")
        self.control_panel.protocol("WM_DELETE_WINDOW", self.on_close_control_panel)

        # 势垒宽度控制
        width_frame = tk.Frame(self.control_panel)
        width_frame.pack(pady=10)
        tk.Label(width_frame, text="势垒宽度:").pack(side=tk.LEFT)
        self.width_scale = tk.Scale(width_frame, from_=0.1, to=2.0, resolution=0.1,
                                    orient=tk.HORIZONTAL, length=200,
                                    command=self.update_barrier_width)
        self.width_scale.set(self.barrier_width)
        self.width_scale.pack(side=tk.LEFT)

        # 势垒高度控制
        height_frame = tk.Frame(self.control_panel)
        height_frame.pack(pady=10)
        tk.Label(height_frame, text="势垒高度:").pack(side=tk.LEFT)
        self.height_scale = tk.Scale(height_frame, from_=0.1, to=2.0, resolution=0.1,
                                     orient=tk.HORIZONTAL, length=200,
                                     command=self.update_barrier_height)
        self.height_scale.set(self.barrier_height)
        self.height_scale.pack(side=tk.LEFT)

        # 波包速度控制
        speed_frame = tk.Frame(self.control_panel)
        speed_frame.pack(pady=10)
        tk.Label(speed_frame, text="波包速度:").pack(side=tk.LEFT)
        self.speed_scale = tk.Scale(speed_frame, from_=0.01, to=2.0, resolution=0.01,
                                    orient=tk.HORIZONTAL, length=200,
                                    command=self.update_wave_speed)
        self.speed_scale.set(self.wave_speed)
        self.speed_scale.pack(side=tk.LEFT)

    def update_barrier_width(self, value):
        """更新势垒宽度"""
        self.barrier_width = float(value)
        self.sync_tunneling_probability()
        if self.glut_initialized:
            try:
                glutSetWindow(self.window)
                glutPostRedisplay()
            except Exception as e:
                print(f"[跳过无效的重绘调用]：{e}")

    def update_barrier_height(self, value):
        """更新势垒高度"""
        self.barrier_height = float(value)
        self.sync_tunneling_probability()
        if self.glut_initialized:
            glutPostRedisplay()

    def update_wave_speed(self, value):
        """更新波包速度，推进所有波包到当前时刻再更新速度"""
        new_speed = float(value)
        now = self.time
        for packet in self.wave_packets:
            if not packet['alive']:
                continue
            # 用旧速度推进到当前时刻
            dt = now - packet['last_update_time']
            if packet['state'] == 'incident':
                packet['current_x'] += self.wave_speed * dt
            elif packet['state'] == 'reflected':
                packet['current_x'] -= self.wave_speed * dt
            elif packet['state'] == 'transmitted':
                packet['current_x'] += self.wave_speed * dt
            packet['last_update_time'] = now
        self.wave_speed = new_speed
        if self.glut_initialized:
            glutPostRedisplay()

    def init_gl(self):
        """初始化OpenGL设置，确保背景色为浅色"""
        try:
            glClearColor(0.95, 0.95, 0.95, 1.0)  # 浅灰色背景
            glClearDepth(1.0)
            glEnable(GL_DEPTH_TEST)
            glDepthFunc(GL_LEQUAL)
            glShadeModel(GL_SMOOTH)
            glEnable(GL_LIGHTING)
            glEnable(GL_LIGHT0)
            glEnable(GL_COLOR_MATERIAL)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            # 光照
            glLightfv(GL_LIGHT0, GL_POSITION, (5.0, 10.0, 5.0, 1.0))
            glLightfv(GL_LIGHT0, GL_AMBIENT, (0.4, 0.4, 0.4, 1.0))
            glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))
            glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))
            glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
            glMaterialfv(GL_FRONT, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))
            glMaterialf(GL_FRONT, GL_SHININESS, 50.0)
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(45.0, 800.0 / 600.0, 0.1, 100.0)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
        except Exception as e:
            print(f"OpenGL初始化错误: {str(e)}")
            raise

    def calculate_tunneling_probability(self):
        # 计算隧穿概率
        k = np.sqrt(2 * self.barrier_height - self.particle_energy)
        T = np.exp(-2 * k * self.barrier_width)
        return T

    def sync_tunneling_probability(self):
        """同步当前隧穿概率，供3D动画和图表统一使用"""
        V0 = self.barrier_height
        a = self.barrier_width
        E = self.particle_energy
        # 这里用和图表一致的公式
        try:
            k = np.sqrt(2 * V0 - E)
            T = np.exp(-2 * k * a)
            self.current_tunneling_prob = max(0, min(1, float(T)))
        except Exception:
            self.current_tunneling_prob = 0.0

    def update_particle(self):
        # 更新粒子状态
        if not self.tunneling_success:
            # 量子涨落
            fluctuation = self.fluctuation_amplitude * np.sin(self.time * self.fluctuation_frequency)
            current_energy = self.particle_energy + fluctuation

            # 计算隧穿概率
            tunneling_prob = self.calculate_tunneling_probability()

            # 随机决定是否尝试隧穿
            if np.random.random() < 0.01:  # 每秒尝试100次
                self.tunneling_attempts += 1
                if np.random.random() < tunneling_prob:
                    self.tunneling_success = True
                    self.tunneling_time = self.time
                    # 势垒越高，速度越快
                    self.particle_speed = 2.0 * self.barrier_height
        else:
            # 粒子正在隧穿
            if self.particle_position < 3.0:  # 还未完全穿过
                self.particle_position += self.particle_speed * 0.01
            else:
                # 重置状态，准备下一次隧穿
                self.tunneling_success = False
                self.particle_position = -3.0
                self.particle_speed = 0.0
                self.tunneling_attempts = 0

    def draw_particle(self):
        # 绘制粒子
        glPushMatrix()
        glTranslatef(self.particle_position, 0.5, 0)

        # 根据状态设置颜色
        if self.tunneling_success:
            glColor3f(1.0, 0.0, 0.0)  # 隧穿时显示红色
        else:
            glColor3f(0.0, 1.0, 0.0)  # 未隧穿时显示绿色

        glutSolidSphere(0.1, 20, 20)
        glPopMatrix()

    def draw_fluctuation(self):
        # 绘制量子涨落效果
        x = np.linspace(-5, -3, 50)
        y = self.fluctuation_amplitude * np.sin(self.time * self.fluctuation_frequency)

        glColor4f(0.0, 1.0, 1.0, 0.5)  # 青色
        glBegin(GL_LINE_STRIP)
        for xi in x:
            yi = y * np.exp(-0.1 * (xi + 4) ** 2)
            glVertex3f(xi, yi + 0.5, 0)
        glEnd()

    def draw_info(self):
        # 显示信息
        glColor3f(1.0, 1.0, 1.0)
        self.render_text(-4, 1.5, 0, f"尝试次数: {self.tunneling_attempts}")
        self.render_text(-4, 1.3, 0, f"隧穿概率: {self.calculate_tunneling_probability():.4f}")
        if self.tunneling_success:
            self.render_text(-4, 1.1, 0, f"隧穿速度: {self.particle_speed:.2f}")

    def _display(self):
        """显示回调函数，确保摄像机参数和绘制流程正确"""
        if not self.glut_initialized or not self.running:
            return
        try:
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()
            glTranslatef(0.0, 0.0, -8.0)
            glRotatef(30, 1.0, 0.0, 0.0)
            glRotatef(self.angle, 0.0, 1.0, 0.0)
            # 绘制地面、势垒、波包
            self.draw_ground()
            self.draw_barrier()
            self.draw_wave_packets()
            glutSwapBuffers()
        except Exception as e:
            print(f"显示回调出错: {str(e)}")
            self.running = False


    def mouse_motion(self, x, y):
        """鼠标移动回调函数"""
        if not self.glut_initialized:
            return

        if self.is_rotating:
            dx = x - self.mouse_x
            self.angle += dx * 0.5
            self.mouse_x = x
            self.mouse_y = y

    def mouse_button(self, button, state, x, y):
        """鼠标按钮回调函数"""
        if not self.glut_initialized:
            return

        if button == GLUT_LEFT_BUTTON:
            if state == GLUT_DOWN:
                self.is_rotating = True
                self.mouse_x = x
                self.mouse_y = y
            else:
                self.is_rotating = False
        elif button == 3:  # 滚轮上滚
            self.zoom += 0.5
        elif button == 4:  # 滚轮下滚
            self.zoom -= 0.5

    def keyboard(self, key, x, y):
        """键盘回调函数"""
        if not self.glut_initialized:
            return

        if key == b'q':
            self.stop_visualization()

    def check_gl_initialized(self):
        """检查OpenGL是否正确初始化"""
        if not self.glut_initialized:
            print("警告: GLUT未初始化")
            return False
        try:
            vendor = glGetString(GL_VENDOR)
            renderer = glGetString(GL_RENDERER)
            version = glGetString(GL_VERSION)
            print(f"OpenGL供应商: {vendor}")
            print(f"OpenGL渲染器: {renderer}")
            print(f"OpenGL版本: {version}")
            return True
        except Exception as e:
            print(f"OpenGL状态检查失败: {str(e)}")
            return False

    def start_visualization(self, V0, a, E):
        """启动3D可视化线程，与主界面分离"""
        # 更新参数
        self.barrier_height = V0
        self.barrier_width = a
        self.particle_energy = E
        # 启动控制面板
        self._init_control_panel()
        # 启动GLUT线程
        if not self.thread or not self.thread.is_alive():
            self.running = True
            self.thread = threading.Thread(target=self._glut_loop, daemon=True)
            self.thread.start()

    def _glut_loop(self):
        """在独立线程中运行 freeglut 事件循环"""
        try:
            glutInit()
            # 关键：关闭窗口时不退出整个进程
            # 需要 freeglut 才有这个选项
            glutSetOption(GLUT_ACTION_ON_WINDOW_CLOSE, GLUT_ACTION_CONTINUE_EXECUTION)

            glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
            glutInitWindowSize(800, 600)
            glutInitWindowPosition(100, 100)
            self.window = glutCreateWindow(b"Quantum Tunneling 3D")
            from OpenGL.GLUT import glutCloseFunc
            glutCloseFunc(self.on_close_opengl_window)

            # 回调
            glutDisplayFunc(self._display)
            glutTimerFunc(0, self._timer, 0)
            glutMouseFunc(self.mouse_button)
            glutMotionFunc(self.mouse_motion)
            glutKeyboardFunc(self.keyboard)
            # 不再使用 glutWMCloseFunc

            self.init_gl()
            self.glut_initialized = True

            # 自己控制循环，60FPS
            while self.running and self.glut_initialized:
                glutMainLoopEvent()
                time.sleep(0.016)
        except Exception as e:
            print(f"GLUT线程错误: {e}")
        finally:
            # 退出循环后，安全销毁窗口，不影响主程序
            if self.window is not None:
                try:
                    glutDestroyWindow(self.window)
                except:
                    pass
            self.glut_initialized = False
            self.window = None

    def _timer(self, value):
        """每帧更新 + 重绘 + 重新注册定时器"""
        if not self.running or not self.glut_initialized or self.window is None:
            return

        self.time += 0.1
        self.update_wave_packets()

        try:
            glutSetWindow(self.window)
            glutPostRedisplay()
        except Exception:
            pass
        glutTimerFunc(16, self._timer, 0)


    def update_visualization(self):
        """使用tkinter的after方法更新可视化，确保事件循环持续"""
        if self.running and self.glut_initialized:
            try:
                glutSetWindow(self.window)
                glutPostRedisplay()
                glutSwapBuffers()
                glutMainLoopEvent()
                if self.control_panel:
                    self.control_panel.after(16, self.update_visualization)
            except Exception as e:
                print(f"更新可视化时出错: {str(e)}")
                self.running = False

    def stop_visualization(self):
        self.running = False
        if self.control_panel:
            self.control_panel.destroy()

    def draw_barrier(self):
        """绘制半透明势垒"""
        glPushMatrix()

        # 设置材质属性
        glColor4f(0.7, 0.7, 0.8, 0.4)  # 淡蓝灰色半透明

        w = self.barrier_width * 1.5  # 增加势垒宽度
        h = self.barrier_height

        # 绘制势垒主体
        glBegin(GL_QUADS)
        # 前面
        glNormal3f(0.0, 0.0, -1.0)
        glVertex3f(-w, 0, -1)
        glVertex3f(w, 0, -1)
        glVertex3f(w, h, -1)
        glVertex3f(-w, h, -1)

        # 后面
        glNormal3f(0.0, 0.0, 1.0)
        glVertex3f(-w, 0, 1)
        glVertex3f(w, 0, 1)
        glVertex3f(w, h, 1)
        glVertex3f(-w, h, 1)

        # 顶面
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(-w, h, -1)
        glVertex3f(w, h, -1)
        glVertex3f(w, h, 1)
        glVertex3f(-w, h, 1)

        # 侧面
        glNormal3f(1.0, 0.0, 0.0)
        glVertex3f(w, 0, -1)
        glVertex3f(w, 0, 1)
        glVertex3f(w, h, 1)
        glVertex3f(w, h, -1)

        glNormal3f(-1.0, 0.0, 0.0)
        glVertex3f(-w, 0, -1)
        glVertex3f(-w, 0, 1)
        glVertex3f(-w, h, 1)
        glVertex3f(-w, h, -1)
        glEnd()

        # 绘制边缘线
        glColor4f(0.5, 0.5, 0.6, 0.8)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        # 垂直边缘
        glVertex3f(-w, 0, -1)
        glVertex3f(-w, h, -1)
        glVertex3f(w, 0, -1)
        glVertex3f(w, h, -1)
        glVertex3f(-w, 0, 1)
        glVertex3f(-w, h, 1)
        glVertex3f(w, 0, 1)
        glVertex3f(w, h, 1)
        # 水平边缘
        glVertex3f(-w, h, -1)
        glVertex3f(w, h, -1)
        glVertex3f(-w, h, 1)
        glVertex3f(w, h, 1)
        glEnd()

        glPopMatrix()

    def draw_wave_packet(self, x, amplitude, color, is_transmitted=False):
        """绘制排成一列的波包"""
        glPushMatrix()

        # 设置小球的基本参数
        sphere_radius = 0.05  # 小球半径
        total_spheres = 10  # 总小球数量
        sphere_spacing = 0.2  # 小球之间的间距

        # 计算波前位置
        center_x = x
        center_y = 0
        center_z = 0

        # 设置材质属性
        glColor4f(*color)
        glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, color)
        glMaterialfv(GL_FRONT, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))
        glMaterialf(GL_FRONT, GL_SHININESS, 50.0)

        # 绘制所有小球
        for i in range(total_spheres):
            # 计算小球位置
            if center_x < 0:  # 入射波
                sphere_x = center_x + i * sphere_spacing
            else:  # 反射波或透射波
                sphere_x = center_x - i * sphere_spacing

            # 计算衰减效果
            fade = 1.0 - (i / total_spheres) * 0.3  # 从前往后逐渐衰减

            # 设置小球颜色（带衰减）
            sphere_color = [
                color[0] * fade,
                color[1] * fade,
                color[2] * fade,
                color[3] * fade
            ]
            glColor4f(*sphere_color)

            # 绘制小球
            glPushMatrix()
            glTranslatef(sphere_x, center_y, center_z)
            glutSolidSphere(sphere_radius, 10, 10)
            glPopMatrix()

        # 添加连接线
        glColor4f(*color)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        for i in range(total_spheres - 1):
            if center_x < 0:  # 入射波
                x1 = center_x + i * sphere_spacing
                x2 = center_x + (i + 1) * sphere_spacing
            else:  # 反射波或透射波
                x1 = center_x - i * sphere_spacing
                x2 = center_x - (i + 1) * sphere_spacing

            glVertex3f(x1, center_y, center_z)
            glVertex3f(x2, center_y, center_z)
        glEnd()

        glPopMatrix()

    def draw_wave_packets(self):
        """绘制当前唯一波包，按状态着色"""
        for packet in self.wave_packets:
            if not packet['alive']:
                continue
            color = [0.9, 0.3, 0.3, 0.7]  # 红色
            if packet['state'] == 'reflected':
                color = [0.3, 0.8, 0.3, 0.6]  # 绿色
            elif packet['state'] == 'transmitted':
                color = [0.9, 0.8, 0.2, 0.6]  # 黄色
            self.draw_wave_packet(packet['current_x'], self.wave_amplitude, color)

    def draw_ground(self):
        """绘制地面网格"""
        glPushMatrix()
        glColor4f(0.8, 0.8, 0.8, 0.3)
        glLineWidth(1.0)

        # 绘制网格
        glBegin(GL_LINES)
        for i in range(-8, 9):
            glVertex3f(i, 0, -2)
            glVertex3f(i, 0, 2)
            glVertex3f(-8, 0, i / 4)
            glVertex3f(8, 0, i / 4)
        glEnd()

        glPopMatrix()

    def render_text(self, x, y, z, text):
        glRasterPos3f(x, y, z)
        for char in text:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(char))

    def create_wave_packet(self):
        """创建新的波包，增加状态字段"""
        return {
            'state': 'incident',  # incident/red, reflected/green, transmitted/yellow
            'creation_time': self.time,
            'last_update_time': self.time,
            'current_x': self.initial_position,
            'transmitted_start_time': None,
            'tunneling_probability': 0.0,
            'alive': True
        }

    def update_wave_packets(self):
        """每次只有一个波包，红色遇势垒概率穿透变黄，否则反射变绿，消失后下一个波包。黄色小球只在势垒右侧运动，超出右侧边界立即消失。"""
        if not self.wave_packets or not self.wave_packets[-1]['alive']:
            self.wave_packets = [self.create_wave_packet()]
        packet = self.wave_packets[-1]
        if not packet['alive']:
            return
        dt = self.time - packet['last_update_time']
        packet['last_update_time'] = self.time
        if packet['state'] == 'incident':
            packet['current_x'] += self.wave_speed * dt
            if packet['current_x'] >= -self.barrier_width / 2:
                tunneling_prob = self.current_tunneling_prob  # 用同步的概率
                packet['tunneling_probability'] = tunneling_prob
                if np.random.random() < tunneling_prob:
                    packet['state'] = 'transmitted'
                    packet['transmitted_start_time'] = self.time
                    packet['current_x'] = self.barrier_width / 2
                else:
                    packet['state'] = 'reflected'
        elif packet['state'] == 'reflected':
            packet['current_x'] -= self.wave_speed * dt
            if packet['current_x'] < -8.0:
                packet['alive'] = False
        elif packet['state'] == 'transmitted':
            packet['current_x'] += self.wave_speed * dt
            if packet['current_x'] > 8.0 or packet['current_x'] < self.barrier_width / 2:
                packet['alive'] = False

    def update_control_panel(self):
        """更新控制面板"""
        self.control_panel.update()
        self.control_panel.after(100, self.update_control_panel)

    def on_close_control_panel(self):
        """关闭控制面板时仅停止可视化"""
        self.running = False
        if self.control_panel:
            self.control_panel.destroy()
            self.control_panel = None

    def on_close_opengl_window(self):
        """关闭3D窗口"""
        self.running = False
        self.glut_initialized = False

        if self.control_panel:
            try:
                self.width_scale.config(command=None)
                self.height_scale.config(command=None)
                self.speed_scale.config(command=None)
            except Exception as e:
                print(f"解绑滑条命令失败: {e}")
            self.control_panel.destroy()
            self.control_panel = None

            # 防止残留引用
        self.window = None


class QuantumExperimentGUI:
    def __init__(self, root):
        self.root = root
        # self.root.title("量子实验模拟器")
        # self.root.geometry("1400x800")

        # 设置样式
        self.setup_styles()

        # 添加3D可视化对象
        self.visualization_3d = None
        self.visualization_running = False

        # 量子隧穿参数
        self.barrier_height_var = tk.DoubleVar(value=1.0)
        self.barrier_width_var = tk.DoubleVar(value=1.0)
        self.particle_energy_var = tk.DoubleVar(value=0.5)
        self.experiment_type_var = tk.StringVar(value="量子隧穿")

        # 双缝干涉参数
        self.slit_distance_var = tk.DoubleVar(value=10.0)
        self.slit_width_var = tk.DoubleVar(value=2.0)
        self.screen_distance_var = tk.DoubleVar(value=100.0)
        self.wavelength_var = tk.DoubleVar(value=0.5)

        # 单量子干涉参数
        self.single_quantum_n_var = tk.IntVar(value=100)

        # 分析参数
        self.analysis_type_var = tk.StringVar(value="势垒高度")
        self.range_start_var = tk.DoubleVar(value=0.1)
        self.range_end_var = tk.DoubleVar(value=2.0)
        self.double_slit_analysis_type_var = tk.StringVar(value="狭缝间距")
        self.double_slit_range_start_var = tk.DoubleVar(value=2.0)
        self.double_slit_range_end_var = tk.DoubleVar(value=50.0)

        # 创建主框架
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # 左侧控制区
        self.control_frame = ttk.LabelFrame(self.main_frame, text="参数配置", width=320, style='Group.TLabelframe')
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.control_frame.pack_propagate(False)

        # 右侧显示区
        self.display_frame = ttk.Frame(self.main_frame)
        self.display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 初始化图表
        self.figure = None
        self.barrier_ax = None
        self.density_ax = None
        self.prob_ax = None
        self.canvas = None

        # 创建控件和显示区域
        self.create_scrollable_display()
        self.create_control_widgets()
        self.create_display_widgets()  # 确保在初始化时创建图表

    def create_scrollable_display(self):
        """创建可滚动的显示区域"""
        # 创建主框架
        self.display_container = ttk.Frame(self.display_frame)
        self.display_container.pack(fill=tk.BOTH, expand=True)

        # 创建画布和滚动条
        self.display_canvas = tk.Canvas(self.display_container, highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(self.display_container, orient="vertical", command=self.display_canvas.yview)
        self.h_scroll = ttk.Scrollbar(self.display_container, orient="horizontal", command=self.display_canvas.xview)

        # 内容框架
        self.content_frame = ttk.Frame(self.display_canvas)
        self.content_frame.bind("<Configure>", lambda e: self.display_canvas.configure(
            scrollregion=self.display_canvas.bbox("all")))

        # 将内容框架添加到画布
        self.display_canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        # 配置画布滚动
        self.display_canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        # 布局
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.display_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 绑定鼠标滚轮事件
        self.display_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.display_canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)

    def _on_mousewheel(self, event):
        """处理垂直滚动"""
        self.display_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_mousewheel(self, event):
        """处理水平滚动"""
        self.display_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def setup_styles(self):
        """配置自定义样式"""
        style = ttk.Style()
        style.theme_use('clam')  # 使用clam主题作为基础

        # 主框架背景色
        style.configure('TFrame', background=COLOR_BG)

        # 标签样式
        style.configure('TLabel',
                        background=COLOR_BG,
                        foreground=COLOR_TEXT,
                        font=('Segoe UI', 10))

        # 按钮样式
        style.configure('TButton',
                        font=('Segoe UI', 10),
                        background=COLOR_ACCENT,
                        foreground='white',
                        borderwidth=1,
                        relief='raised',
                        padding=5,
                        width=10)

        style.map('TButton',
                  background=[('active', '#005a9e'), ('pressed', '#004578')],
                  foreground=[('disabled', '#666666')])

        # 输入框样式
        style.configure('TEntry',
                        fieldbackground='white',
                        foreground=COLOR_TEXT,
                        borderwidth=1,
                        relief='solid',
                        padding=5)

        # 滑条样式
        style.configure('TScale',
                        background=COLOR_BG,
                        troughcolor='#d9d9d9',
                        sliderrelief='raised',
                        sliderthickness=15)

        # 组合框样式
        style.configure('TCombobox',
                        fieldbackground='white',
                        foreground=COLOR_TEXT,
                        selectbackground=COLOR_ACCENT,
                        selectforeground='white',
                        padding=5)

        # 单选按钮样式
        style.configure('TRadiobutton',
                        background=COLOR_BG,
                        foreground=COLOR_TEXT,
                        indicatorbackground=COLOR_BG,
                        padding=5)

        # 分组框样式
        style.configure('Group.TLabelframe',
                        borderwidth=2,
                        relief="groove",
                        font=('SimHei', 10, 'bold'),
                        foreground=COLOR_TEXT,
                        background=COLOR_BG)
        style.configure('Group.TLabelframe.Label',
                        background=COLOR_BG,
                        foreground=COLOR_TEXT)

        # 标题标签样式
        style.configure('Header.TLabel',
                        font=('Segoe UI', 11, 'bold'),
                        foreground=COLOR_ACCENT)

    def create_control_widgets(self):
        """创建控制面板的所有控件，包括滑条和数值显示"""
        # 设置样式
        style = ttk.Style()
        style.configure('TLabel', background=COLOR_BG, foreground=COLOR_TEXT, font=('SimHei', 10))
        style.configure('Header.TLabel', font=('SimHei', 11, 'bold'))

        # 实验类型选择
        ttk.Label(self.control_frame, text="实验类型：", style='Header.TLabel').pack(anchor=tk.W, pady=(5, 0))
        self.experiment_type_combobox = ttk.Combobox(
            self.control_frame,
            textvariable=self.experiment_type_var,
            values=["量子隧穿", "双缝干涉", "量子纠错"],
            state="readonly",
            style='TCombobox'
        )
        self.experiment_type_combobox.pack(fill=tk.X, padx=5, pady=5)
        self.experiment_type_combobox.bind('<<ComboboxSelected>>', self.update_controls)

        # 开始实验按钮
        self.start_button = ttk.Button(
            self.control_frame,
            text="开始实验",
            command=self.start_experiment,
            style='TButton'
        )
        self.start_button.pack(fill=tk.X, padx=5, pady=10)

        # 量子隧穿参数
        self.tunneling_params = ttk.LabelFrame(self.control_frame, text="量子隧穿参数", style='Group.TLabelframe')
        self.tunneling_params.pack(fill=tk.X, padx=5, pady=5)

        # 使用grid布局管理内部控件
        row = 0

        # 势垒高度
        height_label_frame = ttk.Frame(self.tunneling_params)
        height_label_frame.grid(row=row, column=0, sticky=tk.W, padx=5, pady=(5, 0))
        ttk.Label(height_label_frame, text="势垒高度 (eV)：", style='TLabel').pack(side=tk.LEFT)
        self.barrier_height_value_label = ttk.Label(height_label_frame, text="1.0", style='TLabel')
        self.barrier_height_value_label.pack(side=tk.LEFT, padx=5)
        row += 1

        height_frame = ttk.Frame(self.tunneling_params)
        height_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=(0, 10))
        self.barrier_height_scale = ttk.Scale(
            height_frame,
            from_=0.1, to=2.0,
            variable=self.barrier_height_var,
            orient=tk.HORIZONTAL,
            length=260,
            style='TScale',
            command=lambda v: self.update_scale_value(self.barrier_height_value_label, v)
        )
        self.barrier_height_scale.pack(fill=tk.X, expand=True)
        row += 1

        # 势垒宽度
        width_label_frame = ttk.Frame(self.tunneling_params)
        width_label_frame.grid(row=row, column=0, sticky=tk.W, padx=5, pady=(5, 0))
        ttk.Label(width_label_frame, text="势垒宽度 (nm)：", style='TLabel').pack(side=tk.LEFT)
        self.barrier_width_value_label = ttk.Label(width_label_frame, text="1.0", style='TLabel')
        self.barrier_width_value_label.pack(side=tk.LEFT, padx=5)
        row += 1

        width_frame = ttk.Frame(self.tunneling_params)
        width_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=(0, 10))
        self.barrier_width_scale = ttk.Scale(
            width_frame,
            from_=0.1, to=3.0,
            variable=self.barrier_width_var,
            orient=tk.HORIZONTAL,
            length=260,
            style='TScale',
            command=lambda v: self.update_scale_value(self.barrier_width_value_label, v)
        )
        self.barrier_width_scale.pack(fill=tk.X, expand=True)
        row += 1

        # 粒子能量
        energy_label_frame = ttk.Frame(self.tunneling_params)
        energy_label_frame.grid(row=row, column=0, sticky=tk.W, padx=5, pady=(5, 0))
        ttk.Label(energy_label_frame, text="粒子能量 (eV)：", style='TLabel').pack(side=tk.LEFT)
        self.particle_energy_value_label = ttk.Label(energy_label_frame, text="0.5", style='TLabel')
        self.particle_energy_value_label.pack(side=tk.LEFT, padx=5)
        row += 1

        energy_frame = ttk.Frame(self.tunneling_params)
        energy_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=(0, 10))
        self.particle_energy_scale = ttk.Scale(
            energy_frame,
            from_=0.1, to=1.5,
            variable=self.particle_energy_var,
            orient=tk.HORIZONTAL,
            length=260,
            style='TScale',
            command=lambda v: self.update_scale_value(self.particle_energy_value_label, v)
        )
        self.particle_energy_scale.pack(fill=tk.X, expand=True)
        row += 1

        # 3D可视化按钮
        self.visualization_button = ttk.Button(
            self.tunneling_params,
            text="启动3D可视化",
            command=self.start_3d_visualization,
            style='TButton'
        )
        self.visualization_button.grid(
            row=row, column=0, columnspan=3, pady=(10, 5), sticky=tk.EW, padx=5)
        row += 1

        # 量子隧穿参数分析
        self.analysis_frame = ttk.LabelFrame(self.control_frame, text="量子隧穿参数分析", style='Group.TLabelframe')
        self.analysis_frame.pack(fill=tk.X, padx=5, pady=5)

        # 分析类型选择
        ttk.Label(self.analysis_frame, text="分析类型：", style='TLabel').pack(anchor=tk.W)
        self.analysis_type_var = tk.StringVar(value="势垒高度")
        analysis_types = ["势垒高度", "势垒宽度", "粒子能量"]
        for at in analysis_types:
            ttk.Radiobutton(
                self.analysis_frame,
                text=at,
                variable=self.analysis_type_var,
                value=at,
                style='TRadiobutton'
            ).pack(anchor=tk.W)

        # 参数范围设置
        self.range_frame = ttk.Frame(self.analysis_frame)
        self.range_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(self.range_frame, text="起始值：", style='TLabel').pack(side=tk.LEFT)
        self.range_start_var = tk.DoubleVar(value=0.1)
        self.range_start = ttk.Entry(
            self.range_frame,
            textvariable=self.range_start_var,
            width=8,
            style='TEntry'
        )
        self.range_start.pack(side=tk.LEFT, padx=5)

        ttk.Label(self.range_frame, text="终止值：", style='TLabel').pack(side=tk.LEFT)
        self.range_end_var = tk.DoubleVar(value=2.0)
        self.range_end = ttk.Entry(
            self.range_frame,
            textvariable=self.range_end_var,
            width=8,
            style='TEntry'
        )
        self.range_end.pack(side=tk.LEFT, padx=5)

        # 分析按钮
        self.analyze_button = ttk.Button(
            self.analysis_frame,
            text="分析影响",
            command=self.analyze_parameter_effect,
            style='TButton'
        )
        self.analyze_button.pack(pady=10, fill=tk.X)

        # 双缝干涉参数
        self.double_slit_params = ttk.LabelFrame(self.control_frame, text="双缝干涉参数", style='Group.TLabelframe')

        # 狭缝间距
        distance_label_frame = ttk.Frame(self.double_slit_params)
        distance_label_frame.grid(row=0, column=0, sticky=tk.W, padx=5, pady=(5, 0))
        ttk.Label(distance_label_frame, text="狭缝间距 d (μm)：", style='TLabel').pack(side=tk.LEFT)
        self.slit_distance_value_label = ttk.Label(distance_label_frame, text="10.0", style='TLabel')
        self.slit_distance_value_label.pack(side=tk.LEFT, padx=5)

        distance_frame = ttk.Frame(self.double_slit_params)
        distance_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=(0, 10))
        self.slit_distance_scale = ttk.Scale(
            distance_frame,
            from_=2.0, to=200.0,
            variable=self.slit_distance_var,
            orient=tk.HORIZONTAL,
            length=260,
            style='TScale',
            command=lambda v: self.update_scale_value(self.slit_distance_value_label, v)
        )
        self.slit_distance_scale.pack(fill=tk.X, expand=True)

        # 狭缝宽度
        width_label_frame = ttk.Frame(self.double_slit_params)
        width_label_frame.grid(row=2, column=0, sticky=tk.W, padx=5, pady=(5, 0))
        ttk.Label(width_label_frame, text="狭缝宽度 a (μm)：", style='TLabel').pack(side=tk.LEFT)
        self.slit_width_value_label = ttk.Label(width_label_frame, text="2.0", style='TLabel')
        self.slit_width_value_label.pack(side=tk.LEFT, padx=5)

        width_frame = ttk.Frame(self.double_slit_params)
        width_frame.grid(row=3, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=(0, 10))
        self.slit_width_scale = ttk.Scale(
            width_frame,
            from_=0.1, to=50.0,
            variable=self.slit_width_var,
            orient=tk.HORIZONTAL,
            length=260,
            style='TScale',
            command=lambda v: self.update_scale_value(self.slit_width_value_label, v)
        )
        self.slit_width_scale.pack(fill=tk.X, expand=True)

        # 屏幕距离
        screen_label_frame = ttk.Frame(self.double_slit_params)
        screen_label_frame.grid(row=4, column=0, sticky=tk.W, padx=5, pady=(5, 0))
        ttk.Label(screen_label_frame, text="屏幕距离 L (cm)：", style='TLabel').pack(side=tk.LEFT)
        self.screen_distance_value_label = ttk.Label(screen_label_frame, text="100.0", style='TLabel')
        self.screen_distance_value_label.pack(side=tk.LEFT, padx=5)

        screen_frame = ttk.Frame(self.double_slit_params)
        screen_frame.grid(row=5, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=(0, 10))
        self.screen_distance_scale = ttk.Scale(
            screen_frame,
            from_=5.0, to=500.0,
            variable=self.screen_distance_var,
            orient=tk.HORIZONTAL,
            length=260,
            style='TScale',
            command=lambda v: self.update_scale_value(self.screen_distance_value_label, v)
        )
        self.screen_distance_scale.pack(fill=tk.X, expand=True)

        # 粒子波长
        wavelength_label_frame = ttk.Frame(self.double_slit_params)
        wavelength_label_frame.grid(row=6, column=0, sticky=tk.W, padx=5, pady=(5, 0))
        ttk.Label(wavelength_label_frame, text="粒子波长 λ (nm)：", style='TLabel').pack(side=tk.LEFT)
        self.wavelength_value_label = ttk.Label(wavelength_label_frame, text="0.5", style='TLabel')
        self.wavelength_value_label.pack(side=tk.LEFT, padx=5)

        wavelength_frame = ttk.Frame(self.double_slit_params)
        wavelength_frame.grid(row=7, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=(0, 10))
        self.wavelength_scale = ttk.Scale(
            wavelength_frame,
            from_=0.01, to=5.0,
            variable=self.wavelength_var,
            orient=tk.HORIZONTAL,
            length=260,
            style='TScale',
            command=lambda v: self.update_scale_value(self.wavelength_value_label, v)
        )
        self.wavelength_scale.pack(fill=tk.X, expand=True)

        # 双缝干涉参数分析
        self.double_slit_analysis_frame = ttk.LabelFrame(self.control_frame, text="双缝干涉参数分析",
                                                         style='Group.TLabelframe')

        # 分析类型选择
        ttk.Label(self.double_slit_analysis_frame, text="分析类型：", style='TLabel').pack(anchor=tk.W)
        self.double_slit_analysis_type_var = tk.StringVar(value="狭缝间距")
        analysis_types = ["狭缝间距", "狭缝宽度", "波长", "屏幕距离"]
        for at in analysis_types:
            ttk.Radiobutton(
                self.double_slit_analysis_frame,
                text=at,
                variable=self.double_slit_analysis_type_var,
                value=at,
                style='TRadiobutton'
            ).pack(anchor=tk.W)

        # 参数范围设置
        self.double_slit_range_frame = ttk.Frame(self.double_slit_analysis_frame)
        self.double_slit_range_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(self.double_slit_range_frame, text="起始值：", style='TLabel').pack(side=tk.LEFT)
        self.double_slit_range_start_var = tk.DoubleVar(value=2.0)
        self.double_slit_range_start = ttk.Entry(
            self.double_slit_range_frame,
            textvariable=self.double_slit_range_start_var,
            width=8,
            style='TEntry'
        )
        self.double_slit_range_start.pack(side=tk.LEFT, padx=5)

        ttk.Label(self.double_slit_range_frame, text="终止值：", style='TLabel').pack(side=tk.LEFT)
        self.double_slit_range_end_var = tk.DoubleVar(value=50.0)
        self.double_slit_range_end = ttk.Entry(
            self.double_slit_range_frame,
            textvariable=self.double_slit_range_end_var,
            width=8,
            style='TEntry'
        )
        self.double_slit_range_end.pack(side=tk.LEFT, padx=5)

        # 分析按钮
        self.double_slit_analyze_button = ttk.Button(
            self.double_slit_analysis_frame,
            text="分析影响",
            command=self.analyze_double_slit_effect,
            style='TButton'
        )
        self.double_slit_analyze_button.pack(pady=10, fill=tk.X)

        # 单量子干涉演示
        self.single_quantum_frame = ttk.LabelFrame(self.control_frame, text="单量子干涉演示", style='Group.TLabelframe')

        # 3D可视化按钮
        self.double_slit_3d_button = ttk.Button(
            self.control_frame,
            text="单电子",
            command=self.open_double_slit_3d,
            style='TButton'
        )

        # 波前动画按钮
        self.wavefront_anim_button = ttk.Button(
            self.control_frame,
            text="波前干涉动画",
            command=self.open_wavefront_animation,
            style='TButton'
        )

        # 初始隐藏双缝干涉相关控件
        self.double_slit_params.pack_forget()
        self.double_slit_analysis_frame.pack_forget()
        self.single_quantum_frame.pack_forget()
        self.double_slit_3d_button.pack_forget()
        self.wavefront_anim_button.pack_forget()

    def update_scale_value(self, label, value):
        """更新滑条旁边的数值显示"""
        try:
            label.config(text=f"{float(value):.2f}")
        except ValueError:
            pass

    def update_controls(self, event=None):
        if self.experiment_type_var.get() == "量子隧穿":
            self.tunneling_params.pack(fill=tk.X, padx=5, pady=5)
            self.analysis_frame.pack(fill=tk.X, padx=5, pady=5)
            self.visualization_button.grid(column=0, columnspan=2, pady=(10, 5), sticky=tk.EW, padx=5)
            self.double_slit_params.pack_forget()
            self.double_slit_analysis_frame.pack_forget()
            self.single_quantum_frame.pack_forget()
            self.double_slit_3d_button.pack_forget()
            self.wavefront_anim_button.pack_forget()
        elif self.experiment_type_var.get() == "双缝干涉":
            self.tunneling_params.pack_forget()
            self.analysis_frame.pack_forget()
            self.visualization_button.pack_forget()
            self.double_slit_params.pack(fill=tk.X, padx=5, pady=5)
            self.double_slit_analysis_frame.pack(fill=tk.X, padx=5, pady=5)
            self.single_quantum_frame.pack(fill=tk.X, padx=5, pady=5)
            self.double_slit_3d_button.pack(pady=8, padx=10, fill=tk.X, anchor=tk.S)
            self.wavefront_anim_button.pack(pady=8, padx=10, fill=tk.X, anchor=tk.S)

    def create_display_widgets(self):
        """创建显示图表"""
        # 如果已有图表，先清除
        if self.figure:
            plt.close(self.figure)
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.get_tk_widget().destroy()

        # 创建图表
        self.figure = plt.figure(figsize=(12, 7.5), facecolor='white')

        # 调整GridSpec参数
        gs = GridSpec(1, 3, figure=self.figure, width_ratios=[1.7, 1.7, 1.1],
                      height_ratios=[1.25])  # 高度比例增加25%

        # 设置图表背景色
        self.barrier_ax = self.figure.add_subplot(gs[0], facecolor=COLOR_BG_SECONDARY)
        self.density_ax = self.figure.add_subplot(gs[1], facecolor=COLOR_BG_SECONDARY)
        self.prob_ax = self.figure.add_subplot(gs[2], facecolor=COLOR_BG_SECONDARY)

        # 调整边距
        self.figure.subplots_adjust(left=0.08, right=0.95, bottom=0.12, top=0.9, wspace=0.25, hspace=0.15)

        # 创建画布并添加到内容框架
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.content_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)


    def start_experiment(self):
        if self.experiment_type_var.get() == "量子隧穿":
            self.simulate_tunneling()
        else:
            self.simulate_double_slit()

    def simulate_tunneling(self):
        # 获取参数
        V0 = self.barrier_height_var.get()  # 势垒高度 (eV)
        a = self.barrier_width_var.get()  # 势垒宽度 (nm)
        E = self.particle_energy_var.get()  # 粒子能量 (eV)

        # 转换为国际单位
        V0_J = V0 * 1.60218e-19  # eV to J
        a_m = a * 1e-9  # nm to m
        E_J = E * 1.60218e-19  # eV to J

        # 计算波数
        k1 = np.sqrt(2 * m_e * E_J) / hbar
        k2 = np.sqrt(2 * m_e * (E_J - V0_J)) / hbar if E_J > V0_J else 1j * np.sqrt(2 * m_e * (V0_J - E_J)) / hbar

        # 计算透射系数
        if isinstance(k2, complex):
            T = 1 / (1 + (V0_J ** 2 * np.sinh(abs(k2) * a_m) ** 2) / (4 * E_J * (V0_J - E_J)))
        else:
            T = 1 / (1 + (V0_J ** 2 * np.sin(k2 * a_m) ** 2) / (4 * E_J * (E_J - V0_J)))

        # 创建位置数组
        x = np.linspace(-3 * a, 3 * a, 1000)

        # 清除所有子图
        self.barrier_ax.clear()
        self.density_ax.clear()
        self.prob_ax.clear()

        # 1. 绘制势垒示意图
        V = np.zeros_like(x)
        V[(x >= -a / 2) & (x <= a / 2)] = V0

        self.barrier_ax.clear()
        # 设置x轴范围
        self.barrier_ax.set_xlim(-3, 3)
        # 设置y轴范围，确保显示完整的势垒和能量
        self.barrier_ax.set_ylim(0, 1.2)

        # 绘制势垒
        self.barrier_ax.plot(x, V, 'b-', linewidth=2, label='势垒')
        # 在势垒区域添加填充
        self.barrier_ax.fill_between(x[(x >= -a / 2) & (x <= a / 2)],
                                     0, V[(x >= -a / 2) & (x <= a / 2)],
                                     color='blue', alpha=0.1)

        # 绘制粒子能量线
        self.barrier_ax.axhline(y=E, color='r', linestyle='--',
                                label=f'粒子能量: {E:.2f} eV')

        # 添加垂直分隔线
        self.barrier_ax.axvline(-a / 2, color='gray', linestyle='--', alpha=0.5)
        self.barrier_ax.axvline(a / 2, color='gray', linestyle='--', alpha=0.5)

        # 添加势垒宽度标注
        self.barrier_ax.annotate(f'势垒宽度: {a} nm',
                                 xy=(0, V0 / 2),
                                 xytext=(0, V0 / 2),
                                 ha='center',
                                 bbox=dict(boxstyle='round,pad=0.5',
                                           facecolor='white',
                                           edgecolor='gray',
                                           alpha=1.0))

        # 设置标题和标签
        self.barrier_ax.set_title('势垒示意图')
        self.barrier_ax.set_xlabel('位置 (nm)')
        self.barrier_ax.set_ylabel('能量 (eV)')

        # 添加网格
        self.barrier_ax.grid(True, linestyle='--', alpha=0.2)

        # 添加图例，调整样式
        legend = self.barrier_ax.legend(
            loc='upper right',
            frameon=True,
            fancybox=True,
            framealpha=1.0,
            edgecolor='gray'
        )

        # 2. 绘制波函数概率密度分布
        psi = np.zeros_like(x, dtype=complex)
        # 入射区域
        psi[x < -a / 2] = np.exp(1j * k1 * x[x < -a / 2] * 1e9) + 0.5 * np.exp(-1j * k1 * x[x < -a / 2] * 1e9)
        # 势垒区域
        if isinstance(k2, complex):
            psi[(x >= -a / 2) & (x <= a / 2)] = np.exp(-abs(k2) * (x[(x >= -a / 2) & (x <= a / 2)] + a / 2) * 1e9)
        else:
            psi[(x >= -a / 2) & (x <= a / 2)] = np.exp(1j * k2 * x[(x >= -a / 2) & (x <= a / 2)] * 1e9)
        # 透射区域
        psi[x > a / 2] = 0.5 * np.exp(1j * k1 * x[x > a / 2] * 1e9)

        # 计算概率密度并归一化
        prob_density = np.abs(psi) ** 2
        prob_density = prob_density / np.max(prob_density)

        # 创建掩码
        incident_mask = x < -a / 2
        barrier_mask = (x >= -a / 2) & (x <= a / 2)
        transmission_mask = x > a / 2

        # 使用对数刻度
        prob_density_log = np.log10(prob_density + 1e-10)

        # 清除之前的图形
        self.density_ax.clear()

        # 设置图表的边框
        for spine in self.density_ax.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(1.0)

        # 绘制概率密度分布
        self.density_ax.fill_between(x[incident_mask], -3, prob_density_log[incident_mask],
                                     color='#4169E1', alpha=0.4, label='入射波', edgecolor='#1E3F8F', linewidth=0.5)
        self.density_ax.fill_between(x[barrier_mask], -3, prob_density_log[barrier_mask],
                                     color='#90EE90', alpha=0.4, label='势垒区域', edgecolor='#2E8B57', linewidth=0.5)
        self.density_ax.fill_between(x[transmission_mask], -3, prob_density_log[transmission_mask],
                                     color='#FF6B6B', alpha=0.4, label='透射波', edgecolor='#B22222', linewidth=0.5)

        # 添加垂直分隔线
        self.density_ax.axvline(-a / 2, color='gray', linestyle='--', alpha=0.7, linewidth=1.2)
        self.density_ax.axvline(a / 2, color='gray', linestyle='--', alpha=0.7, linewidth=1.2)

        # 设置对数刻度的y轴范围和标签
        self.density_ax.set_ylim(-3, 0)
        yticks = [-3, -2, -1, 0]
        self.density_ax.set_yticks(yticks)
        self.density_ax.set_yticklabels([f'$10^{y}$' for y in yticks], fontsize=10)

        # 设置x轴范围和标签
        self.density_ax.set_xlim(-3, 3)
        self.density_ax.set_xlabel('位置 (nm)', fontsize=11)
        self.density_ax.set_ylabel('相对概率密度（对数刻度）', fontsize=11)

        # 设置标题
        self.density_ax.set_title('波函数概率密度分布', fontsize=12, pad=15)

        # 添加网格
        self.density_ax.grid(True, linestyle='--', alpha=0.2)

        # 添加图例，调整样式
        legend = self.density_ax.legend(
            loc='upper right',
            frameon=True,
            fancybox=True,
            framealpha=0.9,
            edgecolor='gray',
            fontsize=10,
            borderpad=0.8,
            labelspacing=0.8
        )

        # 添加隧穿概率标注
        prob_text = self.density_ax.text(
            0, -1.5,
            f'隧穿概率: {T * 100:.1f}%',
            ha='center',
            va='center',
            fontsize=11,
            bbox=dict(
                boxstyle='round,pad=0.6',
                facecolor='white',
                edgecolor='#B22222',
                linewidth=1.2,
                alpha=0.9
            )
        )

        # 3. 绘制隧穿概率图
        labels = ['透射', '反射']
        values = [T, 1 - T]
        colors = ['green', 'red']

        bars = self.prob_ax.bar(labels, values, color=colors)
        self.prob_ax.set_ylim(0, 1)

        # 在柱状图上添加百分比标签
        for bar in bars:
            height = bar.get_height()
            self.prob_ax.text(bar.get_x() + bar.get_width() / 2., height / 2.,
                              f'{height * 100:.1f}%',
                              ha='center', va='center', color='white')

        self.prob_ax.set_title('隧穿概率')
        self.prob_ax.set_ylabel('概率')

        # 更新画布
        self.figure.canvas.draw()

    def analyze_parameter_effect(self):
        analysis_type = self.analysis_type_var.get()
        start_val = self.range_start_var.get()
        end_val = self.range_end_var.get()

        # 创建参数范围
        param_range = np.linspace(start_val, end_val, 200)  # 增加点数使曲线更平滑
        transmission_probs = []

        # 获取当前固定参数值
        V0 = self.barrier_height_var.get()
        a = self.barrier_width_var.get()
        E = self.particle_energy_var.get()

        # 检查参数是否合法
        if V0 <= 0 or a <= 0 or E <= 0:
            messagebox.showerror("参数错误", "势垒高度、宽度和粒子能量必须大于0")
            return

        # 计算不同参数值下的隧穿概率
        for val in param_range:
            try:
                if analysis_type == "势垒高度":
                    V0_curr = val
                    a_curr = a
                    E_curr = E
                elif analysis_type == "势垒宽度":
                    V0_curr = V0
                    a_curr = val
                    E_curr = E
                else:  # 粒子能量
                    V0_curr = V0
                    a_curr = a
                    E_curr = val

                # 检查当前参数是否合法
                if V0_curr <= 0 or a_curr <= 0 or E_curr <= 0:
                    transmission_probs.append(0)
                    continue

                # 转换为国际单位
                V0_J = V0_curr * 1.60218e-19
                a_m = a_curr * 1e-9
                E_J = E_curr * 1.60218e-19

                # 计算波数和透射系数
                k1 = np.sqrt(2 * m_e * E_J) / hbar
                k2 = np.sqrt(2 * m_e * (E_J - V0_J)) / hbar if E_J > V0_J else 1j * np.sqrt(
                    2 * m_e * (V0_J - E_J)) / hbar

                if isinstance(k2, complex):
                    T = 1 / (1 + (V0_J ** 2 * np.sinh(abs(k2) * a_m) ** 2) / (4 * E_J * (V0_J - E_J)))
                else:
                    T = 1 / (1 + (V0_J ** 2 * np.sin(k2 * a_m) ** 2) / (4 * E_J * (E_J - V0_J)))

                # 确保T是有效的概率值
                T = max(0, min(1, float(T)))
                transmission_probs.append(T)
            except (ValueError, ZeroDivisionError, RuntimeWarning):
                transmission_probs.append(0)

        # 确保两个数组长度相同
        transmission_probs = np.array(transmission_probs)

        # 检查是否有有效的数据
        if not transmission_probs.size or all(p == 0 for p in transmission_probs):
            messagebox.showerror("计算错误", "无法计算有效的隧穿概率")
            return

        # 清除所有子图
        self.barrier_ax.clear()
        self.density_ax.clear()
        self.prob_ax.clear()

        # 设置所有坐标轴的背景为白色
        self.barrier_ax.set_facecolor('white')
        self.density_ax.set_facecolor('white')
        self.prob_ax.set_facecolor('white')

        # 过滤掉无效值并计算y轴范围
        valid_probs = [p for p in transmission_probs if np.isfinite(p) and not np.isnan(p)]
        if valid_probs:
            y_min = max(0, min(valid_probs) * 0.99)
            y_max = min(1, max(valid_probs) * 1.01)
        else:
            y_min, y_max = 0, 1

        # 1. 绘制参数影响曲线
        self.barrier_ax.plot(param_range, transmission_probs, 'b-', linewidth=2)
        self.barrier_ax.set_title(f"{analysis_type}对隧穿概率的影响", pad=20, fontsize=12)
        self.barrier_ax.set_xlabel(f"{analysis_type} " + ("(eV)" if analysis_type != "势垒宽度" else "(nm)"))
        self.barrier_ax.set_ylabel("隧穿概率")
        self.barrier_ax.grid(True, linestyle='--', alpha=0.3)
        self.barrier_ax.set_ylim(y_min, y_max)

        # 添加固定参数说明，调整位置到左上角并优化样式
        if analysis_type == "势垒高度":
            param_text = f"固定参数:\n势垒宽度: {a} nm\n粒子能量: {E} eV"
        elif analysis_type == "势垒宽度":
            param_text = f"固定参数:\n势垒高度: {V0} eV\n粒子能量: {E} eV"
        else:
            param_text = f"固定参数:\n势垒高度: {V0} eV\n势垒宽度: {a} nm"

        # 调整文本框位置和样式
        self.barrier_ax.text(0.02, 0.98, param_text,
                             transform=self.barrier_ax.transAxes,
                             verticalalignment='top',
                             horizontalalignment='left',
                             bbox=dict(boxstyle='round,pad=0.5',
                                       facecolor='white',
                                       edgecolor='gray',
                                       alpha=0.95,  # 增加不透明度
                                       linewidth=1))

        # 调整图表边距，为文本框留出空间
        self.barrier_ax.margins(x=0.02, y=0.15)

        # 确保x轴标签不重叠
        self.barrier_ax.tick_params(axis='x', rotation=45)

        # 调整y轴范围，为文本框留出更多空间
        current_ylim = self.barrier_ax.get_ylim()
        self.barrier_ax.set_ylim(current_ylim[0], current_ylim[1] * 1.1)

        # 2. 绘制参数分析结果
        self.density_ax.set_title("参数影响分析结果", pad=10, fontsize=12)

        # 找到最大和最小值（排除无效值）
        max_prob_idx = np.nanargmax(transmission_probs)
        min_prob_idx = np.nanargmin([p if p > 0 else np.inf for p in transmission_probs])

        # 创建更美观的文本框
        max_text = (f"最大隧穿概率:\n"
                    f"{transmission_probs[max_prob_idx]:.3f}\n"
                    f"在 {param_range[max_prob_idx]:.2f}")
        min_text = (f"最小隧穿概率:\n"
                    f"{transmission_probs[min_prob_idx]:.3f}\n"
                    f"在 {param_range[min_prob_idx]:.2f}")

        # 设置文本框样式
        box_style = {
            'max': {
                'bbox': dict(
                    boxstyle='round,pad=0.6',
                    facecolor='#e8f5e9',  # 浅绿色背景
                    edgecolor='#2e7d32',  # 深绿色边框
                    alpha=0.8,
                    linewidth=2
                ),
                'position': (0.5, 0.7)
            },
            'min': {
                'bbox': dict(
                    boxstyle='round,pad=0.6',
                    facecolor='#ffebee',  # 浅红色背景
                    edgecolor='#c62828',  # 深红色边框
                    alpha=0.8,
                    linewidth=2
                ),
                'position': (0.5, 0.3)
            }
        }

        # 绘制最大值文本框
        self.density_ax.text(
            box_style['max']['position'][0],
            box_style['max']['position'][1],
            max_text,
            ha='center', va='center',
            bbox=box_style['max']['bbox'],
            transform=self.density_ax.transAxes,
            fontsize=10,
            fontweight='bold'
        )

        # 绘制最小值文本框
        self.density_ax.text(
            box_style['min']['position'][0],
            box_style['min']['position'][1],
            min_text,
            ha='center', va='center',
            bbox=box_style['min']['bbox'],
            transform=self.density_ax.transAxes,
            fontsize=10,
            fontweight='bold'
        )

        # 添加装饰线条
        def add_decorative_lines(ax, y_pos, color):
            # 添加水平线
            ax.axhline(y=y_pos, xmin=0.1, xmax=0.9,
                       color=color, alpha=0.3, linewidth=1)

        # 为最大值和最小值添加装饰线
        add_decorative_lines(self.density_ax, 0.85, '#2e7d32')  # 最大值上方
        add_decorative_lines(self.density_ax, 0.55, '#2e7d32')  # 最大值下方
        add_decorative_lines(self.density_ax, 0.45, '#c62828')  # 最小值上方
        add_decorative_lines(self.density_ax, 0.15, '#c62828')  # 最小值下方

        # 设置轴的显示
        self.density_ax.set_xticks([])
        self.density_ax.set_yticks([])

        # 添加背景网格
        self.density_ax.grid(False)

        # 设置图表边框
        for spine in self.density_ax.spines.values():
            spine.set_visible(False)

        # 3. 绘制平均隧穿概率
        avg_prob = np.nanmean(valid_probs)
        self.prob_ax.set_title("平均隧穿概率", pad=10, fontsize=12)
        bar = self.prob_ax.bar(['平均值'], [avg_prob], color='blue')
        self.prob_ax.set_ylim(0, 1)

        # 在柱状图上添加数值标签
        self.prob_ax.text(0, avg_prob / 2,
                          f'{avg_prob * 100:.1f}%',
                          ha='center', va='center',
                          color='white',
                          fontsize=12,
                          fontweight='bold')

        # 更新画布
        self.figure.canvas.draw()

    def start_3d_visualization(self):
        # 检查OpenGL是否可用
        if not OPENGL_AVAILABLE:
            messagebox.showwarning("功能不可用",
                                   "3D量子隧穿可视化需要OpenGL支持，\n"
                                   "请使用以下命令安装必要组件：\n"
                                   "pip install PyOpenGL PyOpenGL_accelerate")
            return

        if self.visualization_running:
            return

        # 获取当前参数
        V0 = self.barrier_height_var.get()
        a = self.barrier_width_var.get()
        E = self.particle_energy_var.get()

        # 停止现有的可视化
        if self.visualization_3d is not None:
            self.visualization_3d.stop_visualization()

        # 创建新的可视化对象
        self.visualization_3d = Quantum3DVisualization()
        self.visualization_running = True

        try:
            # 在主线程中启动可视化
            self.visualization_3d.start_visualization(V0, a, E)
        except Exception as e:
            print(f"可视化启动错误: {str(e)}")
            self.visualization_running = False
            if self.visualization_3d is not None:
                self.visualization_3d.stop_visualization()
                self.visualization_3d = None
        finally:
            self.visualization_running = False

    def simulate_double_slit(self):
        # 获取参数
        d = self.slit_distance_var.get() * 1e-6  # μm -> m
        a = self.slit_width_var.get() * 1e-6  # μm -> m
        L = self.screen_distance_var.get() * 1e-2  # cm -> m
        lam = self.wavelength_var.get() * 1e-9  # nm -> m
        # 屏幕坐标
        y = np.linspace(-0.001, 0.001, 1200)  # -0.1cm~0.1cm
        x = np.linspace(-0.01, 0.01, 200)
        Y, X = np.meshgrid(y, x)
        # 计算二维干涉强度
        beta = np.pi * a * Y / (lam * L)
        alpha = np.pi * d * Y / (lam * L)
        single = (np.sinc(beta / np.pi)) ** 2
        interference = (np.cos(alpha)) ** 2
        intensity2d = single * interference
        # 归一化到0~1
        intensity2d = intensity2d / np.max(intensity2d)
        # 一维强度分布
        intensity1d = intensity2d[int(len(x) / 2)]
        # 清空图表
        self.barrier_ax.clear()
        self.density_ax.clear()
        self.prob_ax.clear()

        # 设置所有坐标轴的背景为白色
        self.barrier_ax.set_facecolor('white')
        self.density_ax.set_facecolor('white')
        self.prob_ax.set_facecolor('white')

        # 左图：标准物理教材风格装置示意
        self.barrier_ax.set_xlim(-0.5, 2.5)
        self.barrier_ax.set_ylim(-0.7, 0.7)
        # 狭缝板
        self.barrier_ax.plot([0, 0], [-0.6, 0.6], 'k', lw=4)
        # 两狭缝中心
        s1_y = 0.15
        s2_y = -0.15
        # 屏幕
        self.barrier_ax.plot([2, 2], [-0.6, 0.6], 'k', lw=2)
        # P点
        p_y = 0.3
        self.barrier_ax.plot(2, p_y, 'ko')
        self.barrier_ax.text(2.08, p_y, r'$P$', fontsize=13, ha='left', va='center')
        # S1、S2
        self.barrier_ax.plot(0, s1_y, 'ko')
        self.barrier_ax.plot(0, s2_y, 'ko')
        self.barrier_ax.text(-0.08, s1_y, r'$S_1$', fontsize=13, ha='right', va='center')
        self.barrier_ax.text(-0.08, s2_y, r'$S_2$', fontsize=13, ha='right', va='center')
        # r1, r2 路径
        self.barrier_ax.plot([0, 2], [s1_y, p_y], 'gray', lw=1)
        self.barrier_ax.plot([0, 2], [s2_y, p_y], 'gray', lw=1)
        self.barrier_ax.text(1.1, (s1_y + p_y) / 2 + 0.03, r'$r_1$', fontsize=11, color='gray')
        self.barrier_ax.text(1.1, (s2_y + p_y) / 2 - 0.03, r'$r_2$', fontsize=11, color='gray')
        # d 虚线和箭头
        self.barrier_ax.plot([0.0, 0.0], [s2_y, s1_y], 'b--', lw=1)
        self.barrier_ax.annotate('', xy=(0.0, s1_y), xytext=(0.0, s2_y),
                                 arrowprops=dict(arrowstyle='<->', color='b', lw=1.5))
        self.barrier_ax.text(0.03, 0, r'$d$', color='b', fontsize=12, va='center')
        # D 虚线和箭头
        self.barrier_ax.plot([0, 2], [-0.5, -0.5], 'purple', lw=1, ls='dashed')
        self.barrier_ax.annotate('', xy=(0, -0.5), xytext=(2, -0.5),
                                 arrowprops=dict(arrowstyle='<->', color='purple', lw=1.5))
        self.barrier_ax.text(1, -0.54, r'$D$', color='purple', fontsize=12, ha='center')
        # x 虚线和箭头
        self.barrier_ax.plot([2, 2], [0, p_y], 'g--', lw=1)
        self.barrier_ax.annotate('', xy=(2, 0), xytext=(2, p_y),
                                 arrowprops=dict(arrowstyle='<->', color='g', lw=1.5))
        self.barrier_ax.text(2.05, p_y / 2, r'$x$', color='g', fontsize=12, va='center')
        # 中轴线
        self.barrier_ax.plot([-0.1, 2.1], [0, 0], 'k:', lw=1)
        self.barrier_ax.axis('off')
        # 中图：二维干涉条纹
        self.density_ax.imshow(intensity2d.T, cmap='hot', aspect='auto',
                               extent=[-0.01, 0.01, -0.1, 0.1], origin='lower')
        self.density_ax.set_title('双缝干涉图谱')
        self.density_ax.set_xlabel('屏幕 x (m)')
        self.density_ax.set_ylabel('y (cm)')
        self.density_ax.set_yticks(np.linspace(-0.1, 0.1, 5))
        # 右图：一维强度分布（放大，范围更细致）
        self.prob_ax.plot(y * 100, intensity1d, color='royalblue', linewidth=2)
        self.prob_ax.set_xlabel('y (cm)', fontsize=12)
        self.prob_ax.set_ylabel('强度', fontsize=12)
        self.prob_ax.set_xlim(-0.1, 0.1)
        self.prob_ax.set_ylim(0, 1.05)
        self.prob_ax.grid(True, linestyle='--', alpha=0.4)
        self.prob_ax.tick_params(axis='both', labelsize=11)
        self.prob_ax.xaxis.set_major_locator(plt.MultipleLocator(0.05))
        self.figure.canvas.draw()

    def analyze_double_slit_effect(self):
        analysis_type = self.double_slit_analysis_type_var.get()
        start_val = self.double_slit_range_start_var.get()
        end_val = self.double_slit_range_end_var.get()
        param_range = np.linspace(start_val, end_val, 200)
        # 获取固定参数
        d = self.slit_distance_var.get() * 1e-6
        a = self.slit_width_var.get() * 1e-6
        L = self.screen_distance_var.get() * 1e-2
        lam = self.wavelength_var.get() * 1e-9
        # 结果数组
        fringe_spacing = []  # 主极大间距
        visibility = []  # 可见度
        max_intensity = []  # 最大强度
        for val in param_range:
            if analysis_type == "狭缝间距":
                d_curr = val * 1e-6
                a_curr = a
                L_curr = L
                lam_curr = lam
            elif analysis_type == "狭缝宽度":
                d_curr = d
                a_curr = val * 1e-6
                L_curr = L
                lam_curr = lam
            elif analysis_type == "波长":
                d_curr = d
                a_curr = a
                L_curr = L
                lam_curr = val * 1e-9
            else:  # 屏幕距离
                d_curr = d
                a_curr = a
                L_curr = val * 1e-2
                lam_curr = lam
            # 计算条纹分布
            x = np.linspace(-0.01, 0.01, 2000)
            beta = np.pi * a_curr * x / (lam_curr * L_curr)
            alpha = np.pi * d_curr * x / (lam_curr * L_curr)
            single = (np.sinc(beta / np.pi)) ** 2
            interference = (np.cos(alpha)) ** 2
            intensity = single * interference
            intensity /= np.max(intensity)
            # 主极大间距Δx = λL/d
            spacing = lam_curr * L_curr / d_curr * 1e3  # mm
            fringe_spacing.append(spacing)
            # 可见度 = (Imax - Imin)/(Imax + Imin)
            Imax = np.max(intensity)
            Imin = np.min(intensity)
            vis = (Imax - Imin) / (Imax + Imin) if (Imax + Imin) > 0 else 0
            visibility.append(vis)
            max_intensity.append(Imax)
        # 绘制分析图
        self.barrier_ax.clear()
        self.density_ax.clear()
        self.prob_ax.clear()
        self.barrier_ax.set_facecolor('white')
        self.density_ax.set_facecolor('white')
        self.prob_ax.set_facecolor('white')
        self.barrier_ax.plot(param_range, fringe_spacing, color='purple')
        self.barrier_ax.set_title('主极大间距 vs ' + analysis_type, fontsize=15, pad=16)
        self.barrier_ax.set_xlabel(analysis_type, fontsize=13)
        self.barrier_ax.set_ylabel('主极大间距 (mm)', fontsize=13)
        self.barrier_ax.grid(True, linestyle='--', alpha=0.3)
        self.density_ax.plot(param_range, visibility, color='teal')
        self.density_ax.set_title('条纹可见度 vs ' + analysis_type, fontsize=15, pad=16)
        self.density_ax.set_xlabel(analysis_type, fontsize=13)
        self.density_ax.set_ylabel('可见度', fontsize=13)
        self.density_ax.grid(True, linestyle='--', alpha=0.3)
        self.prob_ax.plot(param_range, max_intensity, color='orange')
        self.prob_ax.set_title('最大强度 vs ' + analysis_type, fontsize=15, pad=16)
        self.prob_ax.set_xlabel(analysis_type, fontsize=13)
        self.prob_ax.set_ylabel('最大强度', fontsize=13)
        self.prob_ax.grid(True, linestyle='--', alpha=0.3)
        self.figure.canvas.draw()

    def play_single_quantum_interference(self):
        # 获取参数
        d = self.slit_distance_var.get() * 1e-6
        a = self.slit_width_var.get() * 1e-6
        L = self.screen_distance_var.get() * 1e-2
        lam = self.wavelength_var.get() * 1e-9
        n = self.single_quantum_n_var.get()
        # 屏幕y坐标
        y = np.linspace(-0.001, 0.001, 1200)
        beta = np.pi * a * y / (lam * L)
        alpha = np.pi * d * y / (lam * L)
        single = (np.sinc(beta / np.pi)) ** 2
        interference = (np.cos(alpha)) ** 2
        intensity = single * interference
        intensity /= np.max(intensity)
        # 概率分布采样
        y_samples = np.random.choice(y, size=n, p=intensity / np.sum(intensity))
        # 清空并绘制点
        self.single_quantum_ax.clear()
        self.single_quantum_ax.scatter(y_samples * 100, np.random.uniform(0, 1, size=n), s=8, c='royalblue', alpha=0.7)
        self.single_quantum_ax.set_xlim(-0.1, 0.1)
        self.single_quantum_ax.set_ylim(0, 1)
        self.single_quantum_ax.axis('off')
        self.single_quantum_fig.tight_layout()
        self.single_quantum_canvas.draw()

    def open_double_slit_3d(self):
        # 弹出新窗口
        win = tk.Toplevel(self.root)
        win.title("双缝干涉实验（3D可视化）")
        win.geometry("800x500")

        # 设置背景色
        win.configure(bg=COLOR_BG)

        # matplotlib画布
        fig, ax = plt.subplots(figsize=(7.5, 3.5))
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        ax.axis('off')
        # 控件区
        ctrl_frame = ttk.Frame(win, style='TFrame')
        ctrl_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        ttk.Label(ctrl_frame, text="粒子数 n:", style='TLabel').pack(side=tk.LEFT, padx=5)
        n_var = tk.IntVar(value=100)
        n_entry = ttk.Entry(ctrl_frame, textvariable=n_var, width=8)
        n_entry.pack(side=tk.LEFT, padx=5)

        # 粒子数滑动条
        def play():
            d = self.slit_distance_var.get() * 1e-6
            a = self.slit_width_var.get() * 1e-6
            L = self.screen_distance_var.get() * 1e-2
            lam = self.wavelength_var.get() * 1e-9
            n = n_var.get()
            y = np.linspace(-0.001, 0.001, 1200)
            beta = np.pi * a * y / (lam * L)
            alpha = np.pi * d * y / (lam * L)
            single = (np.sinc(beta / np.pi)) ** 2
            interference = (np.cos(alpha)) ** 2
            intensity = single * interference
            intensity /= np.max(intensity)
            y_samples = np.random.choice(y, size=n, p=intensity / np.sum(intensity))
            ax.clear()
            ax.scatter(y_samples * 100, np.random.uniform(0, 1, size=n), s=8, c='royalblue', alpha=0.7)
            ax.set_xlim(-0.1, 0.1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            fig.tight_layout()
            canvas.draw()

        n_scale = tk.Scale(
            ctrl_frame,
            from_=1, to=100000,
            orient=tk.HORIZONTAL,
            length=180,
            showvalue=False,
            variable=n_var,
            command=lambda v: (n_var.set(int(float(v))), play())
        )
        n_scale.pack(side=tk.LEFT, padx=5)

        # 输入框与滑动条双向同步
        def on_n_entry_change(*args):
            try:
                val = int(n_var.get())
                if 1 <= val <= 100000:
                    n_scale.set(val)
                    play()
            except Exception:
                pass

        n_var.trace_add('write', lambda *a: on_n_entry_change())
        play_btn = ttk.Button(ctrl_frame, text="播放", command=play, style='TButton')
        play_btn.pack(side=tk.LEFT, padx=10)

        # 新增3D仿真按钮
        def open_3d_sim():
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d import Axes3D
            import numpy as np
            win3d = tk.Toplevel(self.root)
            win3d.title("双缝干涉3D实验仿真")
            win3d.geometry("900x700")
            fig = plt.figure(figsize=(8, 6))
            ax = fig.add_subplot(111, projection='3d')
            # 参数
            d = self.slit_distance_var.get() * 1e-6
            L = self.screen_distance_var.get() * 1e-2
            lam = self.wavelength_var.get() * 1e-9
            # 空间网格
            x = np.linspace(-0.01, 0.01, 200)
            y = np.linspace(0, L, 200)
            X, Y = np.meshgrid(x, y)
            # 双缝位置
            slit_y1 = d / 2
            slit_y2 = -d / 2
            # 两缝到屏幕上每点的距离
            r1 = np.sqrt((X) ** 2 + (Y - slit_y1) ** 2)
            r2 = np.sqrt((X) ** 2 + (Y - slit_y2) ** 2)
            # 波的叠加
            k = 2 * np.pi / lam
            Z = np.cos(k * r1) + np.cos(k * r2)
            # 绘制
            surf = ax.plot_surface(X * 100, Y * 100, Z, cmap='viridis', linewidth=0, antialiased=False, alpha=0.85)
            ax.set_xlabel('屏幕x (cm)')
            ax.set_ylabel('传播方向y (cm)')
            ax.set_zlabel('波强度')
            ax.set_title('双缝干涉3D波前仿真')
            fig.colorbar(surf, shrink=0.5, aspect=10)
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            canvas = FigureCanvasTkAgg(fig, master=win3d)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 新增波包动态可视化
        def show_wave_packet_animation():
            from matplotlib.animation import FuncAnimation
            import numpy as np

            # 创建新窗口
            wave_win = tk.Toplevel(win)
            wave_win.title("波包干涉过程动画")
            wave_win.geometry("1000x800")

            # 创建图形，只保留一个子图
            fig = plt.figure(figsize=(10, 8), dpi=100)
            ax1 = fig.add_subplot(111)

            # 参数
            d = self.slit_distance_var.get() * 1e-6  # 缝间距，μm转m
            a = self.slit_width_var.get() * 1e-6  # 缝宽度，μm转m
            L = self.screen_distance_var.get() * 1e-2  # 屏幕距离，cm转m
            lam = self.wavelength_var.get() * 1e-9  # 波长，nm转m
            k = 2 * np.pi / lam  # 波数

            # 创建空间网格
            x_start = -5 * d  # 从光源开始
            x_end = L + d  # 到屏幕位置
            x_res = 200  # x方向分辨率
            y_res = 300  # y方向分辨率
            y_range = 2 * d  # y方向范围（应大于缝间距）

            # 空间坐标
            x = np.linspace(x_start, x_end, x_res)
            y = np.linspace(-y_range / 2, y_range / 2, y_res)
            X, Y = np.meshgrid(x, y)

            # 狭缝位置
            slit_x = 0
            slit_y1 = d / 2
            slit_y2 = -d / 2
            slit_width = a  # 缝宽度

            # 计算波包传播
            def calculate_wave(t):
                c = 3e8
                omega = c * k
                phase0 = omega * t
                source_x = x_start
                source_y = 0
                r_to_slit1 = np.sqrt((slit_x - source_x) ** 2 + (slit_y1 - source_y) ** 2)
                r_to_slit2 = np.sqrt((slit_x - source_x) ** 2 + (slit_y2 - source_y) ** 2)
                wave_before = np.zeros_like(X)
                mask_before = X < slit_x
                dist_before = np.sqrt((X - source_x) ** 2 + (Y - source_y) ** 2)
                amp_before = 1.0 / np.maximum(dist_before, 0.1 * d)
                wave_before[mask_before] = amp_before[mask_before] * np.cos(k * dist_before[mask_before] - phase0)
                wave_after = np.zeros_like(X)
                mask_after = X > slit_x
                for offset in np.linspace(-slit_width / 2, slit_width / 2, 5):
                    sub_slit_y = slit_y1 + offset
                    dist1 = np.sqrt((X - slit_x) ** 2 + (Y - sub_slit_y) ** 2)
                    amp1 = 0.5 / np.maximum(dist1, 0.1 * d)
                    init_phase1 = k * (r_to_slit1 + offset) - phase0
                    wave_after[mask_after] += amp1[mask_after] * np.cos(k * dist1[mask_after] - init_phase1)
                for offset in np.linspace(-slit_width / 2, slit_width / 2, 5):
                    sub_slit_y = slit_y2 + offset
                    dist2 = np.sqrt((X - slit_x) ** 2 + (Y - sub_slit_y) ** 2)
                    amp2 = 0.5 / np.maximum(dist2, 0.1 * d)
                    init_phase2 = k * (r_to_slit2 + offset) - phase0
                    wave_after[mask_after] += amp2[mask_after] * np.cos(k * dist2[mask_after] - init_phase2)
                slit_mask = (X > slit_x - 0.02 * d) & (X < slit_x + 0.02 * d)
                wave_after[slit_mask] = 0
                wave_before[slit_mask] = 0
                barrier_mask = (X > slit_x - 0.02 * d) & (X < slit_x + 0.02 * d) & \
                               ~((Y > slit_y1 - slit_width / 2) & (Y < slit_y1 + slit_width / 2) | \
                                 (Y > slit_y2 - slit_width / 2) & (Y < slit_y2 + slit_width / 2))
                wave = wave_before + wave_after
                return wave, barrier_mask

            # 动画初始化
            def init():
                wave, barrier_mask = calculate_wave(0)
                im = ax1.imshow(wave, cmap='seismic',
                                extent=[x_start, x_end, -y_range / 2, y_range / 2],
                                vmin=-1, vmax=1, aspect='auto', origin='lower')
                ax1.axvline(x=slit_x, color='k', linewidth=1, alpha=0.5)
                ax1.axvline(x=L, color='g', linewidth=1.5, alpha=0.8)
                ax1.set_title("波包传播过程")
                ax1.set_xlabel("传播方向 (m)")
                ax1.set_ylabel("垂直方向 (m)")
                slit1_y = slit_y1
                slit2_y = slit_y2
                ax1.plot([slit_x, slit_x], [slit1_y - slit_width / 2, slit1_y + slit_width / 2], 'w-', linewidth=3)
                ax1.plot([slit_x, slit_x], [slit2_y - slit_width / 2, slit2_y + slit_width / 2], 'w-', linewidth=3)
                fig.tight_layout()
                return [im]

            def update(frame):
                t = frame * 0.05 * lam / 3e8
                wave, barrier_mask = calculate_wave(t)
                im.set_array(wave)
                return [im]

            im = ax1.imshow(np.zeros((y_res, x_res)), cmap='seismic',
                            extent=[x_start, x_end, -y_range / 2, y_range / 2],
                            vmin=-1, vmax=1, aspect='auto', origin='lower')
            ax1.axvline(x=slit_x, color='k', linewidth=1, alpha=0.5)
            ax1.axvline(x=L, color='g', linewidth=1.5, alpha=0.8)
            ax1.set_title("波包传播过程")
            ax1.set_xlabel("传播方向 (m)")
            ax1.set_ylabel("垂直方向 (m)")
            slit1_y = slit_y1
            slit2_y = slit_y2
            ax1.plot([slit_x, slit_x], [slit1_y - slit_width / 2, slit1_y + slit_width / 2], 'w-', linewidth=3)
            ax1.plot([slit_x, slit_x], [slit2_y - slit_width / 2, slit2_y + slit_width / 2], 'w-', linewidth=3)
            fig.tight_layout()
            frames = 100
            ani = FuncAnimation(fig, update, frames=frames, interval=50, blit=True)
            canvas = FigureCanvasTkAgg(fig, master=wave_win)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            control_frame = tk.Frame(wave_win)
            control_frame.pack(fill=tk.X, pady=5)
            param_text = f"狭缝间距: {d * 1e6:.1f} μm | 狭缝宽度: {a * 1e6:.1f} μm | 波长: {lam * 1e9:.1f} nm | 屏幕距离: {L * 100:.1f} cm"
            param_label = tk.Label(control_frame, text=param_text, font=("SimHei", 10))
            param_label.pack(pady=5)
            close_btn = tk.Button(control_frame, text="关闭", command=wave_win.destroy,
                                  bg="#e74c3c", fg="white", font=("SimHei", 10), width=10)
            close_btn.pack(pady=5)

        # 添加波包动画按钮
        wave_btn = ttk.Button(ctrl_frame, text="波包动画", command=show_wave_packet_animation)
        wave_btn.pack(side=tk.LEFT, padx=10)

        btn3d = ttk.Button(ctrl_frame, text="3D实验仿真", command=open_3d_sim)
        btn3d.pack(side=tk.LEFT, padx=10)

        play()

    def open_wavefront_animation(self):
        win = tk.Toplevel(self.root)
        win.title("双缝干涉波前动画")
        win.geometry("900x700")
        fig, ax = plt.subplots(figsize=(9, 7))
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        ax.set_xlim(-5, 15)
        ax.set_ylim(-7, 7)
        ax.axis('off')
        # 画装置结构
        # 狭缝板
        ax.add_patch(Rectangle((0, -5), 0.5, 10, color="#6d4c41", alpha=0.8, zorder=1))
        # 两个狭缝
        ax.add_patch(Rectangle((0, 1.2), 0.5, 1.6, color="white", zorder=2))
        ax.add_patch(Rectangle((0, -2.8), 0.5, 1.6, color="white", zorder=2))
        # 屏幕
        ax.add_patch(Rectangle((12, -5), 3.0, 10, color="black", alpha=0.8, zorder=1))
        # 波前参数
        source = (-4, 0)
        slit1 = (0.25, 2)
        slit2 = (0.25, -2)
        screen_x = 12.35
        # 动画帧
        wavefronts = []
        for i in range(12):
            wavefronts.append({'r': i * 0.8 + 0.5, 'alpha': max(0, 1 - i * 0.08)})
        # 动态patch记录
        dynamic_patches = []

        # 动画更新
        def animate(frame):
            # 移除上一帧动态patch
            for p in dynamic_patches:
                p.remove()
            dynamic_patches.clear()
            # 源到狭缝的波前
            for wf in wavefronts:
                r = wf['r'] + frame * 0.1
                max_r = 0 - source[0]  # 不能超过狭缝板左侧
                if r <= max_r:
                    circle = plt.Circle(source, r, color='#2196f3', fill=False, lw=2.2, alpha=wf['alpha'] * 0.8,
                                        zorder=3)
                    ax.add_patch(circle)
                    dynamic_patches.append(circle)
            # 狭缝到屏幕的波前
            for slit in [slit1, slit2]:
                for wf in wavefronts:
                    r = wf['r'] + frame * 0.2
                    # 只画x>=slit[0]的半圆弧
                    theta = np.linspace(-np.pi / 2, np.pi / 2, 120)
                    x_arc = slit[0] + r * np.cos(theta)
                    y_arc = slit[1] + r * np.sin(theta)
                    mask = x_arc >= slit[0]
                    line = plt.Line2D(x_arc[mask], y_arc[mask], color='#7ed6fb', lw=3.2, alpha=wf['alpha'] * 0.9,
                                      zorder=4)
                    ax.add_line(line)
                    dynamic_patches.append(line)
            # 屏幕干涉条纹
            y = np.linspace(-5, 5, 400)
            intensity = (np.cos(2 * np.pi * (y) / 2.5)) ** 2
            intensity = intensity / np.max(intensity)
            for i, yy in enumerate(y[::8]):
                alpha = intensity[::8][i] * 0.8
                rect = Rectangle((screen_x, yy - 0.1), 3.0, 0.2, color='white', alpha=alpha, zorder=10)
                ax.add_patch(rect)
                dynamic_patches.append(rect)
            return dynamic_patches

        ani = animation.FuncAnimation(fig, animate, frames=40, interval=80, blit=False)
        canvas.draw()


if __name__ == "__main__":
    # 仅在OpenGL可用时初始化GLUT
    if OPENGL_AVAILABLE:
        try:
            glutInit(sys.argv)
        except Exception as e:
            print(f"GLUT初始化失败: {str(e)}")
            # 不是致命错误，仍然可以运行其他功能
            OPENGL_AVAILABLE = False

    root = tk.Tk()
    app = QuantumExperimentGUI(root)


    # 关闭窗口时的清理操作
    def on_close():
        if hasattr(app, 'visualization_3d') and app.visualization_3d:
            app.visualization_3d.stop_visualization()
        root.quit()
        root.destroy()


    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()