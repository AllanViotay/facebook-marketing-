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
      export FACEBOOK_PAGE_ID="..."
      ```

    - Or create a `config.py` file in the project root based on `config.example.py`.

## How to Run

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

- Without credentials, the app will run using mock AI and mock Facebook calls.
- With credentials, the app will use OpenAI to extract parameters and the Facebook SDK to create a paused Campaign and Ad Set, upload optional image/video assets, and create an AdCreative and Ad.

## Advanced API (full control)

Use `POST /api/create-ad-advanced` to pass through any Facebook fields when creating:

- Campaign (`campaign`)
- Ad Set (`ad_set`)
- AdCreative (`creative`)
- Ad (`ad`)

Additionally, you may provide convenience top-level fields that will be merged into entities or used to build defaults:

- `objective`, `campaign_status`, `special_ad_categories`, `special_ad_category_country`, `buying_type`, `bid_strategy`
- `daily_budget`, `lifetime_budget`, `billing_event`, `adset_status`, `optimization_goal`, `pacing_type`, `targeting`, `geo_locations`, `publisher_platforms`, `facebook_positions`, `instagram_positions`, `start_time`, `end_time`, `bid_amount`, `promoted_object`
- `ad_name`, `ad_status`, `tracking_specs`, `execution_options`, `adlabels`
- `ad_copy`, `headline`, `description`, `call_to_action_type`, `page_id`, `link_url` (or `website_url`), `object_story_spec`, `asset_feed_spec`, `instagram_actor_id`
- Asset helpers: `image_hash` OR provide one of: `image_path`, `image_base64`, `image_url` (we will upload & inject the hash); `video_id` OR `video_path`/`video_url` (we will upload & inject the id)
- Lead forms: `lead_form_id` to reuse an existing form, or `lead_form` object to create a new one on the Page (requires `page_id`)

Example minimal payload (link ad):

```json
{
  "campaign": {"name": "Site Traffic", "objective": "LINK_CLICKS", "status": "PAUSED"},
  "ad_set": {
    "name": "Prospects US",
    "billing_event": "IMPRESSIONS",
    "daily_budget": 2000,
    "targeting": {"geo_locations": {"countries": ["US"]}}
  },
  "creative": {
    "name": "Link Creative",
    "object_story_spec": {
      "page_id": "<PAGE_ID>",
      "link_data": {"message": "Check this out", "link": "https://example.com", "name": "Learn more"}
    }
  },
  "ad": {"name": "Ad 1", "status": "PAUSED"}
}
```

Example lead-gen ad reusing an existing form:

```json
{
  "objective": "LEAD_GENERATION",
  "ad_set": {"daily_budget": 2000, "targeting": {"geo_locations": {"countries": ["US"]}}},
  "page_id": "<PAGE_ID>",
  "lead_form_id": "<LEAD_FORM_ID>",
  "ad_copy": "Get a free quote",
  "headline": "Request a demo",
  "link_url": "https://www.facebook.com/",
  "call_to_action_type": "LEARN_MORE"
}
```

Example lead-gen ad creating a new form on the Page:

```json
{
  "objective": "LEAD_GENERATION",
  "ad_set": {"daily_budget": 2500, "targeting": {"geo_locations": {"countries": ["US"]}}},
  "page_id": "<PAGE_ID>",
  "lead_form": {
    "name": "Demo Request",
    "follow_up_action_url": "https://example.com/thank-you",
    "privacy_policy_url": "https://example.com/privacy",
    "questions": [
      {"type": "FULL_NAME"},
      {"type": "EMAIL"}
    ]
  },
  "ad_copy": "Request your demo now",
  "headline": "Limited spots"
}
```

Notes:

- For lead forms, the form is created on the `page_id`. You can also pass an existing `lead_form_id` to reuse.
- We automatically wire the `lead_gen_form_id` into the creative’s call-to-action.
- All objects are created with status `PAUSED` by default unless you override.
- To avoid accidental spend, verify budgets and statuses before switching to `ACTIVE`.
