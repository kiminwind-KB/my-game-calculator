import streamlit as st
import pandas as pd

st.set_page_config(page_title="🎮 遊戲經驗值計算器", layout="wide")
st.title("🎮 遊戲經驗值與升級時間計算器")

# ----------------- 讀取 Google 試算表經驗表 -----------------
# ⚠️ 請確保下方的網址是你複製的 Google 試算表 CSV 網址
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ11wmn8osfoi5iYAQd0qqpHZi0VYf6Al3XjTRSL1eTMllTN-LJnNVMCly9sCXOsF477G2w93fOYC1P/pub?gid=1149696631&single=true&output=csv"

@st.cache_data(ttl=60)  # 快取功能，每 60 秒才會重新向 Google 抓一次資料，避免網頁變慢
def load_experience_table():
    try:
        # 直接讀取網址，Pandas 會自動保留你在 Excel/Google 試算表算好的公式結果
        data = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        return data
    except Exception as e:
        st.error(f"無法讀取線上經驗表，請檢查網址或網路連線。錯誤訊息: {e}")
        return None
# -----------------------------------------------------------

# 1. 讀取 Google 試算表資料
exp_df = load_experience_table()

if exp_df is not None:
    # 清洗與確保資料格式正確
    try:
        # 精準對齊你試算表的藍色標頭文字
        level_col = "等級"
        speed_ratio_col = "每小時平均經驗值"
        req_hours_col = "需要幾個小時升級"
        
        exp_df[level_col] = exp_df[level_col].astype(int)
        exp_df[speed_ratio_col] = exp_df[speed_ratio_col].astype(float)
        exp_df[req_hours_col] = exp_df[req_hours_col].astype(float)
        
        # 將資料改為由小到大排序（從 51 等排到 86 等）
        exp_df = exp_df.sort_values(by=level_col).reset_index(drop=True)
        
    except Exception as e:
        st.error(f"試算表欄位名稱不符，請確認頂部文字是否與試算表完全相同。錯誤: {e}")
        st.info(f"目前偵測到的試算表欄位有：{list(exp_df.columns)}")
        st.stop()

    # 顯示原始資料表供對照
    with st.expander("🔍 查看完整線上倍率對照表"):
        st.dataframe(exp_df, use_container_width=True)
        if st.button("🔄 立即重新整理試算表資料"):
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("---")
    st.subheader("🧮 升級時間試算（依據 80 等基數倍率換算）")

    # 2. 使用者輸入區
    available_levels = sorted(exp_df[level_col].unique())
    
    # 第一列：等級與進度
    col1, col2 = st.columns(2)
    with col1:
        current_lvl = st.selectbox("1️⃣ 選擇你目前的【當前等級】", available_levels, index=available_levels.index(85) if 85 in available_levels else 0)
    with col2:
        current_pct = st.number_input("2️⃣ 輸入【當前等級進度 (%)】", min_value=0.0, max_value=99.9, value=0.0, step=1.0)
        
    # 第二列：當前時速與目標等級
    col3, col4 = st.columns(2)
    with col3:
        # 讓使用者填入當前體感的時速 %
        user_speed_input = st.number_input(f"3️⃣ 輸入在 Lv.{current_lvl} 【目前每小時獲得的經驗 %】", min_value=0.0001, value=50.0, step=1.0, format="%.4f")
    with col4:
        # 目標等級必須大於當前等級
        target_levels = [lvl for lvl in available_levels if lvl > current_lvl]
        if target_levels:
            target_lvl = st.selectbox("4️⃣ 選擇你的【目標等級】", target_levels, index=0)
        else:
            st.warning("⚠️ 已達經驗表最高等級，無法設定更高的目標。")
            target_lvl = None

    # 第三列：經驗加成選項
    st.markdown("##### 🪙 經驗加成設定")
    col5, col6 = st.columns(2)
    with col5:
        current_bonus = st.number_input("當前「經驗加成面板 % 數」", min_value=0.0, value=400.0, step=10.0, help="指你目前測出時速時，面板上的總加成百分比（例如 400%）")
    with col6:
        additional_bonus = st.number_input("增加「經驗加成 % 數」", min_value=0.0, value=50.0, step=10.0, help="指你預計要額外開啟的加倍券或活動加成（例如增加 50%）")

    # 3. 核心倍率與加成換算邏輯
    if target_lvl and user_speed_input > 0:
        # 撈出當前等級的資料
        current_rows = exp_df[exp_df[level_col] == current_lvl]
        if not current_rows.empty:
            # 修正後的安全資料提取語法
            current_speed_ratio = float(current_rows.iloc[0][speed_ratio_col])
        else:
            st.error(f"找不到等級 {current_lvl} 的資料。")
            st.stop()
        
        # 💡 依據你的公式計算新增加成後的實質增幅倍率
        bonus_multiplier = ((current_bonus + 100.0) + additional_bonus) / (current_bonus + 100.0)
        
        # 套用增幅倍率，計算出「新增加成後的實際新時速 %」
        adjusted_user_speed = user_speed_input * bonus_multiplier
        
        # 逆推還原出 80 等時的基準時速 %（使用調整後的時速）
        player_efficiency = adjusted_user_speed / current_speed_ratio
        
        total_hours = 0.0
        calculation_details = []
        
        # 逐個等級連鎖計算
        for lvl in range(current_lvl, target_lvl):
            lvl_rows = exp_df[exp_df[level_col] == lvl]
            
            if not lvl_rows.empty:
                # 正確取得該等級的倍率
                lvl_speed_ratio = float(lvl_rows.iloc[0][speed_ratio_col])
                
                # 依據 80 等基準時速，推算出在該等級的實際新時速 %
                calculated_speed_pct = player_efficiency * lvl_speed_ratio
                
                # 判斷該等級需要練多少進度 %
                if lvl == current_lvl:
                    needed_pct = 100.0 - current_pct
                else:
                    needed_pct = 100.0
                
                # 計算時間：需要練的 % / 每小時實際新 %
                hours_for_this_lvl = needed_pct / calculated_speed_pct
                total_hours += hours_for_this_lvl
                
                calculation_details.append({
                    "等級區間": f"Lv.{lvl} ➔ Lv.{lvl+1}",
                    "推算新實際時速": f"{calculated_speed_pct:.4f}% / 小時",
                    "剩餘需練進度": f"{needed_pct:.1f}%",
                    "預估所需時間": f"{hours_for_this_lvl:.2f} 小時"
                })
        
        # 4. 漂亮的結果呈現
        st.info(f"📊 **從 Lv.{current_lvl} ({current_pct}%) 到 Lv.{target_lvl} 的計算結果：**")
        
        # 顯示加成稀釋說明
        st.markdown(f"""
        💡 **經驗增幅分析：**
        * 額外增加 `{additional_bonus}%` 加成後，對你目前的面板實質提升了 **{((bonus_multiplier-1)*100):.2f}%** 的總經驗速度。
        * 你的每小時時速從原本的 `{user_speed_input:.2f}%` 提升到了 **`{adjusted_user_speed:.2f}%`**。
        """)
        
        # 換算總時間成 XX 小時 XX 分鐘
        total_int_hours = int(total_hours)
        total_minutes = int((total_hours - total_int_hours) * 60)
        
        if total_int_hours > 0:
            st.success(f"⏳ 開啟新加成後，預計總共需要 **{total_int_hours} 小時 {total_minutes} 分鐘** 才能達成目標！")
        else:
            st.success(f"⏳ 開啟新加成後，預計總共需要 **{total_minutes} 分鐘** 才能達成目標！")
        
        # 顯示每等級的拆解明細面板
        with st.expander("📋 檢視各等級「全新時速」與時間拆解明細"):
            st.table(pd.DataFrame(calculation_details))
