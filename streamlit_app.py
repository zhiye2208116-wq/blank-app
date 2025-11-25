
import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="廣宣攝影設備借用管理系統", layout="wide")

COLUMNS = ["訂單編號", "姓名", "部門", "設備", "日期", "時段", "借用目的", "狀態", "申請時間", "處理時間"]

# -------------------------
# Google Sheets 連線
# -------------------------
def get_sheet():
    # 從 secrets 取出服務帳戶 JSON 與試算表 ID
    creds_info = st.secrets["gcp_service_account"]
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
    ]
    creds = ServiceAccountCredentials.from_json_keydict(creds_info, scopes=scope)
    client = gspread.authorize(creds)
    # 開啟試算表的第一個工作表（sheet1）
    sheet = client.open_by_key(creds_info["spreadsheet_id"]).sheet1
    # 如果是空表，寫入表頭
    existing = sheet.get_all_values()
    if not existing:
        sheet.append_row(COLUMNS)
    return sheet

@st.cache_data(ttl=15)
def load_df():
    sheet = get_sheet()
    values = sheet.get_all_values()
    if not values:
        return pd.DataFrame(columns=COLUMNS)
    header = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=header)
    # 補齊缺欄位並排序
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS]
    return df

def save_df(df: pd.DataFrame):
    sheet = get_sheet()
    # 清除並重寫（表頭 + 所有資料）
    sheet.clear()
    sheet.append_row(COLUMNS)
    if not df.empty:
        sheet.append_rows(df.values.tolist())
    # 讓下次 load_df 讀到更新後的內容
    load_df.clear()

# -------------------------
# UI：側邊欄
# -------------------------
page = st.sidebar.radio("選擇功能頁面", ["借用與查詢", "歸還設備/取消預約", "後台管理"])

# -------------------------
# 借用與查詢
# -------------------------
if page == "借用與查詢":
    st.title("📷 借用攝影設備與查詢預約狀態")
    st.text("現有廣宣設備主負責人：🧝‍♂️致燁🧑‍🚀文欣")
    st.markdown("""
    **注意事項：**
    1. 借用請完整填寫姓名、部門、理由。
    2. 送出後由負責人審核，審核通過才能借用。
    3. 急需請聯絡 SNS PJ 致燁 / 文欣。
    """, unsafe_allow_html=True)

    with st.form("borrow_form"):
        name = st.text_input("借用人姓名")
        department = st.text_input("借用人部門")
        equipments = st.multiselect("選擇設備（可多選）", ["CANON相機", "V8", "腳架", "讀卡機"])
        date = st.date_input("借用日期", datetime.today())
        time_slots = st.multiselect("借用時段（可多選）", [f"{h}:00-{h+1}:00" for h in range(9, 18)])
        purpose = st.text_area("借用目的")
        submitted = st.form_submit_button("提交")

    if submitted:
        if not name.strip() or not department.strip() or not purpose.strip():
            st.error("⚠️ 姓名、部門與借用目的為必填。")
        elif not equipments or not time_slots:
            st.error("⚠️ 請至少選擇一個設備和一個時段！")
        else:
            df = load_df()
            conflict_records = df[
                (df["設備"].isin(equipments)) &
                (df["日期"] == str(date)) &
                (df["時段"].isin(time_slots)) &
                (df["狀態"].isin(["待審核", "借用中"]))
            ]
            if not conflict_records.empty:
                st.error("⚠️ 以下設備與時段已被預約：")
                for _, row in conflict_records.iterrows():
                    st.write(f"設備：{row['設備']} | 時段：{row['時段']} | 狀態：{row['狀態']} | 申請人：{row['姓名']}")
            else:
                order_id = str(uuid.uuid4())[:8]
                apply_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_records = []
                for eq in equipments:
                    for slot in time_slots:
                        new_records.append([order_id, name, department, eq, str(date), slot, purpose, "待審核", apply_time, ""])
                new_df = pd.DataFrame(new_records, columns=COLUMNS)
                df = pd.concat([df, new_df], ignore_index=True)
                save_df(df)
                st.success(f"✅ 預約請求已送出！訂單編號：{order_id}，等待後台審核")

    st.subheader("📅 選擇日期與設備查看預約狀態")
    st.warning("可查詢：審核是否通過、預約狀態、歸還狀態")
    selected_date = st.date_input("選擇日期", datetime.today())
    selected_equipment = st.selectbox("選擇設備", ["CANON相機", "V8", "腳架", "讀卡機"])
    df = load_df()
    day_records = df[
        (df["日期"] == str(selected_date)) &
        (df["設備"] == selected_equipment) &
        (df["狀態"].isin(["待審核", "借用中"]))
    ]

    all_slots = [f"{h}:00-{h+1}:00" for h in range(9, 18)]
    st.write(f"{selected_date} 的 {selected_equipment} 預約狀態")
    for slot in all_slots:
        booked = day_records[day_records["時段"] == slot]
        if not booked.empty:
            dept = booked.iloc[0]["部門"]
            name_ = booked.iloc[0]["姓名"]
            oid = booked.iloc[0]["訂單編號"]
            status = booked.iloc[0]["狀態"]
            st.markdown(
                f"<div style='background-color:#006666;color:white;padding:8px;border-radius:5px;margin-bottom:5px;'>"
                f"{slot}<br>姓名:{name_}<br>部門:{dept}<br>ID:{oid}<br>狀態:{status}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='background-color:#e0e0e0;padding:8px;border-radius:5px;margin-bottom:5px;'>{slot}</div>",
                unsafe_allow_html=True
            )

# -------------------------
# 歸還設備/取消預約
# -------------------------
elif page == "歸還設備/取消預約":
    st.title("🔄 歸還設備與取消預約")
    st.warning("⚠️ 1.相機使用後請將電池充電並刪除記憶卡中資料再歸還")
    st.warning("⚠️ 2.歸還時請先將設備交付給廣宣設備管理負責人，再按下歸還")

    return_order_id = st.text_input("輸入訂單編號以歸還設備")
    if st.button("歸還"):
        df = load_df()
        mask = (df["訂單編號"] == return_order_id) & (df["狀態"] == "借用中")
        if mask.any():
            df.loc[mask, "狀態"] = "已歸還"
            df.loc[mask, "處理時間"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_df(df)
            st.success("✅ 設備已歸還！")
        else:
            st.warning("⚠️ 找不到符合條件的借用紀錄或尚未審核通過。")

    st.subheader("❌ 取消預約")
    cancel_order_id = st.text_input("輸入訂單編號以取消預約")
    st.warning("⚠️ 取消預約時請輸入訂單編號後，直接按下取消無須告知負責人")
    if st.button("取消預約"):
        df = load_df()
        mask_cancel = (df["訂單編號"] == cancel_order_id) & (df["狀態"].isin(["待審核", "借用中"]))
        if mask_cancel.any():
            df.loc[mask_cancel, "狀態"] = "已取消"
            df.loc[mask_cancel, "處理時間"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_df(df)
            st.success("✅ 預約已取消，該時段已釋出！")
        else:
            st.warning("⚠️ 找不到符合條件的預約紀錄或已處理過。")

    st.subheader("🔍 搜尋借用紀錄")
    search_query = st.text_input("輸入姓名或部門進行搜尋")
    if st.button("搜尋"):
        df = load_df()
        if search_query.strip():
            results = df[
                (df["姓名"].str.contains(search_query, case=False, na=False)) |
                (df["部門"].str.contains(search_query, case=False, na=False))
            ]
            if not results.empty:
                st.write("搜尋結果：")
                st.dataframe(results)
            else:
                st.info("未找到符合條件的紀錄。")

# -------------------------
# 後台管理
# -------------------------
elif page == "後台管理":
    st.title("🔐 後台管理")
    password = st.text_input("請輸入後台密碼", type="password")
    if password == "SNSPJ1103":
        st.success("✅ 登入成功")

        df = load_df()
        st.subheader("待審核的預約")
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
                    if st.button(f"同意 {row['訂單編號']}", key=f"approve_{idx}"):
                        df.loc[idx, "狀態"] = "借用中"
                        df.loc[idx, "處理時間"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        save_df(df)
                        st.success(f"✅ 訂單 {row['訂單編號']} 已審核通過")
                with col2:
                    if st.button(f"駁回 {row['訂單編號']}", key=f"reject_{idx}"):
                        df.loc[idx, "狀態"] = "已駁回"
                        df.loc[idx, "處理時間"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        save_df(df)
                        st.warning(f"❌ 訂單 {row['訂單編號']} 已被駁回")

        st.subheader("📜 查看所有歷史訂單紀錄")
        if st.button("顯示所有紀錄"):
            st.dataframe(df)

        st.download_button(
            label="⬇ 匯出所有紀錄 CSV",
            data=df.to_csv(index=False),
            file_name="all_borrow_records.csv",
            mime="text/csv"
        )
    elif password:
        st.error("❌ 密碼錯誤")
