import streamlit as st
import feedparser
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import re

# ==========================================
# 1. 页面配置与样式
# ==========================================
st.set_page_config(
    page_title="CloudPulse CN | 云脉动",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 美化
st.markdown("""
<style>
    .news-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        border-left: 5px solid #4e8cff;
    }
    .news-title {
        font-size: 18px;
        font-weight: bold;
        color: #1f2937;
    }
    .news-meta {
        font-size: 12px;
        color: #6b7280;
        margin-top: 5px;
    }
    .stock-card {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        transition: transform 0.2s;
    }
    .stock-card:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .positive { color: #ef4444; font-weight: bold; } /* A股红涨 */
    .negative { color: #10b981; font-weight: bold; } /* A股绿跌 */
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心逻辑：标的映射数据库
# ==========================================
# 这是一个简单的知识图谱，将新闻关键词映射到股票代码
STOCK_MAPPING = {
    "阿里云": {"name": "阿里巴巴", "symbol": "9988.HK", "market": "HK"},
    "阿里": {"name": "阿里巴巴", "symbol": "BABA", "market": "US"},
    "腾讯云": {"name": "腾讯控股", "symbol": "0700.HK", "market": "HK"},
    "华为": {"name": "拓维信息", "symbol": "002261.SZ", "market": "CN", "note": "华为算力合作伙伴"},
    "盘古": {"name": "四川长虹", "symbol": "600839.SS", "market": "CN", "note": "华鲲振宇概念"},
    "百度": {"name": "百度集团", "symbol": "9888.HK", "market": "HK"},
    "文心": {"name": "百度", "symbol": "BIDU", "market": "US"},
    "算力": {"name": "中际旭创", "symbol": "300308.SZ", "market": "CN", "note": "光模块龙头"},
    "液冷": {"name": "英维克", "symbol": "002837.SZ", "market": "CN"},
    "微软": {"name": "Microsoft", "symbol": "MSFT", "market": "US"},
    "AWS": {"name": "Amazon", "symbol": "AMZN", "market": "US"},
    "Oracle": {"name": "Oracle", "symbol": "ORCL", "market": "US"},
    "运营商": {"name": "中国移动", "symbol": "600941.SS", "market": "CN"},
    "天翼云": {"name": "中国电信", "symbol": "601728.SS", "market": "CN"},
}

# ==========================================
# 3. 功能函数
# ==========================================

@st.cache_data(ttl=300)  # 缓存5分钟，避免频繁请求
def fetch_cloud_news():
    """
    使用 Google News RSS 获取实时新闻
    搜索词涵盖主要的中国和全球云计算关键词
    """
    # 编码后的搜索词：云计算 OR 阿里云 OR 华为云 OR 腾讯云 OR AWS OR Azure
    rss_url = "https://news.google.com/rss/search?q=%E4%BA%91%E8%AE%A1%E7%AE%97+OR+%E9%98%BF%E9%87%8C%E4%BA%91+OR+%E5%8D%8E%E4%B8%BA%E4%BA%91+OR+%E8%85%BE%E8%AE%AF%E4%BA%91+OR+AWS+OR+%E7%AE%97%E5%8A%9B&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    
    feed = feedparser.parse(rss_url)
    news_items = []
    
    for entry in feed.entries[:20]: # 获取最新的20条
        # 简单清洗时间
        published = entry.get("published", "")
        
        item = {
            "title": entry.title,
            "link": entry.link,
            "published": published,
            "source": entry.source.title if hasattr(entry, 'source') else "未知来源"
        }
        news_items.append(item)
        
    return news_items

def analyze_sentiment_and_stocks(news_list):
    """
    分析新闻，提取相关标的
    """
    recommendations = {} # 使用字典去重
    
    for news in news_list:
        title = news['title']
        
        # 遍历映射表查找关键词
        for keyword, stock_info in STOCK_MAPPING.items():
            if keyword in title:
                symbol = stock_info['symbol']
                if symbol not in recommendations:
                    recommendations[symbol] = {
                        "info": stock_info,
                        "reasons": [title] # 记录触发推荐的新闻标题
                    }
                else:
                    recommendations[symbol]['reasons'].append(title)
    
    return recommendations

def get_realtime_price(symbol_list):
    """
    使用 yfinance 获取实时价格变动
    """
    if not symbol_list:
        return {}
    
    data = {}
    try:
        tickers = yf.Tickers(" ".join(symbol_list))
        for symbol in symbol_list:
            try:
                info = tickers.tickers[symbol].history(period="1d")
                if not info.empty:
                    close = info['Close'].iloc[-1]
                    open_p = info['Open'].iloc[-1]
                    # 如果是盘中，history通常返回最新价作为Close
                    # 计算涨跌幅
                    prev_close = tickers.tickers[symbol].info.get('previousClose', open_p)
                    change_pct = ((close - prev_close) / prev_close) * 100
                    data[symbol] = {"price": close, "change": change_pct}
                else:
                     data[symbol] = {"price": 0, "change": 0}
            except:
                data[symbol] = {"price": 0, "change": 0}
    except Exception as e:
        st.error(f"行情数据获取失败: {e}")
    
    return data

# ==========================================
# 4. 界面渲染
# ==========================================

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ 控制台")
    st.write("数据源：Google News (Real-time)")
    filter_option = st.radio("资讯范围", ["全部", "仅中国", "仅海外"])
    st.info("💡 提示：本应用演示了基于新闻关键词的自动标的映射逻辑。")
    if st.button("🔄 刷新数据"):
        st.cache_data.clear()
        st.rerun()

# --- Header ---
st.title("CloudPulse CN ☁️ 云脉动")
st.markdown("#### 洞察中国云端，链接全球算力价值")
st.markdown("---")

# --- Load Data ---
with st.spinner('正在扫描全球云网络...'):
    news_data = fetch_cloud_news()
    reco_data = analyze_sentiment_and_stocks(news_data)
    
    # 获取行情
    if reco_data:
        symbols = list(reco_data.keys())
        price_data = get_realtime_price(symbols)
    else:
        price_data = {}

# --- Main Content Columns ---
col_news, col_alpha = st.columns([2, 1])

# === 左侧：资讯流 ===
with col_news:
    st.subheader("📰 行业情报 (T-7)")
    
    for news in news_data:
        # 简单的过滤器逻辑
        is_china = any(k in news['title'] for k in ["中国", "阿里", "腾讯", "华为", "百度", "电信", "移动"])
        if filter_option == "仅中国" and not is_china:
            continue
        if filter_option == "仅海外" and is_china:
            continue
            
        # 渲染卡片
        st.markdown(f"""
        <div class="news-card">
            <div class="news-title"><a href="{news['link']}" target="_blank" style="text-decoration:none; color:#1f2937;">{news['title']}</a></div>
            <div class="news-meta">
                <span>📅 {news['published']}</span> | 
                <span>📢 {news['source']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# === 右侧：标的推荐 ===
with col_alpha:
    st.subheader("🎯 智能标的 (Alpha Picks)")
    st.caption("基于本周新闻热度自动生成")
    
    if not reco_data:
        st.warning("当前新闻流中未检测到明确的关联标的。")
    
    for symbol, data in reco_data.items():
        info = data['info']
        market_data = price_data.get(symbol, {"price": 0, "change": 0})
        
        # 颜色逻辑
        change = market_data['change']
        color_class = "positive" if change >= 0 else "negative"
        arrow = "🔺" if change >= 0 else "🔻"
        
        # 映射理由摘要（取第一条新闻的截断）
        reason_text = data['reasons'][0][:30] + "..."
        
        # 渲染股票卡片
        st.markdown(f"""
        <div class="stock-card">
            <h4 style="margin:0;">{info['name']}</h4>
            <div style="color:#666; font-size:12px; margin-bottom:5px;">{symbol} ({info.get('note', '云计算概念')})</div>
            <div class="{color_class}" style="font-size:20px;">
                {market_data['price']:.2f} <span style="font-size:14px;">{arrow} {change:.2f}%</span>
            </div>
            <div style="font-size:11px; color:#888; margin-top:8px; text-align:left; border-top:1px dashed #eee; padding-top:5px;">
                <b>驱动事件：</b><br>{reason_text}
            </div>
        </div>
        <br>
        """, unsafe_allow_html=True)

# --- Footer ---
st.markdown("---")
st.caption("免责声明：本页面数据由算法自动聚合，行情数据可能有延迟，不构成投资建议。")