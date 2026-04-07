from flask import Flask, render_template, request, jsonify
from recommender import (
    User, Recommender,
    save_profile, load_profile,
    log_purchase, get_purchase_history,
    get_category_stats
)

app = Flask(__name__)
recommender = Recommender()


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

        results = recommender.recommend(profile, occasion, sort_by)
        price_chart = recommender.get_price_comparison(occasion)
        quality_chart = recommender.get_quality_comparison(occasion)

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
        success = log_purchase(item_id)
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


if __name__ == '__main__':
    app.run(debug=True)
