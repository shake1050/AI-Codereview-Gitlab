# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from biz.service.review_service import ReviewService

# 设置页面配置
st.set_page_config(layout="wide", page_title="审查详情", page_icon="📋")

# 获取URL参数
query_params = st.query_params
record_id = query_params.get("id", None)
tab_type = query_params.get("type", "mr")  # mr 或 push

if not record_id:
    st.error("缺少记录ID参数")
    st.stop()

try:
    record_id = int(record_id)
except ValueError:
    st.error("无效的记录ID")
    st.stop()

# 根据类型获取数据
if tab_type == "mr":
    df = ReviewService.get_mr_review_log_by_id(record_id)
    title_prefix = "合并请求"
else:
    df = ReviewService.get_push_review_log_by_id(record_id)
    title_prefix = "推送"

if df.empty:
    st.error(f"未找到ID为 {record_id} 的{title_prefix}记录")
    st.stop()

# 获取记录数据
row = df.iloc[0]
review_result = row.get('review_result', '')
project_name = row.get('project_name', '未知项目')
author = row.get('author', '未知作者')
updated_at = row.get('updated_at', '')

# 显示详情
st.markdown(f"# 📋 {title_prefix} Review详情")

# 基本信息卡片
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("项目", project_name)
with col2:
    st.metric("开发者", author)
with col3:
    st.metric("时间", updated_at)

st.markdown("---")

# 显示其他字段信息
if tab_type == "mr":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.info(f"**源分支:** {row.get('source_branch', 'N/A')}")
    with col2:
        st.info(f"**目标分支:** {row.get('target_branch', 'N/A')}")
    with col3:
        score = row.get('score', 'N/A')
        if isinstance(score, (int, float)) and not pd.isna(score):
            st.metric("评分", f"{int(score)}")
        else:
            st.info(f"**评分:** N/A")
    with col4:
        url = row.get('url', '')
        if url and not pd.isna(url) and url.strip():
            st.markdown(f"**链接:** [查看]({url})")
else:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**分支:** {row.get('branch', 'N/A')}")
    with col2:
        score = row.get('score', 'N/A')
        if isinstance(score, (int, float)) and not pd.isna(score):
            st.metric("评分", f"{int(score)}")
        else:
            st.info(f"**评分:** N/A")
    with col3:
        additions = row.get('additions', 0)
        deletions = row.get('deletions', 0)
        st.info(f"**变更:** +{additions} / -{deletions}")

st.markdown("---")

# 提交信息
commit_messages = row.get('commit_messages', '')
if commit_messages and not pd.isna(commit_messages) and commit_messages.strip():
    st.markdown("### 📝 提交信息")
    st.text(commit_messages)
    st.markdown("---")

# Review结果
st.markdown("### 🤖 AI代码审查结果")
if review_result and not pd.isna(review_result) and review_result.strip() != "":
    st.markdown(review_result)
else:
    st.info("该记录暂无review信息")

# 返回按钮
st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("← 返回列表", use_container_width=True):
        # 使用JavaScript返回上一页或主页
        st.markdown(
            '<script>window.history.back();</script>',
            unsafe_allow_html=True
        )
