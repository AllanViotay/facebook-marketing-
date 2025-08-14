# AI-Powered Facebook Ad Creator

This project is a web application that allows users to create Facebook ads using natural language. You describe the ad you want, and the application uses AI to understand your request and create the ad in Facebook Ads Manager.

This MVP (Minimum Viable Product) ships with a working frontend, backend, and mock AI and Facebook services. It can optionally use real OpenAI and Facebook APIs when you provide credentials.

## Project Structure

- `app.py`: The main Flask web server. It handles routing and orchestrates the calls to the AI and Facebook services.
- `ai_service.py`: Handles the Natural Language Processing. It takes a user's description and extracts structured ad parameters.
  - Uses OpenAI (if `OPENAI_API_KEY` is configured) or a local regex-based mock fallback.
- `facebook_service.py`: Handles the integration with the Facebook Marketing API.
  - Uses Facebook SDK if credentials are configured, otherwise returns mock IDs.
- `config.py`: Optional. You can place credentials here instead of environment variables. See `config.example.py`.
- `templates/index.html`: The main HTML file for the user interface.
- `static/`: Contains the CSS and JavaScript for the frontend.
- `requirements.txt`: Python dependencies.
- `.gitignore`: Ensures sensitive files like `config.py` are not committed to version control.

## Setup and Configuration

1.  Create and activate a virtual environment (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Provide credentials (optional for full functionality):
   
    You can either export environment variables or create a `config.py` by copying `config.example.py`.

    - Environment variables (recommended for local/dev):
      ```bash
      export OPENAI_API_KEY="sk-..."
      export FACEBOOK_APP_ID="..."
      export FACEBOOK_APP_SECRET="..."
      export FACEBOOK_ACCESS_TOKEN="..."
      export FACEBOOK_AD_ACCOUNT_ID="act_..."
      ```

    - Or create a `config.py` file in the project root based on `config.example.py`.

## How to Run

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

- Without credentials, the app will run using mock AI and mock Facebook calls.
- With credentials, the app will use OpenAI to extract parameters and the Facebook SDK to create a paused Campaign and Ad Set in your account.

## Notes

- When using the Facebook SDK, minimal required fields are set and all objects are created with status `PAUSED` to avoid accidental spend.
- Budget parsing is simplistic: the first integer found in the description is interpreted as USD dollars per day. Adjust in `facebook_service.py` as needed.
