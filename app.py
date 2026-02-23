"""
تطبيق رفع مشاريع الطلاب - النسخة النهائية المعتمدة
نظام متكامل يستخدم Streamlit + Supabase + Google Drive
"""

import streamlit as st
from supabase import create_client, Client
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import json
import os
from datetime import datetime
import io

# ===========================
# 0. إعدادات المجلد الرئيسي (تم التحديث بمعرف المجلد الخاص بك)
# ===========================
PARENT_FOLDER_ID = "1gkMhBfFAoJMeAzqE4be1GsNAmWORPycg"

# ===========================
# 1. إعداد الاتصالات
# ===========================

@st.cache_resource
def init_supabase() -> Client:
    """إنشاء اتصال مع Supabase"""
    try:
        # محاولة القراءة من Environment Variables (Render) أو st.secrets
        url = os.getenv("SUPABASE_URL") or st.secrets.get("supabase", {}).get("url")
        key = os.getenv("SUPABASE_KEY") or st.secrets.get("supabase", {}).get("key")
        
        if not url or not key:
            st.error("⚠️ لم يتم العثور على إعدادات Supabase (URL/KEY)")
            st.stop()
        
        return create_client(url, key)
    except Exception as e:
        st.error(f"خطأ في الاتصال بقاعدة البيانات: {str(e)}")
        st.stop()

@st.cache_resource
def init_google_drive():
    """إنشاء اتصال مع Google Drive API"""
    try:
        credentials_json = os.getenv("GOOGLE_CREDENTIALS")
        
        if credentials_json:
            # إذا كان النص يبدأ بـ ' أو " فقم بتنظيفه (شائع في Render)
            credentials_dict = json.loads(credentials_json)
        else:
            credentials_dict = dict(st.secrets["google_credentials"])
        
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        st.error(f"خطأ في الاتصال بـ Google Drive: {str(e)}")
        st.stop()

# ===========================
# 2. دوال قاعدة البيانات
# ===========================

def get_system_config(supabase: Client):
    try:
        response = supabase.table('system_config').select('*').limit(1).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"خطأ في جلب إعدادات النظام: {str(e)}")
        return None

def get_classes(supabase: Client):
    try:
        response = supabase.table('classes').select('*').execute()
        return response.data
    except Exception as e:
        st.error(f"خطأ في جلب قائمة الصفوف: {str(e)}")
        return []

def save_submission(supabase: Client, data: dict):
    try:
        supabase.table('submissions').insert(data).execute()
    except Exception as e:
        raise Exception(f"فشل حفظ البيانات في قاعدة البيانات: {str(e)}")

# ===========================
# 3. دوال Google Drive (منطق المجلدات والرفع)
# ===========================

def find_or_create_folder(service, folder_name: str, parent_id: str):
    """البحث عن مجلد أو إنشاؤه داخل مجلد أب محدد"""
    try:
        query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, fields='files(id)').execute()
        files = results.get('files', [])
        
        if files:
            return files[0]['id']
        else:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = service.files().create(body=file_metadata, fields='id').execute()
            return folder['id']
    except Exception as e:
        raise Exception(f"خطأ في إدارة المجلد '{folder_name}': {str(e)}")

def create_full_structure(service, year, semester, grade, section):
    """إنشاء هيكلة المجلدات الأربعة داخل المجلد الرئيسي المشترك"""
    year_id = find_or_create_folder(service, year, PARENT_FOLDER_ID)
    sem_id = find_or_create_folder(service, semester, year_id)
    grade_id = find_or_create_folder(service, grade, sem_id)
    section_id = find_or_create_folder(service, section, grade_id)
    return section_id

def upload_to_drive(service, file_content, file_name, folder_id):
    """رفع الملف الفعلي ومنح صلاحيات الوصول"""
    try:
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/pdf', resumable=True)
        
        file_drive = service.files().create(
            body=file_metadata, media_body=media, fields='id, webViewLink'
        ).execute()
        
        # منح صلاحية العرض لأي شخص لديه الرابط
        service.permissions().create(
            fileId=file_drive['id'],
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        return file_drive.get('webViewLink')
    except Exception as e:
        raise Exception(f"فشل الرفع إلى درايف: {str(e)}")

# ===========================
# 4. واجهة Streamlit الرئيسيّة
# ===========================

def main():
    st.set_page_config(page_title="نظام رفع المشاريع", page_icon="📚", layout="centered")
    
    supabase = init_supabase()
    drive_service = init_google_drive()
    config = get_system_config(supabase)
    
    if not config:
        st.error("لا يمكن تحميل إعدادات النظام. تأكد من جدول system_config.")
        st.stop()
        
    st.title("📚 نظام رفع المشاريع الطلابية")
    st.markdown(f"### السنة الدراسية: **{config['current_year']}** | الفصل: **{config['current_semester']}**")
    st.markdown("---")

    # جلب وترتيب الصفوف
    classes_data = get_classes(supabase)
    
    # منطق الترتيب المطلوب
    grade_priority = {
        "أول متوسط": 1, "ثاني متوسط": 2, "ثالث متوسط": 3,
        "أول ثانوي": 4, "ثاني ثانوي": 5, "ثالث ثانوي": 6
    }
    
    all_grades = sorted(list(set([c['grade_level'] for c in classes_data])), 
                        key=lambda x: grade_priority.get(x, 99))

    # واجهة النموذج
    with st.form("main_form"):
        st.subheader("📝 بيانات المشروع")
        
        # اختيار المرحلة (مع خيار افتراضي غير محدد)
        selected_grade = st.selectbox("اختر المرحلة الدراسية", ["-- اختر المرحلة --"] + all_grades)
        
        # تصفية الشعب بناءً على المرحلة
        available_sections = ["-- اختر الشعبة --"]
        if selected_grade != "-- اختر المرحلة --":
            available_sections += [c['section_name'] for c in classes_data if c['grade_level'] == selected_grade]
            
        selected_section = st.selectbox("اختر الشعبة", available_sections)
        
        student_name = st.text_input("اسم الطالب الثلاثي", placeholder="أدخل اسمك الكامل")
        project_title = st.text_input("عنوان المشروع", placeholder="عنوان بحثك أو مشروعك")
        
        uploaded_file = st.file_uploader("ارفع ملف المشروع (PDF فقط)", type=['pdf'])
        
        submit_btn = st.form_submit_button("🚀 إرسال ورفع المشروع", use_container_width=True)

    # معالجة ضغط الزر
    if submit_btn:
        # التحقق من المدخلات
        if selected_grade == "-- اختر المرحلة --" or selected_section == "-- اختر الشعبة --":
            st.warning("⚠️ فضلاً اختر المرحلة والشعبة")
        elif not student_name or len(student_name) < 6:
            st.warning("⚠️ يرجى كتابة اسم الطالب الثلاثي بشكل صحيح")
        elif not project_title:
            st.warning("⚠️ يرجى كتابة عنوان المشروع")
        elif not uploaded_file:
            st.warning("⚠️ يرجى إرفاق ملف الـ PDF")
        else:
            with st.spinner("جاري العمل على رفع مشروعك..."):
                try:
                    # 1. إنشاء المسار في درايف
                    target_folder_id = create_full_structure(
                        drive_service, 
                        config['current_year'], 
                        config['current_semester'], 
                        selected_grade, 
                        selected_section
                    )
                    
                    # 2. تحضير الملف والرفع
                    file_content = uploaded_file.read()
                    safe_name = student_name.strip().replace(" ", "_")
                    final_filename = f"{safe_name}_{datetime.now().strftime('%H%M%S')}.pdf"
                    
                    drive_link = upload_to_drive(drive_service, file_content, final_filename, target_folder_id)
                    
                    # 3. الحفظ في قاعدة البيانات
                    save_submission(supabase, {
                        'student_name': student_name.strip(),
                        'project_title': project_title.strip(),
                        'file_url': drive_link,
                        'grade_level': selected_grade,
                        'section': selected_section,
                        'year': config['current_year'],
                        'semester': config['current_semester'],
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    st.success("🎉 تم استلام مشروعك ورفعه بنجاح!")
                    st.balloons()
                    st.info(f"يمكنك معاينة ملفك من هنا: [رابط المشروع]({drive_link})")
                    
                except Exception as e:
                    st.error(f"❌ حدث خطأ غير متوقع: {str(e)}")

    st.markdown("---")
    st.caption("نظام الرفع الأكاديمي الموحد - جميع الحقوق محفوظة")

if __name__ == "__main__":
    main()
