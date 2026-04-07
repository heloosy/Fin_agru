import os
from ai import gemini
from pdf import generator as pdf_gen

# 🚜 AgriSpark Pro Manual Generator (JACOB Case Study)
profile = {
    'name': 'Jacob',
    'location': 'Thailand',
    'past_crop': 'Rice',
    'current_crop': 'Chili Peppers',
    'soil_type': 'Sandy',
    'terrain': 'Flat',
    'weather_summary': 'Sunny, 0mm rainfall, 28-35°C',
    'language': 'EN'
}
archive_id = '7804d5c3'

print("🧠 BRAIN: Generating High-Detail 10-Section Agronomic Manual (5,000 token cap)...")
try:
    plan_md = gemini.generate_farm_plan(
        profile['language'],
        profile,
        profile['weather_summary']
    )
    print("✅ BRAIN: Manual Content Generated Successfully!")
    
    print("📊 PDF: Rendering Pro Manual with Tables...")
    pdf_path = pdf_gen.generate_pdf(profile, plan_md)
    # Ensure it's in the static/pdf directory as expected
    print(f"🏆 SUCCESS: Pro Manual saved at -> {pdf_path}")
    
except Exception as e:
    print(f"❌ ERROR: Pro Generation failed: {e}")
