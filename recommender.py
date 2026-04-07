import pandas as pd
import json
import os
from functools import reduce

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
PRODUCTS_FILE = os.path.join(DATA_DIR, 'products.csv')
PROFILE_FILE = os.path.join(DATA_DIR, 'user_profile.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'purchase_history.csv')


# ─── User Profile ────────────────────────────────────────────────
class User:
    def __init__(self, name, age, gender, body_type, skin_tone, size, budget_min, budget_max, interests):
        self.name = name
        self.age = age
        self.gender = gender
        self.body_type = body_type
        self.skin_tone = skin_tone
        self.size = size
        self.budget_min = budget_min
        self.budget_max = budget_max
        self.interests = interests  # list of occasions they like

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d):
        return User(**d)


def save_profile(user: User):
    with open(PROFILE_FILE, 'w') as f:
        json.dump(user.to_dict(), f, indent=2)


def load_profile():
    try:
        with open(PROFILE_FILE, 'r') as f:
            data = json.load(f)
        if not data:
            return None
        return User.from_dict(data)
    except (FileNotFoundError, KeyError, TypeError):
        return None


# ─── Clothing Item ────────────────────────────────────────────────
class ClothingItem:
    def __init__(self, row):
        self.id = row['id']
        self.name = row['name']
        self.category = row['category']
        self.occasion = row['occasion']
        self.platform = row['platform']
        self.price = row['price']
        self.quality_rating = row['quality_rating']
        self.delivery_days = row['delivery_days']
        self.color = row['color']
        self.size = row['size']
        self.gender = row['gender']

    def to_dict(self):
        return self.__dict__


# ─── Purchase History ─────────────────────────────────────────────
def log_purchase(item_id):
    try:
        df = pd.read_csv(PRODUCTS_FILE)
        item = df[df['id'] == int(item_id)]
        if item.empty:
            raise ValueError("Product not found")

        if os.path.exists(HISTORY_FILE):
            history = pd.read_csv(HISTORY_FILE)
        else:
            history = pd.DataFrame()

        history = pd.concat([history, item], ignore_index=True)
        history.to_csv(HISTORY_FILE, index=False)
        return True
    except Exception as e:
        print(f"Error logging purchase: {e}")
        return False


def get_purchase_history():
    try:
        if not os.path.exists(HISTORY_FILE):
            return []
        df = pd.read_csv(HISTORY_FILE)
        return df.to_dict(orient='records')
    except Exception:
        return []


def get_category_stats():
    """Returns category counts for pie chart"""
    try:
        if not os.path.exists(HISTORY_FILE):
            return {}
        df = pd.read_csv(HISTORY_FILE)
        counts = df['category'].value_counts().to_dict()
        return counts
    except Exception:
        return {}


# ─── Recommender ──────────────────────────────────────────────────
class Recommender:
    def __init__(self):
        self.df = pd.read_csv(PRODUCTS_FILE)

    def recommend(self, user: User, occasion: str, sort_by: str = 'price'):
        df = self.df.copy()

        # Filter by occasion
        df = df[df['occasion'].str.lower() == occasion.lower()]

        # Filter by gender
        df = df[df['gender'].str.lower() == user.gender.lower()]

        # Filter by budget using lambda
        df = df[df['price'].apply(lambda p: user.budget_min <= p <= user.budget_max)]

        # Filter by size using filter()
        size_match = list(filter(
            lambda row: row['size'] in [user.size, 'Free Size'],
            df.to_dict(orient='records')
        ))
        df = pd.DataFrame(size_match)

        if df.empty:
            return []

        # Sort based on user preference
        if sort_by == 'price':
            df = df.sort_values('price', ascending=True)
        elif sort_by == 'quality':
            df = df.sort_values('quality_rating', ascending=False)
        elif sort_by == 'delivery':
            df = df.sort_values('delivery_days', ascending=True)

        # Use list comprehension to build result
        results = [ClothingItem(row).to_dict() for _, row in df.iterrows()]
        return results

    def get_price_comparison(self, occasion: str):
        """Average price per platform for charts"""
        df = self.df[self.df['occasion'].str.lower() == occasion.lower()]
        if df.empty:
            return {}
        avg = df.groupby('platform')['price'].mean().round(2).to_dict()
        return avg

    def get_quality_comparison(self, occasion: str):
        """Average quality per platform for charts"""
        df = self.df[self.df['occasion'].str.lower() == occasion.lower()]
        if df.empty:
            return {}
        avg = df.groupby('platform')['quality_rating'].mean().round(2).to_dict()
        return avg
