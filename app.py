import streamlit as st
import feedparser
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from dateutil import parser

# ==========================================
# 1. 系统配置与样式 (UI/UX)
# ==========================================
st.set_page_config(
    page_title="CloudPulse-全球云计算相关资讯",
    page_icon="🌩️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; }
    
    /* --- 新闻卡片样式 --- */
    .news-card { 
        background: #ffffff; 
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 10px; 
        border: 1px solid #e2e8f0; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.03); 
        transition: transform 0.2s;
    }
    .news-card:hover { transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0,0,0,0.08); border-color: #bfdbfe; }
    
    .policy-highlight { border-left: 4px solid #dc2626; background: #fffbfb; }
    .market-highlight { border-left: 4px solid #2563eb; }
    .intl-highlight { border-left: 4px solid #7c3aed; background: #fbf8ff; }
    
    .news-title { font-size: 15px; font-weight: 700; color: #1e293b; text-decoration: none; display: block; margin-bottom: 6px; }
    .news-title:hover { color: #2563eb; text-decoration: underline; }
    
    .meta-row { font-size: 12px; color: #64748b; display: flex; align-items: center; gap: 8px; }
    .tag { padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 10px; }
    .tag-policy { background: #fee2e2; color: #991b1b; }
    .tag-intl { background: #f3e8ff; color: #6b21a8; }
    .tag-source { background: #f1f5f9; color: #475569; }

    /* --- 标的卡片样式 --- */
    .stock-card { background: #fff; border-radius: 8px; padding: 12px; margin-bottom: 10px; border: 1px solid #e2e8f0; }
    .stock-header { display: flex; justify-content: space-between; align-items: center; }
    .stock-name { font-size: 16px; font-weight: 800; color: #0f172a; }
    .stock-code { font-size: 12px; color: #94a3b8; font-family: monospace; margin-left: 5px; }
    .stock-tag { background: #eff6ff; color: #1d4ed8; font-size: 10px; padding: 1px 5px; border-radius: 3px; margin-left: 5px; font-weight: 600; }
    .price-val { font-size: 18px; font-weight: 700; }
    .price-chg { font-size: 12px; font-weight: 600; }
    
    .up { color: #dc2626; }
    .down { color: #16a34a; }
    
    /* --- 研报专用样式 (白纸风格) --- */
    .report-wrapper {
        background-color: #ffffff;
        padding: 40px;
        border-radius: 4px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        border-top: 10px solid #b91c1c;
        max-width: 900px;
        margin: 0 auto;
        font-family: 'Times New Roman', serif; /* 增加正式感 */
    }
    .r-header { text-align: center; border-bottom: 1px solid #eee; padding-bottom: 20px; margin-bottom: 25px; }
    .r-title { font-size: 28px; font-weight: bold; color: #b91c1c; letter-spacing: 1px; }
    .r-meta { color: #666; font-size: 13px; margin-top: 8px; font-family: sans-serif; }
    
    .r-section { margin-bottom: 25px; }
    .r-h2 { 
        font-size: 18px; 
        font-weight: bold; 
        color: #991b1b; 
        background-color: #fff1f2; 
        padding: 6px 12px; 
        border-left: 5px solid #991b1b; 
        margin-bottom: 12px;
        font-family: sans-serif;
    }
    .r-ul { padding-left: 20px; margin: 0; }
    .r-li { font-size: 15px; line-height: 1.6; color: #1f2937; margin-bottom: 6px; }
    .r-source { font-weight: bold; color: #4b5563; }
    .r-link { text-decoration: none; color: #1f2937; }
    .r-link:hover { color: #2563eb; text-decoration: underline; }
    
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心配置 (Data Config)
# ==========================================
TRUSTED_SOURCES = ["新华", "人民网", "央视", "CCTV", "证券时报", "中国证券报", "上海证券报", "证券日报", "财新", "第一财经", "Reuters", "路透", "Bloomberg", "彭博", "CNBC", "WSJ", "36氪", "钛媒体", "智东西"]

# 标的映射库
SECTOR_MAPPING = {
    # US Giants
    "NVIDIA": {"name": "NVIDIA", "symbol": "NVDA", "tag": "AI算力", "region": "US"},
    "英伟达": {"name": "NVIDIA", "symbol": "NVDA", "tag": "AI算力", "region": "US"},
    "Microsoft": {"name": "Microsoft", "symbol": "MSFT", "tag": "Azure", "region": "US"},
    "微软": {"name": "Microsoft", "symbol": "MSFT", "tag": "Azure", "region": "US"},
    "OpenAI": {"name": "Microsoft", "symbol": "MSFT", "tag": "Azure", "region": "US"},
    "AWS": {"name": "Amazon", "symbol": "AMZN", "tag": "Cloud No.1", "region": "US"},
    "Google": {"name": "Google", "symbol": "GOOGL", "tag": "Gemini", "region": "US"},
    "Oracle": {"name": "Oracle", "symbol": "ORCL", "tag": "Database", "region": "US"},
    # CN Core
    "工信部": {"name": "中国电信", "symbol": "601728.SS", "tag": "数字基建", "region": "CN"},
    "算力网": {"name": "中国移动", "symbol": "600941.SS", "tag": "算力网络", "region": "CN"},
    "数据局": {"name": "易华录", "symbol": "300212.SZ", "tag": "数据湖", "region": "CN"},
    "CPO": {"name": "中际旭创", "symbol": "300308.SZ", "tag": "光模块", "region": "CN"},
    "液冷": {"name": "英维克", "symbol": "002837.SZ", "tag": "液冷", "region": "CN"},
    "服务器": {"name": "浪潮信息", "symbol": "000977.SZ", "tag": "AI服务器", "region": "CN"},
    "华为": {"name": "软通动力", "symbol": "301236.SZ", "tag": "鸿蒙欧拉", "region": "CN"},
}

# 保底池 (Fallback)
FALLBACK_POOL_US = [
    {"name": "NVIDIA", "symbol": "NVDA", "tag": "AI算力", "region": "US"},
    {"name": "Microsoft", "symbol": "MSFT", "tag": "Azure", "region": "US"},
    {"name": "Amazon", "symbol": "AMZN", "tag": "Cloud", "region": "US"},
    {"name": "Google", "symbol": "GOOGL", "tag": "Gemini", "region": "US"},
    {"name": "Oracle", "symbol": "ORCL", "tag": "DB Cloud", "region": "US"}
]
FALLBACK_POOL_CN = [
    {"name": "中际旭创", "symbol": "300308.SZ", "tag": "光模块龙一", "region": "CN"},
    {"name": "浪潮信息", "symbol": "000977.SZ", "tag": "AI服务器", "region": "CN"},
    {"name": "中国移动", "symbol": "600941.SS", "tag": "算力网络", "region": "CN"},
    {"name": "中国电信", "symbol": "601728.SS", "tag": "国资云", "region": "CN"},
    {"name": "金山办公", "symbol": "688111.SS", "tag": "AI办公", "region": "CN"},
    {"name": "海光信息", "symbol": "688041.SS", "tag": "国产芯片", "region": "CN"},
    {"name": "科大讯飞", "symbol": "002230.SZ", "tag": "大模型", "region": "CN"},
    {"name": "腾讯控股", "symbol": "0700.HK", "tag": "MaaS", "region": "CN"},
    {"name": "阿里巴巴", "symbol": "9988.HK", "tag": "阿里云", "region": "CN"}
]

POLICY_KWS = ["印发", "通知", "计划", "白皮书", "十四五", "工信部", "发改委", "数据局"]
INTL_KWS = ["AWS", "Azure", "Google", "OpenAI", "NVIDIA", "AMD", "Oracle", "英伟达", "微软", "谷歌", "亚马逊"]

# ==========================================
# 3. 逻辑函数
# ==========================================

def check_category(title):
    cats = []
    if any(k in title for k in INTL_KWS): cats.append("intl")
    if any(k in title for k in POLICY_KWS): cats.append("policy")
    return cats

@st.cache_data(ttl=900)
def fetch_data():
    query = "云计算 OR 算力 OR 阿里云 OR 华为云 OR 英伟达 OR NVIDIA OR 微软 OR AWS OR OpenAI OR Google when:7d"
    # Google News RSS 链接本身是重定向链接，为了速度，我们直接使用它，但前端加 target="_blank"
    rss_url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    feed = feedparser.parse(rss_url)
    
    data = []
    seen = set()
    cutoff = datetime.now() - timedelta(days=7)
    
    for entry in feed.entries:
        try:
            dt = parser.parse(entry.published).replace(tzinfo=None)
            if dt < cutoff: continue
            src = entry.source.title if hasattr(entry, 'source') else ""
            if not any(t in src for t in TRUSTED_SOURCES): continue
            if entry.title in seen: continue
            seen.add(entry.title)
            
            data.append({
                "title": entry.title,
                "link": entry.link,
                "date": dt.strftime("%m-%d"),
                "source": src,
                "cats": check_category(entry.title),
                "ts": dt.timestamp()
            })
        except: continue
    return sorted(data, key=lambda x: x['ts'], reverse=True)

def get_balanced_stocks(news_data):
    # 1. 提取新闻驱动
    driven_us = {}
    driven_cn = {}
    for news in news_data:
        for kw, meta in SECTOR_MAPPING.items():
            if kw in news['title']:
                s_code = meta['symbol']
                driver = f"{news['date']} {news['source']}: {news['title']}"
                target_dict = driven_us if meta['region'] == "US" else driven_cn
                if s_code not in target_dict:
                    target_dict[s_code] = {"info": meta, "drivers": []}
                if len(target_dict[s_code]['drivers']) < 2:
                    target_dict[s_code]['drivers'].append(driver)

    # 2. 补充保底 (凑齐10个)
    final_us = list(driven_us.values())
    existing_us = [x['info']['symbol'] for x in final_us]
    for stock in FALLBACK_POOL_US:
        if len(final_us) >= 3: break
        if stock['symbol'] not in existing_us:
            final_us.append({"info": stock, "drivers": ["行业核心资产"]})
            
    final_cn = list(driven_cn.values())
    existing_cn = [x['info']['symbol'] for x in final_cn]
    for stock in FALLBACK_POOL_CN:
        if len(final_cn) >= 7: break
        if stock['symbol'] not in existing_cn:
            final_cn.append({"info": stock, "drivers": ["行业龙头 / 关注对象"]})
            
    full_list = final_us + final_cn
    
    # 3. 行情获取
    if full_list:
        symbols = [x['info']['symbol'] for x in full_list]
        try:
            tickers = yf.Tickers(" ".join(symbols))
            for item in full_list:
                sym = item['info']['symbol']
                try:
                    d = tickers.tickers[sym].history(period="1d")
                    if not d.empty:
                        curr = d['Close'].iloc[-1]
                        prev = tickers.tickers[sym].info.get('previousClose', d['Open'].iloc[-1])
                        item['price'] = curr
                        item['change'] = ((curr - prev)/prev)*100 if prev else 0
                    else:
                         item['price'] = 0; item['change'] = 0
                except:
                    item['price'] = 0; item['change'] = 0
        except: pass
    return full_list

def generate_report_html_safe(news, stocks):
    """
    安全生成HTML，使用列表拼接而非多行字符串，彻底根除代码块渲染问题
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 数据准备
    us_news = [n for n in news if "intl" in n['cats']][:5]
    cn_news = [n for n in news if "intl" not in n['cats']][:8]
    policy_count = len([n for n in news if 'policy' in n['cats']])
    
    # 构建 HTML 字符串列表 (List Builder Pattern)
    html_parts = []
    
    # --- 容器开始 ---
    html_parts.append('<div class="report-wrapper">')
    
    # --- 头部 ---
    html_parts.append(f'''
        <div class="r-header">
            <div class="r-title">云计算行业深度周报</div>
            <div class="r-meta">【资讯速递】 第 {datetime.now().isocalendar()[1]} 期 | {today}</div>
        </div>
    ''')
    
    # --- 1. 核心概览 ---
    html_parts.append('<div class="r-section">')
    html_parts.append('<div class="r-h2">核心动态概览</div>')
    html_parts.append('<ul class="r-ul">')
    html_parts.append('<li class="r-li"><b>全球视野：</b>美股科技巨头 (NVDA/MSFT) 资本开支指引持续影响全球产业链。</li>')
    html_parts.append(f'<li class="r-li"><b>国内政策：</b>本周监测到 <b>{policy_count}</b> 条政策动态，重点关注算力基建与数据要素。</li>')
    html_parts.append('</ul>')
    html_parts.append('</div>')
    
    # --- 2. 国际速递 ---
    html_parts.append('<div class="r-section">')
    html_parts.append('<div class="r-h2">国际重点行业速递 (Global Giants)</div>')
    html_parts.append('<ul class="r-ul">')
    if us_news:
        for n in us_news:
            html_parts.append(f'<li class="r-li"><span class="r-source">[{n["source"]}]</span> <a href="{n["link"]}" target="_blank" class="r-link">{n["title"]}</a></li>')
    else:
        html_parts.append('<li class="r-li">本周暂无重大国际突发新闻。</li>')
    html_parts.append('</ul>')
    html_parts.append('</div>')
    
    # --- 3. 国内信息 ---
    html_parts.append('<div class="r-section">')
    html_parts.append('<div class="r-h2">国内重点行业信息</div>')
    html_parts.append('<ul class="r-ul">')
    if cn_news:
        for n in cn_news:
            html_parts.append(f'<li class="r-li"><span class="r-source">[{n["source"]}]</span> <a href="{n["link"]}" target="_blank" class="r-link">{n["title"]}</a></li>')
    else:
        html_parts.append('<li class="r-li">本周暂无重大国内资讯。</li>')
    html_parts.append('</ul>')
    html_parts.append('</div>')
    
    # --- 4. 风险提示 ---
    html_parts.append('<div class="r-section">')
    html_parts.append('<div class="r-h2">业务机会与风险提示</div>')
    html_parts.append('<ul class="r-ul">')
    
    risks = [s for s in stocks if s.get('change', 0) < -2]
    opps = [s for s in stocks if s.get('change', 0) > 2]
    
    if not risks and not opps:
        html_parts.append('<li class="r-li">市场走势相对平稳，核心标的无剧烈波动。</li>')
    else:
        for s in risks:
            html_parts.append(f'<li class="r-li"><b>{s["info"]["name"]}</b> 下跌 {s["change"]:.2f}%，关注短期回调风险。</li>')
        for s in opps:
            html_parts.append(f'<li class="r-li"><b>{s["info"]["name"]}</b> 上涨 {s["change"]:.2f}%，资金流入明显。</li>')
            
    html_parts.append('</ul>')
    html_parts.append('</div>')
    
    # --- 底部 ---
    html_parts.append('<div style="text-align:center; color:#999; font-size:12px; margin-top:40px;">CloudPulse System Auto-Generated | 仅供内部参考</div>')
    html_parts.append('</div>') # End wrapper
    
    return "".join(html_parts)

# ==========================================
# 4. 页面主程序
# ==========================================

# 侧边栏
with st.sidebar:
    st.title("📡 信号控制台")
    view_mode = st.radio("视图选择", ["⚡ 实时资讯流", "🌏 国际重点", "🇨🇳 国内重点", "📝 行业深度周报"], index=0)
    st.divider()
    st.caption("数据源：Google News (Filtered) + Yahoo Finance")
    if st.button("🔄 刷新"):
        st.cache_data.clear()
        st.rerun()

# 数据加载
news_all = fetch_data()
stocks_10 = get_balanced_stocks(news_all)

# 视图逻辑
if "行业深度周报" in view_mode:
    st.title("📑 行业深度周报")
    st.info("提示：点击新闻标题可直接跳转至源链接（新窗口打开）。")
    # 使用新的安全生成函数
    final_html = generate_report_html_safe(news_all, stocks_10)
    st.markdown(final_html, unsafe_allow_html=True)

else:
    st.title("CloudPulse Gov | 全球云产业雷达 🏛️")
    
    # 新闻过滤
    if "国际" in view_mode:
        display_news = [n for n in news_all if "intl" in n['cats']]
    elif "国内" in view_mode:
        display_news = [n for n in news_all if "intl" not in n['cats']]
    else:
        display_news = news_all

    c1, c2 = st.columns([0.6, 0.4], gap="large")
    
    # 左侧：新闻
    with c1:
        st.subheader(f"📰 动态 ({len(display_news)})")
        for n in display_news:
            cls = "intl-highlight" if "intl" in n['cats'] else ("policy-highlight" if "policy" in n['cats'] else "market-highlight")
            tag_txt = "🌏 国际" if "intl" in n['cats'] else ("🏛️ 政策" if "policy" in n['cats'] else "📰 市场")
            tag_cls = "tag-intl" if "intl" in n['cats'] else ("tag-policy" if "policy" in n['cats'] else "tag-source")
            
            # 强制 target="_blank"
            st.markdown(f"""
            <div class="news-card {cls}">
                <a href="{n['link']}" target="_blank" class="news-title">{n['title']}</a>
                <div class="meta-row">
                    <span class="tag {tag_cls}">{tag_txt}</span>
                    <span class="tag tag-source">{n['source']}</span>
                    <span>{n['date']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 右侧：标的
    with c2:
        st.subheader("📊 重点标的 (Alpha Picks)")
        st.caption(f"覆盖美股 ({len([s for s in stocks_10 if s['info']['region']=='US'])}) + A/港股 ({len([s for s in stocks_10 if s['info']['region']=='CN'])})")
        
        for s in stocks_10:
            info = s['info']
            p = s.get('price', 0)
            chg = s.get('change', 0)
            clr = "up" if chg >= 0 else "down"
            arr = "▲" if chg >= 0 else "▼"
            
            st.markdown(f"""
            <div class="stock-card">
                <div class="stock-header">
                    <div>
                        <span class="stock-name">{info['name']}</span>
                        <span class="stock-tag">{info['tag']}</span>
                        <span class="stock-code">{info['symbol']}</span>
                    </div>
                    <div style="text-align:right;">
                        <div class="price-val {clr}">{p:.2f}</div>
                        <div class="price-chg {clr}">{arr} {chg:.2f}%</div>
                    </div>
                </div>
                <div style="font-size:11px; color:#666; margin-top:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                    ⚡ {s['drivers'][0] if s['drivers'] else '行业核心资产'}
                </div>
            </div>
            """, unsafe_allow_html=True)


