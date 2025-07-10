import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pytz
from datetime import datetime, timedelta
import time

st.set_page_config(
    page_title="Smart S/R Finder Pro",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

TEHRAN_TZ = pytz.timezone('Asia/Tehran')

# --- Custom CSS for enhanced styling ---
st.markdown("""
<style>
    /* Main styling */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: #e6e6e6;
        transition: background 0.8s cubic-bezier(0.4, 0, 0.2, 1), color 0.8s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Header styling */
    .header {
        background: rgba(10, 15, 35, 0.7);
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        margin-bottom: 25px;
        border: 1px solid #4cc9f0;
        transition: background 0.6s, border 0.6s;
    }
    
    /* Card styling */
    .card {
        background: rgba(20, 25, 45, 0.7) !important;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
        border: 1px solid #4361ee;
        transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 22px rgba(67, 97, 238, 0.4);
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(45deg, #4361ee, #4cc9f0) !important;
        border: none !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
        width: 100%;
    }
    
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 15px rgba(67, 97, 238, 0.6);
    }
    
    /* Input styling */
    .stTextInput>div>div>input, 
    .stSelectbox>div>div>select,
    .stDateInput>div>div>input,
    .stTimeInput>div>div>input,
    .stNumberInput>div>div>input {
        background: rgba(30, 35, 55, 0.7) !important;
        color: white !important;
        border-radius: 8px !important;
        border: 1px solid #4361ee !important;
        transition: background 0.5s, color 0.5s, border 0.5s;
    }
    
    /* Metric styling */
    [data-testid="metric-container"] {
        background: rgba(20, 25, 45, 0.7) !important;
        border: 1px solid #4cc9f0 !important;
        border-radius: 10px;
        padding: 15px !important;
        transition: background 0.5s, border 0.5s;
    }
    
    /* Table styling */
    .dataframe {
        background: rgba(20, 25, 45, 0.7) !important;
        color: white !important;
        border-radius: 10px;
        transition: background 0.5s, color 0.5s;
    }
    
    .dataframe th {
        background: rgba(67, 97, 238, 0.5) !important;
        color: white !important;
        transition: background 0.5s, color 0.5s;
    }
    
    .dataframe td {
        background: rgba(30, 35, 55, 0.5) !important;
        transition: background 0.5s;
    }
    
    /* Tab styling */
    [data-baseweb="tab-list"] {
        gap: 10px !important;
    }
    
    [data-baseweb="tab"] {
        background: rgba(30, 35, 55, 0.7) !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        margin: 0 5px !important;
        transition: background 0.5s, border 0.5s, color 0.5s;
        border: 1px solid #4361ee !important;
    }
    
    [data-baseweb="tab"]:hover {
        background: rgba(67, 97, 238, 0.3) !important;
    }
    
    [aria-selected="true"] {
        background: linear-gradient(45deg, #4361ee, #4cc9f0) !important;
        font-weight: bold !important;
        transition: background 0.5s, color 0.5s;
    }
    
    /* Crypto icons */
    .crypto-icon {
        width: 24px;
        height: 24px;
        margin-right: 10px;
        vertical-align: middle;
        display: inline-block;
        transition: filter 0.5s;
    }
</style>
""", unsafe_allow_html=True)

# --- from utils.py ---
def validate_dates(start: datetime, end: datetime):
    """Validate that the start date is before the end date."""
    if start >= end:
        st.error("⛔ Start date must be before end date.")
        st.stop()

def to_tehran_utc(start: datetime, end: datetime):
    """Convert input dates to Tehran timezone and then to UTC for data download."""
    start_utc = TEHRAN_TZ.localize(start).astimezone(pytz.UTC)
    end_utc = TEHRAN_TZ.localize(end).astimezone(pytz.UTC)
    return start_utc, end_utc

@st.cache_data(ttl=60*15)  # Cache for 15 minutes
def download_data(symbol, start_utc, end_utc, interval, auto_adjust):
    """Cache data download from yfinance."""
    with st.spinner(f'📡 Downloading {symbol} data...'):
        df = yf.download(
            tickers=symbol,
            start=start_utc,
            end=end_utc,
            interval=interval,
            auto_adjust=auto_adjust,
            progress=False
        )
    if df.empty:
        st.error(f"❌ No data found for {symbol} in the selected time range")
        st.stop()
    df.dropna(inplace=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    df.index = df.index.tz_convert(TEHRAN_TZ)
    return df

# --- from analysis.py ---
def plot_smart_money_sr(
    symbol: str,
    df: pd.DataFrame,
    interval: str = '1h',
    left: int = 4,
    right: int = 4
):
    """
    Analyze smart support and resistance points based on swings and plot candlestick chart with annotation.
    """
    highs = df['High'].values
    lows  = df['Low'].values
    
    # Swing highs and lows
    swing_highs = [i for i in range(left, len(highs) - right) if highs[i] == highs[i-left:i+right+1].max()]
    swing_lows  = [i for i in range(left, len(lows) - right) if lows[i] == lows[i-left:i+right+1].min()]

    blocks = []
    block_details = []
    for idx in swing_highs:
        if idx > 0 and np.max(highs[:idx]) > highs[idx]:
            blocks.append(('resistance', idx))
            block_details.append({
                'Date': df.index[idx].strftime('%Y-%m-%d'),
                'Time': df.index[idx].strftime('%H:%M'),
                'Type': 'Resistance',
                'Price': df['High'].iloc[idx],
                'Candle': idx
            })
    for idx in swing_lows:
        if idx > 0 and np.min(lows[:idx]) < lows[idx]:
            blocks.append(('support', idx))
            block_details.append({
                'Date': df.index[idx].strftime('%Y-%m-%d'),
                'Time': df.index[idx].strftime('%H:%M'),
                'Type': 'Support',
                'Price': df['Low'].iloc[idx],
                'Candle': idx
            })

    # Create figure
    fig = go.Figure()
    
    # Add candlesticks with gradient colors
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name='Price',
        increasing_line_color='#2ecc71',  # Green
        decreasing_line_color='#e74c3c'   # Red
    ))
    
    # Add support/resistance annotations
    for kind, idx in blocks:
        ts = df.index[idx]
        high = df['High'].iloc[idx]
        low = df['Low'].iloc[idx]
        height = high - low
        offset_ratio = 0.2
        
        if kind == 'resistance':
            y = high + height * offset_ratio
            ay = -20
            arrow_color = "#f72585"  # Vibrant pink
            annotation_text = "RES"
        else:
            y = low - height * offset_ratio
            ay = 20
            arrow_color = "#4cc9f0"   # Bright teal
            annotation_text = "SUP"

        fig.add_annotation(
            x=ts,
            y=y,
            ax=0, ay=ay,
            xanchor='center', 
            yanchor='bottom' if kind=='resistance' else 'top',
            showarrow=True,
            arrowhead=3,
            arrowsize=1.5,
            arrowwidth=2,
            arrowcolor=arrow_color,
            standoff=10,
            opacity=0.9,
            bgcolor='rgba(10, 15, 35, 0.7)',
            bordercolor=arrow_color,
            borderwidth=1.5,
            text=annotation_text,
            font=dict(color='white', size=10)
        )
        
    # Add dynamic trend lines for support/resistance clusters
    if block_details:
        levels = {}
        tolerance = 0.01 * df['Close'].mean()  # 1% tolerance
        
        for b in block_details:
            price = b['Price']
            found = False
            for level in levels:
                if abs(level - price) < tolerance:
                    levels[level].append(b)
                    found = True
                    break
            if not found:
                levels[price] = [b]
        
        # Only plot significant levels (with at least 2 touches)
        for price, blocks in levels.items():
            if len(blocks) >= 2:
                min_date = min([datetime.strptime(b['Date'] + ' ' + b['Time'], '%Y-%m-%d %H:%M') for b in blocks])
                max_date = max([datetime.strptime(b['Date'] + ' ' + b['Time'], '%Y-%m-%d %H:%M') for b in blocks])
                
                fig.add_shape(
                    type="line",
                    x0=min_date, y0=price,
                    x1=max_date, y1=price,
                    line=dict(
                        color="#4361ee" if blocks[0]['Type'] == 'Support' else "#f72585",
                        width=2,
                        dash="dashdot",
                    ),
                    opacity=0.7
                )
    
    # Layout configuration
    fig.update_layout(
        title=dict(
            text=f"<b>{symbol} {interval} Smart Money Support & Resistance</b>",
            font=dict(size=22, color='white'),
        ),
        xaxis_title="Date (Tehran)",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        dragmode='zoom',
        hovermode='x unified',
        height=700,
        margin=dict(l=50, r=30, t=80, b=50),
        plot_bgcolor='rgba(10, 15, 35, 0.5)',
        paper_bgcolor='rgba(10, 15, 35, 0.3)',
        font=dict(color='#e6e6e6'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        transition=dict(
            duration=600,
            easing='cubic-in-out'
        )
    )
    
    fig.update_xaxes(
        tickformat='%Y-%m-%d %H:%M', 
        ticks='outside',
        gridcolor='rgba(100, 100, 100, 0.2)',
        linecolor='#4cc9f0'
    )
    
    fig.update_yaxes(
        gridcolor='rgba(100, 100, 100, 0.2)',
        linecolor='#4cc9f0'
    )
    
    # Create DataFrame from block details
    df_blocks = pd.DataFrame(block_details)
    if not df_blocks.empty:
        df_blocks = df_blocks.sort_values(by=['Date', 'Time'])
        df_blocks = df_blocks[['Date', 'Time', 'Type', 'Price', 'Candle']]
    return fig, df_blocks

CONFIG = {
    "scrollZoom": True,
    "displayModeBar": True,
    "modeBarButtonsToAdd": [
        "drawline",
        "drawopenpath",
        "drawclosedpath",
        "drawcircle",
        "drawrect",
        "eraseshape"
    ],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "smart_money_sr",
        "height": 800,
        "width": 1200,
        "scale": 2
    }
}

# Default settings based on timeframe
DEFAULTS = {
    '1m': {'left': 10, 'right': 10, 'days': 1},
    '5m': {'left': 8, 'right': 8, 'days': 3},
    '15m': {'left': 6, 'right': 6, 'days': 5},
    '30m': {'left': 5, 'right': 5, 'days': 7},
    '1h': {'left': 4, 'right': 4, 'days': 14}
}

# Comprehensive asset database
ASSET_DATABASE = {
    "Cryptocurrencies": {
        "Bitcoin": "BTC-USD",
        "Ethereum": "ETH-USD",
        "Binance Coin": "BNB-USD",
        "Ripple": "XRP-USD",
        "Cardano": "ADA-USD",
        "Solana": "SOL-USD",
        "Polkadot": "DOT-USD",
        "Dogecoin": "DOGE-USD",
        "Avalanche": "AVAX-USD",
        "Polygon": "MATIC-USD",
        "Chainlink": "LINK-USD",
        "Litecoin": "LTC-USD"
    },
    "Precious Metals": {
        "Gold": "GC=F",
        "Silver": "SI=F",
        "Platinum": "PL=F",
        "Palladium": "PA=F",
        "Copper": "HG=F"
    },
    "Energy": {
        "Crude Oil": "CL=F",
        "Brent Crude": "BZ=F",
        "Natural Gas": "NG=F",
        "Gasoline": "RB=F",
        "Heating Oil": "HO=F"
    },
    "Forex": {
        "EUR/USD": "EURUSD=X",
        "USD/JPY": "JPY=X",
        "GBP/USD": "GBPUSD=X",
        "USD/CHF": "CHF=X",
        "USD/CAD": "CAD=X",
        "AUD/USD": "AUDUSD=X",
        "USD/CNY": "CNY=X",
        "USD/IRR": "USDIRR=X"
    },
    "Indices": {
        "S&P 500": "^GSPC",
        "Dow Jones": "^DJI",
        "NASDAQ": "^IXIC",
        "FTSE 100": "^FTSE",
        "DAX": "^GDAXI",
        "Nikkei 225": "^N225",
        "Shanghai Composite": "000001.SS"
    },
    "Stocks": {
        "Apple": "AAPL",
        "Microsoft": "MSFT",
        "Google": "GOOGL",
        "Amazon": "AMZN",
        "Tesla": "TSLA",
        "Meta": "META",
        "NVIDIA": "NVDA",
        "Samsung": "005930.KS"
    }
}

# --- Page Configuration ---
# (Removed duplicate st.set_page_config block here)

# --- Header ---
st.markdown("""
<div class="header">
    <h1 style="text-align:center; color:#4cc9f0; margin-bottom:0;">SMART MONEY SUPPORT & RESISTANCE FINDER</h1>
    <p style="text-align:center; font-size:1.1rem; color:#a0aec0;">
        Advanced algorithm to detect institutional support/resistance levels using price action analysis
    </p>
</div>
""", unsafe_allow_html=True)

# --- Sidebar for Inputs ---
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding:10px; border-radius:10px; background:rgba(67, 97, 238, 0.3);">
        <h3 style="color:#4cc9f0; margin-bottom:5px;">⚙️ ANALYSIS PARAMETERS</h3>
        <p style="font-size:0.9rem;">Configure your technical analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Asset category selection
    asset_category = st.selectbox(
        '**Asset Category**',
        options=list(ASSET_DATABASE.keys()),
        index=0,
        help="Select the asset category"
    )
    
    # Symbol selection based on category
    assets = ASSET_DATABASE[asset_category]
    symbol_name = st.selectbox(
        f'**{asset_category}**',
        options=list(assets.keys()),
        index=0,
        help="Select the asset to analyze"
    )
    
    symbol = assets[symbol_name]
    
    # Timeframe selection
    interval = st.selectbox(
        '**Timeframe**', 
        options=['1m', '5m', '15m', '30m', '1h'],
        index=1,
        help="Select chart timeframe for analysis"
    )
    
    # Auto-adjust checkbox
    auto_adjust = st.checkbox('**Auto Adjust Prices**', True, 
                           help="Adjust prices for splits and dividends")
    
    # Set default days based on timeframe
    default_days = DEFAULTS[interval]['days'] if interval in DEFAULTS else 7
    end_dt = datetime.now(TEHRAN_TZ)
    start_dt = end_dt - timedelta(days=default_days)
    
    # Date inputs with intelligent defaults
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input('**Start Date**', start_dt.date())
        start_time = st.time_input('**Start Time**', datetime.strptime("00:00:00", "%H:%M:%S").time())
    with col2:
        end_date = st.date_input('**End Date**', end_dt.date())
        end_time = st.time_input('**End Time**', end_dt.time())
    
    # Swing parameters
    st.markdown("---")
    st.markdown("**⚖️ Swing Detection Parameters**")
    if interval in DEFAULTS:
        default_left = DEFAULTS[interval]['left']
        default_right = DEFAULTS[interval]['right']
    else:
        default_left = 4
        default_right = 4
        
    left = st.slider('**Left Candles**', 1, 20, default_left,
                   help="Number of candles to the left to compare")
    right = st.slider('**Right Candles**', 1, 20, default_right,
                    help="Number of candles to the right to compare")
    
    # Calculate coverage info
    time_multipliers = {'1m': 1, '5m': 5, '15m': 15, '30m': 30, '1h': 60}
    coverage_minutes = (left + right + 1) * time_multipliers.get(interval, 60)
    coverage_hours = coverage_minutes / 60
    
    st.info(f"""
    **Current Settings:**
    - Asset: {symbol_name} ({symbol})
    - Timeframe: `{interval}`
    - Swing Window: `{left}` left / `{right}` right
    - Time Coverage: ~{coverage_hours:.1f} hours
    """)
    
    # Analysis button
    if st.button('🚀 Run Smart Analysis', use_container_width=True):
        st.session_state.run_analysis = True

# --- Default state initialization ---
if 'run_analysis' not in st.session_state:
    st.session_state.run_analysis = False
    st.session_state.fig = None
    st.session_state.df_blocks = pd.DataFrame()

# --- Main Analysis Section ---
if st.session_state.run_analysis:
    start_dt = datetime.combine(start_date, start_time)
    end_dt = datetime.combine(end_date, end_time)
    
    try:
        # Date validation
        validate_dates(start_dt, end_dt)
        
        # Convert to appropriate timezone
        start_utc, end_utc = to_tehran_utc(start_dt, end_dt)
        
        # Download data
        df = download_data(symbol, start_utc, end_utc, interval, auto_adjust)
        
        # Run analysis
        with st.spinner('🔍 Detecting smart money levels...'):
            fig, df_blocks = plot_smart_money_sr(
                symbol=symbol,
                df=df,
                interval=interval,
                left=left,
                right=right
            )
            
            # Store results in session state
            st.session_state.fig = fig
            st.session_state.df_blocks = df_blocks
            st.session_state.symbol = symbol
            st.session_state.symbol_name = symbol_name
            st.session_state.interval = interval
            
    except Exception as e:
        st.error(f"❌ Error in analysis: {str(e)}")
        st.session_state.run_analysis = False

# --- Display Results ---
if st.session_state.fig is not None:
    tab1, tab2, tab3 = st.tabs(["📈 Interactive Chart", "📊 Support/Resistance Levels", "ℹ️ About This Tool"])
    
    with tab1:
        st.plotly_chart(st.session_state.fig, use_container_width=True, config=CONFIG)
        
        # Market summary metrics
        if not st.session_state.df_blocks.empty:
            support_count = len(st.session_state.df_blocks[st.session_state.df_blocks['Type'] == 'Support'])
            resistance_count = len(st.session_state.df_blocks[st.session_state.df_blocks['Type'] == 'Resistance'])
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Support Levels", support_count)
            col2.metric("Total Resistance Levels", resistance_count)
            col3.metric("Timeframe", st.session_state.interval)
            col4.metric("Asset", f"{st.session_state.symbol_name} ({st.session_state.symbol})")
    
    with tab2:
        if not st.session_state.df_blocks.empty:
            st.subheader("📋 Detected Support & Resistance Levels")
            
            # Format table
            df_display = st.session_state.df_blocks.copy()
            df_display['Price'] = df_display['Price'].apply(lambda x: f"{x:.2f}")
            
            # Show interactive table
            st.dataframe(
                df_display.style
                .applymap(lambda x: 'background-color: rgba(76, 201, 240, 0.2)' if x == 'Support' 
                          else 'background-color: rgba(247, 37, 133, 0.2)', subset=['Type'])
                .set_properties(**{'color': 'white', 'border': '1px solid #2d3741'}),
                height=min(500, 45 + len(df_display) * 35),
                use_container_width=True
            )
            
            # Download button
            csv = st.session_state.df_blocks.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="💾 Download as CSV",
                data=csv,
                file_name=f"{st.session_state.symbol}_{st.session_state.interval}_smart_levels.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("No support or resistance levels detected in the selected range")
    
    with tab3:
        st.markdown("""
        <div class="card">
            <h3>🧠 How This Tool Works</h3>
            <p>This algorithm identifies institutional support/resistance levels using price action analysis:</p>
            
            <ol>
                <li><b>Swing High Detection:</b> Finds candles with the highest high in a defined window</li>
                <li><b>Swing Low Detection:</b> Finds candles with the lowest low in a defined window</li>
                <li><b>Significance Filter:</b> Only levels that haven't been broken by prior price action are shown</li>
                <li><b>Cluster Detection:</b> Groups nearby levels into significant zones</li>
            </ol>
            
            <h3>🎯 How to Use These Levels</h3>
            <ul>
                <li><b>Support:</b> Price areas where buying interest is strong enough to overcome selling pressure</li>
                <li><b>Resistance:</b> Price areas where selling pressure overcomes buying interest</li>
                <li>Look for price reactions at these levels (bounces or breakouts)</li>
                <li>Combine with other technical indicators for confirmation</li>
            </ul>
            
            <h3>⚙️ Parameter Guidance</h3>
            <p><b>Left/Right Candles:</b> Determines sensitivity of level detection. Higher values find stronger, more significant levels.</p>
            <p><b>Timeframe:</b> Higher timeframes show more significant levels. Use multiple timeframes for confirmation.</p>
            
            <h3>📊 Supported Assets</h3>
            <p>This tool supports analysis of:</p>
            <ul>
                <li>Cryptocurrencies (Bitcoin, Ethereum, etc.)</li>
                <li>Precious Metals (Gold, Silver, etc.)</li>
                <li>Energy Commodities (Oil, Gas, etc.)</li>
                <li>Forex Pairs (EUR/USD, USD/JPY, etc.)</li>
                <li>Market Indices (S&P 500, NASDAQ, etc.)</li>
                <li>Stocks (Apple, Tesla, etc.)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# --- Info when no analysis run yet ---
else:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("""
        <div style="text-align:center; margin-top:100px;">
            <h3 style="color:#4cc9f0;">🚀 Get Started</h3>
            <p>Configure your analysis parameters in the sidebar and click "Run Smart Analysis"</p>
            <div style="margin:30px;">
                <svg width="200" height="200" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2V6" stroke="#4cc9f0" stroke-width="1.5" stroke-linecap="round"/>
                    <path d="M12 18V22" stroke="#4cc9f0" stroke-width="1.5" stroke-linecap="round"/>
                    <path d="M5 12H2" stroke="#4cc9f0" stroke-width="1.5" stroke-linecap="round"/>
                    <path d="M22 12H19" stroke="#4cc9f0" stroke-width="1.5" stroke-linecap="round"/>
                    <path d="M4.92871 4.92871L7.75736 7.75736" stroke="#4361ee" stroke-width="1.5" stroke-linecap="round"/>
                    <path d="M16.2426 16.2426L19.0713 19.0713" stroke="#4361ee" stroke-width="1.5" stroke-linecap="round"/>
                    <path d="M4.92871 19.0713L7.75736 16.2426" stroke="#f72585" stroke-width="1.5" stroke-linecap="round"/>
                    <path d="M16.2426 7.75736L19.0713 4.92871" stroke="#f72585" stroke-width="1.5" stroke-linecap="round"/>
                    <circle cx="12" cy="12" r="3" stroke="#4cc9f0" stroke-width="1.5"/>
                </svg>
            </div>
            <p><i>Detect institutional trading levels across multiple asset classes</i></p>
        </div>
        """, unsafe_allow_html=True)

# --- Footer ---
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#a0aec0; font-size:0.9rem; padding:20px;">
    <p>Smart Money S/R Finder Pro • Real-time institutional level detection • Data from Yahoo Finance</p>
    <p>Note: This is for educational purposes only. Past performance is not indicative of future results.</p>
</div>
""", unsafe_allow_html=True)