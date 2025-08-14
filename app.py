from flask import Flask, render_template, request, jsonify
from ai_service import get_ad_parameters_from_ai
from facebook_service import create_facebook_ad
from facebook_service import get_insights
from ai_service import update_runtime_openai_key
from facebook_service import update_runtime_facebook_creds, get_runtime_facebook_creds
from settings_persistence import save_to_config_py
from ai_service import generate_ad_copy, generate_ad_image, analyze_insights_and_suggest_copy

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/settings')
def settings_page():
    fb = get_runtime_facebook_creds()
    return render_template('settings.html', fb=fb)

@app.route('/api/settings', methods=['POST'])
def save_settings():
    payload = request.get_json() or {}
    persist = bool(payload.get('persist'))
    # Runtime apply
    if 'openai_key' in payload and payload['openai_key']:
        update_runtime_openai_key(payload['openai_key'])
    fb = payload.get('facebook') or {}
    if fb:
        update_runtime_facebook_creds(
            app_id=fb.get('app_id'),
            app_secret=fb.get('app_secret'),
            access_token=fb.get('access_token'),
            ad_account_id=fb.get('ad_account_id'),
            page_id=fb.get('page_id'),
        )
    saved_path = None
    if persist:
        saved_path = save_to_config_py(
            openai_key=payload.get('openai_key'),
            fb_app_id=fb.get('app_id'),
            fb_app_secret=fb.get('app_secret'),
            fb_access_token=fb.get('access_token'),
            fb_ad_account_id=fb.get('ad_account_id'),
            fb_page_id=fb.get('page_id'),
        )
    return jsonify({'success': True, 'message': 'Settings applied.', 'persisted': bool(saved_path), 'path': saved_path})

@app.route('/api/ai/copy', methods=['POST'])
def ai_copy():
    payload = request.get_json() or {}
    res = generate_ad_copy(
        prompt=payload.get('prompt') or '',
        tone=payload.get('tone'),
        length=payload.get('length'),
        language=payload.get('language'),
    )
    return jsonify({'result': res})

@app.route('/api/ai/image', methods=['POST'])
def ai_image():
    payload = request.get_json() or {}
    res = generate_ad_image(
        prompt=payload.get('prompt') or '',
        size=payload.get('size') or '1024x1024',
        n=int(payload.get('n') or 1),
    )
    return jsonify({'result': res})

@app.route('/api/ai/insights-suggest', methods=['POST'])
def ai_insights_suggest():
    payload = request.get_json() or {}
    # Either provide insights directly or fetch via our insights endpoint-like payload
    insights = payload.get('insights')
    if not insights and payload.get('fetch'):
        insights = get_insights(payload.get('fetch') or {})
    suggestions = analyze_insights_and_suggest_copy(insights or {}, context=payload.get('context') or {})
    return jsonify({'result': suggestions})

@app.route('/api/create-ad', methods=['POST'])
def create_ad():
    data = request.get_json()
    description = data.get('description', '')

    # Step 1: Get ad parameters from AI service
    ad_params = get_ad_parameters_from_ai(description)

    # Allow basic overrides from frontend call (optional)
    ad_params.update({k: v for k, v in data.items() if k not in ('description',)})

    # Step 2: Create the ad on Facebook (mock or real)
    facebook_result = create_facebook_ad(ad_params)

    # Step 3: Combine results and return to frontend
    response = {
        'ai_result': ad_params,
        'facebook_result': facebook_result
    }

    return jsonify(response)

@app.route('/api/create-ad-advanced', methods=['POST'])
def create_ad_advanced():
    """
    Accepts a full payload for campaign/ad set/creative/ad via nested dicts.
    Does not call AI; directly passes through to Facebook service.
    """
    payload = request.get_json() or {}
    result = create_facebook_ad(payload)
    return jsonify({'facebook_result': result})

@app.route('/api/insights', methods=['POST'])
def insights():
    payload = request.get_json() or {}
    result = get_insights(payload)
    return jsonify({'insights_result': result})


if __name__ == '__main__':
    app.run(debug=True)
