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

## Targeting helpers

You can provide a complete `targeting` object or use helper fields; the service merges helpers into a valid Marketing API targeting spec.

Supported helpers (selected):
- Geo: `countries`, `regions`, `cities`, `zips`, `custom_locations`, `location_types`, `excluded_geo_locations` (or pass full `geo_locations`)
- Demographics: `age_min`, `age_max`, `genders`, `locales` (alias `languages`), education/work fields
- Platforms/placements: `device_platforms`, `publisher_platforms`, `facebook_positions`, `instagram_positions`, `messenger_positions`, `audience_network_positions`
- Interests: `interest_ids` or full `interests` objects; `interest_terms` (auto-resolves top matches via TargetingSearch when SDK/creds available)
- Behaviors and more: `behaviors`, `life_events`, `industries`, `politics`, `family_statuses`, `income`, `home_ownership`, `ethnic_affinity`
- Custom audiences: `custom_audience_ids`/`custom_audiences`, `excluded_custom_audience_ids`/`excluded_custom_audiences`
- Connections: `connections`, `excluded_connections`, `friends_of_connections`
- Lookalike: `lookalike` with keys `origin_audience_id`, `country`, `type`, `ratio`
- Expansion: `targeting_expansion` / `targeting_optimization`

Example combining helpers:

```json
{
  "ad_set": {
    "daily_budget": 2500
  },
  "countries": ["US"],
  "cities": [{"key": "2424766", "radius": 10, "distance_unit": "mile"}],
  "age_min": 25,
  "age_max": 55,
  "genders": [1],
  "publisher_platforms": ["facebook", "instagram"],
  "facebook_positions": ["feed"],
  "instagram_positions": ["stream", "story"],
  "interest_terms": ["home office", "standing desk"],
  "custom_audience_ids": ["<CA_ID>"]
}
```

You may also pass a full `targeting` object directly; we forward it as-is.

## Advanced creative/format helpers

- Instant Experience (Canvas):
  - Provide `instant_experience_id` (or `canvas_id`) to attach an IX to the creative CTA value.
- Collection/DPA helpers:
  - Provide `product_set_id` and optional `creative_flexible_spec` (images/videos/bodies/titles/descriptions/link_urls/call_to_action_types) to auto-build `asset_feed_spec`.
  - Or pass `retailer_item_ids` for curated sets.
- Use existing post: `object_story_id` to turn a Page post into an ad.
- Carousel helper: `carousel_items` array with per-card `name`, `description`, link/CTA, and auto image uploads.
- App ads helpers: `app_link`/`deep_link` auto-injected as CTA value.
- WhatsApp helper: `whatsapp_number` sets CTA type/value for WhatsApp messaging.

## Placement and media guidance

- We surface warnings for incompatible media specs per placement (e.g., Reels/Stories prefer 9:16 and Reels <= 90s).
- You can optionally pass `media_aspect_ratio` and `video_duration_seconds` to enable richer validation.
- Set placements via `publisher_platforms` and `facebook_positions`/`instagram_positions`/`messenger_positions`/`audience_network_positions`.

## Catalog/Advantage+ notes

- For catalog sales, pass `product_set_id` and optional `asset_feed_spec`/`creative_flexible_spec`.
- Advantage+ Catalog and creative toggles can be set via ad set/campaign fields; any official fields you pass through are forwarded unchanged.

## Compliance

- EU DSA helpers: `dsa_beneficiary`, `dsa_payor` on the ad set.
- Political and other regional disclaimers are supported via pass-through fields you supply; we forward them as-is.

## Validation and dry runs

- Basic enum checks surface warnings for `objective`, `billing_event`, `optimization_goal`, and CTA types.
- Placement/media checks emit warnings; set `strict_validation: true` to raise errors instead.
- Pass `dry_run: true` to validate and receive built `campaign_params`, `ad_set_params`, `creative_params`, and `ad_params` without creating anything.

### Dry run example

```json
{
  "objective": "TRAFFIC",
  "publisher_platforms": ["instagram"],
  "instagram_positions": ["reels"],
  "media_aspect_ratio": "4:5",
  "video_duration_seconds": 120,
  "dry_run": true,
  "strict_validation": false
}
```

The response includes warnings and the fully constructed payloads that would be sent.

## Insights API

Use `POST /api/insights` to fetch performance data.

Payload:
- `level`: `account` | `campaign` | `adset` | `ad`
- `ids`: list of ids for the chosen level (omit for `account`)
- `fields`: array of metric fields (defaults provided)
- `date_preset` or `time_range` ({"since":"YYYY-MM-DD","until":"YYYY-MM-DD"})
- Optional: `breakdowns`, `time_increment`, `filtering`, `limit`

Example (account, last 7 days, daily):
```json
{
  "level": "account",
  "date_preset": "last_7d",
  "time_increment": 1,
  "fields": ["date_start","date_stop","spend","impressions","clicks","ctr","cpc","cpm"]
}
```

Example (campaign IDs with country breakdown):
```json
{
  "level": "campaign",
  "ids": ["<CAMPAIGN_ID_1>","<CAMPAIGN_ID_2>"],
  "date_preset": "last_30d",
  "breakdowns": ["country"],
  "fields": ["impressions","spend","reach"]
}
```

If SDK/creds are not configured, a mock insights payload is returned for development.
