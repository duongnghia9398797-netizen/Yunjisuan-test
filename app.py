import streamlit as st
import feedparser
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from dateutil import parser
import textwrap 

# ==========================================
# 1. 系统配置与样式
# ==========================================
st.set_page_config(
    page_title="CloudPulse Gov | 全球云产业雷达",
    page_icon="🌩️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; }
    
    /* 左侧新闻 */
    .news-card { background: #fff; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.03); }
    .news-card:hover { transform: translateY(-1px); box-shadow: 0 4px 8px rgba(0,0,0,0.08); border-color: #bfdbfe; }
    .policy-highlight { border-left: 4px solid #dc2626; background: #fffbfb; }
    .market-highlight { border-left: 4px solid #2563eb; }
    .intl-highlight { border-left: 4px solid #7c3aed; background: #fbf8ff; }
    
    .news-title { font-size: 15px; font-weight: 700; color: #1e293b; text-decoration: none; display: block; margin-bottom: 6px; }
    .meta-row { font-size: 12px; color: #64748b; display: flex; align-items: center; gap: 8px; }
    .tag { padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 10px; }
    .tag-policy { background: #fee2e2; color: #991b1b; }
    .tag-intl { background: #f3e8ff; color: #6b21a8; }
    .tag-source { background: #f1f5f9; color: #475569; }

    /* 右侧标的 */
    .stock-card { background: #fff; border-radius: 8px; padding: 12px; margin-bottom: 10px; border: 1px solid #e2e8f0; }
    .stock-header { display: flex; justify-content: space-between; align-items: center; }
    .stock-name { font-size: 16px; font-weight: 800; color: #0f172a; }
    .stock-code { font-size: 12px; color: #94a3b8; font-family: monospace; margin-left: 5px; }
    .stock-tag { background: #eff6ff; color: #1d4ed8; font-size: 10px; padding: 1px 5px; border-radius: 3px; margin-left: 5px; font-weight: 600; }
    .price-val { font-size: 18px; font-weight: 700; }
    .price-chg { font-size: 12px; font-weight: 600; }
    
    .up { color: #dc2626; }
    .down { color: #16a34a; }
    
    /* 研报专用样式 (修复渲染问题) */
    .report-box { background: white; padding: 30px; border-radius: 4px; border-top: 8px solid #b91c1c; max-width: 900px; margin: 0 auto; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    .r-header { text-align: center; border-bottom: 1px solid #eee; padding-bottom: 15px; margin-bottom: 20px; }
    .r-title { font-size: 24px; font-weight: bold; color: #b91c1c; }
    .r-date { color: #666; font-size: 12px; margin-top: 5px; }
    .r-sec { margin-bottom: 20px; }
    .r-h2 { font-size: 16px; font-weight: bold; color: #991b1b; background: #fff1f2; padding: 5px 10px; border-left: 4px solid #991b1b; margin-bottom: 8px; }
    .r-ul { padding-left: 20px; font-size: 14px; line-height: 1.6; color: #333; }
    .r-li { margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心数据池 (含保底名单)
# ==========================================
TRUSTED_SOURCES = ["新华", "人民网", "央视", "CCTV", "证券时报", "中国证券报", "上海证券报", "证券日报", "财新", "第一财经", "Reuters", "路透", "Bloomberg", "彭博", "CNBC", "WSJ", "36氪", "钛媒体", "智东西"]

# 新闻映射表 (News Driven)
SECTOR_MAPPING = {
    # US
    "NVIDIA": {"name": "NVIDIA", "symbol": "NVDA", "tag": "AI算力", "region": "US"},
    "英伟达": {"name": "NVIDIA", "symbol": "NVDA", "tag": "AI算力", "region": "US"},
    "Microsoft": {"name": "Microsoft", "symbol": "MSFT", "tag": "Azure", "region": "US"},
    "微软": {"name": "Microsoft", "symbol": "MSFT", "tag": "Azure", "region": "US"},
    "OpenAI": {"name": "Microsoft", "symbol": "MSFT", "tag": "Azure", "region": "US"},
    "AWS": {"name": "Amazon", "symbol": "AMZN", "tag": "Cloud No.1", "region": "US"},
    "Google": {"name": "Google", "symbol": "GOOGL", "tag": "Gemini", "region": "US"},
    "Oracle": {"name": "Oracle", "symbol": "ORCL", "tag": "Database", "region": "US"},
    # CN
    "工信部": {"name": "中国电信", "symbol": "601728.SS", "tag": "数字基建", "region": "CN"},
    "算力网": {"name": "中国移动", "symbol": "600941.SS", "tag": "算力网络", "region": "CN"},
    "数据局": {"name": "易华录", "symbol": "300212.SZ", "tag": "数据湖", "region": "CN"},
    "CPO": {"name": "中际旭创", "symbol": "300308.SZ", "tag": "光模块", "region": "CN"},
    "液冷": {"name": "英维克", "symbol": "002837.SZ", "tag": "液冷", "region": "CN"},
    "服务器": {"name": "浪潮信息", "symbol": "000977.SZ", "tag": "AI服务器", "region": "CN"},
    "华为": {"name": "软通动力", "symbol": "301236.SZ", "tag": "鸿蒙欧拉", "region": "CN"},
}

# 保底池：当新闻不足时，从这里补充 (Fallback)
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
    """
    生成标的列表，强制执行 3(US) : 7(CN) 比例，总数约 10 个
    """
    # 1. 提取新闻驱动的标的
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

    # 2. 补充标的 (Fallback Logic)
    
    # 目标：美股凑够 3 个
    final_us = list(driven_us.values())
    existing_us_syms = [x['info']['symbol'] for x in final_us]
    for stock in FALLBACK_POOL_US:
        if len(final_us) >= 3: break
        if stock['symbol'] not in existing_us_syms:
            final_us.append({"info": stock, "drivers": ["行业龙头 / 核心关注对象"]})
            
    # 目标：A股/港股凑够 7 个
    final_cn = list(driven_cn.values())
    existing_cn_syms = [x['info']['symbol'] for x in final_cn]
    for stock in FALLBACK_POOL_CN:
        if len(final_cn) >= 7: break
        if stock['symbol'] not in existing_cn_syms:
            final_cn.append({"info": stock, "drivers": ["行业龙头 / 核心关注对象"]})
            
    # 合并列表
    full_list = final_us + final_cn
    
    # 3. 获取行情
    if full_list:
        symbols = [x['info']['symbol'] for x in full_list]
        try:
            tickers = yf.Tickers(" ".join(symbols))
            for item in full_list:
                sym = item['info']['symbol']
                try:
                    # 获取数据
                    data = tickers.tickers[sym].history(period="1d")
                    if not data.empty:
                        curr = data['Close'].iloc[-1]
                        prev = tickers.tickers[sym].info.get('previousClose', data['Open'].iloc[-1])
                        # 防止除以0
                        if prev and prev > 0:
                            item['price'] = curr
                            item['change'] = ((curr - prev) / prev) * 100
                        else:
                            item['price'] = curr; item['change'] = 0
                    else:
                         item['price'] = 0; item['change'] = 0
                except:
                    item['price'] = 0; item['change'] = 0
        except: pass
        
    return full_list

def generate_report_html(news, stocks):
    """生成修复了缩进问题的HTML报告"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 准备数据
    us_news = [n for n in news if "intl" in n['cats']][:5]
    cn_news = [n for n in news if "intl" not in n['cats']][:8]
    
    us_html = "".join([f"<li class='r-li'><b>[{n['source']}]</b> {n['title']}</li>" for n in us_news]) or "<li>暂无重大国际新闻</li>"
    cn_html = "".join([f"<li class='r-li'><b>[{n['source']}]</b> {n['title']}</li>" for n in cn_news])
    
    # 风险提示
    risks = [f"<li><b>{s['info']['name']}</b> 下跌 {s['change']:.2f}%，关注风险。</li>" for s in stocks if s.get('change', 0) < -2]
    opps = [f"<li><b>{s['info']['name']}</b> 上涨 {s['change']:.2f}%，资金流入。</li>" for s in stocks if s.get('change', 0) > 2]
    risk_html = "".join(risks + opps) if (risks or opps) else "<li>市场走势相对平稳，无剧烈波动标的。</li>"

    # 使用 dedent 并在 HTML 标签内尽量不留缩进
    html = textwrap.dedent(f"""
    <div class="report-box">
        <div class="r-header">
            <div class="r-title">云计算行业深度周报</div>
            <div class="r-date">第 {datetime.now().isocalendar()[1]} 期 | {today}</div>
        </div>

        <div class="r-sec">
            <div class="r-h2">核心动态概览</div>
            <ul class="r-ul">
                <li><b>全球视野：</b>美股科技巨头 (NVDA/MSFT) 资本开支指引持续影响全球产业链。</li>
                <li><b>国内政策：</b>本周监测到 <b>{len([n for n in news if 'policy' in n['cats']])}</b> 条政策动态，重点关注算力基建与数据要素。</li>
            </ul>
        </div>

        <div class="r-sec">
            <div class="r-h2">国际重点行业速递 (Global Giants)</div>
            <ul class="r-ul">
                {us_html}
            </ul>
        </div>

        <div class="r-sec">
            <div class="r-h2">国内重点行业信息</div>
            <ul class="r-ul">
                {cn_html}
            </ul>
        </div>

        <div class="r-sec">
            <div class="r-h2">业务机会与风险提示</div>
            <ul class="r-ul">
                {risk_html}
            </ul>
        </div>
        
        <div style="text-align:center; color:#999; font-size:12px; margin-top:20px;">CloudPulse System Auto-Generated</div>
    </div>
    """).strip()
    
    return html

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
# 获取 10 个标的 (3美 + 7中)
stocks_10 = get_balanced_stocks(news_all)

# 视图逻辑
if "行业深度周报" in view_mode:
    st.title("📑 行业深度周报")
    # 直接渲染生成的 HTML
    st.markdown(generate_report_html(news_all, stocks_10), unsafe_allow_html=True)

else:
    st.title("CloudPulse Gov 🏛️")
    
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
            # 样式
            cls = "intl-highlight" if "intl" in n['cats'] else ("policy-highlight" if "policy" in n['cats'] else "market-highlight")
            tag_txt = "🌏 国际" if "intl" in n['cats'] else ("🏛️ 政策" if "policy" in n['cats'] else "📰 市场")
            tag_cls = "tag-intl" if "intl" in n['cats'] else ("tag-policy" if "policy" in n['cats'] else "tag-source")
            
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

    # 右侧：标的 (确保显示)
    with c2:
        st.subheader("📊 重点标的 (Alpha Picks)")
        st.caption("Global Giants (3) + China Core (7)")
        
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
                    ⚡ {s['drivers'][0] if s['drivers'] else '行业核心关注'}
                </div>
            </div>
            """, unsafe_allow_html=True)