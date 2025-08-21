import sys
import warnings
import pygame
import numpy as np
import scipy
from pygame.locals import *
import matplotlib
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

current_noise = 0
measuring = False
animating = False
anim_theory_pts = []
anim_exp_pts = []

COLORS = {
    'background': (30, 30, 45),
    'panel': (45, 45, 60),
    'primary': (0, 150, 200),
    'secondary': (100, 200, 150),
    'text': (220, 220, 230),
    'border': (80, 80, 100),
    'button': (70, 70, 90),
    'hover': (90, 90, 110),
    'theory': '#64c896',
    'experiment': '#c86496'
}

WIDTH, HEIGHT = 1400, 820
PANEL_WIDTH = 300
SPHERE_CENTER = (PANEL_WIDTH + (WIDTH - PANEL_WIDTH) // 2, HEIGHT // 2)
CONTROL_START = 20


class Button:
    def __init__(self, x, y, w, h, text, callback):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.callback = callback
        self.hover = False

    def draw(self, surface):
        color = COLORS['hover'] if self.hover else COLORS['button']
        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        pygame.draw.rect(surface, COLORS['border'], self.rect, 2, border_radius=4)
        text_surf = font.render(self.text, True, COLORS['text'])
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.callback()


class Slider:
    def __init__(self, x, y, label, min_val, max_val, initial):
        self.x = x
        self.y = y
        self.label = label
        self.min = min_val
        self.max = max_val
        self.range = max_val - min_val
        self.value = initial
        self.grabbed = False
        self.knob_size = 14
        self.bar_width = 200
        self.bar_height = 4

    def draw(self, surface):
        label_surf = font.render(f"{self.label}: {self.value:.2f}", True, COLORS['text'])
        surface.blit(label_surf, (self.x, self.y - 5))
        bar_rect = pygame.Rect(self.x, self.y + 20, self.bar_width, self.bar_height)
        pygame.draw.rect(surface, COLORS['border'], bar_rect, border_radius=2)
        knob_x = self.x + (self.value - self.min) / self.range * self.bar_width
        pygame.draw.circle(surface, COLORS['primary'], (knob_x, self.y + 20 + self.bar_height // 2), 8)

    def update(self, mouse_pos):
        if self.grabbed or pygame.Rect(self.x, self.y, self.bar_width, 40).collidepoint(mouse_pos):
            rel_x = mouse_pos[0] - self.x
            self.value = np.clip(self.min + (rel_x / self.bar_width) * self.range, self.min, self.max)
            return True
        return False


class QuantumState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.theta = np.pi / 4
        self.phi = 0
        self.state = self.get_state_vector()
        self.theory_rho = np.outer(self.state, self.state.conj())
        self.experimental_rho = None
        self.experimental_counts = {'X': (0, 0), 'Y': (0, 0), 'Z': (0, 0)}
        self.bloch = (0, 0, 0)

    def get_state_vector(self):
        return np.array([
            np.cos(self.theta / 2),
            np.sin(self.theta / 2) * np.exp(1j * self.phi)
        ], dtype=np.complex128)

    def apply_gate(self, matrix):
        self.state = matrix @ self.state
        self.state /= np.linalg.norm(self.state)
        self.update_angles()
        self.theory_rho = np.outer(self.state, self.state.conj())
        self.experimental_rho = None
        self.experimental_counts = {'X': (0, 0), 'Y': (0, 0), 'Z': (0, 0)}

    def update_angles(self):
        a, b = self.state[0], self.state[1]
        self.theta = 2 * np.arctan2(np.abs(b), np.abs(a))
        self.phi = (np.angle(b) - np.angle(a)) % (2 * np.pi) if np.abs(a) > 1e-8 else np.angle(b)

    def get_bloch_coordinates(self, rho=None):
        if rho is None:
            x = np.sin(self.theta) * np.cos(self.phi)
            y = np.sin(self.theta) * np.sin(self.phi)
            z = np.cos(self.theta)
            return (x, y, z)
        else:
            X = np.array([[0, 1], [1, 0]])
            Y = np.array([[0, -1j], [1j, 0]])
            Z = np.array([[1, 0], [0, -1]])
            return (np.real(np.trace(rho @ X)),
                    np.real(np.trace(rho @ Y)),
                    np.real(np.trace(rho @ Z)))

    def measure_in_basis(self, basis, noise_param, noise_type, n_shots):
        # 复制当前量子态
        temp_state = self.state.copy()

        # 应用基变换
        if basis == 'X':
            gate = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
        elif basis == 'Y':
            gate = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2) @ np.array([[1, 0], [0, -1j]],
                                                                                            dtype=np.complex128)
        else:  # Z基
            gate = np.eye(2)

        transformed_state = gate @ temp_state

        # 应用噪声
        rho = np.outer(transformed_state, transformed_state.conj())
        noisy_rho = NoiseManager.apply_noise(rho, noise_param, noise_type)

        # 计算测量概率
        p0 = np.real(noisy_rho[0, 0])
        p1 = np.real(noisy_rho[1, 1])

        # 生成测量结果
        count0 = np.random.binomial(n_shots, p0)
        count1 = n_shots - count0
        return count0, count1

    def get_fidelity(self):
        if self.experimental_rho is None:
            return 0.0
        sqrt_rho = scipy.linalg.sqrtm(self.theory_rho)
        inner = sqrt_rho @ self.experimental_rho @ sqrt_rho
        sqrt_inner = scipy.linalg.sqrtm(inner)
        fid = np.real(np.trace(sqrt_inner)) ** 2
        return min(max(fid, 0.0), 1.0)


class NoiseManager:
    noise_types = {
        "退极化噪声": "depolarizing",
        "振幅阻尼": "amplitude_damping",
        "相位阻尼": "phase_damping"
    }

    @classmethod
    def apply_noise(cls, rho, param, noise_type):
        if noise_type == "depolarizing":
            return cls.depolarizing(rho, param)
        elif noise_type == "amplitude_damping":
            return cls.amplitude_damping(rho, param)
        elif noise_type == "phase_damping":
            return cls.phase_damping(rho, param)
        return rho

    @staticmethod
    def depolarizing(rho, p):
        I = np.eye(2)
        X = np.array([[0, 1], [1, 0]])
        Y = np.array([[0, -1j], [1j, 0]])
        Z = np.array([[1, 0], [0, -1]])
        return (1 - p) * rho + p / 3 * (X @ rho @ X + Y @ rho @ Y + Z @ rho @ Z)

    @staticmethod
    def amplitude_damping(rho, gamma):
        E0 = np.array([[1, 0], [0, np.sqrt(1 - gamma)]], dtype=np.complex128)
        E1 = np.array([[0, np.sqrt(gamma)], [0, 0]], dtype=np.complex128)
        return E0 @ rho @ E0.conj().T + E1 @ rho @ E1.conj().T

    @staticmethod
    def phase_damping(rho, gamma):
        E0 = np.array([[1, 0], [0, np.sqrt(1 - gamma)]], dtype=np.complex128)
        E1 = np.array([[0, 0], [0, np.sqrt(gamma)]], dtype=np.complex128)
        return E0 @ rho @ E0.conj().T + E1 @ rho @ E1.conj().T


class BlochSphere:
    def __init__(self):
        self.radius = 220
        self.cam_angle_x = 0.4
        self.cam_angle_y = -0.6
        self.dragging = False
        self.grid_color = (80, 80, 100)

    def project_3d_to_2d(self, point):
        rx = np.array([[1, 0, 0],
                       [0, np.cos(self.cam_angle_x), -np.sin(self.cam_angle_x)],
                       [0, np.sin(self.cam_angle_x), np.cos(self.cam_angle_x)]])
        ry = np.array([[np.cos(self.cam_angle_y), 0, np.sin(self.cam_angle_y)],
                       [0, 1, 0],
                       [-np.sin(self.cam_angle_y), 0, np.cos(self.cam_angle_y)]])
        rotated = ry @ rx @ point
        return (int(SPHERE_CENTER[0] + rotated[0] * self.radius),
                int(SPHERE_CENTER[1] + rotated[1] * self.radius))

    def draw_wireframe(self, surface):
        # 经线
        for phi in np.linspace(0, 2 * np.pi, 16):
            points = []
            for theta in np.linspace(0, np.pi, 30):
                x = np.sin(theta) * np.cos(phi)
                y = np.sin(theta) * np.sin(phi)
                z = np.cos(theta)
                points.append(self.project_3d_to_2d(np.array([x, y, z])))
            pygame.draw.lines(surface, self.grid_color, False, points, 1)

        # 纬线
        for theta in np.linspace(0, np.pi, 8):
            points = []
            for phi in np.linspace(0, 2 * np.pi, 50):
                x = np.sin(theta) * np.cos(phi)
                y = np.sin(theta) * np.sin(phi)
                z = np.cos(theta)
                points.append(self.project_3d_to_2d(np.array([x, y, z])))
            pygame.draw.lines(surface, self.grid_color, True, points, 1)

        # 坐标轴
        axes = [
            (np.array([1.5, 0, 0]), 'X', (200, 50, 50)),
            (np.array([0, 1.5, 0]), 'Y', (50, 200, 50)),
            (np.array([0, 0, 1.5]), 'Z', (50, 50, 200))
        ]
        for vec, label, color in axes:
            start = self.project_3d_to_2d(vec * 0.8)
            end = self.project_3d_to_2d(vec * 1.2)
            pygame.draw.line(surface, color, start, end, 3)
            text = font.render(label, True, color)
            surface.blit(text, (end[0] + 5, end[1] - 10))

    def draw_states(self, surface, qstate):
        # 绘制理论态
        theory_pos = self.project_3d_to_2d(qstate.get_bloch_coordinates())
        pygame.draw.circle(surface, COLORS['theory'], theory_pos, 10)
        pygame.draw.circle(surface, (200, 200, 100), theory_pos, 10, 2)

        # 绘制实验态
        if qstate.experimental_rho is not None:
            ex, ey, ez = qstate.get_bloch_coordinates(qstate.experimental_rho)
            exp_pos = self.project_3d_to_2d([ex, ey, ez])
            pygame.draw.circle(surface, COLORS['experiment'], exp_pos, 10)
            pygame.draw.circle(surface, (200, 100, 100), exp_pos, 10, 2)

    def draw_projection(self, surface, qstate, plane, rect):
        pygame.draw.rect(surface, COLORS['panel'], rect)
        pygame.draw.rect(surface, COLORS['border'], rect, 2)
        center_x = rect.x + rect.width // 2
        center_y = rect.y + rect.height // 2
        scale = min(rect.width, rect.height) // 2 * 0.8

        # 理论投影
        tx, ty, tz = qstate.get_bloch_coordinates()
        if plane == 'xy':
            x, y = tx, ty
        elif plane == 'xz':
            x, y = tx, tz
        elif plane == 'yz':
            x, y = ty, tz
        pygame.draw.circle(surface, COLORS['theory'],
                           (int(center_x + x * scale), int(center_y - y * scale)), 6)

        # 实验投影
        if qstate.experimental_rho is not None:
            ex, ey, ez = qstate.get_bloch_coordinates(qstate.experimental_rho)
            if plane == 'xy':
                x, y = ex, ey
            elif plane == 'xz':
                x, y = ex, ez
            elif plane == 'yz':
                x, y = ey, ez
            pygame.draw.circle(surface, COLORS['experiment'],
                               (int(center_x + x * scale), int(center_y - y * scale)), 6)

        # 绘制坐标轴
        axis_color = COLORS['text']
        pygame.draw.line(surface, axis_color, (rect.x + 10, center_y), (rect.right - 10, center_y), 2)
        pygame.draw.line(surface, axis_color, (center_x, rect.y + 10), (center_x, rect.bottom - 10), 2)
        pygame.draw.circle(surface, COLORS['border'], (center_x, center_y), int(scale), 1)


def plot_analysis(qstate, sliders):
    import matplotlib.pyplot as plt
    import numpy as np

    # 提取数据
    noise_level = sliders[0].value
    shots = int(sliders[1].value)
    theta = sliders[2].value
    phi = sliders[3].value
    fidelity = qstate.get_fidelity()

    if not hasattr(qstate, "fidelity_history"):
        qstate.fidelity_history = []

    # Bloch球坐标
    theory_coords = qstate.get_bloch_coordinates()
    exp_coords = qstate.get_bloch_coordinates(qstate.experimental_rho) if qstate.experimental_rho is not None else (
    0, 0, 0)

    # 创建图形窗口
    fig = plt.figure(figsize=(12, 10))

    # Fidelity 曲线
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.plot(qstate.fidelity_history, label="Fidelity", color='purple', marker='o')
    ax1.set_title("保真度变化曲线")
    ax1.set_xlabel("测量次数")
    ax1.set_ylabel("Fidelity")
    ax1.set_ylim(0, 1)
    ax1.grid(True)
    ax1.legend()

    # Bloch球坐标对比
    ax2 = fig.add_subplot(2, 2, 2)
    labels = ['X', 'Y', 'Z']
    x = np.arange(len(labels))
    width = 0.35
    ax2.bar(x - width / 2, theory_coords, width, label='理论值', color='#64c896')
    ax2.bar(x + width / 2, exp_coords, width, label='实验值', color='#c86496')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_title("Bloch球坐标对比")
    ax2.legend()
    ax2.grid(True)

    # Z基下测量统计
    ax3 = fig.add_subplot(2, 2, 3)
    counts = qstate.experimental_counts.get('Z', (0, 0))
    ax3.bar(['|0>', '|1>'], counts, color=['#409EFF', '#67C23A'])
    ax3.set_title("Z基测量结果统计")
    ax3.set_ylabel("次数")
    ax3.grid(True, axis='y')

    # 3D Bloch 球展示
    ax4 = fig.add_subplot(2, 2, 4, projection='3d')
    u = np.linspace(0, 2 * np.pi, 100)
    v = np.linspace(0, np.pi, 100)
    x_sphere = np.outer(np.cos(u), np.sin(v))
    y_sphere = np.outer(np.sin(u), np.sin(v))
    z_sphere = np.outer(np.ones(np.size(u)), np.cos(v))
    ax4.plot_surface(x_sphere, y_sphere, z_sphere, color='lightgray', alpha=0.3, edgecolor='gray', linewidth=0.2,
                     zorder=0)

    # 绘制坐标轴
    ax4.plot([-1.2, 1.2], [0, 0], [0, 0], color='black', linewidth=1, linestyle='--')
    ax4.plot([0, 0], [-1.2, 1.2], [0, 0], color='black', linewidth=1, linestyle='--')
    ax4.plot([0, 0], [0, 0], [-1.2, 1.2], color='black', linewidth=1, linestyle='--')
    ax4.text(1.1, 0, 0, 'X', color='black')
    ax4.text(0, 1.1, 0, 'Y', color='black')
    ax4.text(0, 0, 1.1, 'Z', color='black')

    # 绘制理论和实验向量
    ax4.quiver(0, 0, 0, *theory_coords, color='#64c896', label='理论态', linewidth=3, arrow_length_ratio=0.1)
    ax4.quiver(0, 0, 0, *exp_coords, color='#c86496', label='实验态', linewidth=3, arrow_length_ratio=0.1)

    ax4.set_xlim([-1.2, 1.2])
    ax4.set_ylim([-1.2, 1.2])
    ax4.set_zlim([-1.2, 1.2])
    ax4.set_box_aspect([1, 1, 1])
    ax4.set_title("Bloch球三维向量")
    ax4.view_init(elev=20, azim=45)
    ax4.legend()

    plt.tight_layout()
    plt.show()


def run():
    global font, title_font
    pygame.init()
    matplotlib.use('TkAgg')
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    font = pygame.font.SysFont('simhei', 16)
    title_font = pygame.font.SysFont('simhei', 20, bold=True)
    pygame.display.set_caption("量子噪声模拟器")

    global current_noise, measuring, animating, anim_theory_pts, anim_exp_pts
    qstate = QuantumState()
    bloch = BlochSphere()
    sliders = [
        Slider(CONTROL_START, 120, "噪声强度", 0, 1, 0.2),
        Slider(CONTROL_START, 180, "测量次数", 10, 5000, 1000),
        Slider(CONTROL_START, 240, "极角 θ", 0, np.pi, np.pi / 4),
        Slider(CONTROL_START, 300, "方位角 φ", 0, 2 * np.pi, 0)
    ]

    def create_gate_callback(gate_matrix):
        def callback():
            qstate.apply_gate(gate_matrix)
            sliders[2].value, sliders[3].value = qstate.theta, qstate.phi

        return callback

    def toggle_animation():
        nonlocal_button = anim_button
        globals()['animating'] = not globals()['animating']
        if globals()['animating']:
            nonlocal_button.text = "停止动画"
        else:
            nonlocal_button.text = "动画演示"
            anim_theory_pts.clear()
            anim_exp_pts.clear()

    buttons = [
        Button(CONTROL_START, 360, 260, 40, "哈达玛门 (H)",
               create_gate_callback(np.array([[1, 1], [1, -1]], np.complex128) / np.sqrt(2))),
        Button(CONTROL_START, 410, 260, 40, "泡利 X 门",
               create_gate_callback(np.array([[0, 1], [1, 0]], np.complex128))),
        Button(CONTROL_START, 460, 260, 40, "泡利 Y 门",
               create_gate_callback(np.array([[0, -1j], [1j, 0]], np.complex128))),
        Button(CONTROL_START, 510, 260, 40, "泡利 Z 门",
               create_gate_callback(np.array([[1, 0], [0, -1]], np.complex128))),
        Button(CONTROL_START, 560, 260, 40, "重置量子态",
               lambda: [qstate.reset(), setattr(sliders[2], 'value', qstate.theta),
                        setattr(sliders[3], 'value', qstate.phi)]),
        Button(CONTROL_START, 610, 260, 40, "切换噪声类型",
               lambda: globals().update(current_noise=(current_noise + 1) % 3)),
        Button(CONTROL_START, 660, 260, 40, "开始测量", lambda: globals().update(measuring=True)),
        Button(CONTROL_START, 710, 260, 40, "生成图表", lambda: plot_analysis(qstate, sliders))
    ]

    anim_button = Button(CONTROL_START, 760, 260, 40, "动画演示", toggle_animation)
    buttons.append(anim_button)

    running = True
    clock = pygame.time.Clock()

    MAX_PTS = 200
    while running:
        screen.fill(COLORS['background'])
        pygame.draw.rect(screen, COLORS['panel'], (0, 0, PANEL_WIDTH, HEIGHT))

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            # Bloch 球拖动...
            if event.type == MOUSEBUTTONDOWN:
                if SPHERE_CENTER[0] - 250 < event.pos[0] < SPHERE_CENTER[0] + 250 and \
                        SPHERE_CENTER[1] - 250 < event.pos[1] < SPHERE_CENTER[1] + 250:
                    bloch.dragging = True
                    last_pos = event.pos
            elif event.type == MOUSEMOTION and getattr(bloch, 'dragging', False):
                dx, dy = event.pos[0] - last_pos[0], event.pos[1] - last_pos[1]
                bloch.cam_angle_y += dx * 0.005
                bloch.cam_angle_x -= dy * 0.005
                last_pos = event.pos
            elif event.type == MOUSEBUTTONUP:
                bloch.dragging = False

            # Slider & Button 事件
            for s in sliders:
                if event.type == MOUSEBUTTONDOWN:
                    s.grabbed = s.update(event.pos)
                elif event.type == MOUSEMOTION and s.grabbed:
                    s.update(event.pos)
                elif event.type == MOUSEBUTTONUP:
                    s.grabbed = False
            for b in buttons:
                b.handle_event(event)

        # 更新量子态
        qstate.theta, qstate.phi = sliders[2].value, sliders[3].value
        qstate.state = qstate.get_state_vector()
        qstate.theory_rho = np.outer(qstate.state, qstate.state.conj())

        # 单次测量逻辑
        if measuring:
            noise_param = sliders[0].value
            noise_type = list(NoiseManager.noise_types.values())[current_noise]
            shots = int(sliders[1].value)

            # 分别在 X, Y, Z 方向执行完整测量
            x_c = qstate.measure_in_basis('X', noise_param, noise_type, shots)
            y_c = qstate.measure_in_basis('Y', noise_param, noise_type, shots)
            z_c = qstate.measure_in_basis('Z', noise_param, noise_type, shots)

            # 计算期望值
            x_e = (x_c[0] - x_c[1]) / shots
            y_e = (y_c[0] - y_c[1]) / shots
            z_e = (z_c[0] - z_c[1]) / shots

            # 避免 Bloch 向量超出单位球
            vec = np.array([x_e, y_e, z_e])
            norm = np.linalg.norm(vec)
            if norm > 1.0:
                vec = vec / norm
            x_e, y_e, z_e = vec

            # 构造密度矩阵
            I = np.eye(2)
            X = np.array([[0, 1], [1, 0]], dtype=complex)
            Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
            Z = np.array([[1, 0], [0, -1]], dtype=complex)
            qstate.experimental_rho = 0.5 * (I + x_e * X + y_e * Y + z_e * Z)

            # 存储统计信息
            qstate.experimental_counts = {'X': x_c, 'Y': y_c, 'Z': z_c}
            qstate.fidelity_history = getattr(qstate, 'fidelity_history', []) + [qstate.get_fidelity()]
            measuring = False

        if animating:
            shots = int(sliders[1].value);
            per = max(1, shots // 3)
            # 理论3D向量
            tc = [qstate.measure_in_basis(b, 0.0, None, per) for b in ['X', 'Y', 'Z']]
            vec_t = np.array([(tc[0][0] - tc[0][1]) / per, (tc[1][0] - tc[1][1]) / per, (tc[2][0] - tc[2][1]) / per])
            if np.linalg.norm(vec_t): vec_t /= np.linalg.norm(vec_t)
            anim_theory_pts.append(vec_t)
            if len(anim_theory_pts) > MAX_PTS: anim_theory_pts.pop(0)
            # 实验3D向量
            nc = [qstate.measure_in_basis(b, sliders[0].value, list(NoiseManager.noise_types.values())[current_noise],
                                          per) for b in ['X', 'Y', 'Z']]
            vec_e = np.array([(nc[0][0] - nc[0][1]) / per, (nc[1][0] - nc[1][1]) / per, (nc[2][0] - nc[2][1]) / per])
            if np.linalg.norm(vec_e): vec_e /= np.linalg.norm(vec_e)
            anim_exp_pts.append(vec_e)
            if len(anim_exp_pts) > MAX_PTS: anim_exp_pts.pop(0)
            # 绘制球面与状态
        bloch.draw_wireframe(screen);
        bloch.draw_states(screen, qstate)
        # 实时投影动画点
        for vec in anim_theory_pts:
            pygame.draw.circle(screen, COLORS['theory'], bloch.project_3d_to_2d(vec), 4)
        for vec in anim_exp_pts:
            pygame.draw.circle(screen, COLORS['experiment'], bloch.project_3d_to_2d(vec), 4)

        # 绘制投影面板
        proj_size = 120
        proj_gap = 15
        proj_rects = [
            (pygame.Rect(WIDTH - proj_size * 2 - proj_gap - 20, 20, proj_size, proj_size), 'xy'),
            (pygame.Rect(WIDTH - proj_size - 20, 20, proj_size, proj_size), 'xz'),
            (pygame.Rect(WIDTH - proj_size * 2 - proj_gap - 20, proj_size + proj_gap + 20, proj_size, proj_size), 'yz')
        ]
        for rect, plane in proj_rects:
            bloch.draw_projection(screen, qstate, plane, rect)

        # 绘制控制面板
        title = title_font.render("量子噪声模拟系统", True, COLORS['text'])
        screen.blit(title, (CONTROL_START, 30))
        for s in sliders: s.draw(screen)
        for b in buttons: b.draw(screen)

        for slider in sliders:
            slider.draw(screen)
        for btn in buttons:
            btn.draw(screen)

        # 绘制统计信息
        theory_p0 = np.abs(qstate.state[0]) ** 2
        theory_p1 = np.abs(qstate.state[1]) ** 2

        # 实验概率基于Z基测量结果
        if qstate.experimental_counts['Z'][0] + qstate.experimental_counts['Z'][1] > 0:
            count0_z, count1_z = qstate.experimental_counts['Z']
            total_z = count0_z + count1_z
            exp_p0 = count0_z / total_z
            exp_p1 = count1_z / total_z
        else:
            exp_p0, exp_p1 = 0.0, 0.0

        stats = [
            f"当前噪声: {list(NoiseManager.noise_types.keys())[current_noise % 3]}",
            f"理论 |0>: {theory_p0:.2%}",
            f"理论 |1>: {theory_p1:.2%}",
            f"实验 |0>: {exp_p0:.2%}",
            f"实验 |1>: {exp_p1:.2%}",
            f"量子态参数:",
            f"θ = {qstate.theta:.2f} rad",
            f"φ = {qstate.phi:.2f} rad"
        ]
        stats_x = PANEL_WIDTH + 30
        stats_y = HEIGHT - 200
        for i, text in enumerate(stats):
            text_surf = font.render(text, True, COLORS['text'])
            screen.blit(text_surf, (stats_x, stats_y + i * 25))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()

if __name__ == "__main__":
    run()