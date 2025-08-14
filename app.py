from flask import Flask, render_template, request, jsonify
from ai_service import get_ad_parameters_from_ai
from facebook_service import create_facebook_ad

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

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


if __name__ == '__main__':
    app.run(debug=True)
