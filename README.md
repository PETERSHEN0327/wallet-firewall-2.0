Wallet Firewall – How to Run
Virtual Wallet Lab with Integrated AML Decision Engine

Note
The .venv/ directory and local database files are intentionally excluded from version control.
Please create your own virtual environment and install dependencies using the provided requirements.txt.

Dataset Note
The file below is not included in this repository due to GitHub file size limits:
data/elliptic_txs_features.csv

Please download the Elliptic Bitcoin Dataset separately and place the CSV file under the data/ directory.

Required file:
data/elliptic_txs_features.csv

Project Overview | 项目简介
Wallet Firewall is a local full-stack prototype for wallet transaction simulation, AML risk analysis, and decision enforcement.
The system demonstrates how AML models and rule-based engines can be integrated into a transaction workflow, including ALLOW / WARN / BLOCK decisions.

It consists of:
Virtual Wallet UI: Browser-based frontend (FastAPI static UI)
Backend API: FastAPI + Uvicorn
AML Engine: XGBoost-based AML model + decision adapter
Data Layer: Local CSV files + SQLite demo database

Wallet Firewall 是一个本地运行的钱包交易与反洗钱（AML）风控原型系统，用于演示：
钱包创建与转账流程
AML 风险评分与模型预测
基于风险的交易决策（放行 / 警告 / 拦截）
风险告警与交易审计记录
适用于 课程设计、系统架构展示、区块链与安全研究实验。

System Requirements | 环境要求
OS: Windows 10 / 11
Python: 3.11.x（必须）
Package Manager: pip
Browser: Chrome / Edge
⚠️ Python 3.13 / 3.14 不支持（pandas / 编译依赖不兼容）

Project Structure | 项目结构说明
wallet-firewall-main
├── backend/                     # AML 后端（模型推理服务）
│   └── app/
│       ├── main.py              # AML API（/risk/predict）
│       ├── models/
│       │   └── xgboost_aml_model.pkl
│       └── schemas.py
│
├── virtual_wallet/              # 钱包系统（业务层）
│   └── app/
│       ├── main.py              # Wallet API & UI
│       ├── aml_client.py        # AML HTTP 客户端
│       ├── aml_adapter.py       # AML 决策适配层
│       ├── generator.py         # 数据集生成
│       ├── db.py                # SQLite & session
│       ├── models.py            # Wallet / Transaction / Alert
│       └── ui/                  # 前端静态页面
│
├── data/
│   ├── elliptic_txs_features.csv
│   ├── elliptic_txs_edgelist.csv
│   ├── elliptic_txs_classes.csv
│   └── app.db
│
├── make_sample.py               # AML 测试样本生成脚本
├── .venv/                       # 本地虚拟环境（不提交）
├── .gitignore
└── README.md

Step 1 – Create Virtual Environment | 创建虚拟环境

在项目根目录执行：
py -3.11 -m venv .venv

激活虚拟环境：
.venv\Scripts\Activate.ps1


验证 Python 版本：
python --version

期望输出：
Python 3.11.x

Step 2 – Upgrade Build Tools | 升级构建工具
python -m pip install --upgrade pip setuptools wheel

Step 3 – Install Dependencies | 安装依赖
Backend（AML 模型服务）
pip install -r backend/requirements.txt

Virtual Wallet（钱包系统）
pip install -r virtual_wallet/requirements.txt

Step 4 – Start AML Backend (FastAPI) | 启动 AML 后端
打开一个终端（保持 .venv 已激活）：
python -m uvicorn backend.app.main:app --reload --port 8000


成功后你会看到：
Uvicorn running on http://127.0.0.1:8000
Application startup complete.

Swagger UI：
http://127.0.0.1:8000/docs

Step 5 – Start Virtual Wallet System | 启动钱包系统

打开 第二个终端（同样激活 .venv）：
python -m uvicorn virtual_wallet.app.main:app --reload --port 8002

访问 Wallet UI：
http://127.0.0.1:8002

Step 6 – Generate AML Test Sample | 生成 AML 测试样本（重要）
AML 模型 严格依赖训练时的特征维度（165 维）。
请勿手写 features。
前置条件
确认以下文件存在：
backend/app/models/xgboost_aml_model.pkl
data/elliptic_txs_features.csv

运行脚本
python make_sample.py


终端期望输出类似：
len(features) = 165
{"features": [ ... 165 values ... ]}

Step 7 – Test AML Prediction API | 测试 AML 接口
打开浏览器：
http://127.0.0.1:8000/docs

测试接口：
POST /risk/predict

请求体粘贴 make_sample.py 输出的 JSON。
Expected Response
{
  "prediction": "licit",
  "risk_score": 0.0
}


含义：
licit：模型判断为正常交易
illicit：模型判断为高风险交易
AML Decision Logic | AML 决策规则说明
Wallet 系统基于 AML 返回结果做 三态决策：
AML 结果	系统行为
prediction = licit 且 risk_score < threshold	ALLOW（写入交易）
prediction = licit 且 risk_score ≥ threshold	REQUIRE_CONFIRM / WARN
prediction = illicit	BLOCK（直接拦截）
所有高风险与中风险行为都会生成 Alert 记录，用于审计与监控。

Ports Summary | 端口说明
Service	URL
AML Backend API	http://127.0.0.1:8000
AML Swagger UI	http://127.0.0.1:8000/docs
Virtual Wallet UI	http://127.0.0.1:8002
Common Issues | 常见问题
1. Connection refused (8000 / 8002)
原因：对应服务未启动
解决：确认两个 Uvicorn 服务都在运行

2. Feature shape mismatch
原因：AML 输入维度不正确
解决：
不要手写 features
使用 make_sample.py

3. Python version error
原因：使用了 Python 3.13 / 3.14
解决：切换到 Python 3.11.x

Notes | 备注说明
本项目为 教学 / 演示原型
数据与规则为可解释性设计
重点在 系统架构、风控流程与决策逻辑
并非生产级金融系统

Author / Usage
Designed for:
Coursework / FYP
System architecture demonstration
AML / blockchain security experiments