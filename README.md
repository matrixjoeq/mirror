# 多策略系统分析 v3.0

企业级多策略交易管理与分析平台，采用三层架构与模块化服务，支持动态策略、精确盈亏计算（含费用）、数据审计与可视化分析。

## 📖 文档导航

- **[项目说明与使用](doc/README.md)**
- **[架构设计](doc/ARCHITECTURE.md)**
- **[需求规格](doc/REQUIREMENTS.md)**
- **[测试指南](doc/TESTING.md)**
- **[进度记录](doc/PROGRESS.md)**
- **[测试报告](doc/TESTING_REPORT.md)**

## 🚀 快速开始

### 一键启动（建议先激活 venv）

```bash
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

./start.sh   # macOS/Linux
start.bat    # Windows
```

### 手动启动

```bash
source venv/bin/activate
python3 -m pip install -r requirements.txt
python3 app.py
```

启动后访问：`http://127.0.0.1:8383`

## 📁 项目结构

```
mirror/
├── app.py                    # Flask 应用工厂与蓝图注册
├── config.py                 # 配置（dev/prod/testing）
├── services/                 # 业务层（Trading/Strategy/Analysis/DB/Admin）
├── routes/                   # 路由层（main/trading/strategy/analysis/api/admin）
├── models/                   # 数据模型
├── utils/                    # 工具与校验
├── doc/                      # 项目文档
├── tests/                    # 单元/功能/集成/性能测试
├── reports/                  # 覆盖率报告（自动生成）
├── start.sh | start.bat      # 启动脚本
├── run_tests.py              # 测试执行与覆盖校验
└── requirements.txt          # Python 依赖
```

## 🎯 核心特性

- 动态策略与标签管理（预置+自定义）
- 精确财务计算（WAC 口径；净利=毛利−卖出费−分摊买入费）
- 交易审计（修改历史、软删除/恢复/永久删）
- 多维策略分析（策略/标的/时间；评分与趋势）
- 管理工具：数据库一致性诊断与一键校准（`/admin/db/diagnose`）

## 🧪 运行测试

```bash
source venv/bin/activate
python3 run_tests.py all             # 全量
python3 run_tests.py unit            # 单元 ≥90%
python3 run_tests.py functional      # 功能 ≥80%
python3 run_tests.py integration     # 集成 ≥67%
python3 run_tests.py performance     # 性能 ≥50%
```

脚本还会执行：
- 模板/JS/CSS 静态检查（djlint/eslint/stylelint）
- MyPy 类型检查（不阻塞，通过结果写入 SUMMARY）

## ⚠️ 注意事项

- 定期备份 `database/trading_tracker.db`
- 确保 8383 端口空闲
- 建议始终在 `venv` 中运行
- 现代浏览器访问（Chrome/Firefox/Safari）

如需更详细说明，请参见 `doc/` 目录。