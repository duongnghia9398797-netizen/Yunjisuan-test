import streamlit as st
import feedparser
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from dateutil import parser
import time

# ==========================================
# 1. 系统配置与样式 (UI/UX Upgrade)
# ==========================================
st.set_page_config(
    page_title="CloudPulse Gov | 云产业政策与市场",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS：修复了渲染问题，增强了标的卡片的视觉冲击力
st.markdown("""
<style>
    /* 全局字体优化 */
    body { font-family: "Source Sans Pro", sans-serif; }

    /* --- 左侧：新闻卡片 --- */
    .news-card {
        background-color: #ffffff;
        padding: 16px;
        border-radius: 10px;
        margin-bottom: 12px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .news-card:hover { transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    
    /* 政策类新闻特殊样式 (红色边框) */
    .policy-highlight { border-left: 5px solid #dc2626; background-color: #fff1f2; }
    /* 市场类新闻特殊样式 (蓝色边框) */
    .market-highlight { border-left: 5px solid #2563eb; }
    
    .news-title { font-size: 16px; font-weight: 700; color: #1f2937; text-decoration: none; line-height: 1.4; display: block; margin-bottom: 8px; }
    .news-title:hover { color: #2563eb; text-decoration: underline; }
    
    .meta-row { font-size: 12px; color: #6b7280; display: flex; align-items: center; gap: 10px; }
    .tag { padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 10px; letter-spacing: 0.5px; }
    .tag-policy { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
    .tag-source { background: #f3f4f6; color: #374151; border: 1px solid #e5e7eb; }

    /* --- 右侧：标的卡片 (V1 风格回归) --- */
    .stock-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* 头部区域：名称和价格并排 */
    .stock-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
    
    .stock-name { font-size: 20px; font-weight: 800; color: #111827; margin: 0; line-height: 1.2; }
    .stock-code { font-size: 13px; color: #6b7280; font-family: monospace; margin-top: 2px; }
    .stock-tag { display: inline-block; background: #eff6ff; color: #1d4ed8; font-size: 10px; padding: 2px 6px; border-radius: 4px; margin-left: 5px; vertical-align: middle; font-weight: 600;}

    .stock-price-box { text-align: right; }
    .stock-price { font-size: 22px; font-weight: 700; line-height: 1; }
    .stock-change { font-size: 14px; font-weight: 600; margin-top: 4px; }

    /* 底部逻辑区域 */
    .driver-box { background-color: #f9fafb; border-radius: 6px; padding: 8px 12px; margin-top: 10px; border-top: 1px solid #f3f4f6; }
    .driver-title { font-size: 11px; font-weight: 700; color: #4b5563; margin-bottom: 4px; text-transform: uppercase; }
    .driver-item { font-size: 12px; color: #4b5563; line-height: 1.4; margin-bottom: 2px; display: flex; }
    .driver-item::before { content: "•"; color: #cbd5e1; margin-right: 6px; }

    /* 涨跌颜色 */
    .up { color: #d32f2f; }
    .down { color: #16a34a; }
    .bg-up { background-color: #fef2f2; } /* 涨幅背景淡红 */
    .bg-down { background-color: #f0fdf4; } /* 跌幅背景淡绿 */
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 配置项
# ==========================================
TRUSTED_SOURCES = [
    "新华", "人民网", "央视", "CCTV", "求是", "中国政府网", 
    "证券时报", "中国证券报", "上海证券报", "证券日报", 
    "财新", "第一财经", "每日经济新闻", "21世纪经济报道", "界面新闻", "澎湃", "经济日报", "金融界",
    "Reuters", "路透", "Bloomberg", "彭博", "CNBC", "Wall Street Journal",
    "36氪", "钛媒体", "智东西"
]

SECTOR_MAPPING = {
    # === 政策/国资云 (高权重) ===
    "政策": [{"name": "深桑达A", "symbol": "000032.SZ", "tag": "中国电子云"}, {"name": "易华录", "symbol": "300212.SZ", "tag": "数据湖"}],
    "工信部": [{"name": "中国电信", "symbol": "601728.SS", "tag": "数字基建"}, {"name": "中国移动", "symbol": "600941.SS", "tag": "算力网络"}],
    "算力网": [{"name": "中科曙光", "symbol": "603019.SS", "tag": "国家超算"}, {"name": "浪潮信息", "symbol": "000977.SZ", "tag": "服务器龙头"}],
    "数据局": [{"name": "云赛智联", "symbol": "600602.SS", "tag": "上海数据"}, {"name": "太极股份", "symbol": "002368.SZ", "tag": "政务云"}],

    # === 核心硬科技 ===
    "CPO": [{"name": "中际旭创", "symbol": "300308.SZ", "tag": "光模块龙一"}, {"name": "新易盛", "symbol": "300502.SZ", "tag": "LPO技术"}],
    "液冷": [{"name": "英维克", "symbol": "002837.SZ", "tag": "精密温控"}, {"name": "曙光数创", "symbol": "872808.BJ", "tag": "浸没式液冷"}],
    "华为云": [{"name": "拓维信息", "symbol": "002261.SZ", "tag": "昇腾+盘古"}, {"name": "软通动力", "symbol": "301236.SZ", "tag": "鸿蒙+欧拉"}],
    
    # === 全球映射 ===
    "AWS": [{"name": "Amazon", "symbol": "AMZN", "tag": "Global Cloud"}],
    "Azure": [{"name": "Microsoft", "symbol": "MSFT", "tag": "OpenAI Partner"}],
}

POLICY_KEYWORDS = ["印发", "通知", "行动计划", "白皮书", "十四五", "工信部", "发改委", "网信办", "数据局", "解读", "指南", "号召", "建设"]

# ==========================================
# 3. 数据处理函数
# ==========================================

def is_trusted_source(source_name):
    if not source_name: return False
    for trusted in TRUSTED_SOURCES:
        if trusted in source_name: return True
    return False

def is_policy_news(title):
    for kw in POLICY_KEYWORDS:
        if kw in title: return True
    return False

@st.cache_data(ttl=900)
def fetch_authoritative_news():
    """修复了时区问题的获取函数"""
    query = "云计算 OR 算力 OR 数据要素 OR 工业互联网 OR 阿里云 OR 华为云 OR 工信部 OR 发改委 when:7d"
    encoded_query = query.replace(" ", "+")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    
    feed = feedparser.parse(rss_url)
    cleaned_data = []
    seen_titles = set()
    
    # 使用不带时区的时间进行比较
    now_naive = datetime.now()
    cutoff_date = now_naive - timedelta(days=7)
    
    for entry in feed.entries:
        try:
            pub_date = parser.parse(entry.published)
            # 核心修复：去除时区信息再比较
            if pub_date.replace(tzinfo=None) < cutoff_date:
                continue
                
            source_name = entry.source.title if hasattr(entry, 'source') else ""
            if not is_trusted_source(source_name):
                continue
                
            if entry.title in seen_titles:
                continue
            seen_titles.add(entry.title)
            
            is_policy = is_policy_news(entry.title)
            
            cleaned_data.append({
                "title": entry.title,
                "link": entry.link,
                "date_str": pub_date.strftime("%m-%d %H:%M"),
                "source": source_name,
                "is_policy": is_policy,
                "timestamp": pub_date.timestamp()
            })
        except Exception:
            continue
    
    cleaned_data.sort(key=lambda x: x['timestamp'], reverse=True)
    return cleaned_data

def map_alpha_targets(news_items):
    targets = {}
    for news in news_items:
        for keyword, stocks in SECTOR_MAPPING.items():
            if keyword in news['title'] or (keyword == "政策" and news['is_policy']):
                for stock in stocks:
                    sym = stock['symbol']
                    if sym not in targets:
                        targets[sym] = {"info": stock, "score": 0, "drivers": []}
                    
                    weight = 3 if news['is_policy'] else 1
                    targets[sym]['score'] += weight
                    
                    if len(targets[sym]['drivers']) < 2:
                        targets[sym]['drivers'].append(f"{news['date_str']} - {news['source']}: {news['title']}")
    
    return sorted(targets.values(), key=lambda x: x['score'], reverse=True)

def get_market_data(target_list):
    if not target_list: return {}
    symbols = [t['info']['symbol'] for t in target_list]
    unique_symbols = list(set(symbols))
    quotes = {}
    try:
        tickers = yf.Tickers(" ".join(unique_symbols))
        for sym in unique_symbols:
            try:
                hist = tickers.tickers[sym].history(period="1d")
                if not hist.empty:
                    curr = hist['Close'].iloc[-1]
                    prev = tickers.tickers[sym].info.get('previousClose', hist['Open'].iloc[-1])
                    chg = ((curr - prev) / prev) * 100 if prev else 0
                    quotes[sym] = {"price": curr, "change": chg}
                else:
                    quotes[sym] = {"price": 0, "change": 0}
            except:
                quotes[sym] = {"price": 0, "change": 0}
    except:
        pass
    return quotes

# ==========================================
# 4. 页面渲染 (Layout)
# ==========================================

# --- Sidebar ---
with st.sidebar:
    st.title("📡 信号控制台")
    st.info("已启用：严格白名单模式")
    st.markdown("""
    *   **信源：** 仅限新华、央媒、财新等
    *   **去重：** T-7 智能时间窗
    *   **策略：** 政策权重 > 技术权重
    """)
    if st.button("🚀 刷新全网数据"):
        st.cache_data.clear()
        st.rerun()

# --- Header ---
st.title("CloudPulse Gov 🏛️")
st.markdown("#### 权威信源驱动的云计算政策与市场监测")
st.divider()

# --- Loading & Processing ---
with st.spinner("正在同步全球节点与交易所数据..."):
    news_data = fetch_authoritative_news()
    alpha_targets = map_alpha_targets(news_data)
    quotes = get_market_data(alpha_targets)

col_news, col_alpha = st.columns([0.55, 0.45], gap="large")

# === Left Column: News Feed ===
with col_news:
    st.subheader(f"📜 权威快讯 ({len(news_data)})")
    
    if not news_data:
        st.warning("过去一周未监测到白名单内的重大云计算新闻。")
    
    for news in news_data:
        # 动态选择样式类
        card_style = "policy-highlight" if news['is_policy'] else "market-highlight"
        
        # HTML 拼接 (注意：这里去除了缩进，防止被识别为代码块)
        news_html = f"""
        <div class="news-card {card_style}">
            <a href="{news['link']}" target="_blank" class="news-title">{news['title']}</a>
            <div class="meta-row">
                <span class="tag {'tag-policy' if news['is_policy'] else 'tag-source'}">
                    {'🏛️ 政策重磅' if news['is_policy'] else '📰 ' + news['source']}
                </span>
                <span>🕒 {news['date_str']}</span>
            </div>
        </div>
        """
        st.markdown(news_html, unsafe_allow_html=True)

# === Right Column: Alpha Targets ===
with col_alpha:
    st.subheader("📊 标的推荐 (Alpha Picks)")
    
    if not alpha_targets:
        st.info("等待新闻信号触发标的映射...")
    
    for item in alpha_targets:
        info = item['info']
        sym = info['symbol']
        mkt = quotes.get(sym, {"price": 0, "change": 0})
        
        # 颜色逻辑
        is_up = mkt['change'] >= 0
        color_class = "up" if is_up else "down"
        arrow = "▲" if is_up else "▼"
        sign = "+" if is_up else ""
        
        # 驱动理由逻辑 (截取去重)
        drivers_list_html = ""
        for d in item['drivers'][:2]: # 只显示前2条
            # 截断过长的文本
            short_d = (d[:38] + '..') if len(d) > 38 else d
            drivers_list_html += f'<div class="driver-item">{short_d}</div>'

        # 卡片 HTML 结构 (Flexbox 布局)
        card_html = f"""
        <div class="stock-card">
            <div class="stock-header">
                <!-- 左侧：名称与代码 -->
                <div>
                    <div class="stock-name">
                        {info['name']} 
                        <span class="stock-tag">{info.get('tag', '云计算')}</span>
                    </div>
                    <div class="stock-code">{sym}</div>
                </div>
                <!-- 右侧：价格与涨跌 -->
                <div class="stock-price-box">
                    <div class="stock-price {color_class}">{mkt['price']:.2f}</div>
                    <div class="stock-change {color_class}">{arrow} {sign}{mkt['change']:.2f}%</div>
                </div>
            </div>
            
            <!-- 底部：逻辑驱动 -->
            <div class="driver-box">
                <div class="driver-title">⚡ 逻辑驱动 (Catalysts)</div>
                {drivers_list_html}
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

# --- Footer ---
st.markdown("---")
st.caption("数据来源：Google News (Filtered), Yahoo Finance | 仅供参考，不作为投资建议")