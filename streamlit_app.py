
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import uuid

# 設定 CSV 檔案名稱
CSV_FILE = "borrow_records.csv"

# 如果檔案不存在，建立空的 DataFrame 並儲存
if not os.path.exists(CSV_FILE):
    df = pd.DataFrame(columns=["訂單編號", "姓名", "部門", "設備", "日期", "時段", "借用目的", "狀態", "申請時間"])
    df.to_csv(CSV_FILE, index=False)

# 讀取現有借用紀錄
df = pd.read_csv(CSV_FILE)

# Streamlit 頁面設定
st.set_page_config(page_title="攝影設備借用管理系統", layout="wide")

# 側邊欄選單
page = st.sidebar.radio("選擇功能頁面", ["借用與查詢", "歸還設備/取消預約", "後台管理"])

# -------------------------
# 借用與查詢頁面
# -------------------------
if page == "借用與查詢":
    st.title("📷 借用攝影設備與查詢預約狀態")
    st.text("現有廣宣設備主負責人：🧝‍♂️致燁🧑‍🚀文欣")
    st.markdown("""
    **注意事項：**
    1. 借用請請完整填寫姓名、部門、理由。
    2. 借用申請填寫完送出，會經由負責人審核，審核通過才能借用，未完整填寫會駁回申請。
    3. 不固定時間上來查看申請，如有急需或是借用問題請發信或 TEAMS 給 SNS PJ 擔當 致燁 / 文欣。
    4. 同時借用多個設備需分開申請。
    5. 審核通過後，請提早向廣宣負責人拿取設備。(如為整天借用，請於前一個工作日的17點前找我們)
    """, unsafe_allow_html=True)


    # 借用表單
    with st.form("borrow_form"):
        name = st.text_input("借用人姓名")
        department = st.text_input("借用人部門")
        equipment = st.selectbox("設備名稱", ["CANON相機", "V8", "腳架", "讀卡機"])
        date = st.date_input("借用日期", datetime.today())
        time_slots = st.multiselect("借用時段（可多選）", [f"{h}:00-{h+1}:00" for h in range(9, 18)])
        purpose = st.text_area("借用目的")
        submitted = st.form_submit_button("提交")

    if submitted:
        if not time_slots:
            st.error("⚠️ 請至少選擇一個時段！")
        else:
            # 衝突檢查：避免待審核或借用中重疊
            conflict = df[(df["設備"] == equipment) & (df["日期"] == str(date)) &
                          (df["時段"].isin(time_slots)) & (df["狀態"].isin(["待審核", "借用中"]))]
            if not conflict.empty:
                st.error("⚠️ 部分選擇的時段已被預約！")
            else:
                order_id = str(uuid.uuid4())[:8]
                apply_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_records = pd.DataFrame(
                    [[order_id, name, department, equipment, str(date), slot, purpose, "待審核", apply_time] for slot in time_slots],
                    columns=["訂單編號", "姓名", "部門", "設備", "日期", "時段", "借用目的", "狀態", "申請時間"]
                )
                df = pd.concat([df, new_records], ignore_index=True)
                df.to_csv(CSV_FILE, index=False)
                st.success(f"✅ 預約請求已送出！訂單編號：{order_id}，等待後台審核")

    # 查詢預約狀態（新增設備分類）
    st.subheader("📅 選擇日期與設備查看預約狀態")
    st.warning(" 可查詢：審核是否通過、預約狀態、歸還狀態")
    selected_date = st.date_input("選擇日期", datetime.today())
    selected_equipment = st.selectbox("選擇設備", ["CANON相機", "V8", "腳架", "讀卡機"])

    day_records = df[(df["日期"] == str(selected_date)) & (df["設備"] == selected_equipment) &
                     (df["狀態"].isin(["待審核", "借用中"]))]

    st.write(f"{selected_date} 的 {selected_equipment} 預約狀態")
    all_slots = [f"{h}:00-{h+1}:00" for h in range(9, 18)]

    for slot in all_slots:
        booked = day_records[day_records["時段"] == slot]
        if not booked.empty:
            dept = booked.iloc[0]["部門"]
            name = booked.iloc[0]["姓名"]
            order_id = booked.iloc[0]["訂單編號"]
            status = booked.iloc[0]["狀態"]
            st.markdown(
                f"<div style='background-color:#006666;color:white;padding:8px;border-radius:5px;margin-bottom:5px;'>"
                f"{slot}<br>姓名:{name}<br>部門:{dept}<br>ID:{order_id}<br>狀態:{status}</div>",
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
elif page == "歸還設備/取消預約":
    st.title("🔄 歸還設備與取消預約")
    st.warning("⚠️ 1.相機使用後請將電池充電並刪除記憶卡中資料再歸還")
    st.warning("⚠️ 2.歸還時請先將設備交付給廣宣設備管理負責人，再按下歸還")
    
    return_order_id = st.text_input("輸入訂單編號以歸還設備")
    if st.button("歸還"):
        mask = (df["訂單編號"] == return_order_id) & (df["狀態"] == "借用中")
        if mask.any():
            df.loc[mask, "狀態"] = "已歸還"
            df.to_csv(CSV_FILE, index=False)
            st.success("✅ 設備已歸還！")
        else:
            st.warning("⚠️ 找不到符合條件的借用紀錄或尚未審核通過。")

    st.subheader("❌ 取消預約")
    st.warning("⚠️ 取消預約時請輸入訂單編號後，直接按下取消無須告知負責人")
    cancel_order_id = st.text_input("輸入訂單編號以取消預約")
    if st.button("取消預約"):
        mask_cancel = (df["訂單編號"] == cancel_order_id) & (df["狀態"].isin(["待審核", "借用中"]))
        if mask_cancel.any():
            df.loc[mask_cancel, "狀態"] = "已取消"
            df.to_csv(CSV_FILE, index=False)
            st.success("✅ 預約已取消，該時段已釋出！")
        else:
            st.warning("⚠️ 找不到符合條件的預約紀錄或已處理過。")

    st.subheader("🔍 搜尋借用紀錄")
    search_query = st.text_input("輸入姓名或部門進行搜尋")
    if st.button("搜尋"):
        if search_query.strip():
            results = df[(df["姓名"].str.contains(search_query, case=False, na=False)) |
                         (df["部門"].str.contains(search_query, case=False, na=False))]
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
        st.warning("⚠️ 同筆訂單多個時段申請的話需狂按同意")
        pending = df[df["狀態"] == "待審核"]
        if pending.empty:
            st.info("目前沒有待審核的預約")
        else:
            for idx, row in pending.iterrows():
                st.markdown(
                    f"訂單編號: {row['訂單編號']} | 姓名: {row['姓名']} | 部門: {row['部門']} | 設備: {row['設備']} | 日期: {row['日期']} | 時段: {row['時段']} | 目的: {row['借用目的']} | 申請時間: {row.get('申請時間', '無資料')}"
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"同意 {row['訂單編號']}", key=f"approve_{row['訂單編號']}"):
                        df.loc[idx, "狀態"] = "借用中"
                        df.to_csv(CSV_FILE, index=False)
                        st.success(f"✅ 訂單 {row['訂單編號']} 已審核通過")
                with col2:
                    if st.button(f"駁回 {row['訂單編號']}", key=f"reject_{row['訂單編號']}"):
                        df.loc[idx, "狀態"] = "已駁回"
                        df.to_csv(CSV_FILE, index=False)
                        st.warning(f"❌ 訂單 {row['訂單編號']} 已被駁回")

        # 查看所有紀錄 + 匯出 CSV
        st.subheader("📜 查看所有歷史訂單紀錄")
        if st.button("顯示所有紀錄"):
            st.dataframe(df)

        st.download_button(
            label="⬇ 匯出所有紀錄 CSV",
            data=df.to_csv(index=False),
            file_name="all_borrow_records.csv",
            mime="text/csv"
        )

        # 顯示設備借用統計圖表
        st.subheader("📊 設備借用次數統計")
        stats = df["設備"].value_counts()
        st.bar_chart(stats)

    elif password:
        st.error("❌ 密碼錯誤")
