"""
Whitted-Style 光线追踪器 - 高级版本
包含所有必做任务 + 选做内容：
1. 折射与玻璃材质 (+15%)
2. 抗锯齿 MSAA (+10%)
"""

import taichi as ti
import numpy as np

ti.init(arch=ti.gpu)

# ============================================
# 画布分辨率
# ============================================
width, height = 800, 600
pixels = ti.Vector.field(3, dtype=ti.f32, shape=(width, height))

# ============================================
# 摄像机参数
# ============================================
camera_pos = ti.Vector([0.0, 0.5, 5.0])
camera_dir = ti.Vector([0.0, 0.0, -1.0])
camera_up = ti.Vector([0.0, 1.0, 0.0])
fov = 60.0
aspect_ratio = width / height

# ============================================
# 场景参数（动态可调）
# ============================================
light_pos = ti.Vector.field(3, dtype=ti.f32, shape=())
max_bounces = ti.field(ti.i32, shape=())
samples_per_pixel = ti.field(ti.i32, shape=())  # 抗锯齿采样数
enable_refraction = ti.field(ti.i32, shape=())  # 是否启用折射

# 初始化参数
light_pos[None] = ti.Vector([0.0, 3.0, 2.0])
max_bounces[None] = 5  # 折射需要更多弹射次数
samples_per_pixel[None] = 4  # 默认4倍MSAA
enable_refraction[None] = 1  # 默认启用折射

# ============================================
# 材质类型定义
# ============================================
MATERIAL_DIFFUSE = 0   # 漫反射
MATERIAL_MIRROR = 1    # 镜面反射
MATERIAL_GLASS = 2     # 玻璃（折射）

# ============================================
# 场景几何体定义
# ============================================
# 球体1：玻璃球（启用折射时）或 红色漫反射球（禁用折射时）
sphere1_center = ti.Vector([-1.5, 0.0, 0.0])
sphere1_radius = 1.0
sphere1_color_diffuse = ti.Vector([1.0, 0.2, 0.2])  # 红色（漫反射模式）
sphere1_color_glass = ti.Vector([0.95, 0.95, 1.0])   # 淡蓝色（玻璃模式）

# 球体2：银色镜面球
sphere2_center = ti.Vector([1.5, 0.0, 0.0])
sphere2_radius = 1.0
sphere2_color = ti.Vector([0.9, 0.9, 0.9])  # 银色
sphere2_material = MATERIAL_MIRROR

# 地面平面：y = -1.0
ground_y = -1.0
ground_normal = ti.Vector([0.0, 1.0, 0.0])

# 物理常数
EPSILON = 1e-4
IOR_AIR = 1.0       # 空气折射率
IOR_GLASS = 1.5     # 玻璃折射率


# ============================================
# 随机数生成器（用于抗锯齿）
# ============================================
@ti.func
def random_float(seed):
    """简单的随机数生成器"""
    # 使用 Taichi 的随机数
    return ti.random(dtype=ti.f32)


# ============================================
# 核心函数：光线-球体相交测试
# ============================================
@ti.func
def ray_sphere_intersect(ray_origin, ray_dir, sphere_center, sphere_radius):
    """
    光线与球体相交测试
    返回: (是否相交, 交点距离, 交点位置, 法向量)
    """
    hit = False
    t = 1e10
    hit_pos = ti.Vector([0.0, 0.0, 0.0])
    normal = ti.Vector([0.0, 0.0, 0.0])
    
    oc = ray_origin - sphere_center
    a = ray_dir.dot(ray_dir)
    b = 2.0 * oc.dot(ray_dir)
    c = oc.dot(oc) - sphere_radius * sphere_radius
    discriminant = b * b - 4 * a * c
    
    if discriminant >= 0:
        sqrt_d = ti.sqrt(discriminant)
        t1 = (-b - sqrt_d) / (2.0 * a)
        t2 = (-b + sqrt_d) / (2.0 * a)
        
        # 选择最近的正交点
        if t1 > EPSILON:
            t = t1
        elif t2 > EPSILON:
            t = t2
        else:
            t = 1e10
            
        if t < 1e10:
            hit = True
            hit_pos = ray_origin + t * ray_dir
            normal = (hit_pos - sphere_center).normalized()
    
    return hit, t, hit_pos, normal


# ============================================
# 核心函数：光线-平面相交测试
# ============================================
@ti.func
def ray_plane_intersect(ray_origin, ray_dir, plane_y, plane_normal):
    """
    光线与平面相交测试
    返回: (是否相交, 交点距离, 交点位置, 法向量)
    """
    hit = False
    t = 1e10
    hit_pos = ti.Vector([0.0, 0.0, 0.0])
    normal = plane_normal
    
    denom = ray_dir.dot(plane_normal)
    if ti.abs(denom) > 1e-6:
        t = (plane_y - ray_origin.y) / ray_dir.y
        if t > EPSILON:
            hit = True
            hit_pos = ray_origin + t * ray_dir
    
    return hit, t, hit_pos, normal


# ============================================
# 纹理：棋盘格
# ============================================
@ti.func
def checkerboard_pattern(pos):
    """棋盘格纹理"""
    scale = 1.0
    x_int = ti.floor(pos.x / scale)
    z_int = ti.floor(pos.z / scale)
    checker = (int(x_int) + int(z_int)) % 2
    
    color = ti.Vector([0.0, 0.0, 0.0])
    if checker == 0:
        color = ti.Vector([0.9, 0.9, 0.9])
    else:
        color = ti.Vector([0.2, 0.2, 0.2])
    
    return color


# ============================================
# 场景求交：找到最近的交点
# ============================================
@ti.func
def trace_scene(ray_origin, ray_dir):
    """
    场景相交测试
    返回: (是否击中, 距离, 位置, 法向量, 颜色, 材质类型)
    """
    hit = False
    min_t = 1e10
    hit_pos = ti.Vector([0.0, 0.0, 0.0])
    hit_normal = ti.Vector([0.0, 1.0, 0.0])
    hit_color = ti.Vector([0.0, 0.0, 0.0])
    hit_material = MATERIAL_DIFFUSE
    
    # 球体1的材质根据设置动态切换
    sphere1_material = MATERIAL_GLASS if enable_refraction[None] == 1 else MATERIAL_DIFFUSE
    sphere1_color = sphere1_color_glass if enable_refraction[None] == 1 else sphere1_color_diffuse
    
    # 测试球体1（玻璃球或漫反射球）
    hit1, t1, pos1, normal1 = ray_sphere_intersect(ray_origin, ray_dir, 
                                                     sphere1_center, sphere1_radius)
    if hit1 and t1 < min_t:
        hit = True
        min_t = t1
        hit_pos = pos1
        hit_normal = normal1
        hit_color = sphere1_color
        hit_material = sphere1_material
    
    # 测试球体2（银色镜面球）
    hit2, t2, pos2, normal2 = ray_sphere_intersect(ray_origin, ray_dir,
                                                     sphere2_center, sphere2_radius)
    if hit2 and t2 < min_t:
        hit = True
        min_t = t2
        hit_pos = pos2
        hit_normal = normal2
        hit_color = sphere2_color
        hit_material = sphere2_material
    
    # 测试地面平面
    hit3, t3, pos3, normal3 = ray_plane_intersect(ray_origin, ray_dir,
                                                    ground_y, ground_normal)
    if hit3 and t3 < min_t:
        hit = True
        min_t = t3
        hit_pos = pos3
        hit_normal = normal3
        hit_color = checkerboard_pattern(pos3)
        hit_material = MATERIAL_DIFFUSE
    
    return hit, min_t, hit_pos, hit_normal, hit_color, hit_material


# ============================================
# 阴影测试
# ============================================
@ti.func
def is_shadowed(point, light_position):
    """阴影测试"""
    shadowed = False
    
    to_light = light_position - point
    light_distance = to_light.norm()
    light_dir = to_light.normalized()
    
    shadow_ray_origin = point + light_dir * EPSILON
    
    hit, t, _, _, _, _ = trace_scene(shadow_ray_origin, light_dir)
    
    if hit and t < light_distance:
        shadowed = True
    
    return shadowed


# ============================================
# Phong 光照模型
# ============================================
@ti.func
def phong_shading(point, normal, view_dir, color, light_position):
    """Phong 光照模型"""
    # 环境光
    ambient = ti.Vector([0.1, 0.1, 0.1])
    
    # 初始化最终颜色
    final_color = ambient * color
    
    # 检查是否在阴影中
    in_shadow = is_shadowed(point, light_position)
    
    # 如果不在阴影中，添加漫反射和镜面高光
    if not in_shadow:
        # 漫反射
        to_light = (light_position - point).normalized()
        diffuse_intensity = ti.max(0.0, normal.dot(to_light))
        diffuse = color * diffuse_intensity * 0.6
        
        # 镜面高光
        reflect_dir = reflect(-to_light, normal)
        spec_intensity = ti.pow(ti.max(0.0, view_dir.dot(reflect_dir)), 32.0)
        specular = ti.Vector([1.0, 1.0, 1.0]) * spec_intensity * 0.3
        
        final_color = ambient * color + diffuse + specular
    
    return final_color


# ============================================
# 反射向量计算
# ============================================
@ti.func
def reflect(incident, normal):
    """
    反射向量计算
    R = L_in - 2(L_in·N)N
    """
    return incident - 2.0 * incident.dot(normal) * normal


# ============================================
# 折射向量计算（Snell's Law）
# ============================================
@ti.func
def refract(incident, normal, eta):
    """
    折射向量计算（斯涅尔定律）
    
    参数:
        incident: 入射方向（指向表面）
        normal: 表面法线（指向外部）
        eta: 折射率比值 (n1/n2)
    
    返回:
        (是否发生折射, 折射方向)
        如果发生全反射，返回 (False, zero_vector)
    """
    cos_i = -incident.dot(normal)
    sin_t2 = eta * eta * (1.0 - cos_i * cos_i)
    
    refracted = ti.Vector([0.0, 0.0, 0.0])
    has_refraction = True
    
    if sin_t2 > 1.0:
        # 全反射（Total Internal Reflection）
        has_refraction = False
    else:
        cos_t = ti.sqrt(1.0 - sin_t2)
        refracted = eta * incident + (eta * cos_i - cos_t) * normal
    
    return has_refraction, refracted


# ============================================
# Fresnel 方程（Schlick 近似）
# ============================================
@ti.func
def fresnel_schlick(cos_theta, f0):
    """
    Fresnel 方程的 Schlick 近似
    计算反射率（剩余部分为折射率）
    
    参数:
        cos_theta: 入射角余弦
        f0: 垂直入射时的反射率
    """
    return f0 + (1.0 - f0) * ti.pow(1.0 - cos_theta, 5.0)


# ============================================
# 主渲染函数（迭代式光线追踪 + 抗锯齿）
# ============================================
@ti.kernel
def render():
    """
    主渲染函数
    包含：迭代式光线追踪 + MSAA抗锯齿
    """
    # 计算摄像机坐标系
    camera_right = camera_dir.cross(camera_up).normalized()
    camera_actual_up = camera_right.cross(camera_dir).normalized()
    
    fov_rad = fov * 3.14159265 / 180.0
    viewport_height = 2.0 * ti.tan(fov_rad / 2.0)
    viewport_width = viewport_height * aspect_ratio
    
    # 遍历每个像素
    for i, j in pixels:
        # ========================================
        # 抗锯齿：多重采样
        # ========================================
        pixel_color = ti.Vector([0.0, 0.0, 0.0])
        num_samples = samples_per_pixel[None]
        
        for sample in range(num_samples):
            # 在像素内随机偏移（抗锯齿）
            offset_x = 0.0
            offset_y = 0.0
            if num_samples > 1:
                offset_x = (random_float(i * width + j + sample) - 0.5)
                offset_y = (random_float(j * height + i + sample) - 0.5)
            
            # 计算采样点的归一化坐标
            u = (2.0 * (i + offset_x) / width - 1.0) * viewport_width / 2.0
            v = (2.0 * (j + offset_y) / height - 1.0) * viewport_height / 2.0
            
            # 计算主光线方向
            ray_dir = (camera_dir + u * camera_right + v * camera_actual_up).normalized()
            ray_origin = camera_pos
            
            # ========================================
            # 迭代式光线追踪
            # ========================================
            final_color = ti.Vector([0.0, 0.0, 0.0])
            throughput = ti.Vector([1.0, 1.0, 1.0])
            
            # 当前介质折射率（初始在空气中）
            current_ior = IOR_AIR
            
            for bounce in range(15):  # 玻璃需要更多弹射
                if bounce >= max_bounces[None]:
                    break
                
                # 场景相交测试
                hit, t, hit_pos, hit_normal, hit_color, hit_material = trace_scene(ray_origin, ray_dir)
                
                if not hit:
                    # 背景色
                    bg_color = ti.Vector([0.5, 0.7, 1.0])
                    final_color += throughput * bg_color * 0.3
                    break
                
                # ========================================
                # 材质分支
                # ========================================
                if hit_material == MATERIAL_DIFFUSE:
                    # 漫反射 - 终止
                    shaded_color = phong_shading(hit_pos, hit_normal, -ray_dir, 
                                                hit_color, light_pos[None])
                    final_color += throughput * shaded_color
                    break
                
                elif hit_material == MATERIAL_MIRROR:
                    # 镜面反射 - 继续
                    reflect_dir = reflect(ray_dir, hit_normal)
                    ray_origin = hit_pos + hit_normal * EPSILON
                    ray_dir = reflect_dir
                    throughput *= hit_color * 0.9
                
                elif hit_material == MATERIAL_GLASS:
                    # ========================================
                    # 玻璃材质：折射 + 反射（Fresnel）
                    # ========================================
                    
                    # 判断是否从内部射出
                    cos_i = -ray_dir.dot(hit_normal)
                    outward_normal = hit_normal
                    eta = IOR_AIR / IOR_GLASS
                    
                    if cos_i < 0:
                        # 从内部射出
                        outward_normal = -hit_normal
                        cos_i = -cos_i
                        eta = IOR_GLASS / IOR_AIR
                    
                    # 计算 Fresnel 反射率
                    f0 = ((IOR_GLASS - IOR_AIR) / (IOR_GLASS + IOR_AIR)) ** 2
                    fresnel = fresnel_schlick(ti.abs(cos_i), f0)
                    
                    # 尝试折射
                    has_refraction, refract_dir = refract(ray_dir, outward_normal, eta)
                    
                    if has_refraction:
                        # 发生折射（简化：只追踪折射光线）
                        # 实际应该同时追踪反射和折射，这里简化处理
                        if fresnel < 0.5:  # 折射为主
                            ray_origin = hit_pos - outward_normal * EPSILON
                            ray_dir = refract_dir
                            throughput *= hit_color * (1.0 - fresnel)
                        else:  # 反射为主
                            reflect_dir = reflect(ray_dir, outward_normal)
                            ray_origin = hit_pos + outward_normal * EPSILON
                            ray_dir = reflect_dir
                            throughput *= hit_color * fresnel
                    else:
                        # 全反射
                        reflect_dir = reflect(ray_dir, outward_normal)
                        ray_origin = hit_pos + outward_normal * EPSILON
                        ray_dir = reflect_dir
                        throughput *= hit_color * 0.95
            
            pixel_color += final_color
        
        # ========================================
        # 平均所有采样
        # ========================================
        pixels[i, j] = pixel_color / num_samples


# ============================================
# 主函数 - UI 交互
# ============================================
def main():
    """
    主函数 - 创建交互窗口和控制面板
    """
    window = ti.ui.Window("Ray Tracer - Advanced (Refraction + MSAA)", (width, height))
    canvas = window.get_canvas()
    gui = window.get_gui()
    
    # UI 参数
    light_x = light_pos[None].x
    light_y = light_pos[None].y
    light_z = light_pos[None].z
    bounces = max_bounces[None]
    samples = samples_per_pixel[None]
    refraction_enabled = bool(enable_refraction[None])
    
    print("=" * 60)
    print("Whitted-Style 光线追踪器 - 高级版本")
    print("=" * 60)
    print("功能：")
    print("  ✓ 迭代式光线追踪")
    print("  ✓ 硬阴影")
    print("  ✓ 镜面反射")
    print("  ✓ 折射（玻璃材质）+15%")
    print("  ✓ 抗锯齿 MSAA +10%")
    print("=" * 60)
    print("控制说明：")
    print("  - Light X/Y/Z: 调整光源位置")
    print("  - Max Bounces: 弹射次数（1-8）")
    print("  - MSAA Samples: 抗锯齿采样数（1-16）")
    print("  - Enable Refraction: 开关折射效果")
    print("=" * 60)
    
    while window.running:
        # ========================================
        # UI 控制面板
        # ========================================
        with gui.sub_window("Controls", 0.02, 0.02, 0.32, 0.45):
            gui.text("=== Light Position ===")
            light_x = gui.slider_float("Light X", light_x, -5.0, 5.0)
            light_y = gui.slider_float("Light Y", light_y, 0.0, 10.0)
            light_z = gui.slider_float("Light Z", light_z, -5.0, 5.0)
            
            gui.text("")
            gui.text("=== Rendering ===")
            bounces = gui.slider_int("Max Bounces", bounces, 1, 8)
            
            gui.text("")
            gui.text("=== Anti-Aliasing ===")
            samples = gui.slider_int("MSAA Samples", samples, 1, 16)
            if samples == 1:
                gui.text("(No AA)")
            else:
                gui.text(f"({samples}x MSAA)")
            
            gui.text("")
            gui.text("=== Glass Material ===")
            refraction_enabled = gui.checkbox("Enable Refraction", refraction_enabled)
            
            gui.text("")
            gui.text("=== Info ===")
            if refraction_enabled:
                gui.text("Left: Glass sphere")
            else:
                gui.text("Left: Red diffuse")
            gui.text("Right: Mirror sphere")
            
            gui.text("")
            if samples > 4:
                gui.text("Warning: High samples")
                gui.text("may reduce FPS")
        
        # 更新参数
        light_pos[None] = ti.Vector([light_x, light_y, light_z])
        max_bounces[None] = bounces
        samples_per_pixel[None] = samples
        enable_refraction[None] = 1 if refraction_enabled else 0
        
        # 渲染
        render()
        
        # 显示
        canvas.set_image(pixels)
        window.show()


if __name__ == "__main__":
    main()
