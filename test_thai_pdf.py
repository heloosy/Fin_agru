from pdf.generator import generate_pdf
import os

profile = {
    "name": "สมชาย",
    "location": "เชียงใหม่",
    "past_crop": "ข้าว",
    "current_crop": "ทุเรียน",
    "soil_type": "ดินเหนียว",
    "terrain": "ราบเรียบ"
}

plan_text = """
# แผนงานเกษตร
นี่คือแผนงานสำหรับคุณ สมชาย
1. การรดน้ำ: ควรทำอย่างสม่ำเสมอ
2. การใส่ปุ๋ย: ใช้ปุ๋ยคอก
"""

try:
    print("Testing PDF generation with Thai text...")
    pdf_path = generate_pdf(profile, plan_text, lang="TH")
    print(f"Success! PDF created at: {pdf_path}")
except Exception as e:
    print(f"FAILED! PDF generation crashed: {e}")
