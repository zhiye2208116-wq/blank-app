import streamlit as st
import pandas as pd
import os
from datetime import datetime
import uuid

# 設定 CSV 檔案名稱
CSV_FILE = "borrow_records.csv"

# 如果檔案不存在，建立空的 DataFrame 並儲存
if not os.path.exists(CSV_FILE):
    df = pd.DataFrame(columns=["訂單編號", "姓名", "部門", "設備", "日期", "時段", "借用目的", "狀態"])
    df.to_csv(CSV_FILE, index=False)

# 讀取現有借用紀錄
df = pd.read_csv(CSV_FILE)

# Streamlit 頁面設定
st.set_page_config(page_title="廣宣攝影設備借用管理系統", layout="wide")

# 側邊欄選單
page = st.sidebar.radio("選擇功能頁面", ["借用與查詢", "歸還設備/預約取消", "後台管理"])

# -------------------------
# 借用與查詢頁面
# -------------------------
if page == "借用與查詢":
    st.title("📷 廣宣攝影設備借用與預約狀態查詢")
    st.text("現有廣宣設備主負責人：🧝‍♂️致燁🤹文欣")
    st.warning("⚠️ 1.請完整填寫姓名、部門、理由。")
    st.warning("⚠️ 2.借用申請填寫完送出，會經由負責人審核，未完整填寫會駁回申請")
    st.warning("⚠️ 3.非每天審查，如有急需請直接teams或發信洽廣宣負責人。")
    st.text("↖️點擊左上角切換至歸還或取消頁面")
    # 借用表單
    with st.form("borrow_form"):
        name = st.text_input("借用人姓名")
        department = st.text_input("借用人部門")
        equipment = st.selectbox("設備名稱", ["CANON相機", "V8", "腳架", "讀卡機"])
        date = st.date_input("借用日期", datetime.today())
        time_slots = st.multiselect("借用時段（可多選）", [f"{h}:00-{h+1}:00" for h in range(9, 18)])
        purpose = st.text_area("借用目的(務必填寫清楚)")
        submitted = st.form_submit_button("提交")

    if submitted:
        if not time_slots:
            st.error("⚠️ 請至少選擇一個時段！")
        else:
            conflict = df[(df["設備"] == equipment) & (df["日期"] == str(date)) & (df["時段"].isin(time_slots)) & (df["狀態"] == "借用中")]
            if not conflict.empty:
                st.error("⚠️ 部分選擇的時段已被預約！")
            else:
                order_id = str(uuid.uuid4())[:8]
                new_records = pd.DataFrame([[order_id, name, department, equipment, str(date), slot, purpose, "待審核"] for slot in time_slots],
                                           columns=["訂單編號", "姓名", "部門", "設備", "日期", "時段", "借用目的", "狀態"])
                df = pd.concat([df, new_records], ignore_index=True)
                df.to_csv(CSV_FILE, index=False)
                st.success(f"✅ 預約請求已送出！訂單編號：{order_id}，等待後台審核")

    # 查詢預約狀態（僅顯示待審核或借用中）
    st.subheader("📅 選擇日期查看目前預約狀態⬇️")
    selected_date = st.date_input("選擇日期", datetime.today())
    day_records = df[(df["日期"] == str(selected_date)) & (df["狀態"].isin(["待審核", "借用中"]))]

    st.write(f"{selected_date} 的時段預約狀態")
    all_slots = [f"{h}:00-{h+1}:00" for h in range(9, 18)]

    for slot in all_slots:
        booked = day_records[day_records["時段"] == slot]
        if not booked.empty:
            dept = booked.iloc[0]["部門"]
            equip = booked.iloc[0]["設備"]
            order_id = booked.iloc[0]["訂單編號"]
            status = booked.iloc[0]["狀態"]
            st.markdown(
                f"<div style='background-color:#006666;color:white;padding:8px;border-radius:5px;margin-bottom:5px;'>"
                f"{slot}<br>部門:{dept}<br>設備:{equip}<br>ID:{order_id}<br>狀態:{status}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='background-color:#e0e0e0;padding:8px;border-radius:5px;margin-bottom:5px;'>{slot}</div>",
                unsafe_allow_html=True
            )

# -------------------------
# 歸還設備頁面
# -------------------------
elif page == "歸還設備/預約取消":
    st.title("🔄 歸還設備或取消預約")
    st.warning("⚠️ 1.相機使用後請將電池充電並刪除記憶卡中資料再歸還")
    st.warning("⚠️ 2.歸還時請先將設備交付給廣宣設備管理負責人，再按下歸還/取消")
    st.warning("⚠️ 3.取消預約時請可直接按下歸還/取消")
    return_order_id = st.text_input("輸入訂單編號以歸還/取消，可用下面的功能查詢訂單編號")
    if st.button("歸還/取消"):
        mask = (df["訂單編號"] == return_order_id) & (df["狀態"] == "借用中")
        if mask.any():
            df.loc[mask, "狀態"] = "已歸還"
            df.to_csv(CSV_FILE, index=False)
            st.success("✅ 設備已歸還！")
        else:
            st.warning("⚠️ 找不到符合條件的借用紀錄或尚未審核通過。")

    # 搜尋功能
    st.subheader("🔍 搜尋借用紀錄")
    search_query = st.text_input("輸入姓名或部門進行訂單編號搜尋")
    if st.button("搜尋"):
        if search_query.strip():
            results = df[(df["姓名"].str.contains(search_query, case=False, na=False)) | (df["部門"].str.contains(search_query, case=False, na=False))]
            if not results.empty:
                st.write("搜尋結果：")
                st.dataframe(results)
            else:
                st.info("未找到符合條件的紀錄。")

# -------------------------
# 後台管理頁面
# -------------------------
elif page == "後台管理":
    st.title("🔐 後台管理")
    password = st.text_input("請輸入後台密碼", type="password")
    if password == "SNSPJ1103":
        st.success("✅ 登入成功")
        st.subheader("待審核的預約")
        pending = df[df["狀態"] == "待審核"]
        if pending.empty:
            st.info("目前沒有待審核的預約")
        else:
            for idx, row in pending.iterrows():
                st.markdown(
                    f"訂單編號: {row['訂單編號']} | 姓名: {row['姓名']} | 部門: {row['部門']} | 設備: {row['設備']} | 日期: {row['日期']} | 時段: {row['時段']} | 目的: {row['借用目的']}"
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"同意 {row['訂單編號']}"):
                        df.loc[idx, "狀態"] = "借用中"
                        df.to_csv(CSV_FILE, index=False)
                        st.success(f"✅ 訂單 {row['訂單編號']} 已審核通過")
                with col2:
                    if st.button(f"駁回 {row['訂單編號']}"):
                        df.loc[idx, "狀態"] = "已駁回"
                        df.to_csv(CSV_FILE, index=False)
                        st.warning(f"❌ 訂單 {row['訂單編號']} 已被駁回")
    elif password:
        st.error("❌ 密碼錯誤")

