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

    # Step 2: Create the ad on Facebook (mocked)
    facebook_result = create_facebook_ad(ad_params)

    # Step 3: Combine results and return to frontend
    response = {
        'ai_result': ad_params,
        'facebook_result': facebook_result
    }

    return jsonify(response)


if __name__ == '__main__':
    app.run(debug=True)
