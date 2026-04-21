# 🚀 Quick Start Guide - Hackathon Copilot

## 1️⃣ สร้าง Python Virtual Environment

```bash
cd hackathon-copilot

# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

## 2️⃣ ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

## 3️⃣ ตั้งค่า API Key

```bash
# คัดลอกไฟล์ตัวอย่าง
copy .env.example .env    # Windows
cp .env.example .env      # Mac/Linux

# แล้วแก้ไข .env ใส่ API key ของคุณ
```

เปิดไฟล์ `.env` แล้วใส่:
```
QWEN_API_KEY=your_api_key_here
```

## 4️⃣ ทดสอบรัน Backend

```bash
python -m src.main
```

เปิดเบราว์เซอร์ไปที่: `http://localhost:8000`
ถ้าเห็น `{"status": "ok"}` = ใช้ได้!

## 5️⃣ ทดสอบรัน Frontend (อีก terminal)

```bash
# เปิด terminal ใหม่ แล้ว activate venv ก่อน
venv\Scripts\activate     # Windows
streamlit run src/frontend/app.py
```

เปิดเบราว์เซอร์ไปที่: `http://localhost:8501`

---

## 📦 Push ขึ้น GitHub

```bash
# 1. Initialize git (ถ้ายังไม่มี)
git init

# 2. เพิ่มไฟล์ทั้งหมด (ยกเว้น .gitignore)
git add .

# 3. Commit
git commit -m "Initial commit: Hackathon Copilot"

# 4. สร้าง repository ใหม่บน GitHub แล้ว copy URL

# 5. Push
git remote add origin https://github.com/YOUR_USERNAME/hackathon-copilot.git
git branch -M main
git push -u origin main
```

---

## 🧪 วิธีทดสอบแบบง่าย

1. เปิด Backend: `python -m src.main`
2. เปิด Browser: `http://localhost:8000/docs` (Swagger UI)
3. ลองกด `/health` เพื่อดูว่า API ทำงาน

---

## ❓ ปัญหาที่พบบ่อย

**API Error?**
- ตรวจสอบว่าใส่ QWEN_API_KEY ถูกต้องใน .env

**Import Error?**
- ตรวจสอบว่า activate venv แล้ว
- ลอง `pip install -r requirements.txt` ใหม่

**Port Already in Use?**
- เปลี่ยน port ใน .env: `PORT=8001`