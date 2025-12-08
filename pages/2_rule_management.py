# -*- coding: utf-8 -*-
"""AI代码审查规则管理页面"""
import datetime
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from biz.service.rule_service import RuleService

# 获取项目根目录
def get_project_root():
    """获取项目根目录的绝对路径"""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent

PROJECT_ROOT = get_project_root()
os.environ['PROJECT_ROOT'] = str(PROJECT_ROOT)

# 页面配置 - 必须在最开始
st.set_page_config(layout="wide", page_title="规则管理 - AI代码审查平台", page_icon="⚙️")

# 加载环境变量
env_path = PROJECT_ROOT / "conf" / ".env"
load_dotenv(env_path)

# 导入认证相关的配置和函数（不导入ui.py以避免set_page_config冲突）
import sys
import time
import hashlib
import hmac
import base64
sys.path.insert(0, str(PROJECT_ROOT))

from streamlit_cookies_manager import CookieManager

# 认证配置
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin")
USER_CREDENTIALS = {DASHBOARD_USER: DASHBOARD_PASSWORD}
SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "fac8cf149bdd616c07c1a675c4571ccacc40d7f7fe16914cfe0f9f9d966bb773")

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

def logout():
    cookies = get_cookies()
    st.session_state['login_status'] = False
    st.session_state.pop('username', None)
    st.session_state.pop('saved_username', None)
    if 'auth_token' in cookies:
        del cookies['auth_token']
    cookies.save()
    st.rerun()

# 样式
st.markdown("""<style>
#MainMenu,header,footer{visibility:hidden}
div.block-container{padding-top:0}
.main{background-color:#f0f2f6;padding-top:0}
.stButton>button{background-color:#4CAF50;color:white;border-radius:20px;padding:0.5rem 2rem;border:none;transition:all 0.3s ease}
.stButton>button:hover{background-color:#45a049;box-shadow:0 2px 5px rgba(0,0,0,0.2);color:#fff}
.stTextArea>div>div>textarea{font-family:monospace;font-size:14px}
</style>""", unsafe_allow_html=True)


def format_timestamp(timestamp):
    """格式化时间戳"""
    if isinstance(timestamp, (int, float)):
        return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    return timestamp


def show_confirmation_dialog():
    """显示二次确认对话框"""
    if 'show_confirm' not in st.session_state or not st.session_state.show_confirm:
        return
    
    if 'pending_update' not in st.session_state:
        return
    
    pending = st.session_state.pending_update
    
    # 使用对话框
    with st.container():
        st.markdown("---")
        st.warning("### ⚠️ 确认修改")
        st.markdown("""
        **重要提示：**
        - 此操作将立即生效，影响后续所有代码审查
        - 修改后的规则会立即应用到新的审查请求
        - 历史审查记录不受影响
        """)
        
        st.markdown(f"**规则:** {pending['rule_key']}")
        if pending.get('change_reason'):
            st.markdown(f"**修改原因:** {pending['change_reason']}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 确认保存", key="confirm_save", use_container_width=True):
                # 执行保存
                username = st.session_state.get('username', 'unknown')
                
                try:
                    # 验证Jinja2模板语法
                    from jinja2 import Template
                    try:
                        Template(pending['system_prompt'])
                        Template(pending['user_prompt'])
                    except Exception as e:
                        st.error(f"❌ 模板语法错误: {e}")
                        st.info("💡 提示：请检查Jinja2模板语法，确保 {{ }} 和 {% %} 标签正确闭合")
                        return
                    
                    success = RuleService.update_rule(
                        pending['rule_key'],
                        pending['system_prompt'],
                        pending['user_prompt'],
                        username,
                        pending.get('change_reason')
                    )
                    
                    if success:
                        st.success("✅ 规则更新成功！修改已立即生效。")
                        st.session_state.edit_mode = False
                        st.session_state.show_confirm = False
                        st.session_state.pop('pending_update', None)
                        # 延迟刷新，让用户看到成功消息
                        import time
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 规则更新失败，请查看日志获取详细错误信息")
                        st.info("💡 提示：编辑内容已保留，修复问题后可以重新保存")
                        
                except Exception as e:
                    st.error(f"❌ 保存失败: {str(e)}")
                    st.info("💡 提示：编辑内容已保留，请检查输入内容后重试")
        
        with col2:
            if st.button("❌ 取消", key="cancel_save", use_container_width=True):
                st.session_state.show_confirm = False
                st.rerun()


def rule_management_page():
    """规则管理页面主函数"""
    # 页面标题和导航
    col_title, _, col_logout = st.columns([7, 2, 1.2])
    with col_title:
        st.markdown("### ⚙️ AI审查规则管理")
    with col_logout:
        if st.button("退出登录", key="logout_button", use_container_width=True):
            logout()
    
    # 显示确认对话框（如果需要）
    show_confirmation_dialog()
    
    st.markdown("---")
    
    # 获取所有规则
    rules_df = RuleService.get_all_rules()
    
    if rules_df.empty:
        st.warning("暂无规则配置，系统将在首次使用时自动从YAML导入")
        return
    
    # 规则选择
    rule_keys = rules_df['rule_key'].tolist()
    selected_rule = st.selectbox(
        "选择要管理的规则",
        rule_keys,
        key="selected_rule"
    )
    
    if not selected_rule:
        return
    
    # 获取选中规则的详细信息
    try:
        rule_data = RuleService.get_rule(selected_rule)
    except Exception as e:
        st.error(f"加载规则失败: {e}")
        return
    
    # 显示规则基本信息
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**规则键名:** {rule_data.get('rule_key', 'N/A')}")
    with col2:
        updated_at = format_timestamp(rule_data.get('updated_at', 0))
        st.info(f"**最后修改时间:** {updated_at}")
    with col3:
        updated_by = rule_data.get('updated_by', 'N/A')
        st.info(f"**最后修改人:** {updated_by}")
    
    st.markdown("---")
    
    # 编辑模式切换
    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = False
    
    # 显示规则内容
    st.markdown("#### 📝 规则内容")
    
    if not st.session_state.edit_mode:
        # 查看模式
        st.markdown("**System Prompt:**")
        st.text_area(
            "System Prompt",
            value=rule_data.get('system_prompt', ''),
            height=300,
            key="system_prompt_view",
            disabled=True,
            label_visibility="collapsed"
        )
        
        st.markdown("**User Prompt:**")
        st.text_area(
            "User Prompt",
            value=rule_data.get('user_prompt', ''),
            height=200,
            key="user_prompt_view",
            disabled=True,
            label_visibility="collapsed"
        )
        
        if st.button("✏️ 编辑规则", key="edit_button"):
            st.session_state.edit_mode = True
            st.rerun()
    else:
        # 编辑模式
        with st.form("rule_edit_form"):
            st.markdown("**System Prompt:**")
            system_prompt = st.text_area(
                "System Prompt",
                value=rule_data.get('system_prompt', ''),
                height=300,
                key="system_prompt_edit",
                label_visibility="collapsed",
                help="支持Jinja2模板语法，如 {{ style }}"
            )
            
            st.markdown("**User Prompt:**")
            user_prompt = st.text_area(
                "User Prompt",
                value=rule_data.get('user_prompt', ''),
                height=200,
                key="user_prompt_edit",
                label_visibility="collapsed",
                help="支持Jinja2模板语法和变量占位符，如 {diffs_text}"
            )
            
            change_reason = st.text_input(
                "修改原因（可选）",
                key="change_reason",
                placeholder="请简要说明本次修改的原因..."
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit_button = st.form_submit_button("💾 保存修改", use_container_width=True)
            with col2:
                if st.form_submit_button("❌ 取消", use_container_width=True):
                    st.session_state.edit_mode = False
                    st.rerun()
            
            if submit_button:
                # 暂存编辑内容，等待二次确认
                st.session_state.pending_update = {
                    'rule_key': selected_rule,
                    'system_prompt': system_prompt,
                    'user_prompt': user_prompt,
                    'change_reason': change_reason
                }
                st.session_state.show_confirm = True
                st.rerun()
    
    # 历史记录区域
    st.markdown("---")
    st.markdown("#### 📜 修改历史")
    
    with st.expander("查看修改历史", expanded=False):
        history_df = RuleService.get_rule_history(selected_rule, limit=50)
        
        if history_df.empty:
            st.info("暂无修改历史记录")
        else:
            # 格式化时间戳
            if 'changed_at' in history_df.columns:
                history_df['changed_at'] = history_df['changed_at'].apply(format_timestamp)
            
            # 显示历史记录表格
            display_columns = ['id', 'change_type', 'changed_at', 'changed_by', 'change_reason']
            available_columns = [col for col in display_columns if col in history_df.columns]
            
            column_config = {
                'id': '记录ID',
                'change_type': '变更类型',
                'changed_at': '变更时间',
                'changed_by': '变更人',
                'change_reason': '变更原因'
            }
            
            st.dataframe(
                history_df[available_columns],
                use_container_width=True,
                column_config=column_config,
                hide_index=True
            )
            
            st.markdown(f"**共 {len(history_df)} 条历史记录**")
            
            # 差异对比功能
            if len(history_df) > 0:
                st.markdown("---")
                st.markdown("**查看详细差异:**")
                
                history_ids = history_df['id'].tolist()
                selected_history_id = st.selectbox(
                    "选择历史记录",
                    history_ids,
                    format_func=lambda x: f"记录 #{x} - {history_df[history_df['id']==x]['changed_at'].values[0]}",
                    key="selected_history"
                )
                
                if selected_history_id:
                    selected_record = history_df[history_df['id'] == selected_history_id].iloc[0]
                    
                    st.markdown(f"**变更类型:** {selected_record['change_type']}")
                    st.markdown(f"**变更时间:** {selected_record['changed_at']}")
                    st.markdown(f"**变更人:** {selected_record['changed_by']}")
                    if selected_record.get('change_reason'):
                        st.markdown(f"**变更原因:** {selected_record['change_reason']}")
                    
                    # 显示差异
                    import difflib
                    
                    # System Prompt 差异
                    st.markdown("**System Prompt 变更:**")
                    old_system = selected_record.get('system_prompt_old', '') or ''
                    new_system = selected_record.get('system_prompt_new', '') or ''
                    
                    if old_system or new_system:
                        diff_system = difflib.unified_diff(
                            old_system.splitlines(keepends=True),
                            new_system.splitlines(keepends=True),
                            fromfile='修改前',
                            tofile='修改后',
                            lineterm=''
                        )
                        diff_text_system = ''.join(diff_system)
                        if diff_text_system:
                            st.code(diff_text_system, language='diff')
                        else:
                            st.info("无变更")
                    else:
                        st.info("无内容")
                    
                    # User Prompt 差异
                    st.markdown("**User Prompt 变更:**")
                    old_user = selected_record.get('user_prompt_old', '') or ''
                    new_user = selected_record.get('user_prompt_new', '') or ''
                    
                    if old_user or new_user:
                        diff_user = difflib.unified_diff(
                            old_user.splitlines(keepends=True),
                            new_user.splitlines(keepends=True),
                            fromfile='修改前',
                            tofile='修改后',
                            lineterm=''
                        )
                        diff_text_user = ''.join(diff_user)
                        if diff_text_user:
                            st.code(diff_text_user, language='diff')
                        else:
                            st.info("无变更")
                    else:
                        st.info("无内容")


# 主程序
if check_login_status():
    rule_management_page()
else:
    st.warning("请先登录")
    st.markdown("[返回登录页面](/)")
