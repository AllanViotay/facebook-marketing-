from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/create-ad', methods=['POST'])
def create_ad():
    data = request.get_json()
    description = data.get('description', '')

    # Mock AI processing
    ad_params = mock_ai_processing(description)

    return jsonify(ad_params)

def mock_ai_processing(description):
    # Super simple keyword extraction
    import re
    params = {
        'target_audience': 'not specified',
        'budget': 'not specified',
        'ad_copy': description # default to full description
    }

    # Example: find budget
    budget_match = re.search(r'(\d+\s*(?:USD|dollars|\$))', description, re.IGNORECASE)
    if budget_match:
        params['budget'] = budget_match.group(1)

    # Example: find audience
    audience_match = re.search(r'for an audience of\s*([\w\s]+)', description, re.IGNORECASE)
    if audience_match:
        potential_audience = audience_match.group(1).strip()
        params['target_audience'] = potential_audience

    # Example: find ad copy
    copy_match = re.search(r'the ad copy should be\s*"(.*?)"', description, re.IGNORECASE)
    if copy_match:
        params['ad_copy'] = copy_match.group(1)

    return params


if __name__ == '__main__':
    app.run(debug=True)
