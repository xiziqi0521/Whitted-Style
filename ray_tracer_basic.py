"""
Whitted-Style 光线追踪器 - 基础版本
包含所有必做任务：
1. 场景搭建（平面+红球+镜面球）
2. 迭代式光线追踪
3. 硬阴影
4. UI交互
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

# 初始化参数
light_pos[None] = ti.Vector([0.0, 3.0, 2.0])
max_bounces[None] = 3

# ============================================
# 材质类型定义
# ============================================
MATERIAL_DIFFUSE = 0  # 漫反射
MATERIAL_MIRROR = 1   # 镜面反射

# ============================================
# 场景几何体定义
# ============================================
# 球体1：红色漫反射球
sphere1_center = ti.Vector([-1.5, 0.0, 0.0])
sphere1_radius = 1.0
sphere1_color = ti.Vector([1.0, 0.2, 0.2])  # 红色
sphere1_material = MATERIAL_DIFFUSE

# 球体2：银色镜面球
sphere2_center = ti.Vector([1.5, 0.0, 0.0])
sphere2_radius = 1.0
sphere2_color = ti.Vector([0.9, 0.9, 0.9])  # 银色
sphere2_material = MATERIAL_MIRROR

# 地面平面：y = -1.0
ground_y = -1.0
ground_normal = ti.Vector([0.0, 1.0, 0.0])

# Shadow Acne 修复用的 epsilon
EPSILON = 1e-4


# ============================================
# 核心函数：光线-球体相交测试
# ============================================
@ti.func
def ray_sphere_intersect(ray_origin, ray_dir, sphere_center, sphere_radius):
    """
    光线与球体相交测试
    数学原理：
        球面方程：|P - C|² = r²
        光线方程：P = O + tD
        代入得：at² + bt + c = 0
    
    返回: (是否相交, 交点距离, 交点位置, 法向量)
    """
    hit = False
    t = 1e10
    hit_pos = ti.Vector([0.0, 0.0, 0.0])
    normal = ti.Vector([0.0, 0.0, 0.0])
    
    # 计算判别式
    oc = ray_origin - sphere_center
    a = ray_dir.dot(ray_dir)
    b = 2.0 * oc.dot(ray_dir)
    c = oc.dot(oc) - sphere_radius * sphere_radius
    discriminant = b * b - 4 * a * c
    
    if discriminant >= 0:
        sqrt_d = ti.sqrt(discriminant)
        t1 = (-b - sqrt_d) / (2.0 * a)
        t2 = (-b + sqrt_d) / (2.0 * a)
        
        # 选择最近的正交点（过滤自相交）
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
    平面方程：y = plane_y（水平平面）
    
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
    """
    棋盘格纹理
    通过 x 和 z 坐标的奇偶性判断颜色
    """
    scale = 1.0
    x_int = ti.floor(pos.x / scale)
    z_int = ti.floor(pos.z / scale)
    checker = (int(x_int) + int(z_int)) % 2
    
    color = ti.Vector([0.0, 0.0, 0.0])
    if checker == 0:
        color = ti.Vector([0.9, 0.9, 0.9])  # 白色
    else:
        color = ti.Vector([0.2, 0.2, 0.2])  # 深灰色
    
    return color


# ============================================
# 场景求交：找到最近的交点
# ============================================
@ti.func
def trace_scene(ray_origin, ray_dir):
    """
    场景相交测试，返回最近的交点信息
    返回: (是否击中, 距离, 位置, 法向量, 颜色, 材质类型)
    """
    hit = False
    min_t = 1e10
    hit_pos = ti.Vector([0.0, 0.0, 0.0])
    hit_normal = ti.Vector([0.0, 1.0, 0.0])
    hit_color = ti.Vector([0.0, 0.0, 0.0])
    hit_material = MATERIAL_DIFFUSE
    
    # 测试球体1（红色漫反射球）
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
        hit_color = checkerboard_pattern(pos3)  # 棋盘格纹理
        hit_material = MATERIAL_DIFFUSE
    
    return hit, min_t, hit_pos, hit_normal, hit_color, hit_material


# ============================================
# 阴影测试
# ============================================
@ti.func
def is_shadowed(point, light_position):
    """
    阴影测试：从点向光源发射暗影射线
    关键：起点需要沿光线方向偏移 epsilon，避免自相交（Shadow Acne）
    """
    shadowed = False
    
    # 计算指向光源的方向
    to_light = light_position - point
    light_distance = to_light.norm()
    light_dir = to_light.normalized()
    
    # 🔑 关键：从交点向外偏移，避免自相交（Shadow Acne Bug修复）
    shadow_ray_origin = point + light_dir * EPSILON
    
    # 检查阴影射线路径上是否有遮挡物
    hit, t, _, _, _, _ = trace_scene(shadow_ray_origin, light_dir)
    
    # 🔑 关键：只有在光源之前的遮挡才算阴影
    if hit and t < light_distance:
        shadowed = True
    
    return shadowed


# ============================================
# Phong 光照模型
# ============================================
@ti.func
def phong_shading(point, normal, view_dir, color, light_position):
    """
    Phong 光照模型
    包含：环境光 + 漫反射 + 镜面高光
    """
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
    计算反射向量
    公式：R = L_in - 2(L_in·N)N
    
    几何意义：
        N
        ↑
        |
    L_in ↘   ↗ R
    -----●-----
    """
    return incident - 2.0 * incident.dot(normal) * normal


# ============================================
# 主渲染函数（迭代式光线追踪）
# ============================================
@ti.kernel
def render():
    """
    主渲染函数 - 迭代式光线追踪
    使用 for 循环代替递归，适合 GPU 并行计算
    """
    # 计算摄像机坐标系
    camera_right = camera_dir.cross(camera_up).normalized()
    camera_actual_up = camera_right.cross(camera_dir).normalized()
    
    # 计算视口尺寸
    fov_rad = fov * 3.14159265 / 180.0
    viewport_height = 2.0 * ti.tan(fov_rad / 2.0)
    viewport_width = viewport_height * aspect_ratio
    
    # 遍历每个像素
    for i, j in pixels:
        # 像素归一化坐标 [-1, 1]
        u = (2.0 * i / width - 1.0) * viewport_width / 2.0
        v = (2.0 * j / height - 1.0) * viewport_height / 2.0
        
        # 计算主光线方向
        ray_dir = (camera_dir + u * camera_right + v * camera_actual_up).normalized()
        ray_origin = camera_pos
        
        # ========================================
        # 迭代式光线追踪（代替递归）
        # ========================================
        final_color = ti.Vector([0.0, 0.0, 0.0])
        throughput = ti.Vector([1.0, 1.0, 1.0])  # 光线吞吐量（能量衰减）
        
        # 最大弹射次数循环
        for bounce in range(10):  # 使用固定上限
            if bounce >= max_bounces[None]:
                break
            
            # 场景相交测试
            hit, t, hit_pos, hit_normal, hit_color, hit_material = trace_scene(ray_origin, ray_dir)
            
            if not hit:
                # 未击中任何物体，添加背景色
                bg_color = ti.Vector([0.5, 0.7, 1.0])  # 天空蓝
                final_color += throughput * bg_color * 0.3
                break
            
            # 材质分支处理
            if hit_material == MATERIAL_DIFFUSE:
                # ========================================
                # 漫反射材质 - 计算光照并终止路径
                # ========================================
                shaded_color = phong_shading(hit_pos, hit_normal, -ray_dir, 
                                            hit_color, light_pos[None])
                final_color += throughput * shaded_color
                break  # 终止光线传播
            
            elif hit_material == MATERIAL_MIRROR:
                # ========================================
                # 镜面反射材质 - 计算反射光线并继续
                # ========================================
                reflect_dir = reflect(ray_dir, hit_normal)
                
                # 🔑 更新光线起点（向外偏移避免自相交）
                ray_origin = hit_pos + hit_normal * EPSILON
                ray_dir = reflect_dir
                
                # 🔑 更新吞吐量（镜面反射率）
                reflectance = 0.9
                throughput *= hit_color * reflectance
                # 继续循环
        
        pixels[i, j] = final_color


# ============================================
# 主函数 - UI 交互
# ============================================
def main():
    """
    主函数 - 创建交互窗口和控制面板
    """
    window = ti.ui.Window("Ray Tracer - Basic Version", (width, height))
    canvas = window.get_canvas()
    gui = window.get_gui()
    
    # UI 参数
    light_x = light_pos[None].x
    light_y = light_pos[None].y
    light_z = light_pos[None].z
    bounces = max_bounces[None]
    
    print("=" * 60)
    print("Whitted-Style 光线追踪器 - 基础版本")
    print("=" * 60)
    print("功能：")
    print("  ✓ 迭代式光线追踪")
    print("  ✓ 硬阴影（Shadow Ray）")
    print("  ✓ 镜面反射")
    print("  ✓ 棋盘格纹理")
    print("=" * 60)
    print("控制说明：")
    print("  - Light X/Y/Z: 调整光源位置")
    print("  - Max Bounces: 调整最大弹射次数（1-5）")
    print("=" * 60)
    
    while window.running:
        # ========================================
        # UI 控制面板
        # ========================================
        with gui.sub_window("Controls", 0.02, 0.02, 0.3, 0.28):
            gui.text("Light Position:")
            light_x = gui.slider_float("Light X", light_x, -5.0, 5.0)
            light_y = gui.slider_float("Light Y", light_y, 0.0, 10.0)
            light_z = gui.slider_float("Light Z", light_z, -5.0, 5.0)
            
            gui.text("")
            gui.text("Rendering:")
            bounces = gui.slider_int("Max Bounces", bounces, 1, 5)
            
            gui.text("")
            gui.text("Tips:")
            gui.text("Bounces=1: No reflection")
            gui.text("Bounces=3: Full effect")
        
        # 更新参数
        light_pos[None] = ti.Vector([light_x, light_y, light_z])
        max_bounces[None] = bounces
        
        # 渲染
        render()
        
        # 显示
        canvas.set_image(pixels)
        window.show()


if __name__ == "__main__":
    main()
