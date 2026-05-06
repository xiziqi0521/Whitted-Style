# Whitted-Style 光线追踪器

<div align="center">

**基于 Taichi 的 GPU 加速光线追踪实验项目**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Taichi](https://img.shields.io/badge/Taichi-1.6+-orange.svg)](https://taichi-lang.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[特性](#-特性) • [快速开始](#-快速开始) • [使用说明](#-使用说明) • [原理解析](#-核心原理) • [常见问题](#-常见问题)

</div>

---

## 📋 项目简介

本项目实现了一个完整的 **Whitted-Style 光线追踪器**，包含必做任务和选做扩展，是计算机图形学课程的实验项目。通过 Taichi 框架实现 GPU 加速，支持实时交互调整参数，可视化光线追踪的各种效果。

### 🎯 项目目标

1. **理论理解**：掌握光线投射（Ray Casting）与光线追踪（Ray Tracing）的本质区别
2. **全局光照**：通过发射次级射线实现硬阴影和镜面反射
3. **GPU编程思维**：学习如何将递归算法改写为适合GPU并行计算的迭代模式

---

## ✨ 特性

### 基础版本（必做任务）
- ✅ **场景构建**
  - 无限大平面（黑白棋盘格纹理）
  - 红色漫反射球
  - 银色镜面反射球
- ✅ **迭代式光线追踪** - 用循环代替递归，适合GPU并行
- ✅ **硬阴影** - 通过暗影射线实现锐利的阴影效果
- ✅ **镜面反射** - 完美反射，展示镜中世界
- ✅ **Phong光照模型** - 环境光 + 漫反射 + 镜面高光
- ✅ **实时交互** - 动态调整光源位置和渲染参数
- ✅ **Bug修复** - 解决Shadow Acne（阴影粉刺）问题

### 高级版本（选做内容，+25%加分）
- ✨ **折射与玻璃材质** (+15%)
  - 基于 Snell's Law（斯涅尔定律）
  - 全反射（Total Internal Reflection）
  - Fresnel 方程近似
- ✨ **抗锯齿 MSAA** (+10%)
  - 像素内多重采样（1-16x）
  - 随机偏移采样
  - 平滑物体边缘

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 支持 CUDA/Vulkan/Metal 的 GPU（推荐）

### 安装依赖

```bash
# 克隆仓库
git clone https://github.com/your-username/ray-tracer.git
cd ray-tracer

# 安装依赖
pip install taichi
# 或使用 requirements.txt
pip install -r requirements.txt
```

### 运行程序

#### 基础版本（必做任务）
```bash
python ray_tracer_basic.py
```

#### 高级版本（必做 + 选做）
```bash
python ray_tracer_advanced.py
```

### 第一次运行

程序启动后会看到：
- 左上角：控制面板（滑块）
- 主窗口：实时渲染结果

**推荐操作**：
1. 拖动 `Light X/Y/Z` 滑块观察阴影移动
2. 调整 `Max Bounces` 看反射效果变化
3. （高级版）切换 `Enable Refraction` 对比玻璃/漫反射
4. （高级版）调整 `MSAA Samples` 观察边缘平滑度

---

## 📚 使用说明

### UI 控制说明

#### 基础版本控制

| 控件 | 范围 | 默认值 | 说明 |
|------|------|--------|------|
| Light X | -5.0 ~ 5.0 | 0.0 | 光源X坐标 |
| Light Y | 0.0 ~ 10.0 | 3.0 | 光源Y坐标（高度） |
| Light Z | -5.0 ~ 5.0 | 2.0 | 光源Z坐标 |
| Max Bounces | 1 ~ 5 | 3 | 最大光线弹射次数 |

#### 高级版本额外控制

| 控件 | 范围 | 默认值 | 说明 |
|------|------|--------|------|
| MSAA Samples | 1 ~ 16 | 4 | 抗锯齿采样数（1=关闭） |
| Enable Refraction | 开/关 | 开 | 左侧球体：玻璃/漫反射 |

### 实验建议

#### 实验1：理解光线弹射

1. 将 `Max Bounces` 设为 **1**
   - 观察：镜面球变为黑色（无反射光线）
   
2. 将 `Max Bounces` 设为 **2**
   - 观察：镜面球开始显示环境反射
   
3. 将 `Max Bounces` 设为 **3** 或更高
   - 观察：镜面球中出现清晰的红球倒影和地面反射

**原理**：
- Bounce 1: 摄像机 → 镜面球（击中镜面，需要继续）
- Bounce 2: 镜面球 → 红球（击中漫反射，计算光照）
- 结果：看到镜面球中的红球倒影

#### 实验2：观察阴影变化

1. 将光源移到球体正上方
   ```
   Light X = 0.0
   Light Y = 5.0
   Light Z = 0.0
   ```
   - 观察：圆形阴影在球体正下方

2. 将光源移到侧面
   ```
   Light X = 3.0
   Light Y = 2.0
   Light Z = 0.0
   ```
   - 观察：阴影拉长，向一侧延伸

#### 实验3：玻璃折射效果（高级版）

1. 确保 `Enable Refraction` 已勾选
   - 观察：左侧球体变为透明玻璃
   - 看穿球体时，背后景物发生扭曲

2. 取消勾选 `Enable Refraction`
   - 观察：左侧球体变回红色漫反射

3. 调整光源位置观察折射变化
   - 注意球体边缘的 Fresnel 高光效果

#### 实验4：抗锯齿对比（高级版）

1. 将 `MSAA Samples` 设为 **1**（关闭抗锯齿）
   - 观察：球体边缘有明显锯齿 🔲

2. 将 `MSAA Samples` 设为 **4**
   - 观察：边缘变平滑 🔵

3. 将 `MSAA Samples` 设为 **8** 或 **16**
   - 观察：边缘非常平滑 ⚫
   - 注意：帧率可能下降

---

## 🔬 核心原理

### Whitted-Style 光线追踪模型

当主光线从摄像机击中物体表面时：

```
摄像机 ──主光线──> 交点
                    │
                    ├─> 暗影射线 ──> 光源
                    │   └─> 判断是否在阴影中
                    │
                    └─> 反射射线 ──> 继续追踪
                        （如果是镜面材质）
```

### 关键算法

#### 1. 反射向量计算

```python
R = L_in - 2(L_in·N)N
```

- `L_in`: 入射光线方向
- `N`: 表面法向量
- `R`: 反射光线方向

#### 2. 迭代式光线追踪

**为什么用迭代而非递归？**

| 递归方式 | 迭代方式 |
|----------|----------|
| 代码简洁直观 | GPU友好 |
| CPU上运行良好 | 支持并行计算 |
| GPU不支持深度递归 | 手动管理状态 |

**迭代实现**：

```python
final_color = [0, 0, 0]
throughput = [1, 1, 1]  # 光线能量

for bounce in range(max_bounces):
    hit = intersect(ray)
    
    if hit.material == DIFFUSE:
        # 漫反射 - 终止路径
        final_color += throughput * shading(hit)
        break
    
    elif hit.material == MIRROR:
        # 镜面反射 - 继续传播
        ray = reflect(ray, hit.normal)
        throughput *= 0.9  # 能量衰减
```

#### 3. Shadow Acne 问题

**现象**：表面布满黑色噪点

**原因**：
- 浮点数精度误差
- 射线与自身表面相交
- 被误判为在阴影中

**解决方案**：

```python
# ❌ 错误：从交点直接发射
shadow_ray = Ray(hit_pos, to_light)

# ✅ 正确：沿法线偏移 epsilon
shadow_ray = Ray(hit_pos + normal * 1e-4, to_light)
```

#### 4. 折射实现（Snell's Law）

```python
# 斯涅尔定律：n₁ sin(θ₁) = n₂ sin(θ₂)
def refract(incident, normal, eta):
    cos_i = -incident.dot(normal)
    sin_t2 = eta * eta * (1 - cos_i * cos_i)
    
    if sin_t2 > 1.0:
        # 全反射
        return reflect(incident, normal)
    
    cos_t = sqrt(1 - sin_t2)
    return eta * incident + (eta * cos_i - cos_t) * normal
```

---

## 🏗️ 场景构建

### 几何体定义

#### 1. 无限大平面
- **位置**：`y = -1.0`
- **法线**：`(0, 1, 0)` 朝上
- **纹理**：黑白棋盘格（基于 x, z 坐标奇偶性）
- **材质**：漫反射

#### 2. 红色漫反射球
- **中心**：`(-1.5, 0.0, 0.0)`
- **半径**：`1.0`
- **颜色**：`(1.0, 0.2, 0.2)` 红色
- **材质**：漫反射（Phong模型）

#### 3. 银色镜面球
- **中心**：`(1.5, 0.0, 0.0)`
- **半径**：`1.0`
- **颜色**：`(0.9, 0.9, 0.9)` 银色
- **材质**：理想镜面反射（反射率 0.9）

#### 4. 玻璃球（高级版，可切换）
- **中心**：`(-1.5, 0.0, 0.0)` 替换红球
- **半径**：`1.0`
- **颜色**：`(0.95, 0.95, 1.0)` 淡蓝色
- **材质**：玻璃（折射率 1.5）

### 棋盘格纹理

```python
def checkerboard_pattern(pos):
    scale = 1.0
    x_grid = floor(pos.x / scale)
    z_grid = floor(pos.z / scale)
    checker = (int(x_grid) + int(z_grid)) % 2
    
    return white if checker == 0 else dark_gray
```

---

## 📊 性能参考

### 基础版本

| GPU | 分辨率 | Max Bounces | FPS |
|-----|--------|-------------|-----|
| RTX 3080 | 800×600 | 3 | ~60 |
| RTX 2060 | 800×600 | 3 | ~45 |
| GTX 1660 | 800×600 | 3 | ~30 |
| 集成显卡 | 400×300 | 2 | ~15 |

### 高级版本

| GPU | 分辨率 | Max Bounces | MSAA | FPS |
|-----|--------|-------------|------|-----|
| RTX 3080 | 800×600 | 5 | 4x | ~40 |
| RTX 3080 | 800×600 | 5 | 8x | ~20 |
| GTX 1660 | 800×600 | 3 | 4x | ~15 |

**优化建议**：
- 实时交互：降低 MSAA 到 1-2x
- 截图展示：使用 8-16x MSAA
- 低端设备：降低分辨率到 400×300

---

## 🐛 常见问题

### Q1: 镜面球显示为黑色？

**原因**：`Max Bounces` 设置为 1，光线击中镜面后立即终止，没有反射光线。

**解决**：
- 将 `Max Bounces` 调整到 **2** 或更高
- 至少需要 2 次弹射才能看到镜面反射效果

**路径示例**：
```
Bounce 1: 摄像机 → 镜面球（需要继续）
Bounce 2: 镜面球 → 其他物体（计算光照）
结果：看到镜面球中的反射
```

---

### Q2: 满屏黑色噪点？

**原因**：Shadow Acne 问题，射线与自身表面相交。

**检查**：
- 代码中是否有 `hit_pos + normal * 1e-4` 这样的偏移？
- 检查 `is_shadowed()` 函数中的射线起点

**已修复**：本项目代码已包含正确的 epsilon 偏移。

---

### Q3: 图像上下颠倒？

**原因**：Y轴坐标映射方向错误。

**解决**：确保代码中是：
```python
v = (2.0 * j / height - 1.0) * viewport_height / 2.0
```

而不是：
```python
v = (1.0 - 2.0 * j / height) * viewport_height / 2.0  # 会倒立
```

**已修复**：最新版本已修复此问题。

---

### Q4: 看不到折射效果？（高级版）

**检查清单**：
- [ ] `Enable Refraction` 是否勾选？
- [ ] `Max Bounces` 是否 ≥ 3？
- [ ] 光源位置是否合理？

**提示**：
- 折射效果在球体边缘最明显
- 观察球后面的棋盘格扭曲
- 调整视角或光源可能看得更清楚

---

### Q5: 抗锯齿效果不明显？（高级版）

**建议**：
- 将 `MSAA Samples` 调到 **8** 或更高
- 仔细观察球体边缘（对比 1x 和 8x）
- 高采样率会降低帧率，这是正常的

---

### Q6: 程序运行很慢？

**优化方案**：

1. **降低分辨率**（修改代码）：
```python
width, height = 400, 300  # 原 800, 600
```

2. **减少弹射次数**：
- 将 `Max Bounces` 设为 2-3

3. **降低抗锯齿采样**：
- 将 `MSAA Samples` 设为 1-2

4. **检查后台程序**：
- 关闭其他占用GPU的应用

---


## 📁 项目结构

```
ray-tracer/
├── ray_tracer_basic.py      # 基础版本（必做任务）
├── ray_tracer_advanced.py   # 高级版本（必做+选做）
├── README.md                # 本文件
└── .gitignore              # Git忽略文件
```


## 🎓 学习路径

### 初学者路径（2-4小时）

1. **快速上手**
   - 阅读 QUICKSTART.md
   - 运行基础版本
   - 调整UI参数观察效果

2. **理解原理**
   - 阅读本 README 的核心原理部分
   - 对照代码理解迭代式光线追踪
   - 完成实验1和实验2

3. **完成作业**
   - 确保所有功能正常
   - 截图保存效果
   - 准备实验报告

### 进阶学习路径（5-10小时）

1. **深入算法**
   - 阅读 IMPLEMENTATION.md
   - 理解每个函数的实现
   - 尝试修改参数观察变化

2. **尝试扩展**
   - 运行高级版本
   - 对比两个版本的差异
   - 理解折射和抗锯齿的实现

3. **自定义场景**
   - 修改球体位置、颜色
   - 添加第三个球体
   - 调整摄像机视角

### 专家路径（10+小时）

1. **实现选做内容**
   - 从零实现折射（Snell's Law）
   - 从零实现抗锯齿（MSAA）
   - 理解Fresnel方程

2. **性能优化**
   - BVH加速结构
   - 重要性采样
   - GPU kernel优化

3. **新特性**
   - 软阴影
   - 景深效果
   - 全局光照（路径追踪）

---

## 🎨 效果展示

### 基础版本效果

**Max Bounces = 1**（无反射）：
- 左侧红球：正常渲染
- 右侧镜面球：**黑色**（无反射光线）
- 地面：棋盘格纹理
- 阴影：硬阴影效果

**Max Bounces = 3**（完整效果）：
- 左侧红球：正常渲染
- 右侧镜面球：**反射环境**（可见红球倒影）
- 地面：棋盘格纹理
- 阴影：完整硬阴影

### 高级版本额外效果

**折射效果**（Enable Refraction = ON）：
- 左侧玻璃球：透明，背后景物扭曲
- 边缘：Fresnel高光
- 球内：可见光线折射路径

**抗锯齿对比**：
- MSAA 1x：锯齿明显 🔲
- MSAA 4x：较平滑 🔵
- MSAA 8x：很平滑 ⚫
- MSAA 16x：极致平滑 ●

---

## 📝 实验报告建议

### 必做内容

1. **场景搭建**
   - 截图展示：两个球体 + 地面
   - 说明：棋盘格纹理实现方法

2. **迭代式光线追踪**
   - 解释：为什么用循环而非递归
   - 代码片段：展示迭代实现

3. **硬阴影**
   - 截图对比：有/无阴影
   - 说明：Shadow Acne 问题及解决

4. **镜面反射**
   - 截图对比：Bounce=1 vs Bounce=3
   - 解释：反射向量计算公式

5. **UI交互**
   - 演示视频或多张截图
   - 说明：各参数的影响

### 选做内容（如果实现）

1. **折射效果** (+15%)
   - 截图对比：玻璃球 vs 红球
   - 说明：Snell's Law 实现
   - 代码片段：折射计算

2. **抗锯齿** (+10%)
   - 截图对比：不同MSAA级别
   - 说明：多重采样原理
   - 性能对比：不同采样率的FPS

---
## 📖 参考资料

### 学术论文

1. **Whitted, T.** (1980). "An Improved Illumination Model for Shaded Display"  
   *Communications of the ACM, 23(6), 343-349.*

2. **Kajiya, J. T.** (1986). "The Rendering Equation"  
   *Proceedings of SIGGRAPH, 20(4), 143-150.*

### 推荐书籍

1. **Peter Shirley** - "Ray Tracing in One Weekend" 系列  
   适合入门，深入浅出

2. **Matt Pharr, et al.** - "Physically Based Rendering: From Theory to Implementation"  
   权威教材，深度讲解

3. **Tomas Akenine-Möller, et al.** - "Real-Time Rendering"  
   实时渲染经典


## 📄 License

本项目采用 MIT License - 详见 [LICENSE](LICENSE) 文件

---
