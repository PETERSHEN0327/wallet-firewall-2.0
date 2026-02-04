import streamlit as st
from utils.api import backend_base, healthcheck
from utils.state import init_state

# -------------------------------------------------
# Page config
# -------------------------------------------------
st.set_page_config(
    page_title="Wallet Firewall - Admin",
    layout="wide"
)

# -------------------------------------------------
# Init session state
# -------------------------------------------------
init_state()

# -------------------------------------------------
# Sidebar
# -------------------------------------------------
st.sidebar.title("app admin")

st.sidebar.markdown("### Backend Services")

# AML Backend (Risk Engine)
st.sidebar.markdown("**AML Backend**")
st.sidebar.code("http://127.0.0.1:8000", language="text")

# Virtual Wallet Backend
st.sidebar.markdown("**Virtual Wallet Service**")
st.sidebar.code("http://127.0.0.1:8002", language="text")

# Health check (still based on AML backend)
ok, msg = healthcheck()
if ok:
    st.sidebar.success("Services: OK")
else:
    st.sidebar.error("Service Error")
    st.sidebar.caption(msg)

# -------------------------------------------------
# Main content
# -------------------------------------------------
st.title("Wallet Firewall Admin Dashboard")

st.markdown("""
使用左侧菜单进入各功能页面：

- **Overview**：总体状态与关键指标  
- **Intercepts**：拦截记录列表（来自 Virtual Wallet Alerts）  
- **Transaction Detail**：单笔请求详情  
- **Wallets / Wallet Profile**：地址维度统计与画像  
- **Cases**：案例管理（本地示例）  
- **Graph Explorer**：关系图（本地示例）  
- **Reports**：导出报告（示例）  
- **Models Thresholds**：阈值配置（本地）  
- **Settings Audit**：黑白名单与审计  
""")

st.info(
    "📌 系统运行说明：\n\n"
    "本系统采用 **双后端架构**：\n\n"
    "1️⃣ **AML Backend（端口 8000）**\n"
    "   - 负责风险评估、模型推理与管理接口\n"
    "   - 启动命令：\n"
    "     `python -m uvicorn backend.app.main:app --reload --port 8000`\n\n"
    "2️⃣ **Virtual Wallet Service（端口 8002）**\n"
    "   - 负责交易执行、告警生成与钱包模拟\n"
    "   - 启动命令：\n"
    "     `python -m uvicorn app.main:app --reload --port 8002`\n\n"
    "请确保 **两个服务均已启动**，否则部分页面将无法显示数据。"
)
