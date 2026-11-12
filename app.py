import streamlit as st
import gspread
import pandas as pd
from datetime import datetime

# ปรับเลย์เอาต์ให้กว้างขึ้น (wide) เพื่อให้ดูกราฟได้สวยเต็มตา
st.set_page_config(page_title="ระบบจัดการข้อมูลฟาร์มเป็ดเนื้อ", layout="wide")
st.title("🦆 ระบบวิเคราะห์และจัดการข้อมูลฟาร์มเป็ดเนื้อ")

# ฟังก์ชันเชื่อมต่อ Google Sheets
def get_sheet():
    gc = gspread.service_account(filename="credentials.json")
    return gc.open("DuckFarm_Data").sheet1

# สร้าง แท็บ (Tabs) แยกหน้าการทำงาน
tab1, tab2 = st.tabs(["📝 บันทึกข้อมูลและประเมินผล", "📊 แดชบอร์ดกราฟวิเคราะห์"])

# ==========================================
# แท็บที่ 1: บันทึกข้อมูลและแจ้งเตือน (UI / Alerts)
# ==========================================
with tab1:
    with st.form("duck_data_form"):
        st.subheader("1. บันทึกข้อมูลฝูงประจำวัน")
        col1, col2 = st.columns(2)
        with col1:
            start_count = st.number_input("จำนวนเป็ดเริ่มเลี้ยง (ตัว)", min_value=1, value=10000)
            start_weight = st.number_input("น้ำหนักเฉลี่ยเริ่มเลี้ยง (กก./ตัว)", min_value=0.01, value=0.05, format="%.2f")
            days = st.number_input("จำนวนวันที่เลี้ยง (วัน)", min_value=1, value=45)
        with col2:
            current_weight = st.number_input("น้ำหนักเฉลี่ยปัจจุบัน (กก./ตัว)", min_value=0.01, value=3.20, format="%.2f")
            total_feed = st.number_input("ปริมาณอาหารที่กินสะสมทั้งหมด (กก.)", min_value=0.1, value=60000.0, format="%.1f")
            sick_count = st.number_input("จำนวนเป็ดป่วยสะสม (ตัว)", min_value=0, value=50)
            dead_count = st.number_input("จำนวนเป็ดตายสะสม (ตัว)", min_value=0, value=100)
            
        submitted = st.form_submit_button("คำนวณและบันทึกลง Google Sheets")

    if submitted:
        surviving_count = start_count - dead_count
        weight_gain_per_bird = current_weight - start_weight
        total_weight_gain = weight_gain_per_bird * surviving_count
        
        adg = weight_gain_per_bird / days
        fcr = total_feed / total_weight_gain if total_weight_gain > 0 else 0
        morbidity_rate = (sick_count / start_count) * 100
        mortality_rate = (dead_count / start_count) * 100
        survival_rate = (surviving_count / start_count) * 100

        # แสดง KPI
        st.divider()
        st.subheader("2. ดัชนีชี้วัดประสิทธิภาพ (KPIs)")
        m1, m2, m3 = st.columns(3)
        m1.metric("ADG (กก./ตัว/วัน)", f"{adg:.3f}")
        m2.metric("FCR (อัตราแลกเนื้อ)", f"{fcr:.2f}")
        m3.metric("อัตราการรอด (%)", f"{survival_rate:.1f}%")
        
        m4, m5, m6 = st.columns(3)
        m4.metric("เป็ดคงเหลือ (ตัว)", f"{surviving_count:,}")
        m5.metric("อัตราการป่วย (%)", f"{morbidity_rate:.1f}%")
        m6.metric("อัตราการตาย (%)", f"{mortality_rate:.1f}%")

        # ระบบแจ้งเตือนตามเกณฑ์ (Alerts)
        st.divider()
        st.subheader("🩺 ระบบประเมินสุขภาพฝูงเบื้องต้น")
        if mortality_rate >= 5.0:
            st.error(f"🚨 **วิกฤต:** อัตราการตายสูงถึง {mortality_rate:.1f}% (เกินเกณฑ์ 5%) แนะนำให้หมอเข้าสุ่มชันสูตรซากและตรวจสอบการระบายอากาศด่วน!")
        elif morbidity_rate >= 2.0:
            st.warning(f"⚠️ **เฝ้าระวัง:** พบเป็ดป่วยสะสม {morbidity_rate:.1f}% ควรแยกคอกสังเกตอาการและเช็กคุณภาพน้ำ/อาหาร")
        else:
            st.success("✅ **ปกติ:** สุขภาพฝูงโดยรวมอยู่ในเกณฑ์มาตรฐาน อัตราการสูญเสียต่ำ")

        # บันทึกลง Google Sheets
        try:
            sheet = get_sheet()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row_data = [now, start_count, start_weight, days, current_weight, total_feed, sick_count, dead_count, round(adg, 3), round(fcr, 2), round(survival_rate, 1)]
            sheet.append_row(row_data)
            st.toast("บันทึกข้อมูลลง Google Sheets สำเร็จแล้ว!", icon="💾")
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดในการบันทึก: {e}")

# ==========================================
# แท็บที่ 2: ดึงข้อมูลทำกราฟ (Charts & Dashboard)
# ==========================================
with tab2:
    st.subheader("📈 แนวโน้มประสิทธิภาพการผลิตและสุขภาพฝูง")
    st.caption("ข้อมูลอัปเดตเรียลไทม์จากตาราง Google Sheets")
    
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        
        if records:
            # แปลงข้อมูลเป็น Pandas DataFrame
            df = pd.DataFrame(records)
            
            # ตั้งคอลัมน์ "วันที่และเวลา" เป็นแกน X สำหรับกราฟ
            df.set_index('วันที่และเวลา', inplace=True)

            # แบ่งครึ่งโชว์ 2 กราฟซ้ายขวา
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("**กราฟแนวโน้มอัตราแลกเนื้อ (FCR)**")
                # สร้างกราฟเส้น โชว์ค่า FCR ย้อนหลัง
                st.line_chart(df['FCR'], color="#1f77b4") 

            with c2:
                st.markdown("**กราฟจำนวนเป็ดตายสะสม (ตัว)**")
                # สร้างกราฟแท่ง โชว์จำนวนเป็ดตาย
                st.bar_chart(df['เป็ดตาย'], color="#d62728")

            st.divider()
            st.markdown("**📋 ตารางข้อมูลประวัติทั้งหมด**")
            st.dataframe(df, use_container_width=True)
            
        else:
            st.info("ยังไม่มีข้อมูลสำหรับสร้างกราฟ ลองสลับไปบันทึกข้อมูลในแท็บแรกดูก่อนครับ")
    except Exception as e:
        st.error(f"❌ ไม่สามารถดึงข้อมูลมาแสดงกราฟได้: {e}")