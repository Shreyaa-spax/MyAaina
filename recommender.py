import pandas as pd
import json
import os
import math

BASE_DIR = os.path.dirname(__file__)
PRODUCTS_FILE = os.path.join(BASE_DIR, 'products.csv')
PROFILE_FILE = os.path.join(BASE_DIR, 'user_profile.json')
HISTORY_FILE = os.path.join(BASE_DIR, 'purchase_history.csv')

SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
SKIN_TONE_COLOR_PREFERENCES = {
    'Fair': {'red', 'maroon', 'emerald', 'green', 'lavender', 'black', 'blue', 'navy', 'pink'},
    'Wheatish': {'mustard', 'teal', 'maroon', 'navy', 'olive', 'cream', 'rust', 'purple'},
    'Dusky': {'white', 'mustard', 'magenta', 'teal', 'rust', 'pink', 'yellow', 'gold'},
    'Dark': {'white', 'yellow', 'green', 'emerald', 'blue', 'royal blue', 'orange', 'gold', 'red', 'cream'},
}
BODY_TYPE_CATEGORY_PREFERENCES = {
    'Slim': {'lehenga', 'saree', 'kurti', 'kurtis', 'indo-western'},
    'Athletic': {'sherwani', 'indo-western', 'nehru jacket', 'bandhgala', 'dhoti'},
    'Curvy': {'saree', 'salwar', 'lehenga'},
    'Plus Size': {'salwar', 'saree', 'kurta sets'},
    'Petite': {'kurti', 'kurtis', 'indo-western'},
}


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
        self.image_url = row.get('image_url', '')

    def to_dict(self):
        return self.__dict__


# ─── Purchase History ─────────────────────────────────────────────
def log_purchase(item_id, item_payload=None):
    try:
        if item_payload:
            item = pd.DataFrame([item_payload])
        else:
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
        records = df.to_dict(orient='records')
        return [_sanitize_record(record) for record in records]
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


def _sanitize_record(record):
    cleaned = {}
    for key, value in record.items():
        if isinstance(value, float) and math.isnan(value):
            cleaned[key] = None
        else:
            cleaned[key] = value
    return cleaned


# ─── Recommender ──────────────────────────────────────────────────
class Recommender:
    def __init__(self):
        self.df = pd.read_csv(PRODUCTS_FILE)

    def recommend(self, user: User, occasion: str, sort_by: str = 'price', limit: int = 12, platform: str | None = None):
        df = self.df.copy()
        df = df[df['occasion'].str.lower() == occasion.lower()]
        df = df[df['gender'].str.lower() == user.gender.lower()]
        if platform:
            df = df[df['platform'].str.lower() == platform.lower()]

        if df.empty:
            return []

        scored_rows = []
        for _, row in df.iterrows():
            item = row.to_dict()
            size_penalty = self._size_penalty(user.size, item['size'])
            budget_penalty = self._budget_penalty(user.budget_min, user.budget_max, item['price'])
            profile_penalty = self._profile_penalty(user, item, occasion)
            match_reason = self._match_reason(size_penalty, budget_penalty, profile_penalty)
            scored_rows.append({
                **item,
                '_size_penalty': size_penalty,
                '_budget_penalty': budget_penalty,
                '_profile_penalty': profile_penalty,
                '_match_reason': match_reason,
            })

        ranked = pd.DataFrame(scored_rows)
        ranked = self._sort_ranked(ranked, sort_by)
        ranked = ranked.head(limit)

        results = []
        for _, row in ranked.iterrows():
            item = ClothingItem(row).to_dict()
            item['match_reason'] = row['_match_reason']
            results.append(item)
        return results

    def _sort_ranked(self, df, sort_by):
        sort_columns = ['_budget_penalty', '_size_penalty', '_profile_penalty']
        ascending = [True, True, True]

        if sort_by == 'price':
            sort_columns.append('price')
            ascending.append(True)
        elif sort_by == 'quality':
            sort_columns.append('quality_rating')
            ascending.append(False)
        elif sort_by == 'delivery':
            sort_columns.append('delivery_days')
            ascending.append(True)
        else:
            sort_columns.append('price')
            ascending.append(True)

        sort_columns.append('id')
        ascending.append(True)
        return df.sort_values(sort_columns, ascending=ascending)

    def _size_penalty(self, user_size, item_size):
        if item_size == 'Free Size':
            return 0.05
        if item_size == user_size:
            return 0.0
        if user_size not in SIZE_ORDER or item_size not in SIZE_ORDER:
            return 0.8

        distance = abs(SIZE_ORDER.index(user_size) - SIZE_ORDER.index(item_size))
        return 0.25 * distance

    def _budget_penalty(self, budget_min, budget_max, price):
        if budget_min <= price <= budget_max:
            return 0.0

        if price < budget_min:
            return round((budget_min - price) / max(budget_min, 1), 3)

        return round((price - budget_max) / max(budget_max, 1), 3)

    def _profile_penalty(self, user, item, occasion):
        penalty = 0.0

        preferred_colors = SKIN_TONE_COLOR_PREFERENCES.get(user.skin_tone, set())
        color = self._normalize_text(item.get('color'))
        if preferred_colors and color not in preferred_colors:
            penalty += 0.18

        preferred_categories = BODY_TYPE_CATEGORY_PREFERENCES.get(user.body_type, set())
        category_text = ' '.join([
            self._normalize_text(item.get('category')),
            self._normalize_text(item.get('name')),
        ])
        if preferred_categories and not any(pref in category_text for pref in preferred_categories):
            penalty += 0.22

        if user.interests and occasion not in user.interests:
            penalty += 0.08

        return round(penalty, 3)

    def _normalize_text(self, value):
        return str(value or '').strip().lower()

    def _match_reason(self, size_penalty, budget_penalty, profile_penalty):
        if size_penalty <= 0.05 and budget_penalty == 0:
            return 'Exact match' if profile_penalty <= 0.12 else 'Good match'
        if budget_penalty == 0:
            return 'More sizes' if profile_penalty <= 0.12 else 'Style compromise'
        if size_penalty <= 0.05:
            return 'Budget stretch'
        return 'Close match'

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
