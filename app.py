import streamlit as st
import feedparser
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from dateutil import parser
import re

# ==========================================
# 1. 系统配置与样式
# ==========================================
st.set_page_config(
    page_title="CloudPulse Gov | 云产业政策与市场",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* 政策卡片样式 - 红色调强调权威性 */
    .policy-card { background-color: #fff1f2; padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 5px solid #be123c; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    /* 市场卡片样式 - 蓝色调 */
    .market-card { background-color: #f8fafc; padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 5px solid #3b82f6; }
    
    .news-title { font-size: 16px; font-weight: 600; color: #111827; text-decoration: none; }
    .news-title:hover { color: #2563eb; }
    
    .meta-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 8px; }
    .tag-policy { background: #fda4af; color: #881337; } /* 政策标签 */
    .tag-source { background: #e2e8f0; color: #475569; } /* 来源标签 */
    
    .stock-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-bottom: 10px; background: white; transition: 0.3s; }
    .stock-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-color: #cbd5e1; }
    
    .up { color: #d32f2f; font-weight: bold; }
    .down { color: #2e7d32; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 严格的可信源白名单 (Trusted Sources)
# ==========================================
# 系统将只放行包含以下关键词的来源
TRUSTED_SOURCES = [
    # --- 官方/党媒 ---
    "新华", "人民网", "央视", "CCTV", "求是", "中国政府网", 
    # --- 核心财经媒体 (四大报) ---
    "证券时报", "中国证券报", "上海证券报", "证券日报", 
    # --- 一线专业财经 ---
    "财新", "第一财经", "每日经济新闻", "21世纪经济报道", "界面新闻", "澎湃", "经济日报", "金融界",
    # --- 国际顶级信源 ---
    "Reuters", "路透", "Bloomberg", "彭博", "CNBC", "Wall Street Journal",
    # --- 科技垂直权威 ---
    "36氪", "钛媒体" # 仅保留头部科技媒体，剔除普通自媒体
]

# ==========================================
# 3. 产业链映射 (Mapping V3.0 - Policy Enhanced)
# ==========================================
SECTOR_MAPPING = {
    # === 政策/国资云 (高优先级) ===
    "政策": [{"name": "深桑达A", "symbol": "000032.SZ", "tag": "中国电子云"}, {"name": "易华录", "symbol": "300212.SZ", "tag": "数据湖"}],
    "工信部": [{"name": "中国电信", "symbol": "601728.SS", "tag": "数字基建"}, {"name": "中国移动", "symbol": "600941.SS", "tag": "算力网络"}],
    "算力网": [{"name": "中科曙光", "symbol": "603019.SS", "tag": "国家超算"}, {"name": "浪潮信息", "symbol": "000977.SZ", "tag": "服务器"}],
    "数据局": [{"name": "云赛智联", "symbol": "600602.SS", "tag": "上海数据"}, {"name": "太极股份", "symbol": "002368.SZ", "tag": "政务云"}],

    # === 核心硬科技 ===
    "CPO": [{"name": "中际旭创", "symbol": "300308.SZ", "tag": "全球光模块"}, {"name": "新易盛", "symbol": "300502.SZ", "tag": "LPO技术"}],
    "液冷": [{"name": "英维克", "symbol": "002837.SZ", "tag": "全链条液冷"}, {"name": "曙光数创", "symbol": "872808.BJ", "tag": "浸没式"}],
    "华为云": [{"name": "拓维信息", "symbol": "002261.SZ", "tag": "昇腾+盘古"}, {"name": "软通动力", "symbol": "301236.SZ", "tag": "鸿蒙+欧拉"}],
    
    # === 全球映射 ===
    "AWS": [{"name": "Amazon", "symbol": "AMZN", "tag": "Global Cloud"}],
    "Azure": [{"name": "Microsoft", "symbol": "MSFT", "tag": "OpenAI Partner"}],
}

# 政策关键词组，用于给新闻打“政策”标签
POLICY_KEYWORDS = ["印发", "通知", "行动计划", "白皮书", "十四五", "工信部", "发改委", "网信办", "数据局", "解读", "指南"]

# ==========================================
# 4. 数据处理逻辑
# ==========================================

def is_trusted_source(source_name):
    """检查来源是否在白名单中"""
    if not source_name: return False
    for trusted in TRUSTED_SOURCES:
        if trusted in source_name:
            return True
    return False

def is_policy_news(title):
    """检查是否属于政策类新闻"""
    for kw in POLICY_KEYWORDS:
        if kw in title:
            return True
    return False

@st.cache_data(ttl=900) # 15分钟缓存，减轻接口压力
def fetch_authoritative_news():
    """
    获取并严格过滤新闻
    """
    # 搜索查询构造：增加“政策、发改委”等宏观词
    query = "云计算 OR 算力 OR 数据要素 OR 工业互联网 OR 阿里云 OR 华为云 OR 工信部 OR 发改委 when:7d"
    encoded_query = query.replace(" ", "+")
    
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    
    feed = feedparser.parse(rss_url)
    
    cleaned_data = []
    seen_titles = set()
    
    cutoff_date = datetime.now(pd.Timestamp.now().tz.tzinfo) - timedelta(days=7)
    
    for entry in feed.entries:
        try:
            # 1. 时间过滤 (T-7)
            pub_date = parser.parse(entry.published)
            if pub_date.replace(tzinfo=None) < datetime.now() - timedelta(days=7):
                continue
                
            # 2. 来源过滤 (核心步骤：只保留白名单)
            source_name = entry.source.title if hasattr(entry, 'source') else ""
            if not is_trusted_source(source_name):
                continue
                
            # 3. 去重
            if entry.title in seen_titles:
                continue
            seen_titles.add(entry.title)
            
            # 4. 识别属性
            is_policy = is_policy_news(entry.title)
            
            item = {
                "title": entry.title,
                "link": entry.link,
                "date_str": pub_date.strftime("%m-%d %H:%M"),
                "source": source_name,
                "is_policy": is_policy,
                "timestamp": pub_date.timestamp()
            }
            cleaned_data.append(item)
            
        except Exception:
            continue
    
    # 按时间倒序排列
    cleaned_data.sort(key=lambda x: x['timestamp'], reverse=True)
    return cleaned_data

def map_alpha_targets(news_items):
    """
    根据新闻生成标的池
    """
    targets = {}
    
    for news in news_items:
        # 检查新闻标题是否命中 SECTOR_MAPPING 的 key
        for keyword, stocks in SECTOR_MAPPING.items():
            if keyword in news['title'] or (keyword == "政策" and news['is_policy']):
                for stock in stocks:
                    sym = stock['symbol']
                    if sym not in targets:
                        targets[sym] = {
                            "info": stock,
                            "score": 0,
                            "drivers": []
                        }
                    # 政策新闻权重加倍
                    weight = 2 if news['is_policy'] else 1
                    targets[sym]['score'] += weight
                    
                    # 记录驱动理由 (去重)
                    if len(targets[sym]['drivers']) < 2:
                        targets[sym]['drivers'].append(f"{news['date_str']} {news['title']}")
    
    # 转换为列表并排序 (按关联热度)
    result_list = sorted(targets.values(), key=lambda x: x['score'], reverse=True)
    return result_list

def get_market_data(target_list):
    """
    获取实时行情
    """
    if not target_list: return {}
    
    symbols = [t['info']['symbol'] for t in target_list]
    unique_symbols = list(set(symbols))
    
    quotes = {}
    try:
        # 批量请求
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
# 5. 页面渲染
# ==========================================

# --- Sidebar ---
with st.sidebar:
    st.header("📡 信号控制台")
    st.info("严格模式：已开启")
    st.write("✅ 仅限官方/一级财经媒体")
    st.write("✅ T-7 实时去重")
    st.write("✅ 政策优先算法")
    
    st.divider()
    st.write("📋 **当前白名单示例:**")
    st.caption("新华、人民、财新、四大报、彭博、路透...")
    
    if st.button("🚀 刷新全网数据"):
        st.cache_data.clear()
        st.rerun()

# --- Main ---
st.title("CloudPulse Gov 🏛️")
st.markdown("#### 权威信源驱动的云计算政策与市场监测")

with st.spinner("正在进行信源核查与政策NLP分析..."):
    news_data = fetch_authoritative_news()
    alpha_targets = map_alpha_targets(news_data)
    quotes = get_market_data(alpha_targets)

col1, col2 = st.columns([0.6, 0.4], gap="large")

# === 左侧：权威资讯流 ===
with col1:
    st.subheader(f"📜 权威快讯 ({len(news_data)})")
    
    if not news_data:
        st.warning("过去一周未监测到白名单内的重大云计算新闻，或网络连接受限。")
    
    for news in news_data:
        # 样式判定
        card_class = "policy-card" if news['is_policy'] else "market-card"
        policy_badge = '<span class="meta-tag tag-policy">🏛️ 政策重磅</span>' if news['is_policy'] else ''
        
        st.markdown(f"""
        <div class="{card_class}">
            <div style="margin-bottom:6px;">
                {policy_badge}
                <span class="meta-tag tag-source">{news['source']}</span>
                <span style="font-size:12px; color:#666;">{news['date_str']}</span>
            </div>
            <a href="{news['link']}" target="_blank" class="news-title">
                {news['title']}
            </a>
        </div>
        """, unsafe_allow_html=True)

# === 右侧：逻辑映射标的 ===
with col2:
    st.subheader("📊 标的映射 (Alpha Logic)")
    
    if not alpha_targets:
        st.write("当前资讯流未触发明确标的逻辑。")
    
    for item in alpha_targets:
        info = item['info']
        sym = info['symbol']
        mkt = quotes.get(sym, {"price": 0, "change": 0})
        
        color = "up" if mkt['change'] >= 0 else "down"
        arrow = "▲" if mkt['change'] >= 0 else "▼"
        
        # 构造驱动理由列表
        drivers_html = "".join([f"<li style='font-size:11px; color:#555; margin-top:3px;'>{d}</li>" for d in item['drivers']])
        
        st.markdown(f"""
        <div class="stock-card">
            <div style="display:flex; justify-content:space-between;">
                <div>
                    <div style="font-weight:700; font-size:16px;">{info['name']}</div>
                    <div style="font-size:12px; color:#64748b;">{sym} · {info['tag']}</div>
                </div>
                <div style="text-align:right;">
                    <div class="{color}" style="font-size:18px;">{mkt['price']:.2f}</div>
                    <div class="{color}" style="font-size:12px;">{arrow} {mkt['change']:.2f}%</div>
                </div>
            </div>
            <div style="margin-top:10px; padding-top:8px; border-top:1px dashed #eee;">
                <span style="font-size:11px; font-weight:bold; color:#475569;">⚡ 逻辑/事件驱动:</span>
                <ul style="padding-left:15px; margin-bottom:0;">
                    {drivers_html}
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()
st.caption("免责声明：本系统仅依据公开权威媒体信息进行逻辑关联，不构成投资建议。政策解读请以政府官网原文为准。")