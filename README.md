Wallet Firewall – How to Run

Note: The .venv/ directory and local database files are intentionally excluded from version control.
Please create your own virtual environment and install dependencies using the provided requirements.txt.

Dataset Note

The file data/elliptic_txs_features.csv is not included in this repository due to GitHub file size limits.

Please download the Elliptic Bitcoin Dataset separately and place the CSV file under the data/ directory.

Required file:

data/elliptic_txs_features.csv

Project Overview | 项目简介

Wallet Firewall is a local full-stack prototype for wallet risk analysis and monitoring.

It consists of:

Admin Dashboard: Streamlit (Frontend, Port 8501)

Backend API: FastAPI + Uvicorn (Port 8000)

Data Layer: Local CSV / SQLite demo data

Wallet Firewall 是一个本地运行的钱包风险分析与监控原型系统，采用前后端分离架构，适用于课程设计、系统架构演示与安全研究实验。

System Requirements | 环境要求

OS: Windows 10 / 11

Python: 3.11.9（必须）

Package Manager: pip

Browser: Chrome / Edge

⚠️ Python 3.13 / 3.14 不支持（pandas / 编译问题）

Project Structure | 项目结构说明

wallet-firewall-main
├── admin_dashboard/ Streamlit 管理端
│ ├── app_admin.py
│ ├── pages/
│ └── requirements.txt
│
├── backend/ FastAPI 后端
│ ├── app/
│ │ ├── main.py
│ │ ├── models/
│ │ │ └── xgboost_aml_model.pkl
│ │ └── schemas.py
│ └── requirements.txt
│
├── data/ 本地数据
│ ├── elliptic_txs_features.csv
│ ├── elliptic_txs_edgelist.csv
│ ├── elliptic_txs_classes.csv
│ └── app.db
│
├── make_sample.py 测试样本生成脚本
├── .venv/ 本地虚拟环境（不提交）
├── .gitignore
└── README.md

Step 1 – Create Virtual Environment | 创建虚拟环境

在项目根目录执行：

py -3.11 -m venv .venv

激活虚拟环境：

..venv\Scripts\Activate.ps1

验证 Python 版本：

python --version

期望输出：

Python 3.11.x

Step 2 – Upgrade Build Tools | 升级构建工具

python -m pip install --upgrade pip setuptools wheel

Step 3 – Install Dependencies | 安装依赖
Admin Dashboard 依赖

pip install -r admin_dashboard\requirements.txt

Backend 依赖

pip install -r backend\requirements.txt

Step 4 – Start Backend (FastAPI) | 启动后端服务

打开一个新的终端（保持 .venv 已激活）：

python -m uvicorn backend.app.main:app --reload --port 8000

成功后你会看到：

Uvicorn running on http://127.0.0.1:8000

Application startup complete.

可选健康检查：

http://127.0.0.1:8000/health

Step 5 – Generate AML Test Sample | 生成模型测试样本（重要）

本项目的 AML 模型 严格依赖训练时的特征维度（165 维）。

为避免常见的维度错误，请使用项目自带脚本生成测试样本。

前置条件

确认以下文件存在：

backend/app/models/xgboost_aml_model.pkl

data/elliptic_txs_features.csv

运行脚本

在项目根目录执行：

python make_sample.py

脚本将自动：

读取模型的 n_features_in_

从 Elliptic BTC 数据集中提取数值特征

自动对齐特征维度（补零 / 截断）

输出可直接用于 API 的 JSON

终端期望输出类似：

len(features) = 165
{"features": [ ... 165 values ... ]}

Step 6 – Test AML Prediction API | 测试 AML 风险预测接口

打开浏览器：

http://127.0.0.1:8000/docs

进入接口：

POST /risk/predict

将 make_sample.py 输出的 JSON 粘贴到请求体中并执行。

Expected Response | 期望返回

This guarantees:
No feature length mismatch
No 400 / 500 errors
Correct alignment with trained model

prediction: licit 或 illicit
risk_score: 0.xxxx

示例含义：

licit：模型判断为正常交易

illicit：模型判断为高风险交易

Step 7 – Start Admin Dashboard (Streamlit) | 启动管理端

打开另一个终端（同样激活 .venv）：

streamlit run admin_dashboard\app_admin.py --server.port 8501

终端将显示：

Local URL: http://localhost:8501

在浏览器中打开即可。

Ports Summary | 端口说明

Admin Dashboard
http://localhost:8501

Backend API
http://127.0.0.1:8000

Swagger UI
http://127.0.0.1:8000/docs

Common Issues | 常见问题
1. ERR_CONNECTION_REFUSED on localhost:8501

原因：Streamlit 未启动

解决：

streamlit run admin_dashboard\app_admin.py

2. No module named uvicorn

原因：后端依赖未安装

解决：

pip install fastapi uvicorn

3. Backend shows DOWN in Admin page

原因：FastAPI 后端未运行

解决：

python -m uvicorn backend.app.main:app --reload --port 8000

4. Feature shape mismatch / features must be length XXX

原因：输入特征维度与模型不一致

解决：

不要手写 features

使用 make_sample.py 自动生成测试样本

Notes | 备注说明

本项目使用本地演示数据

部分分析与图表为原型或示意

重点在系统架构、接口设计与风险控制流程

Author / Usage

Designed for:

Coursework

System architecture demonstration

AML / blockchain security experiments

你已成功启动 FastAPI 并进入 Swagger UI 页面：

http://127.0.0.1:8000/docs