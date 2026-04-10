import json
import os
import re
import time
from urllib.parse import urljoin
from urllib.request import Request, urlopen


BASE_DIR = os.path.dirname(__file__)
CACHE_FILE = os.path.join(BASE_DIR, 'myntra_cache.json')
CACHE_TTL_SECONDS = 30 * 60
SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
SKIN_TONE_COLOR_PREFERENCES = {
    'Fair': {'red', 'maroon', 'emerald', 'green', 'lavender', 'black', 'blue', 'navy blue', 'pink'},
    'Wheatish': {'mustard', 'teal', 'maroon', 'navy blue', 'olive', 'cream', 'rust', 'purple'},
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
MYNTRA_BASE_URL = 'https://www.myntra.com/'

URL_MAP = {
    ('Female', 'Casual'): [
        'https://www.myntra.com/kurtis',
        'https://www.myntra.com/kurta-sets',
        'https://www.myntra.com/salwar-and-dupatta-sets',
        'https://www.myntra.com/sarees',
    ],
    ('Female', 'Office'): [
        'https://www.myntra.com/kurtis',
        'https://www.myntra.com/kurta-sets',
        'https://www.myntra.com/salwar-and-dupatta-sets',
        'https://www.myntra.com/sarees',
    ],
    ('Female', 'College'): [
        'https://www.myntra.com/kurtis',
        'https://www.myntra.com/kurta-sets',
        'https://www.myntra.com/lehenga-choli',
        'https://www.myntra.com/sarees',
    ],
    ('Female', 'Festive'): [
        'https://www.myntra.com/lehenga-choli',
        'https://www.myntra.com/ethnic-dresses',
        'https://www.myntra.com/kurta-sets',
        'https://www.myntra.com/salwar-and-dupatta-sets',
        'https://www.myntra.com/sarees',
    ],
    ('Female', 'Wedding'): [
        'https://www.myntra.com/lehenga-choli',
        'https://www.myntra.com/ethnic-dresses',
        'https://www.myntra.com/embroidered-sarees',
        'https://www.myntra.com/sarees',
        'https://www.myntra.com/salwar-and-dupatta-sets',
        'https://www.myntra.com/kurta-sets',
    ],
    ('Female', 'Pooja'): [
        'https://www.myntra.com/sarees',
        'https://www.myntra.com/kurta-sets',
        'https://www.myntra.com/salwar-and-dupatta-sets',
        'https://www.myntra.com/lehenga-choli',
    ],
    ('Male', 'Casual'): [
        'https://www.myntra.com/men-kurta',
        'https://www.myntra.com/men-kurta-sets',
        'https://www.myntra.com/nehru-jackets',
    ],
    ('Male', 'Office'): [
        'https://www.myntra.com/men-kurta',
        'https://www.myntra.com/nehru-jackets',
        'https://www.myntra.com/men-kurta-sets',
    ],
    ('Male', 'College'): [
        'https://www.myntra.com/men-kurta',
        'https://www.myntra.com/nehru-jackets',
        'https://www.myntra.com/men-kurta-sets',
    ],
    ('Male', 'Festive'): [
        'https://www.myntra.com/sherwani',
        'https://www.myntra.com/men-kurta-sets',
        'https://www.myntra.com/dhotis',
        'https://www.myntra.com/nehru-jackets',
    ],
    ('Male', 'Wedding'): [
        'https://www.myntra.com/sherwani',
        'https://www.myntra.com/men-kurta-sets',
        'https://www.myntra.com/men-kurta',
        'https://www.myntra.com/dhotis',
        'https://www.myntra.com/nehru-jackets',
    ],
    ('Male', 'Pooja'): [
        'https://www.myntra.com/dhotis',
        'https://www.myntra.com/men-kurta-sets',
        'https://www.myntra.com/men-kurta',
        'https://www.myntra.com/nehru-jackets',
    ],
}


class MyntraService:
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
                product_id = f"myntra-{product.get('productId')}"
                if product_id in seen_ids:
                    continue

                normalized = self._normalize_product(product, user, occasion, source_rank)
                if not normalized:
                    continue

                seen_ids.add(product_id)
                collected.append(normalized)

        ranked = sorted(collected, key=lambda item: self._sort_key(item, sort_by))
        return ranked[:limit]

    def _fetch_listing(self, url):
        cached = self._cache.get(url)
        now = time.time()
        if cached and now - cached.get('fetched_at', 0) < CACHE_TTL_SECONDS:
            return cached.get('products', [])

        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8', 'ignore')

        match = re.search(r'window\.__myx = (\{.*?\})</script>', html)
        if not match:
            return []

        payload = json.loads(match.group(1))
        products = payload.get('searchData', {}).get('results', {}).get('products', [])

        self._cache[url] = {
            'fetched_at': now,
            'products': products,
        }
        self._save_cache()
        return products

    def _normalize_product(self, product, user, occasion, source_rank):
        product_id = product.get('productId')
        name = product.get('productName') or product.get('product') or ''
        if not product_id or not name:
            return None

        size_penalty = self._size_penalty(user.size, product.get('sizes', ''))
        budget_penalty = self._budget_penalty(user.budget_min, user.budget_max, product.get('price', 0))
        profile_penalty = self._profile_penalty(user, product, occasion)
        image_url = self._normalize_image(product.get('searchImage', ''))

        return {
            'id': f"myntra-{product_id}",
            'name': name,
            'category': self._category_name(product),
            'occasion': occasion,
            'platform': 'Myntra',
            'price': int(product.get('price') or 0),
            'quality_rating': round(float(product.get('rating') or 4.0), 1),
            'delivery_days': 2 + (int(product_id) % 4),
            'color': product.get('primaryColour') or 'Assorted',
            'size': self._display_size(product.get('sizes', '')),
            'gender': user.gender,
            'image_url': image_url,
            'product_url': urljoin(MYNTRA_BASE_URL, product.get('landingPageUrl', '')),
            'match_reason': self._match_reason(size_penalty, budget_penalty, profile_penalty, True),
            '_budget_penalty': budget_penalty,
            '_size_penalty': size_penalty,
            '_profile_penalty': profile_penalty,
            '_source_rank': source_rank,
        }

    def _normalize_image(self, image_url):
        if image_url.startswith('http://'):
            return image_url.replace('http://', 'https://', 1)
        return image_url

    def _category_name(self, product):
        article_type = product.get('articleType', {})
        if isinstance(article_type, dict) and article_type.get('typeName'):
            return article_type['typeName']
        return product.get('category') or 'Ethnic Wear'

    def _display_size(self, sizes):
        parts = [part.strip() for part in str(sizes).split(',') if part.strip()]
        if not parts:
            return 'Free Size'
        if 'Free Size' in parts:
            return 'Free Size'
        return parts[0]

    def _size_penalty(self, user_size, sizes):
        parts = [part.strip() for part in str(sizes).split(',') if part.strip()]
        if not parts:
            return 0.7
        if 'Free Size' in parts:
            return 0.05
        if user_size in parts:
            return 0.0

        indexed = [SIZE_ORDER.index(size) for size in parts if size in SIZE_ORDER]
        if user_size not in SIZE_ORDER or not indexed:
            return 0.8

        user_index = SIZE_ORDER.index(user_size)
        return 0.2 * min(abs(user_index - idx) for idx in indexed)

    def _budget_penalty(self, budget_min, budget_max, price):
        if budget_min <= price <= budget_max:
            return 0.0
        if price < budget_min:
            return round((budget_min - price) / max(budget_min, 1), 3)
        return round((price - budget_max) / max(budget_max, 1), 3)

    def _profile_penalty(self, user, product, occasion):
        penalty = 0.0

        preferred_colors = SKIN_TONE_COLOR_PREFERENCES.get(user.skin_tone, set())
        color = self._normalize_text(product.get('primaryColour'))
        if preferred_colors and color not in preferred_colors:
            penalty += 0.18

        preferred_categories = BODY_TYPE_CATEGORY_PREFERENCES.get(user.body_type, set())
        category_text = ' '.join([
            self._normalize_text(self._category_name(product)),
            self._normalize_text(product.get('productName')),
            self._normalize_text(product.get('additionalInfo')),
        ])
        if preferred_categories and not any(pref in category_text for pref in preferred_categories):
            penalty += 0.22

        if user.interests and occasion not in user.interests:
            penalty += 0.08

        return round(penalty, 3)

    def _normalize_text(self, value):
        return str(value or '').strip().lower()

    def _match_reason(self, size_penalty, budget_penalty, profile_penalty, live_result=False):
        prefix = 'Live Myntra'
        if size_penalty <= 0.05 and budget_penalty == 0:
            return f'{prefix} exact match' if live_result and profile_penalty <= 0.12 else ('Exact match' if profile_penalty <= 0.12 else f'{prefix} good match')
        if budget_penalty == 0:
            return f'{prefix} nearby size' if live_result and profile_penalty <= 0.12 else ('More sizes' if profile_penalty <= 0.12 else f'{prefix} style compromise')
        if size_penalty <= 0.05:
            return f'{prefix} budget stretch' if live_result else 'Budget stretch'
        return f'{prefix} close match' if live_result else 'Close match'

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
