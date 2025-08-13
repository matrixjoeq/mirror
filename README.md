# 多策略系统分析 v3.0

一个企业级的多策略交易管理和分析平台，支持动态策略管理、精确财务计算、数据审计跟踪和专业级策略分析。

## 📖 项目文档

完整的项目文档已迁移到 `doc/` 目录，请参考：

- **[📋 项目说明](doc/README.md)** - 完整的项目介绍、安装指南和使用说明
- **[📈 开发进度](doc/PROGRESS.md)** - 详细的功能实现进度和开发历程
- **[📝 需求文档](doc/REQUIREMENTS.md)** - 详细的功能需求规格说明书
- **[🧪 测试文档](doc/TESTING.md)** - 完整的测试套件使用指南

## 🚀 快速开始

### 一键启动（建议先激活 venv）

```bash
# Windows（激活虚拟环境）
.\\venv\\Scripts\\activate

# macOS/Linux（激活虚拟环境）
source venv/bin/activate

# 启动
./start.sh   # macOS/Linux
start.bat    # Windows
```

### 手动启动

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 安装依赖（首次运行）
python3 -m pip install -r requirements.txt

# 3. 启动应用
python3 app.py
```

### 访问应用

启动后访问：http://127.0.0.1:8383

## 📁 项目结构

```
mirror/
├── app.py                    # 主应用程序
├── requirements.txt          # Python依赖
├── start.sh / start.bat      # 启动脚本
├── run_tests.py             # 测试运行脚本
├── doc/                     # 📖 项目文档
│   ├── README.md           # 详细项目说明
│   ├── PROGRESS.md         # 开发进度记录
│   ├── REQUIREMENTS.md     # 需求规格说明
│   └── TESTING.md          # 测试指南
├── database/               # 💾 数据库文件
│   └── trading_tracker.db  # SQLite数据库
├── templates/              # 🎨 HTML模板
├── static/                 # 🎯 静态资源
├── tests/                  # 🧪 测试套件
├── venv/                   # 🐍 Python虚拟环境
```

## 🎯 核心特性

- **🏆 动态策略管理** - 完全自定义的策略创建和标签系统
- **💰 精确财务计算** - 考虑交易费用的准确盈亏计算
- **📝 完整交易记录** - 买入理由、卖出理由、交易日志
- **🔒 企业级数据保护** - 软删除、修改审计、数据恢复
- **🏆 专业策略评分** - 三维评分模型和可视化分析
- **📊 多维度分析** - 按策略、标的、时间的灵活分析

## 🧪 运行测试

```bash
# Windows
.\\venv\\Scripts\\activate
# macOS/Linux
source venv/bin/activate

# 运行所有测试
python3 run_tests.py all

# 运行特定类型测试
python3 run_tests.py unit        # 单元测试
python3 run_tests.py functional  # 功能测试
python3 run_tests.py integration # 集成测试
python3 run_tests.py performance # 性能测试（discover 收集，阈值50%）
```

## ⚠️ 注意事项

1. **数据安全**: 定期备份 `database/trading_tracker.db` 文件
2. **端口要求**: 确保8383端口未被占用
3. **虚拟环境**: 始终在venv环境中运行程序
4. **浏览器兼容**: 推荐使用现代浏览器(Chrome/Firefox/Safari)

## 🎉 系统状态

- ✅ **核心功能**: 100% 完成
- ✅ **文档完整**: 100% 完成
- ✅ **测试覆盖（阶段性）**:
  - 单元测试: 行覆盖率 92.7%/分支 92.4%
  - 功能测试: 行覆盖率 82.8%/分支 78.8%
  - 集成测试: 行覆盖率 74.0%/分支 69.5%
- 性能测试: TOTAL ≥ 50%（当前约 53%，已达标）
- ✅ **整体质量**: 企业级标准

---

**多策略系统分析 v2.0 - 您的专业交易管理伙伴！** 🚀

*详细信息请参考 [doc/README.md](doc/README.md)*