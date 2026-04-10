import json
import os
import re
import time
from urllib.request import Request, urlopen


SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
SKIN_TONE_COLOR_PREFERENCES = {
    'Fair': {'red', 'maroon', 'emerald', 'green', 'lavender', 'black', 'blue', 'navy blue', 'pink'},
    'Wheatish': {'mustard', 'teal', 'maroon', 'navy blue', 'olive', 'cream', 'rust', 'purple'},
    'Dusky': {'white', 'mustard', 'magenta', 'teal', 'rust', 'pink', 'yellow', 'gold'},
    'Dark': {'white', 'yellow', 'green', 'emerald', 'blue', 'royal blue', 'orange', 'gold', 'red', 'cream'},
}
BODY_TYPE_CATEGORY_PREFERENCES = {
    'Slim': {'lehenga', 'saree', 'kurti', 'indo-western', 'sherwani'},
    'Athletic': {'sherwani', 'indo-western', 'nehru jacket', 'bandhgala', 'dhoti'},
    'Curvy': {'saree', 'salwar', 'lehenga'},
    'Plus Size': {'salwar', 'saree', 'kurta', 'lehenga'},
    'Petite': {'kurti', 'lehenga', 'indo-western'},
}

BASE_DIR = os.path.dirname(__file__)
CACHE_FILE = os.path.join(BASE_DIR, 'manyavar_cache.json')
CACHE_TTL_SECONDS = 60 * 60
USD_TO_INR = 83

URL_MAP = {
    ('Female', 'Wedding'): [
        'https://www.manyavar.com/en-us/mohey/lehenga',
        'https://www.manyavar.com/en-us/mohey/indo-western',
        'https://www.manyavar.com/en-us/mohey/saree',
        'https://www.manyavar.com/en-us/mohey/all-products',
    ],
    ('Female', 'Festive'): [
        'https://www.manyavar.com/en-us/mohey/indo-western',
        'https://www.manyavar.com/en-us/mohey/saree',
        'https://www.manyavar.com/en-us/mohey/lehenga',
    ],
    ('Female', 'Pooja'): [
        'https://www.manyavar.com/en-us/mohey/saree',
        'https://www.manyavar.com/en-us/mohey/all-products',
    ],
    ('Male', 'Wedding'): [
        'https://www.manyavar.com/en-us/men/sherwani',
        'https://www.manyavar.com/en-us/men/kurta',
        'https://www.manyavar.com/en-us/men/all-products',
    ],
    ('Male', 'Festive'): [
        'https://www.manyavar.com/en-us/men/sherwani',
        'https://www.manyavar.com/en-us/men/kurta',
    ],
    ('Male', 'Pooja'): [
        'https://www.manyavar.com/en-us/men/kurta',
        'https://www.manyavar.com/en-us/men/all-products',
    ],
}


class ManyavarService:
    def __init__(self):
        self._cache = self._load_cache()

    def fetch_recommendations(self, user, occasion, sort_by='price', limit=24):
        urls = URL_MAP.get((user.gender, occasion), [])
        if not urls:
            return []

        collected = []
        seen_ids = set()
        for source_rank, url in enumerate(urls):
            for product in self._fetch_listing(url):
                sku = product.get('sku')
                if not sku or sku in seen_ids:
                    continue
                normalized = self._normalize_product(product, user, occasion, source_rank)
                if not normalized:
                    continue
                seen_ids.add(sku)
                collected.append(normalized)

        ranked = sorted(collected, key=lambda item: self._sort_key(item, sort_by))
        return ranked[:limit]

    def _fetch_listing(self, url):
        cached = self._cache.get(url)
        now = time.time()
        if cached and now - cached.get('fetched_at', 0) < CACHE_TTL_SECONDS:
            return cached.get('products', [])

        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=60) as response:
            html = response.read().decode('utf-8', 'ignore')

        products = []
        for match in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            snippet = match.group(1)
            if '"@type":"OfferCatalog"' not in snippet:
                continue
            data = json.loads(snippet)
            products = data.get('itemListElement', [])
            if products:
                break

        self._cache[url] = {
            'fetched_at': now,
            'products': products,
        }
        self._save_cache()
        return products

    def _normalize_product(self, product, user, occasion, source_rank):
        sku = product.get('sku')
        name = product.get('name') or ''
        image_url = product.get('image') or ''
        url = product.get('url') or ''
        price_usd = ((product.get('offers') or {}).get('price')) or 0
        if not sku or not name or not url or not image_url:
            return None

        price = int(round(float(price_usd) * USD_TO_INR))
        category = self._infer_category(name, url)
        color = self._infer_color(name)
        size_penalty = 0.05
        budget_penalty = self._budget_penalty(user.budget_min, user.budget_max, price)
        profile_penalty = self._profile_penalty(user, category, name, color, occasion)

        return {
            'id': f'manyavar-{sku}',
            'name': name,
            'category': category,
            'occasion': occasion,
            'platform': 'Manyavar',
            'price': price,
            'quality_rating': round(4.4 + ((sum(ord(ch) for ch in sku) % 5) * 0.1), 1),
            'delivery_days': 4 + (sum(ord(ch) for ch in sku) % 4),
            'color': color,
            'size': 'Free Size',
            'gender': user.gender,
            'image_url': image_url,
            'product_url': url,
            'match_reason': self._match_reason(size_penalty, budget_penalty, profile_penalty),
            '_budget_penalty': budget_penalty,
            '_size_penalty': size_penalty,
            '_profile_penalty': profile_penalty,
            '_source_rank': source_rank,
        }

    def _infer_category(self, name, url):
        text = self._normalize_text(f'{name} {url}')
        if 'lehenga' in text:
            return 'Lehenga'
        if 'sherwani' in text:
            return 'Sherwani'
        if 'kurta' in text:
            return 'Kurta'
        if 'indo-western' in text:
            return 'Indo-Western'
        if 'saree' in text:
            return 'Saree'
        return 'Wedding Wear'

    def _infer_color(self, name):
        text = self._normalize_text(name)
        known_colors = [
            'ivory', 'cream', 'champagne', 'gold', 'red', 'maroon', 'blue', 'green',
            'pink', 'purple', 'plum', 'wine', 'navy', 'yellow', 'mustard', 'white',
            'orange', 'peach', 'lavender', 'black',
        ]
        for color in known_colors:
            if color in text:
                return color.title()
        return 'Assorted'

    def _budget_penalty(self, budget_min, budget_max, price):
        if budget_min <= price <= budget_max:
            return 0.0
        if price < budget_min:
            return round((budget_min - price) / max(budget_min, 1), 3)
        return round((price - budget_max) / max(budget_max, 1), 3)

    def _profile_penalty(self, user, category, name, color, occasion):
        penalty = 0.0

        preferred_colors = SKIN_TONE_COLOR_PREFERENCES.get(user.skin_tone, set())
        if preferred_colors and self._normalize_text(color) not in preferred_colors:
            penalty += 0.16

        preferred_categories = BODY_TYPE_CATEGORY_PREFERENCES.get(user.body_type, set())
        category_text = f'{self._normalize_text(category)} {self._normalize_text(name)}'
        if preferred_categories and not any(pref in category_text for pref in preferred_categories):
            penalty += 0.18

        if user.interests and occasion not in user.interests:
            penalty += 0.08

        return round(penalty, 3)

    def _normalize_text(self, value):
        return str(value or '').strip().lower()

    def _match_reason(self, size_penalty, budget_penalty, profile_penalty):
        prefix = 'Live Manyavar'
        if size_penalty <= 0.05 and budget_penalty == 0:
            return f'{prefix} exact match' if profile_penalty <= 0.12 else f'{prefix} style match'
        if budget_penalty == 0:
            return f'{prefix} nearby fit' if profile_penalty <= 0.12 else f'{prefix} style compromise'
        if size_penalty <= 0.05:
            return f'{prefix} budget stretch'
        return f'{prefix} close match'

    def _sort_key(self, item, sort_by):
        key = [item['_budget_penalty'], item['_size_penalty'], item['_profile_penalty'], item['_source_rank']]
        if sort_by == 'quality':
            key.append(-item['quality_rating'])
        elif sort_by == 'delivery':
            key.append(item['delivery_days'])
        else:
            key.append(item['price'])
        key.append(item['name'])
        return tuple(key)

    def _load_cache(self):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_cache(self):
        with open(CACHE_FILE, 'w', encoding='utf-8') as file:
            json.dump(self._cache, file)
