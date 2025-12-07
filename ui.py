# -*- coding: utf-8 -*-
"""AI代码审查平台 - 主界面"""
import math
import datetime
import os
import hashlib
import hmac
import base64
import time
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm
import streamlit as st
from dotenv import load_dotenv
from matplotlib.ticker import MaxNLocator
from streamlit_cookies_manager import CookieManager

from biz.service.review_service import ReviewService

# 获取项目根目录（基于当前脚本文件的位置）
def get_project_root():
    """获取项目根目录的绝对路径"""
    current_file = Path(__file__).resolve()
    # ui.py 在项目根目录，所以直接返回其所在目录
    return current_file.parent

PROJECT_ROOT = get_project_root()

# 设置项目根目录为环境变量，供其他模块使用
os.environ['PROJECT_ROOT'] = str(PROJECT_ROOT)

# st.set_page_config() 必须在第一个 Streamlit 命令之前调用
st.set_page_config(layout="wide", page_title="AI代码审查平台", page_icon="🤖", initial_sidebar_state="expanded")

# 使用绝对路径加载 .env 文件
env_path = PROJECT_ROOT / "conf" / ".env"
load_dotenv(env_path)

DETAIL_PAGE_PATH = "/审查详情"
DETAIL_COLUMN_NAME = "详细信息"
HIDDEN_COLUMNS = ['id', 'review_result']
JS_INIT_DELAYS = [100, 500]
DETAIL_LINK_ICON = "📋"
NO_REVIEW_ICON = "⚠️"
NO_REVIEW_STYLE = "color: #cccccc; cursor: not-allowed; font-size: 1.2rem;"


def set_global_font():
    font_path = PROJECT_ROOT / "fonts" / "SourceHanSansCN-Regular.otf"
    if font_path.exists():
        try:
            fm.fontManager.addfont(str(font_path))
            mpl.rcParams["font.family"] = "Source Han Sans CN"
        except Exception as e:
            st.warning(f"字体加载失败：{e}")
    mpl.rcParams["axes.unicode_minus"] = False

# 在 st.set_page_config() 之后调用 set_global_font()
set_global_font()

DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin")
USER_CREDENTIALS = {DASHBOARD_USER: DASHBOARD_PASSWORD}
SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "fac8cf149bdd616c07c1a675c4571ccacc40d7f7fe16914cfe0f9f9d966bb773")

# CookieManager 延迟初始化，避免在模块级别触发 Streamlit 命令
_cookies = None

def get_cookies():
    """获取 CookieManager 实例（延迟初始化）"""
    global _cookies
    if _cookies is None:
        _cookies = CookieManager()
    return _cookies


def generate_token(username):
    timestamp = str(int(time.time()))
    message = f"{username}:{timestamp}"
    signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    return base64.b64encode(f"{message}:{base64.b64encode(signature).decode()}".encode()).decode()


def verify_token(token):
    try:
        decoded = base64.b64decode(token.encode()).decode()
        message, signature = decoded.rsplit(":", 1)
        username, timestamp = message.split(":", 1)
        expected_sig = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected_sig, base64.b64decode(signature)):
            return None
        if int(time.time()) - int(timestamp) > 30 * 24 * 60 * 60:
            return None
        return username
    except:
        return None


def check_login_status():
    cookies = get_cookies()
    if not cookies.ready():
        st.stop()
    if 'login_status' not in st.session_state:
        st.session_state['login_status'] = False
    auth_token = cookies.get('auth_token')
    if auth_token:
        username = verify_token(auth_token)
        if username and username in USER_CREDENTIALS:
            st.session_state['login_status'] = True
            st.session_state['username'] = username
            st.session_state['saved_username'] = username
    return st.session_state['login_status']


def set_login_status(username, remember):
    cookies = get_cookies()
    st.session_state['login_status'] = True
    st.session_state['username'] = username
    st.session_state['saved_username'] = username if remember else ''
    if remember:
        cookies['auth_token'] = generate_token(username)
    elif 'auth_token' in cookies:
        del cookies['auth_token']
    cookies.save()


def get_saved_credentials():
    cookies = get_cookies()
    auth_token = cookies.get('auth_token')
    if auth_token:
        username = verify_token(auth_token)
        if username:
            return username, ''
    return st.session_state.get('saved_username', ''), ''


def authenticate(username, password, remember_password=False):
    if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
        set_login_status(username, remember_password)
        return True
    return False


def format_timestamp(timestamp):
    if isinstance(timestamp, (int, float)):
        return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    return timestamp


def format_delta(row):
    if not math.isnan(row['additions']) and not math.isnan(row['deletions']):
        return f"+{int(row['additions'])}  -{int(row['deletions'])}"
    return ""


def get_data(service_func, authors=None, project_names=None, updated_at_gte=None, updated_at_lte=None, columns=None):
    df = service_func(authors=authors, project_names=project_names, 
                      updated_at_gte=updated_at_gte, updated_at_lte=updated_at_lte)
    if df.empty:
        return pd.DataFrame(columns=columns or [])
    if "updated_at" in df.columns:
        df["updated_at"] = df["updated_at"].apply(format_timestamp)
    if "additions" in df.columns and "deletions" in df.columns:
        df["delta"] = df.apply(format_delta, axis=1)
    else:
        df["delta"] = ""
    display_columns = columns.copy() if columns else []
    for hidden_col in HIDDEN_COLUMNS:
        if hidden_col in df.columns and hidden_col not in display_columns:
            display_columns.append(hidden_col)
    return df[[col for col in display_columns if col in df.columns]]


def _build_detail_urls(df, tab_type):
    urls = []
    for idx, row in df.iterrows():
        try:
            record_id = row.get('id')
            record_id = int(record_id) if record_id is not None and not pd.isna(record_id) else int(idx) if isinstance(idx, (int, float)) else idx
            review_result = row.get('review_result', '')
            has_review = review_result and not pd.isna(review_result) and review_result.strip() != ""
            urls.append(f"{DETAIL_PAGE_PATH}?id={record_id}&type={tab_type}" if has_review else "")
        except:
            urls.append("")
    return urls


def _render_detail_links_script():
    delays = ', '.join([f"setTimeout(initLinks, {d})" for d in JS_INIT_DELAYS])
    script = f"""<script>
    function initLinks() {{
        document.querySelectorAll('div[data-testid="stDataFrame"] a[href*="{DETAIL_PAGE_PATH}"]').forEach(link => {{
            link.setAttribute('target', '_blank');
            link.setAttribute('rel', 'noopener noreferrer');
            if (link.textContent.trim() !== '{DETAIL_LINK_ICON}') link.textContent = '{DETAIL_LINK_ICON}';
        }});
        document.querySelectorAll('div[data-testid="stDataFrame"] tbody tr').forEach(row => {{
            const cells = row.querySelectorAll('td');
            if (cells.length > 0) {{
                const lastCell = cells[cells.length - 1];
                const link = lastCell.querySelector('a');
                if (!link || !link.getAttribute('href') || !link.getAttribute('href').trim()) {{
                    lastCell.innerHTML = '<span style="{NO_REVIEW_STYLE}">{NO_REVIEW_ICON}</span>';
                }}
            }}
        }});
    }}
    initLinks();
    {delays};
    new MutationObserver(() => initLinks()).observe(document.body, {{ childList: true, subtree: true }});
    </script>"""
    st.markdown(script, unsafe_allow_html=True)


st.markdown("""<style>
#MainMenu,header,footer{visibility:hidden}
div.block-container{padding-top:0}
.main{background-color:#f0f2f6;padding-top:0}
.stButton>button{background-color:#4CAF50;color:white;border-radius:20px;padding:0.5rem 2rem;border:none;transition:all 0.3s ease}
.stButton>button:hover{background-color:#45a049;box-shadow:0 2px 5px rgba(0,0,0,0.2);color:#fff}
.stTextInput>div>div>input{border:1px solid #ccc;border-radius:4px;padding:0.5rem}
.stCheckbox>div>div>input{accent-color:#4CAF50}
.stDataFrame{border:1px solid #ddd;border-radius:4px;box-shadow:0 2px 4px rgba(0,0,0,0.05)}
.stMarkdown{font-size:18px}
.login-title{text-align:center;color:#2E4053;margin:0.5rem 0;font-size:2.2rem;font-weight:bold}
.login-container{background-color:white;border-radius:15px;box-shadow:0 4px 6px rgba(0,0,0,0.1);margin-top:0}
.platform-icon{font-size:3.5rem;margin-bottom:0.5rem;text-align:center}
</style>""", unsafe_allow_html=True)


def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container"><div class="platform-icon">🤖</div><h1 class="login-title">AI代码审查平台</h1>', unsafe_allow_html=True)
        if DASHBOARD_USER == "admin" and DASHBOARD_PASSWORD == "admin":
            st.warning("安全提示：检测到默认用户名和密码为 'admin'，存在安全风险！\n\n请立即修改：\n1. 打开 `.env` 文件\n2. 修改 `DASHBOARD_USER` 和 `DASHBOARD_PASSWORD` 变量\n3. 保存并重启应用")
            st.write(f"当前用户名: `{DASHBOARD_USER}`, 当前密码: `{DASHBOARD_PASSWORD}`")
        saved_username, saved_password = get_saved_credentials()
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("👤 用户名", value=saved_username)
            password = st.text_input("🔑 密码", type="password", value=saved_password)
            remember_password = st.checkbox("记住密码", value=bool(saved_username))
            if st.form_submit_button("登 录"):
                if authenticate(username, password, remember_password):
                    st.rerun()
                else:
                    st.error("用户名或密码错误")
        st.markdown('</div>', unsafe_allow_html=True)


def _create_bar_chart(df, x_col, y_col, colormap='tab20', use_mean=False):
    if df.empty:
        st.info("没有数据可供展示")
        return
    if use_mean:
        # 排除0分记录后再计算平均值
        df_filtered = df[df[y_col] != 0] if y_col in df.columns else df
        if df_filtered.empty:
            st.info("没有数据可供展示")
            return
        data = df_filtered.groupby(x_col)[y_col].mean().reset_index()
        data.columns = [x_col, y_col]
        y_values = data[y_col]
    else:
        data = df[x_col].value_counts().reset_index()
        data.columns = [x_col, 'count']
        y_values = data['count']
    colors = plt.colormaps[colormap].resampled(len(data))
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(data[x_col], y_values, color=[colors(i) for i in range(len(data))])
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.xticks(rotation=45, ha='right', fontsize=26)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def generate_project_count_chart(df):
    _create_bar_chart(df, 'project_name', 'count', 'tab20')


def generate_project_score_chart(df):
    _create_bar_chart(df, 'project_name', 'score', 'Accent', True)


def generate_author_count_chart(df):
    _create_bar_chart(df, 'author', 'count', 'Paired')


def generate_author_score_chart(df):
    _create_bar_chart(df, 'author', 'score', 'Pastel1', True)


def generate_author_code_line_chart(df):
    if df.empty or 'additions' not in df.columns or 'deletions' not in df.columns:
        st.warning("无法生成代码行数图表：缺少必要的数据列") if not df.empty else st.info("没有数据可供展示")
        return
    add_data = df.groupby('author')['additions'].sum().reset_index()
    del_data = df.groupby('author')['deletions'].sum().reset_index()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(add_data['author'], add_data['additions'], color=(0.7, 1, 0.7))
    ax.bar(del_data['author'], -del_data['deletions'], color=(1, 0.7, 0.7))
    plt.xticks(rotation=45, ha='right', fontsize=26)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def show_review_detail(review_result: str, record_id: int, record_type: str = "MR"):
    if not review_result or pd.isna(review_result) or review_result.strip() == "":
        st.info("该记录暂无review信息")
        return
    st.markdown("### 📋 AI代码审查结果\n---")
    st.markdown(review_result)


def logout():
    cookies = get_cookies()
    st.session_state['login_status'] = False
    st.session_state.pop('username', None)
    st.session_state.pop('saved_username', None)
    if 'auth_token' in cookies:
        del cookies['auth_token']
    cookies.save()
    st.rerun()


def main_page():
    col_title, _, col_logout = st.columns([7, 2, 1.2])
    with col_title:
        st.markdown("#### 📊 代码审查统计")
    with col_logout:
        if st.button("退出登录", key="logout_button", use_container_width=True):
            logout()

    current_date = datetime.date.today()
    start_date_default = current_date - datetime.timedelta(days=7)
    show_push_tab = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'
    push_tab, mr_tab = (st.tabs(["代码推送", "合并请求"]) if show_push_tab else (None, st.container()))

    def display_data(tab, service_func, columns, column_config):
        with tab:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                start_date = st.date_input("开始日期", start_date_default, key=f"{tab}_start_date")
            with col2:
                end_date = st.date_input("结束日期", current_date, key=f"{tab}_end_date")
            start_timestamp = int(datetime.datetime.combine(start_date, datetime.time.min).timestamp())
            end_timestamp = int(datetime.datetime.combine(end_date, datetime.time.max).timestamp())
            initial_df = pd.DataFrame(get_data(service_func, updated_at_gte=start_timestamp,
                                              updated_at_lte=end_timestamp, columns=columns))
            unique_authors = sorted(initial_df["author"].dropna().unique().tolist()) if not initial_df.empty else []
            unique_projects = sorted(initial_df["project_name"].dropna().unique().tolist()) if not initial_df.empty else []
            with col3:
                authors = st.multiselect("开发者", unique_authors, default=[], key=f"{tab}_authors")
            with col4:
                project_names = st.multiselect("项目名称", unique_projects, default=[], key=f"{tab}_projects")
            df = pd.DataFrame(get_data(service_func, authors=authors, project_names=project_names,
                                     updated_at_gte=start_timestamp, updated_at_lte=end_timestamp, columns=columns))
            display_columns = [col for col in columns if col not in HIDDEN_COLUMNS]
            available_display_columns = [col for col in display_columns if col in df.columns]
            display_df = df[available_display_columns].copy() if not df.empty else pd.DataFrame(columns=available_display_columns)
            if not df.empty and all(col in df.columns for col in HIDDEN_COLUMNS):
                display_df[DETAIL_COLUMN_NAME] = _build_detail_urls(df, tab)
                updated_column_config = column_config.copy()
                updated_column_config[DETAIL_COLUMN_NAME] = st.column_config.LinkColumn(
                    DETAIL_COLUMN_NAME, help="点击查看详情（新标签页打开）", width="small", display_text=DETAIL_LINK_ICON)
                st.dataframe(display_df, use_container_width=True, column_config=updated_column_config, hide_index=True)
                _render_detail_links_script()
            else:
                st.dataframe(display_df, use_container_width=True, column_config=column_config, hide_index=True)
            if not df.empty and 'score' in df.columns:
                df_non_zero = df[df['score'] != 0]
                avg_score = df_non_zero['score'].mean() if not df_non_zero.empty else 0.0
                avg_score_text = f"{avg_score:.2f}" if not df_non_zero.empty else "0.00"
            else:
                avg_score_text = "0.00"
            st.markdown(f"**总记录数:** {len(df)}，**平均得分:** {avg_score_text}" if not df.empty else "**总记录数:** 0，**平均得分:** 0.00")
            row1, row2, row3, row4 = st.columns(4)
            for col, title, func in [(row1, "项目提交统计", generate_project_count_chart),
                                     (row2, "项目平均得分", generate_project_score_chart),
                                     (row3, "开发者提交统计", generate_author_count_chart),
                                     (row4, "开发者平均得分", generate_author_score_chart)]:
                with col:
                    st.markdown(f"<div style='text-align: center; font-size: 20px;'><b>{title}</b></div>", unsafe_allow_html=True)
                    func(df)
            row5, _, _, _ = st.columns(4)
            with row5:
                st.markdown("<div style='text-align: center;'><b>人员代码变更行数</b></div>", unsafe_allow_html=True)
                generate_author_code_line_chart(df) if 'additions' in df.columns and 'deletions' in df.columns else st.info("无法显示代码行数图表：缺少必要的数据列")

    mr_columns = ["project_name", "author", "source_branch", "target_branch", "updated_at", "commit_messages", "delta", "score", "url", 'additions', 'deletions']
    mr_column_config = {
        "project_name": "项目名称", "author": "开发者", "source_branch": "源分支", "target_branch": "目标分支",
        "updated_at": "更新时间", "commit_messages": "提交信息",
        "score": st.column_config.ProgressColumn("得分", format="%f", min_value=0, max_value=100),
        "url": st.column_config.LinkColumn("详细信息", max_chars=100, display_text="查看详情"),
        "additions": None, "deletions": None,
    }
    display_data(mr_tab, ReviewService().get_mr_review_logs, mr_columns, mr_column_config)

    if show_push_tab:
        push_columns = ["project_name", "author", "branch", "updated_at", "commit_messages", "delta", "score", 'additions', 'deletions']
        push_column_config = {
            "project_name": "项目名称", "author": "开发者", "branch": "分支", "updated_at": "更新时间",
            "commit_messages": "提交信息",
            "score": st.column_config.ProgressColumn("得分", format="%f", min_value=0, max_value=100),
            "additions": None, "deletions": None,
        }
        display_data(push_tab, ReviewService().get_push_review_logs, push_columns, push_column_config)


if check_login_status():
    main_page()
else:
    login_page()
