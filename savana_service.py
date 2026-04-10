import os
import re
import time
from urllib.parse import quote
from urllib.request import Request, urlopen


SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
SKIN_TONE_COLOR_PREFERENCES = {
    'Fair': {'red', 'maroon', 'emerald', 'green', 'lavender', 'black', 'blue', 'navy blue', 'pink'},
    'Wheatish': {'mustard', 'teal', 'maroon', 'navy blue', 'olive', 'cream', 'rust', 'purple'},
    'Dusky': {'white', 'mustard', 'magenta', 'teal', 'rust', 'pink', 'yellow', 'gold'},
    'Dark': {'white', 'yellow', 'green', 'emerald', 'blue', 'royal blue', 'orange', 'gold', 'red', 'cream'},
}
BODY_TYPE_CATEGORY_PREFERENCES = {
    'Slim': {'dress', 'a-line', 'top', 'blouse', 'skirt'},
    'Athletic': {'dress', 'shirt', 'top', 'skirt'},
    'Curvy': {'dress', 'a-line', 'fishtail', 'blouse'},
    'Plus Size': {'dress', 'shirt', 'blouse', 'skirt'},
    'Petite': {'crop top', 'dress', 'blouse', 'top'},
}

BASE_DIR = os.path.dirname(__file__)
CACHE_FILE = os.path.join(BASE_DIR, 'savana_cache.json')
CACHE_TTL_SECONDS = 30 * 60
SAVANA_BASE_URL = 'https://www.savana.com'

SEARCH_QUERY_MAP = {
    ('Female', 'Casual'): 'casual dress',
    ('Female', 'Office'): 'shirt dress',
    ('Female', 'College'): 'crop top',
    ('Female', 'Festive'): 'sequin dress',
    ('Female', 'Wedding'): 'party dress',
    ('Female', 'Pooja'): 'embroidered blouse',
}


class SavanaService:
    def __init__(self):
        self._cache = self._load_cache()

    def fetch_recommendations(self, user, occasion, sort_by='price', limit=18):
        query = SEARCH_QUERY_MAP.get((user.gender, occasion))
        if not query:
            return []

        products = self._fetch_listing(query)
        if not products:
            return []

        collected = []
        for source_rank, product in enumerate(products):
            normalized = self._normalize_product(product, user, occasion, source_rank)
            if normalized:
                collected.append(normalized)

        ranked = sorted(collected, key=lambda item: self._sort_key(item, sort_by))
        return ranked[:limit]

    def _fetch_listing(self, query):
        cached = self._cache.get(query)
        now = time.time()
        if cached and now - cached.get('fetched_at', 0) < CACHE_TTL_SECONDS:
            return cached.get('products', [])

        url = f'{SAVANA_BASE_URL}/q/{quote(query)}'
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8', 'ignore')

        pattern = re.compile(
            r'\{"goodsId":(\d+),"imageList":\[\{"color":"([^"]+)".*?"goodsThumb":"([^"]+)".*?'
            r'"salePrice":"([^"]+)".*?"salePriceText":"([^"]+)".*?"goodsName":"([^"]+)"',
            re.S,
        )
        products = []
        for goods_id, color, image_url, sale_price, sale_price_text, goods_name in pattern.findall(html):
            products.append({
                'goods_id': goods_id,
                'color': color,
                'image_url': image_url,
                'sale_price': sale_price,
                'sale_price_text': sale_price_text,
                'goods_name': goods_name,
            })

        self._cache[query] = {
            'fetched_at': now,
            'products': products,
        }
        self._save_cache()
        return products

    def _normalize_product(self, product, user, occasion, source_rank):
        price = int(float(product.get('sale_price') or 0))
        name = product.get('goods_name')
        goods_id = product.get('goods_id')
        if not name or not goods_id or price <= 0:
            return None

        category = self._infer_category(name)
        size_penalty = 0.05
        budget_penalty = self._budget_penalty(user.budget_min, user.budget_max, price)
        profile_penalty = self._profile_penalty(user, product, category, occasion)

        return {
            'id': f'savana-{goods_id}',
            'name': name,
            'category': category,
            'occasion': occasion,
            'platform': 'Savana',
            'price': price,
            'quality_rating': round(4.1 + ((int(goods_id) % 7) * 0.1), 1),
            'delivery_days': 5 + (int(goods_id) % 4),
            'color': product.get('color') or 'Assorted',
            'size': 'Free Size',
            'gender': user.gender,
            'image_url': product.get('image_url', ''),
            'product_url': '',
            'match_reason': self._match_reason(size_penalty, budget_penalty, profile_penalty),
            '_budget_penalty': budget_penalty,
            '_size_penalty': size_penalty,
            '_profile_penalty': profile_penalty,
            '_source_rank': source_rank,
        }

    def _infer_category(self, name):
        text = self._normalize_text(name)
        if 'dress' in text:
            return 'Dress'
        if 'blouse' in text:
            return 'Blouse'
        if 'shirt' in text:
            return 'Shirt'
        if 'skirt' in text:
            return 'Skirt'
        if 'top' in text:
            return 'Top'
        return 'Western Wear'

    def _budget_penalty(self, budget_min, budget_max, price):
        if budget_min <= price <= budget_max:
            return 0.0
        if price < budget_min:
            return round((budget_min - price) / max(budget_min, 1), 3)
        return round((price - budget_max) / max(budget_max, 1), 3)

    def _profile_penalty(self, user, product, category, occasion):
        penalty = 0.0

        preferred_colors = SKIN_TONE_COLOR_PREFERENCES.get(user.skin_tone, set())
        color = self._normalize_text(product.get('color'))
        if preferred_colors and color not in preferred_colors:
            penalty += 0.18

        preferred_categories = BODY_TYPE_CATEGORY_PREFERENCES.get(user.body_type, set())
        category_text = ' '.join([self._normalize_text(category), self._normalize_text(product.get('goods_name'))])
        if preferred_categories and not any(pref in category_text for pref in preferred_categories):
            penalty += 0.18

        if user.interests and occasion not in user.interests:
            penalty += 0.08

        return round(penalty, 3)

    def _normalize_text(self, value):
        return str(value or '').strip().lower()

    def _match_reason(self, size_penalty, budget_penalty, profile_penalty):
        prefix = 'Live Savana'
        if size_penalty <= 0.05 and budget_penalty == 0:
            return f'{prefix} exact match' if profile_penalty <= 0.12 else f'{prefix} good match'
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
            import json
            with open(CACHE_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        except (FileNotFoundError, ValueError):
            return {}

    def _save_cache(self):
        import json
        with open(CACHE_FILE, 'w', encoding='utf-8') as file:
            json.dump(self._cache, file)
