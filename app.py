import streamlit as st
import feedparser
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from dateutil import parser
import textwrap 

# ==========================================
# 1. 系统配置与样式 (UI/UX)
# ==========================================
st.set_page_config(
    page_title="CloudPulse Gov | 全球云产业雷达",
    page_icon="🌩️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 样式表：保持了之前的修复，针对国际板块增加了紫色调
st.markdown("""
<style>
    body { font-family: "Helvetica Neue", Helvetica, Arial, "Microsoft Yahei", sans-serif; }
    
    /* --- 左侧：新闻卡片 --- */
    .news-card {
        background-color: #ffffff;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
    }
    .news-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-color: #bfdbfe; }
    
    .policy-highlight { border-left: 4px solid #dc2626; background: #fffbfb; } /* 政策红 */
    .market-highlight { border-left: 4px solid #2563eb; } /* 市场蓝 */
    .intl-highlight { border-left: 4px solid #7c3aed; background: #fbf8ff; } /* 国际紫 */
    
    .news-title { font-size: 15px; font-weight: 700; color: #1e293b; text-decoration: none; line-height: 1.5; display: block; margin-bottom: 8px; }
    .news-title:hover { color: #2563eb; }
    
    .meta-row { font-size: 12px; color: #64748b; display: flex; align-items: center; gap: 8px; }
    .tag { padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 10px; }
    .tag-policy { background: #fee2e2; color: #991b1b; }
    .tag-intl { background: #f3e8ff; color: #6b21a8; border: 1px solid #e9d5ff; }
    .tag-source { background: #f1f5f9; color: #475569; }

    /* --- 右侧：标的卡片 --- */
    .stock-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stock-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .stock-name { font-size: 18px; font-weight: 800; color: #0f172a; }
    .stock-code { font-size: 12px; color: #94a3b8; font-family: monospace; margin-left: 6px; }
    .stock-tag { background: #eff6ff; color: #1d4ed8; font-size: 10px; padding: 2px 6px; border-radius: 4px; margin-left: 8px; vertical-align: middle; font-weight: 600; }
    
    .price-box { text-align: right; }
    .price-val { font-size: 20px; font-weight: 700; font-family: "Roboto", sans-serif; }
    .price-chg { font-size: 13px; font-weight: 600; }
    
    .driver-box { background: #f8fafc; border-radius: 6px; padding: 10px; margin-top: 12px; border: 1px solid #f1f5f9; }
    .driver-head { font-size: 11px; font-weight: 700; color: #64748b; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
    .driver-item { font-size: 12px; color: #334155; line-height: 1.4; margin-bottom: 4px; display: flex; }
    .driver-item::before { content: "•"; color: #cbd5e1; margin-right: 8px; flex-shrink: 0; }

    .up { color: #dc2626; } /* A股红涨 */
    .down { color: #16a34a; } /* A股绿跌 */
    /* 注意：美股通常绿涨红跌，这里统一用A股习惯（红涨）以免混淆 */
    
    /* --- 研报模式样式 --- */
    .report-container { background: white; padding: 40px; border-radius: 4px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); max-width: 900px; margin: 0 auto; border-top: 10px solid #b91c1c; }
    .report-header { text-align: center; border-bottom: 2px solid #eee; padding-bottom: 20px; margin-bottom: 20px; }
    .report-h1 { font-size: 28px; font-weight: bold; color: #b91c1c; margin-bottom: 5px; }
    .report-sub { color: #666; font-size: 14px; }
    .report-section { margin-bottom: 25px; }
    .report-h2 { font-size: 18px; font-weight: bold; color: #991b1b; border-left: 4px solid #991b1b; padding-left: 10px; margin-bottom: 10px; background: #fff1f2; padding-top: 5px; padding-bottom: 5px; }
    .report-ul { list-style-type: disc; padding-left: 20px; color: #333; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心配置：映射表与关键词
# ==========================================
TRUSTED_SOURCES = [
    "新华", "人民网", "央视", "CCTV", "求是", "中国政府网", 
    "证券时报", "中国证券报", "上海证券报", "证券日报", 
    "财新", "第一财经", "每日经济新闻", "21世纪经济报道", "界面新闻", "澎湃", "经济日报", "金融界",
    "Reuters", "路透", "Bloomberg", "彭博", "CNBC", "Wall Street Journal", "WSJ",
    "36氪", "钛媒体", "智东西", "TechCrunch", "VentureBeat"
]

SECTOR_MAPPING = {
    # === 全球核心龙头 (Global Giants) ===
    # 显式增加美股巨头，确保国际新闻有标的承接
    "NVIDIA": [{"name": "NVIDIA", "symbol": "NVDA", "tag": "AI算力霸主"}],
    "英伟达": [{"name": "NVIDIA", "symbol": "NVDA", "tag": "AI算力霸主"}],
    "Microsoft": [{"name": "Microsoft", "symbol": "MSFT", "tag": "Azure/OpenAI"}],
    "微软": [{"name": "Microsoft", "symbol": "MSFT", "tag": "Azure/OpenAI"}],
    "OpenAI": [{"name": "Microsoft", "symbol": "MSFT", "tag": "Azure/OpenAI"}], # OpenAI新闻映射到微软
    "AWS": [{"name": "Amazon", "symbol": "AMZN", "tag": "Cloud No.1"}],
    "亚马逊": [{"name": "Amazon", "symbol": "AMZN", "tag": "Cloud No.1"}],
    "Google": [{"name": "Google", "symbol": "GOOGL", "tag": "Cloud/Gemini"}],
    "谷歌": [{"name": "Google", "symbol": "GOOGL", "tag": "Cloud/Gemini"}],
    "Oracle": [{"name": "Oracle", "symbol": "ORCL", "tag": "Database Cloud"}],
    "甲骨文": [{"name": "Oracle", "symbol": "ORCL", "tag": "Database Cloud"}],

    # === 国内政策与国资 ===
    "政策": [{"name": "深桑达A", "symbol": "000032.SZ", "tag": "中国电子云"}],
    "工信部": [{"name": "中国电信", "symbol": "601728.SS", "tag": "数字基建"}, {"name": "中国移动", "symbol": "600941.SS", "tag": "算力网络"}],
    "数据局": [{"name": "云赛智联", "symbol": "600602.SS", "tag": "上海数据"}, {"name": "易华录", "symbol": "300212.SZ", "tag": "数据湖"}],
    
    # === 国内核心硬科技 ===
    "CPO": [{"name": "中际旭创", "symbol": "300308.SZ", "tag": "光模块龙一"}, {"name": "新易盛", "symbol": "300502.SZ", "tag": "LPO技术"}],
    "液冷": [{"name": "英维克", "symbol": "002837.SZ", "tag": "精密温控"}, {"name": "曙光数创", "symbol": "872808.BJ", "tag": "浸没式"}],
    "服务器": [{"name": "浪潮信息", "symbol": "000977.SZ", "tag": "AI服务器"}, {"name": "中科曙光", "symbol": "603019.SS", "tag": "国产超算"}],
}

# 关键词分类器
POLICY_KWS = ["印发", "通知", "计划", "白皮书", "十四五", "工信部", "发改委", "数据局", "指南", "建设"]
# 扩充国际关键词，包含中文名
INTL_KWS = ["AWS", "Azure", "Google", "OpenAI", "NVIDIA", "AMD", "Oracle", "美股", "全球", "英伟达", "微软", "谷歌", "亚马逊", "甲骨文"]
RISK_KWS = ["警示", "立案", "处罚", "下跌", "亏损", "放缓", "裁员", "危机", "延迟", "制裁", "禁令"]

# ==========================================
# 3. 数据逻辑
# ==========================================

def check_category(title):
    """判断新闻类别"""
    cats = []
    # 优先判定国际，包含大厂名字即视为国际
    if any(k in title for k in INTL_KWS): cats.append("intl")
    if any(k in title for k in POLICY_KWS): cats.append("policy")
    if any(k in title for k in RISK_KWS): cats.append("risk")
    return cats

@st.cache_data(ttl=900)
def fetch_data():
    """获取数据核心函数"""
    # 构造强大的搜索串：覆盖国内关键词 + 国际巨头的中英文名
    # 注意：Google RSS search string 有长度限制，挑选最核心的
    query = "云计算 OR 算力 OR 阿里云 OR 华为云 OR 英伟达 OR NVIDIA OR 微软 OR Microsoft OR AWS OR OpenAI OR Google OR 谷歌 OR Oracle when:7d"
    encoded_query = query.replace(" ", "+")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    
    feed = feedparser.parse(rss_url)
    cleaned_data = []
    seen_titles = set()
    
    now_naive = datetime.now()
    cutoff_date = now_naive - timedelta(days=7)
    
    for entry in feed.entries:
        try:
            pub_date = parser.parse(entry.published)
            # 时区修复：统一转为无时区时间比较
            if pub_date.replace(tzinfo=None) < cutoff_date: continue
            
            src = entry.source.title if hasattr(entry, 'source') else ""
            if not any(t in src for t in TRUSTED_SOURCES): continue
            
            if entry.title in seen_titles: continue
            seen_titles.add(entry.title)
            
            cats = check_category(entry.title)
            
            cleaned_data.append({
                "title": entry.title,
                "link": entry.link,
                "date": pub_date.strftime("%m-%d"),
                "source": src,
                "categories": cats,
                "timestamp": pub_date.timestamp()
            })
        except: continue
        
    cleaned_data.sort(key=lambda x: x['timestamp'], reverse=True)
    return cleaned_data

def get_market_snapshot(news_data):
    """生成标的数据和行情"""
    targets = {}
    for news in news_data:
        # 遍历映射表，支持中文关键词（如“英伟达”）映射到美股（NVDA）
        for kw, stocks in SECTOR_MAPPING.items():
            if kw in news['title']:
                for s in stocks:
                    sym = s['symbol']
                    if sym not in targets:
                        targets[sym] = {"info": s, "drivers": set()}
                    targets[sym]['drivers'].add(f"{news['date']} {news['source']}: {news['title']}")
    
    # 获取行情
    if targets:
        symbols = list(targets.keys())
        try:
            # yfinance 支持混合查询，如 "000032.SZ NVDA MSFT"
            tickers = yf.Tickers(" ".join(symbols))
            for sym in symbols:
                try:
                    h = tickers.tickers[sym].history(period="1d")
                    if not h.empty:
                        curr = h['Close'].iloc[-1]
                        prev = tickers.tickers[sym].info.get('previousClose', h['Open'].iloc[-1])
                        chg = ((curr - prev) / prev) * 100 if prev else 0
                        targets[sym]['price'] = curr
                        targets[sym]['change'] = chg
                    else:
                        targets[sym]['price'] = 0; targets[sym]['change'] = 0
                except:
                    targets[sym]['price'] = 0; targets[sym]['change'] = 0
        except: pass
        
    return list(targets.values())

# ==========================================
# 4. 报告生成器 (Report Generator)
# ==========================================
def generate_weekly_report_md(news_data, stock_data):
    """生成 Markdown 格式的周报"""
    today_str = datetime.now().strftime("%Y年%m月%d日")
    
    # 1. 筛选内容
    policy_news = [n for n in news_data if "policy" in n['categories']][:5]
    intl_news = [n for n in news_data if "intl" in n['categories']][:6] # 增加国际新闻显示数量
    # 国内新闻排除 purely intl
    domestic_news = [n for n in news_data if "intl" not in n['categories']][:8] 
    
    # 2. 计算风险/机会
    risks = []
    opps = []
    for s in stock_data:
        name = s['info']['name']
        chg = s.get('change', 0)
        if chg < -2.0:
            risks.append(f"**{name}** 下跌 {chg:.2f}%，关注回调风险。")
        elif chg > 2.0:
            opps.append(f"**{name}** 上涨 {chg:.2f}%，市场资金关注度高。")
            
    # 3. 组装 Markdown
    md = f"""
    <div class="report-container">
        <div class="report-header">
            <div class="report-h1">云计算行业行研周报</div>
            <div class="report-sub">【资讯速递】 第 {datetime.now().isocalendar()[1]} 期 | {today_str}</div>
        </div>

        <div class="report-section">
            <div class="report-h2">核心动态概览</div>
            <ul class="report-ul">
                <li><b>本周焦点：</b>AI算力军备竞赛持续升级，国际巨头(NVIDIA/MSFT)动向与国内政策共振。</li>
                <li><b>政策面：</b>共监测到 <b>{len(policy_news)}</b> 条行业重磅政策/官方动态。</li>
                <li><b>国际面：</b>重点关注 <b>英伟达、微软、OpenAI</b> 等全球龙头的技术路线与资本开支变化。</li>
            </ul>
        </div>

        <div class="report-section">
            <div class="report-h2">国际重点行业速递 (Global Giants)</div>
            <ul class="report-ul">
    """
    for n in intl_news:
        md += f"<li><b>[{n['source']}]</b> {n['title']}</li>"
    if not intl_news: md += "<li>本周暂无重大国际云计算突发新闻。</li>"
    
    md += """
            </ul>
        </div>

        <div class="report-section">
            <div class="report-h2">国内重点行业信息</div>
            <ul class="report-ul">
    """
    for n in domestic_news:
         md += f"<li><b>[{n['source']}]</b> {n['title']}</li>"
    
    md += """
            </ul>
        </div>

        <div class="report-section">
            <div class="report-h2">业务机会与风险提示</div>
            <ul class="report-ul">
                <li><b>行业提示：</b>关注美股科技巨头财报对国内算力产业链的映射效应。</li>
    """
    for r in risks: md += f"<li>{r}</li>"
    for o in opps: md += f"<li>{o}</li>"
    
    md += """
            </ul>
        </div>
        
        <div style="text-align:center; margin-top:40px; color:#999; font-size:12px;">
            CloudPulse Gov 系统自动生成 | 仅供内部研究参考
        </div>
    </div>
    """
    return md

# ==========================================
# 5. 主页面逻辑
# ==========================================

# --- Sidebar ---
with st.sidebar:
    st.title("📡 信号控制台")
    
    # 分类选择器
    view_mode = st.radio(
        "情报视图选择",
        ["⚡ 实时资讯流", "🌏 国际重点 (巨头)", "🇨🇳 国内重点 (政策)", "⚠️ 机会与风险", "📝 资讯整理汇总 (周报)"],
        index=0
    )
    
    st.divider()
    st.info(f"当前模式：{view_mode}")
    if st.button("🔄 刷新全网数据"):
        st.cache_data.clear()
        st.rerun()

# --- Data Load ---
news_all = fetch_data()
stocks_all = get_market_snapshot(news_all)

# --- View Logic ---

# Mode: 资讯整理汇总 (周报生成)
if "资讯整理汇总" in view_mode:
    st.title("📑 行业深度周报")
    st.markdown("自动生成类似券商研报风格的汇总，支持直接复制用于汇报。")
    report_html = generate_weekly_report_md(news_all, stocks_all)
    st.markdown(report_html, unsafe_allow_html=True)

# Mode: 仪表盘模式
else:
    st.title("CloudPulse Gov 🏛️")
    st.caption("权威信源驱动的云计算政策与市场监测系统")

    # 过滤逻辑
    filtered_news = []
    if "实时资讯流" in view_mode:
        filtered_news = news_all
    elif "国际" in view_mode:
        filtered_news = [n for n in news_all if "intl" in n['categories']]
    elif "国内" in view_mode:
        filtered_news = [n for n in news_all if "intl" not in n['categories']]
    elif "机会与风险" in view_mode:
        filtered_news = [n for n in news_all if "risk" in n['categories'] or "policy" in n['categories']]

    col_news, col_alpha = st.columns([0.55, 0.45], gap="large")

    # === 左侧：动态新闻 ===
    with col_news:
        st.subheader(f"📰 {view_mode.split(' ')[1]} ({len(filtered_news)})")
        
        if not filtered_news:
            st.info("当前分类下暂无过去一周的重大资讯。")
        
        for news in filtered_news:
            # 样式判定
            style_cls = ""
            tag_html = ""
            
            if "intl" in news['categories']:
                style_cls = "intl-highlight"
                tag_html = '<span class="tag tag-intl">🌏 国际龙头</span>'
            elif "policy" in news['categories']:
                style_cls = "policy-highlight"
                tag_html = '<span class="tag tag-policy">🏛️ 政策</span>'
            else:
                style_cls = "market-highlight"
                tag_html = '<span class="tag tag-source">📰 市场</span>'
            
            # 使用 textwrap.dedent 消除缩进，解决源码泄露问题
            html_content = textwrap.dedent(f"""
                <div class="news-card {style_cls}">
                    <a href="{news['link']}" target="_blank" class="news-title">{news['title']}</a>
                    <div class="meta-row">
                        {tag_html}
                        <span class="tag tag-source">{news['source']}</span>
                        <span>{news['date']}</span>
                    </div>
                </div>
            """).strip()
            
            st.markdown(html_content, unsafe_allow_html=True)

    # === 右侧：标的推荐 (仅在非周报模式显示) ===
    with col_alpha:
        st.subheader("📊 关联标的 (Alpha Picks)")
        
        if not stocks_all:
            st.write("暂无关联标的数据。")
        
        # 根据涨跌幅排序
        sorted_stocks = sorted(stocks_all, key=lambda x: abs(x.get('change', 0)), reverse=True)
        
        for item in sorted_stocks:
            info = item['info']
            price = item.get('price', 0)
            change = item.get('change', 0)
            
            # 颜色
            # 统一逻辑：红色(+)/绿色(-)
            c_class = "up" if change >= 0 else "down"
            sign = "+" if change >= 0 else ""
            arrow = "▲" if change >= 0 else "▼"
            
            # 驱动因子 (取前2个)
            drivers = list(item['drivers'])[:2]
            drivers_html = "".join([f'<div class="driver-item">{d[:40]}..</div>' for d in drivers])
            
            # 卡片 HTML
            card_html = textwrap.dedent(f"""
                <div class="stock-card">
                    <div class="stock-header">
                        <div>
                            <span class="stock-name">{info['name']}</span>
                            <span class="stock-tag">{info['tag']}</span>
                            <div class="stock-code">{info['symbol']}</div>
                        </div>
                        <div class="price-box">
                            <div class="price-val {c_class}">{price:.2f}</div>
                            <div class="price-chg {c_class}">{arrow} {sign}{change:.2f}%</div>
                        </div>
                    </div>
                    <div class="driver-box">
                        <div class="driver-head">⚡ LOGIC / EVENTS</div>
                        {drivers_html}
                    </div>
                </div>
            """).strip()
            
            st.markdown(card_html, unsafe_allow_html=True)