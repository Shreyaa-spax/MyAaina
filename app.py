import os
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import Flask, render_template, request, jsonify, Response
from manyavar_service import ManyavarService
from myntra_service import MyntraService
from savana_service import SavanaService
from recommender import (
    User, Recommender,
    save_profile, load_profile,
    log_purchase, get_purchase_history,
    get_category_stats
)

BASE_DIR = os.path.dirname(__file__)

app = Flask(
    __name__,
    template_folder=BASE_DIR,
    static_folder=BASE_DIR,
)
recommender = Recommender()
myntra_service = MyntraService()
savana_service = SavanaService()
manyavar_service = ManyavarService()


@app.route('/')
def index():
    profile = load_profile()
    return render_template('index.html', profile=profile)


@app.route('/api/save-profile', methods=['POST'])
def save_profile_route():
    try:
        data = request.json
        user = User(
            name=data['name'],
            age=int(data['age']),
            gender=data['gender'],
            body_type=data['body_type'],
            skin_tone=data['skin_tone'],
            size=data['size'],
            budget_min=int(data['budget_min']),
            budget_max=int(data['budget_max']),
            interests=data['interests']
        )
        save_profile(user)
        return jsonify({'success': True, 'message': f'Profile saved for {user.name}!'})
    except (KeyError, ValueError) as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/recommend', methods=['POST'])
def recommend():
    try:
        data = request.json
        profile = load_profile()
        if not profile:
            return jsonify({'success': False, 'message': 'Please create your profile first!'}), 400

        occasion = data.get('occasion', '')
        sort_by = data.get('sort_by', 'price')

        if not occasion:
            return jsonify({'success': False, 'message': 'Please select an occasion!'}), 400

        live_results = myntra_service.fetch_recommendations(profile, occasion, sort_by, limit=24)
        savana_results = savana_service.fetch_recommendations(profile, occasion, sort_by, limit=18)
        manyavar_limit = 30 if occasion == 'Wedding' else 18
        manyavar_results = manyavar_service.fetch_recommendations(profile, occasion, sort_by, limit=manyavar_limit)
        local_results = [
            item for item in recommender.recommend(profile, occasion, sort_by, limit=36)
            if item.get('platform') != 'Meesho'
        ]

        if occasion == 'Wedding':
            sources = [manyavar_results[:12], manyavar_results[12:], live_results, local_results]
        else:
            sources = [live_results, savana_results, manyavar_results, local_results]

        results = merge_results(*sources, limit=12)
        chart_results = merge_results(*sources, limit=36)
        price_chart = build_platform_chart(chart_results, 'price')
        quality_chart = build_platform_chart(chart_results, 'quality_rating')

        return jsonify({
            'success': True,
            'results': results,
            'price_chart': price_chart,
            'quality_chart': quality_chart,
            'occasion': occasion,
            'user': profile.name
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/log-purchase', methods=['POST'])
def log_purchase_route():
    try:
        data = request.json
        item_id = data.get('item_id')
        item_payload = data.get('item')
        success = log_purchase(item_id, item_payload)
        if success:
            return jsonify({'success': True, 'message': 'Purchase logged!'})
        return jsonify({'success': False, 'message': 'Item not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def history():
    try:
        items = get_purchase_history()
        stats = get_category_stats()
        return jsonify({'success': True, 'items': items, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/profile', methods=['GET'])
def profile():
    try:
        saved_profile = load_profile()
        if not saved_profile:
            return jsonify({'success': True, 'profile': None})
        return jsonify({'success': True, 'profile': saved_profile.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/image-proxy', methods=['GET'])
def image_proxy():
    try:
        image_url = request.args.get('url', '').strip()
        if not image_url.startswith(('http://', 'https://')):
            return jsonify({'success': False, 'message': 'Invalid image URL'}), 400

        parsed = urlparse(image_url)
        referer_map = {
            'myntra.com': 'https://www.myntra.com/',
            'manyavar.com': 'https://www.manyavar.com/',
            'savana.com': 'https://www.savana.com/',
        }

        referer = None
        for domain, value in referer_map.items():
            if domain in parsed.netloc:
                referer = value
                break

        headers = {'User-Agent': 'Mozilla/5.0'}
        if referer:
            headers['Referer'] = referer

        req = Request(image_url, headers=headers)
        with urlopen(req, timeout=25) as response:
            content = response.read()
            mimetype = response.headers.get_content_type()

        return Response(
            content,
            mimetype=mimetype,
            headers={'Cache-Control': 'public, max-age=21600'}
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 502


def merge_results(*result_sets, limit=12):
    merged = []
    seen = set()
    buckets = [list(result_set) for result_set in result_sets if result_set]

    while buckets and len(merged) < limit:
        active = False
        for bucket in buckets:
            if len(merged) >= limit:
                break
            while bucket:
                result = bucket.pop(0)
                key = (result.get('platform'), result.get('name'))
                if key in seen:
                    continue
                seen.add(key)
                merged.append(result)
                active = True
                break
        if not active:
            break
    return merged


def build_platform_chart(results, field):
    grouped = {}
    for item in results:
        platform = item.get('platform')
        value = item.get(field)
        if platform is None or value is None:
            continue
        grouped.setdefault(platform, []).append(float(value))

    chart = {}
    for platform, values in grouped.items():
        if values:
            chart[platform] = round(sum(values) / len(values), 2)
    return chart


if __name__ == '__main__':
    app.run(debug=True)
