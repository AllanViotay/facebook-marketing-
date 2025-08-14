# In a real app, you would install the facebook_business SDK
# pip install facebook-business

try:
    from config import FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, FACEBOOK_ACCESS_TOKEN, FACEBOOK_AD_ACCOUNT_ID, FACEBOOK_PAGE_ID
except Exception:
    import os
    FACEBOOK_APP_ID = os.environ.get("FACEBOOK_APP_ID")
    FACEBOOK_APP_SECRET = os.environ.get("FACEBOOK_APP_SECRET")
    FACEBOOK_ACCESS_TOKEN = os.environ.get("FACEBOOK_ACCESS_TOKEN")
    FACEBOOK_AD_ACCOUNT_ID = os.environ.get("FACEBOOK_AD_ACCOUNT_ID")
    FACEBOOK_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID")

# Optional Facebook SDK imports
try:
    from facebook_business.api import FacebookAdsApi  # type: ignore
    from facebook_business.adobjects.adaccount import AdAccount  # type: ignore
    from facebook_business.adobjects.adimage import AdImage  # type: ignore
    from facebook_business.adobjects.advideo import AdVideo  # type: ignore
    _FB_SDK_AVAILABLE = True
except Exception:
    _FB_SDK_AVAILABLE = False

import base64
from typing import Dict, Any


def _can_use_real_facebook():
    return (
        _FB_SDK_AVAILABLE
        and bool(FACEBOOK_APP_ID)
        and bool(FACEBOOK_APP_SECRET)
        and bool(FACEBOOK_ACCESS_TOKEN)
        and bool(FACEBOOK_AD_ACCOUNT_ID)
    )


def initialize_facebook_api():
    """
    Initializes the Facebook Ads API with credentials from config or env.
    In a real app, this would be called once when the app starts.
    """
    if not _can_use_real_facebook():
        print("Facebook API initialized (mock).")
        return
    FacebookAdsApi.init(app_id=FACEBOOK_APP_ID, app_secret=FACEBOOK_APP_SECRET, access_token=FACEBOOK_ACCESS_TOKEN)


def _parse_budget_to_cents(budget_str):
    """Very simple parser that extracts the first integer and converts to cents (USD)."""
    if not budget_str:
        return 1000  # default $10/day
    import re
    match = re.search(r"(\d+)", str(budget_str))
    if match:
        try:
            dollars = int(match.group(1))
            return max(100, dollars * 100)  # minimum $1
        except Exception:
            pass
    return 1000


def _merge_params(base, override):
    """Shallow merge dictionaries, return new dict."""
    combined = dict(base or {})
    for k, v in (override or {}).items():
        combined[k] = v
    return combined


def _build_campaign_params(ad_params):
    # Defaults
    campaign_params = {
        'name': f"AI Campaign: {ad_params.get('ad_copy', 'Untitled')[:50]}",
        'objective': ad_params.get('objective') or 'LINK_CLICKS',
        'status': ad_params.get('campaign_status') or 'PAUSED',
        'special_ad_categories': ad_params.get('special_ad_categories') or [],
    }
    # Allow full override via nested dict
    campaign_params = _merge_params(campaign_params, ad_params.get('campaign'))
    # Buying type and bid strategy (if provided)
    if 'buying_type' in ad_params:
        campaign_params['buying_type'] = ad_params['buying_type']
    if 'bid_strategy' in ad_params:
        campaign_params['bid_strategy'] = ad_params['bid_strategy']
    if 'special_ad_category_country' in ad_params:
        campaign_params['special_ad_category_country'] = ad_params['special_ad_category_country']
    return campaign_params


def _build_adset_params(ad_params, campaign_id):
    # Budget
    daily_budget = ad_params.get('daily_budget')
    lifetime_budget = ad_params.get('lifetime_budget')
    if daily_budget is None and lifetime_budget is None:
        daily_budget = _parse_budget_to_cents(ad_params.get('budget'))

    ad_set_defaults = {
        'name': f"AI Ad Set for {ad_params.get('target_audience', 'default audience')}",
        'campaign_id': campaign_id,
        'billing_event': ad_params.get('billing_event') or 'IMPRESSIONS',
        'status': ad_params.get('adset_status') or 'PAUSED',
        'optimization_goal': ad_params.get('optimization_goal') or 'REACH',
        'pacing_type': ad_params.get('pacing_type') or ['standard'],
    }
    if daily_budget is not None:
        ad_set_defaults['daily_budget'] = int(daily_budget)
    if lifetime_budget is not None:
        ad_set_defaults['lifetime_budget'] = int(lifetime_budget)

    # Targeting
    targeting = ad_params.get('targeting') or {
        'geo_locations': ad_params.get('geo_locations') or {'countries': ['US']},
    }
    # Placement helpers
    if 'publisher_platforms' in ad_params or 'facebook_positions' in ad_params or 'instagram_positions' in ad_params:
        targeting = dict(targeting)
        if 'publisher_platforms' in ad_params:
            targeting['publisher_platforms'] = ad_params['publisher_platforms']
        if 'facebook_positions' in ad_params:
            targeting['facebook_positions'] = ad_params['facebook_positions']
        if 'instagram_positions' in ad_params:
            targeting['instagram_positions'] = ad_params['instagram_positions']
    if targeting:
        ad_set_defaults['targeting'] = targeting

    # Time and scheduling
    for time_field in ('start_time', 'end_time'):  # Expect ISO8601 strings
        if time_field in ad_params:
            ad_set_defaults[time_field] = ad_params[time_field]

    # Bidding
    if 'bid_amount' in ad_params:
        ad_set_defaults['bid_amount'] = ad_params['bid_amount']

    # Promoted object (for conversion goals)
    if 'promoted_object' in ad_params:
        ad_set_defaults['promoted_object'] = ad_params['promoted_object']

    # Frequency control, attribution, etc. (pass-through if present)
    passthrough_keys = [
        'is_autobid', 'attribution_spec', 'destination_type', 'daily_imps',
        'targeting_optimization_types', 'rf_prediction_id', 'contextual_bundling_spec',
        'adset_schedule', 'time_series', 'line_number', 'budget_remaining'
    ]
    for k in passthrough_keys:
        if k in ad_params:
            ad_set_defaults[k] = ad_params[k]

    # Allow advanced override via nested dict
    ad_set_params = _merge_params(ad_set_defaults, ad_params.get('ad_set'))
    return ad_set_params


def _maybe_upload_image_and_apply(account: Any, creative_params: Dict[str, Any], ad_params: Dict[str, Any]):
    """If image parameters are provided and no image_hash exists, upload and apply to creative."""
    if not _can_use_real_facebook():
        return creative_params

    # Resolve target for placing image_hash
    def _ensure_link_data(cp):
        if 'object_story_spec' not in cp:
            cp['object_story_spec'] = {}
        if 'link_data' not in cp['object_story_spec']:
            cp['object_story_spec']['link_data'] = {}
        return cp['object_story_spec']['link_data']

    # Skip if user already provides
    link_data = None
    if 'object_story_spec' in creative_params and 'link_data' in creative_params['object_story_spec']:
        link_data = creative_params['object_story_spec']['link_data']
        if link_data.get('image_hash'):
            return creative_params

    image_hash = None
    # Direct hash provided at top-level
    if creative_params.get('image_hash'):
        image_hash = creative_params['image_hash']
    elif ad_params.get('image_hash'):
        image_hash = ad_params['image_hash']
    else:
        # Try upload from path/url/base64
        try:
            if ad_params.get('image_path'):
                created = account.create_ad_image(params={'filename': ad_params['image_path']})
                image_hash = created['images'][0]['hash'] if 'images' in created else created.get('hash')
            elif ad_params.get('image_base64'):
                raw = base64.b64decode(ad_params['image_base64'])
                created = account.create_ad_image(params={'bytes': raw})
                image_hash = created.get('hash')
            elif ad_params.get('image_url'):
                import requests
                resp = requests.get(ad_params['image_url'], timeout=20)
                resp.raise_for_status()
                created = account.create_ad_image(params={'bytes': resp.content})
                image_hash = created.get('hash')
        except Exception:
            # Silent fallback; user may not want image
            image_hash = None

    if image_hash:
        link_data = link_data or _ensure_link_data(creative_params)
        link_data['image_hash'] = image_hash
    return creative_params


def _maybe_upload_video_and_apply(account: Any, creative_params: Dict[str, Any], ad_params: Dict[str, Any]):
    """If video parameters are provided and no video_id exists, upload and switch to video_data."""
    if not _can_use_real_facebook():
        return creative_params

    # If user already supplied video_id in the creative, keep it
    if creative_params.get('object_story_spec', {}).get('video_data', {}).get('video_id'):
        return creative_params

    video_id = ad_params.get('video_id') or creative_params.get('video_id')
    try:
        if not video_id and (ad_params.get('video_path') or ad_params.get('video_url')):
            if ad_params.get('video_path'):
                created = account.create_ad_video(params={'filename': ad_params['video_path']})
            else:
                # Attempt remote URL upload; may not be supported depending on SDK version
                created = account.create_ad_video(params={'file_url': ad_params['video_url']})
            video_id = created.get('id') or created.get('video_id')
    except Exception:
        video_id = None

    if video_id:
        if 'object_story_spec' not in creative_params:
            creative_params['object_story_spec'] = {}
        message = ad_params.get('ad_copy') or ''
        title = ad_params.get('headline') or 'Watch now'
        creative_params['object_story_spec']['video_data'] = {
            'video_id': video_id,
            'message': message,
            'title': title,
        }
        # If link_data exists and no explicit request for mixed type, remove link_data to avoid conflicts
        if 'link_data' in creative_params['object_story_spec']:
            creative_params['object_story_spec'].pop('link_data', None)
    return creative_params


def _build_creative_params(ad_params):
    # Provide a simple default object_story_spec if not provided
    object_story_spec = ad_params.get('object_story_spec') or ad_params.get('creative_object_story_spec')
    if not object_story_spec:
        # Basic link ad defaults (requires a page_id for real creation)
        page_id = (ad_params.get('page_id') or FACEBOOK_PAGE_ID)
        link_url = ad_params.get('link_url') or ad_params.get('website_url')
        ad_copy = ad_params.get('ad_copy', '')
        headline = ad_params.get('headline') or 'Learn more'
        description = ad_params.get('description') or ''
        if page_id and link_url:
            object_story_spec = {
                'page_id': page_id,
                'link_data': {
                    'message': ad_copy,
                    'link': link_url,
                    'name': headline,
                    'description': description,
                    # Optional call to action
                    **({'call_to_action': {'type': ad_params.get('call_to_action_type', 'LEARN_MORE'), 'value': {'link': link_url}}} if ad_params.get('call_to_action_type') else {})
                }
            }

    creative_defaults = {
        'name': ad_params.get('creative_name') or 'AI Creative',
    }
    if object_story_spec:
        creative_defaults['object_story_spec'] = object_story_spec

    # Allow override via nested dict
    creative_params = _merge_params(creative_defaults, ad_params.get('creative'))

    # Additional passthrough fields commonly used
    for key in (
        'title', 'body', 'image_hash', 'link_url', 'video_id', 'product_set_id',
        'degrees_of_freedom_spec', 'template_data', 'instagram_actor_id',
        'branded_content_sponsor_page_id', 'call_to_action_type', 'object_type',
        'asset_feed_spec'
    ):
        if key in ad_params and key not in creative_params:
            creative_params[key] = ad_params[key]

    return creative_params


def _build_ad_params(ad_params, ad_set_id, creative_id):
    ad_defaults = {
        'name': ad_params.get('ad_name') or 'AI Ad',
        'adset_id': ad_set_id,
        'creative': {'creative_id': creative_id} if creative_id else ad_params.get('ad', {}).get('creative', {}),
        'status': ad_params.get('ad_status') or 'PAUSED',
    }

    # Allow override via nested dict
    ad_params_final = _merge_params(ad_defaults, ad_params.get('ad'))

    # Common passthrough fields
    for key in ('tracking_specs', 'bid_amount', 'redownload', 'execution_options', 'adlabels'):
        if key in ad_params and key not in ad_params_final:
            ad_params_final[key] = ad_params[key]

    return ad_params_final


def create_facebook_ad(ad_params):
    """
    Takes ad parameters and creates a Facebook ad if credentials/SDK are configured.
    Otherwise, simulates the process and returns mock IDs.

    Accepts both simple AI-extracted fields and advanced nested dicts with keys:
    - campaign: dict of Campaign fields
    - ad_set: dict of Ad Set fields
    - creative: dict of AdCreative fields
    - ad: dict of Ad fields

    Returns a dict: success, message, campaign_id, ad_set_id, creative_id, ad_id
    """
    print(f"--- Starting Facebook Ad Creation ({'Real' if _can_use_real_facebook() else 'Mock'}) ---")
    print(f"Received ad parameters: {ad_params}")

    try:
        initialize_facebook_api()

        campaign_id = None
        ad_set_id = None
        creative_id = None
        ad_id = None

        # Build params
        campaign_params = _build_campaign_params(ad_params)

        if _can_use_real_facebook():
            account = AdAccount(FACEBOOK_AD_ACCOUNT_ID)
            # Campaign
            campaign = account.create_campaign(params=campaign_params)
            campaign_id = campaign.get('id') or campaign.get('campaign_id')

            # Ad Set
            ad_set_params = _build_adset_params(ad_params, campaign_id)
            ad_set = account.create_ad_set(params=ad_set_params)
            ad_set_id = ad_set.get('id') or ad_set.get('adset_id')

            # Determine if we can reuse an existing creative
            existing_creative_id = None
            # Top-level creative_id hint
            if 'creative_id' in ad_params:
                existing_creative_id = ad_params['creative_id']
            # Or inside ad.creative
            ad_obj_in = ad_params.get('ad') or {}
            if isinstance(ad_obj_in, dict):
                ad_creative_in = ad_obj_in.get('creative') or {}
                if isinstance(ad_creative_in, dict):
                    existing_creative_id = existing_creative_id or ad_creative_in.get('creative_id') or ad_creative_in.get('id')
            # Or inside creative dict
            creative_in = ad_params.get('creative') or {}
            if isinstance(creative_in, dict):
                existing_creative_id = existing_creative_id or creative_in.get('creative_id') or creative_in.get('id')

            # If using source_ad_id on the Ad, we can skip creating a creative
            source_ad_id = None
            if isinstance(ad_obj_in, dict):
                source_ad_id = ad_obj_in.get('source_ad_id')

            if source_ad_id:
                creative_id = None  # Will be ignored by create_ad when source_ad_id is provided
            elif existing_creative_id:
                creative_id = existing_creative_id
            else:
                # Creative
                creative_params = _build_creative_params(ad_params)
                creative_params = _maybe_upload_image_and_apply(account, creative_params, ad_params)
                creative_params = _maybe_upload_video_and_apply(account, creative_params, ad_params)
                creative = account.create_ad_creative(params=creative_params)
                creative_id = creative.get('id') or creative.get('creative_id')

            # Ad
            ad_params_final = _build_ad_params(ad_params, ad_set_id, creative_id)
            ad_obj = account.create_ad(params=ad_params_final)
            ad_id = ad_obj.get('id') or ad_obj.get('ad_id')

            print(f"Created Campaign ID: {campaign_id}")
            print(f"Created Ad Set ID: {ad_set_id}")
            if creative_id:
                print(f"Created/Reused Creative ID: {creative_id}")
            if source_ad_id:
                print(f"Used Source Ad ID: {source_ad_id}")
            print(f"Created Ad ID: {ad_id}")
        else:
            # Mock behavior with IDs
            campaign_id = "campaign_12345_mock"
            ad_set_id = "ad_set_67890_mock"
            creative_id = "creative_24680_mock"
            ad_id = "ad_13579_mock"
            print(f"Mock Campaign created with ID: {campaign_id}")
            print(f"Mock Ad Set created with ID: {ad_set_id}")
            print(f"Mock Creative created with ID: {creative_id}")
            print(f"Mock Ad created with ID: {ad_id}")

        print(f"--- Facebook Ad Creation Finished ---")

        return {
            "success": True,
            "message": (
                "Created Facebook campaign, ad set, creative, and ad." if _can_use_real_facebook() else "Successfully simulated creating a Facebook ad."
            ),
            "campaign_id": campaign_id,
            "ad_set_id": ad_set_id,
            "creative_id": creative_id,
            "ad_id": ad_id,
        }

    except Exception as e:
        print(f"An error occurred during Facebook ad creation: {e}")
        return {"success": False, "message": str(e), "campaign_id": None, "ad_set_id": None, "creative_id": None, "ad_id": None}
