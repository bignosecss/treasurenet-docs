# 文档链接检查脚本

这个目录包含了用于检查文档链接完整性的Python脚本及其相关文件。

## 环境设置

1. **创建虚拟环境**

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
## Windows
venv\Scripts\activate
## macOS/Linux
source venv/bin/activate
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

## 使用方法

1. **激活虚拟环境**

```bash
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows
```

2. **运行脚本**

```bash
python doc_link_checker.py
```

默认会扫描项目根目录下的 `docs` 目录中的所有 `.md` 文件。

3. **配置忽略规则**

在 `docs` 目录下创建 `.ignore` 文件，每行一个规则：

```text
example.com
TODO
```

## 文件说明

- `doc_link_checker.py` - 主程序文件
- `requirements.txt` - Python依赖列表
- `README.md` - 使用说明文档

## 功能特点

1. **链接提取与分类**
   - 支持多种链接格式
   - 保留链接上下文信息
   - 提取文档标题

2. **链接验证**
   - 异步检查外部链接
   - 验证本地文件路径
   - 识别无效链接

3. **智能建议**
   - 检测潜在的缺失链接
   - 提供链接建议

## 注意事项

1. 请确保在虚拟环境中运行脚本
2. 外部链接检查使用异步请求，避免阻塞
3. 本地文件路径使用相对路径验证
4. 支持通过 `.ignore` 文件排除特定链接 