# 🪡 वस्त्र — Desi Smart Clothing Recommender

A Python + Flask + HTML/CSS/JS web app that recommends Indian clothing
based on your body type, size, budget, and occasion.

## 📁 Project Structure
```
desi_clothing_recommender/
├── app.py                  # Flask backend
├── recommender.py          # OOP + Pandas logic
├── requirements.txt
├── data/
│   ├── products.csv        # 40 Indian clothing items
│   └── user_profile.json   # Your saved profile
├── templates/
│   └── index.html          # Main UI
└── static/
    ├── css/style.css
    └── js/main.js
```

## 🚀 How to Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

## ✨ Features
- Save your style profile (body type, size, skin tone, budget)
- Select occasion (Wedding, Festive, Casual, Office, College, Pooja)
- Get outfit recommendations filtered by your profile
- Sort by: Lowest Price / Highest Quality / Fastest Delivery
- Price & Quality comparison charts (Myntra vs Meesho vs Amazon)
- Log purchases and track wardrobe history
- Category breakdown doughnut chart

## 📚 Python Concepts Used
| Concept | Where |
|---|---|
| OOP (Classes) | User, ClothingItem, Recommender |
| File Handling | JSON (profile), CSV (products, history) |
| Pandas | Loading, filtering, groupby |
| lambda + filter() | Size & budget filtering |
| List comprehensions | Building result lists |
| Exception Handling | All input validations |
| Flask | REST API backend |
| Chart.js | Frontend charts |
