# AI-Powered Facebook Ad Creator

This project is a web application that allows users to create Facebook ads using natural language. You describe the ad you want, and the application uses AI to understand your request and create the ad in Facebook Ads Manager.

This MVP (Minimum Viable Product) is fully scaffolded with a working frontend, backend, and mock AI and Facebook services. It is ready for a developer to integrate real API keys and services.

## Project Structure

- `app.py`: The main Flask web server. It handles routing and orchestrates the calls to the AI and Facebook services.
- `ai_service.py`: Handles the Natural Language Processing. It takes a user's description and extracts structured ad parameters.
  - Contains `_mock_ai_processing()` which uses regex for local development.
  - Ready to be integrated with a real LLM like GPT or Claude.
- `facebook_service.py`: Handles the integration with the Facebook Marketing API.
  - Contains `create_facebook_ad()` which is a placeholder that logs the actions it would take.
  - Ready to be integrated with the `facebook_business` SDK.
- `config.py`: **IMPORTANT!** This is where you put your API keys. This file is NOT committed to git (see `.gitignore`).
- `templates/index.html`: The main HTML file for the user interface.
- `static/`: Contains the CSS and JavaScript for the frontend.
- `requirements.txt`: A list of Python dependencies.
- `.gitignore`: Ensures sensitive files like `config.py` are not committed to version control.

## Setup and Configuration

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure API Keys:**
    The application requires API keys for the AI service and Facebook.
    - Create a `config.py` file in the root directory.
    - Add your credentials to this file. It should look like this:
    ```python
    # config.py
    OPENAI_API_KEY = "sk-..."
    FACEBOOK_APP_ID = "..."
    FACEBOOK_APP_SECRET = "..."
    FACEBOOK_ACCESS_TOKEN = "..."
    FACEBOOK_AD_ACCOUNT_ID = "act_..."
    ```

## How to Run

Once you have completed the setup and configuration, you can run the application with the following command:

```bash
python app.py
```

The application will be available at `http://127.0.0.1:5000`.

## Next Steps: Going to Production

To make this application fully functional, you need to replace the mock services with real ones.

1.  **AI Service (`ai_service.py`):**
    - Uncomment the `import openai` and `from config ...` lines.
    - In the `get_ad_parameters_from_ai` function, replace the call to `_mock_ai_processing` with a real API call to your chosen LLM provider. An example prompt is provided in the comments.

2.  **Facebook Service (`facebook_service.py`):**
    - Install the Facebook SDK: `pip install facebook_business`
    - Uncomment the import lines at the top of the file.
    - In the `create_facebook_ad` function, replace the `print` statements and mock IDs with real calls to the Facebook Marketing API using the SDK. You will need to handle the ad account ID and other parameters dynamically.
