Wallet Firewall – Full Project README
Local AML Transaction Simulation & Risk Control Prototype

Project Overview | 项目简介
Wallet Firewall is a local full-stack prototype for wallet transaction simulation, AML risk analysis, and decision enforcement.
The system demonstrates how machine-learning-based AML models and a rule-based decision engine can be integrated into a transaction workflow, supporting:
ALLOW – normal transaction
WARN / REQUIRE_CONFIRM – medium risk
BLOCK – high-risk or illicit transaction

Wallet Firewall 是一个本地运行的钱包交易与反洗钱（AML）风控原型系统，用于演示：
钱包创建与转账流程
AML 模型风险评分与预测
基于风险的交易决策（放行 / 警告 / 拦截）
风险告警（Alerts）与交易审计记录
管理端 Dashboard 实时监控
适用于 课程设计 / 系统架构展示 / 区块链与安全研究实验。

System Components | 系统组成
Component	Description
AML Backend	FastAPI 服务，提供 /risk/predict 模型推理接口
Virtual Wallet System	钱包业务系统（交易、告警、UI、API）
AML Engine	XGBoost AML 模型 + 决策适配层
Admin Dashboard	Streamlit 管理端，监控交易与拦截
Data Layer	本地 CSV 数据 + SQLite 演示数据库
System Requirements | 环境要求

OS: Windows 10 / 11
Python: 3.11.x（必须）
Package Manager: pip
Browser: Chrome / Edge
Python 3.13 / 3.14 不支持（pandas / 编译依赖不兼容）

Project Structure | 项目结构说明
wallet-firewall-main
├── backend/                     # AML 后端（模型推理服务）
│   └── app/
│       ├── main.py              # AML API（/risk/predict）
│       ├── schemas.py
│       └── models/
│           └── xgboost_aml_model.pkl
│
├── virtual_wallet/              # 钱包系统（业务层）
│   └── app/
│       ├── main.py              # Wallet API & UI
│       ├── aml_client.py        # AML HTTP 客户端（8000）
│       ├── aml_adapter.py       # 决策规则适配层
│       ├── generator.py         # 数据集生成
│       ├── db.py                # SQLite & session
│       ├── models.py            # Wallet / Transaction / Alert
│       └── ui/                  # 前端静态页面
│
├── admin_dashboard/             # 管理端 Dashboard（Streamlit）
│   ├── app_admin.py
│   ├── pages/
│   └── requirements.txt
│
├── data/
│   ├── elliptic_txs_features.csv
│   ├── elliptic_txs_edgelist.csv
│   ├── elliptic_txs_classes.csv
│   └── wallet.db
│
├── make_sample.py               # AML 测试样本生成脚本
├── .venv/                       # 本地虚拟环境（不提交）
├── .gitignore
└── README.md

Step 1 – Create Virtual Environment | 创建虚拟环境
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1

验证 Python 版本：
python --version
期望输出：
Python 3.11.x

Step 2 – Upgrade Build Tools | 升级构建工具
python -m pip install --upgrade pip setuptools wheel

Step 3 – Install Dependencies | 安装依赖
AML Backend（模型推理服务）
pip install -r backend/requirements.txt
Virtual Wallet（钱包系统）
pip install -r virtual_wallet/requirements.txt
Admin Dashboard（管理端）
pip install -r admin_dashboard/requirements.txt

Step 4 – Start AML Backend | 启动 AML 后端（端口 8000）
python -m uvicorn backend.app.main:app --reload --port 8000
访问：
AML Swagger UI
http://127.0.0.1:8000/docs

Step 5 – Start Virtual Wallet System | 启动钱包系统（端口 8002）
python -m uvicorn virtual_wallet.app.main:app --reload --port 8002
访问 Virtual Wallet：
Wallet UI（交易模拟界面）
http://127.0.0.1:8002
Virtual Wallet Swagger API Docs
http://127.0.0.1:8002/docs
（包含 /api/transactions/{tx_id}、/api/alerts/{tx_id} 等接口）

Step 6 – Start Admin Dashboard | 启动管理端（端口 8501）
streamlit run admin_dashboard/app_admin.py --server.port 8501
访问 Dashboard：
Admin Dashboard
http://127.0.0.1:8501

Step 7 – Generate AML Test Sample | 生成 AML 测试样本（重要）
python make_sample.py

说明：
自动对齐模型所需 165 维特征
避免 feature shape mismatch 错误
输出可直接用于 /risk/predict 的 JSON

Step 8 – Test AML Prediction API | 测试 AML 接口
访问：
http://127.0.0.1:8000/docs

接口：
POST /risk/predict
返回示例字段：
{
  "prediction": "licit",
  "risk_score": 0.23
}

AML Decision Logic | AML 决策规则说明
AML Result	System Decision
licit 且 risk_score < threshold	ALLOW
licit 且 risk_score ≥ threshold	WARN / REQUIRE_CONFIRM
illicit	BLOCK

所有 WARN / BLOCK 行为都会生成 Alert，并显示在 Admin Dashboard 中。

Ports Summary | 端口说明
Service	URL
AML Backend API	http://127.0.0.1:8000
AML Swagger UI	http://127.0.0.1:8000/docs
Virtual Wallet UI	http://127.0.0.1:8002
Virtual Wallet API Docs	http://127.0.0.1:8002/docs
Admin Dashboard	http://127.0.0.1:8501

Common Issues | 常见问题
Dashboard 显示 Backend DOWN
→ Virtual Wallet（8002）未启动
Feature shape mismatch
→ 未使用 make_sample.py
Python version error
→ 必须使用 Python 3.11.x

Notes | 备注说明
本项目为 教学 / 演示原型
重点在 系统架构、AML 决策流程与风险控制逻辑
并非生产级金融系统

Author / Usage
Designed for:
Coursework / FYP
System architecture demonstration
AML / blockchain security experiments