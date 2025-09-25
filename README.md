# Cloudflare IP 优选脚本

基于原始 JavaScript `bestIP` 功能改写的 Python 脚本，**智能遍历所有IP库**，直到找到指定数量的目标国家IP为止。

## 功能特点

- 🌍 **智能库遍历**: 自动遍历所有IP库（CF官方、CM整理、AS列表等），直到找到足够数量的目标国家IP
- 🎯 **精准数量控制**: 可指定需要的IP数量（默认10个），找到后立即停止，节省时间
- ⚡ **高效测试**: 支持自定义并发数，每个库内找到足够IP后自动跳转到下一个库
- 🏆 **延迟优选**: 自动按延迟排序，确保获得最优质的IP节点
- 💾 **自动保存**: 测试结果自动保存为txt文件，支持覆盖更新
- 🤖 **GitHub Actions**: 支持定时自动运行和手动触发

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本用法

```bash
# 获取10个中国地区的IP（默认参数）
python ip_optimizer.py

# 获取20个美国地区的IP
python ip_optimizer.py --country US --count 20

# 获取5个日本地区的IP，使用2053端口
python ip_optimizer.py --country JP --count 5 --port 2053

# 高并发快速获取
python ip_optimizer.py --country CN --count 15 --concurrent 64
```

### 完整参数说明

```bash
python ip_optimizer.py [选项]

选项:
  --country, -c     目标国家代码 (默认: CN)
  --count, -n       目标IP数量 (默认: 10)
  --port, -p        目标端口 (默认: 443)
  --max-ips, -m     每个库最大IP数量 (默认: 512)
  --concurrent      并发数 (默认: 32)
  --output, -o      输出文件名 (默认: nodes.txt)
```

### 工作流程

1. **按优先级遍历IP库**: 脚本会按以下顺序遍历IP库：
   - `official` - Cloudflare官方IP列表
   - `cm` - CM整理的IP列表
   - `as13335` - AS13335 Cloudflare全段IP
   - `as209242` - AS209242 Cloudflare非官方IP
   - `proxyip` - 反代IP列表
   - `as24429` - AS24429 Alibaba IP段
   - `as35916` - AS35916 IP段
   - `as199524` - AS199524 G-Core IP段

2. **智能停止机制**: 一旦找到指定数量的目标国家IP，立即停止遍历

3. **延迟优选**: 对所有找到的IP按延迟排序，确保最优质量

### 优势特点

- **⏱️ 高效率**: 不需要测试所有IP库，找到足够数量后立即停止
- **🎯 精准控制**: 可精确指定需要的IP数量，避免浪费时间
- **📈 智能优先级**: 优先使用质量更好的IP库（如官方库）
- **🔄 自动切换**: 如果某个库质量不佳，自动切换到下一个库
- **💡 资源节约**: 避免不必要的网络请求和计算资源消耗

## GitHub Actions 自动化

本项目支持通过 GitHub Actions 自动运行IP优选：

### 定时运行
- 每天北京时间早上8点自动运行
- 使用默认参数（CN国家，10个IP，443端口）

### 手动触发
1. 进入 GitHub 仓库的 Actions 页面
2. 选择 "Update Cloudflare IPs" 工作流
3. 点击 "Run workflow"
4. 可自定义参数：
   - 目标国家代码
   - 目标IP数量
   - 端口
   - 每库最大IP数量

### 输出文件
- 优选结果会自动提交到仓库的 `nodes.txt` 文件
- 手动触发时会创建 Release 并上传文件
- 工作流会生成详细的运行摘要

## 输出格式

生成的 `nodes.txt` 文件格式如下：

```
104.16.1.1:443#US 官方优选 45ms
172.64.1.1:443#US 官方优选 52ms
198.41.1.1:443#US 官方优选 58ms
```

每行包含：
- IP地址和端口
- 国家代码
- IP类型（官方优选/反代优选）
- 延迟时间

## 注意事项

1. **网络环境**: 建议在直连网络环境下运行，避免代理影响测试结果
2. **并发限制**: 过高的并发数可能导致网络拥塞，建议根据网络环境调整
3. **IP数量**: 默认最多测试512个IP，可根据需要调整
4. **超时设置**: 单个IP测试超时时间为5秒，失败会自动重试3次

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0
- 初始版本发布
- 支持多国家IP获取
- 支持多种IP源
- 集成GitHub Actions自动化
