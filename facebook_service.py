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
    from facebook_business.adobjects.page import Page  # type: ignore
    from facebook_business.adobjects.targetingsearch import TargetingSearch  # type: ignore
    _FB_SDK_AVAILABLE = True
except Exception:
    _FB_SDK_AVAILABLE = False

import base64
from typing import Dict, Any, List, Optional


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


def _resolve_interests_from_terms(terms: List[str]) -> List[Dict[str, Any]]:
    if not terms or not _can_use_real_facebook():
        return []
    out: List[Dict[str, Any]] = []
    try:
        for t in terms:
            res = TargetingSearch.search(params={'q': t, 'type': 'adinterest'})
            if isinstance(res, list):
                for item in res[:10]:
                    if item.get('id'):
                        out.append({'id': item['id'], 'name': item.get('name', t)})
    except Exception:
        return []
    return out


def _build_targeting(ad_params: Dict[str, Any]) -> Dict[str, Any]:
    targeting: Dict[str, Any] = dict(ad_params.get('targeting') or {})

    # Basic demographics
    for key in ('age_min', 'age_max', 'genders', 'locales', 'user_os', 'user_device', 'wireless_carrier'):
        if key in ad_params and key not in targeting:
            targeting[key] = ad_params[key]

    # Device/platform placements
    for key in (
        'device_platforms', 'publisher_platforms', 'facebook_positions', 'instagram_positions',
        'messenger_positions', 'audience_network_positions'
    ):
        if key in ad_params:
            targeting[key] = ad_params[key]

    # Languages helper (aliases locales) if provided as strings; expect numeric codes otherwise
    if 'languages' in ad_params and 'locales' not in targeting:
        targeting['locales'] = ad_params['languages']

    # Geo locations
    geo = ad_params.get('geo_locations') or {}
    if not geo:
        # Build from helpers
        helper_geo: Dict[str, Any] = {}
        if 'countries' in ad_params:
            helper_geo['countries'] = ad_params['countries']
        if 'regions' in ad_params:
            helper_geo['regions'] = ad_params['regions']
        if 'cities' in ad_params:
            helper_geo['cities'] = ad_params['cities']
        if 'zips' in ad_params:
            helper_geo['zips'] = ad_params['zips']
        if 'custom_locations' in ad_params:
            helper_geo['custom_locations'] = ad_params['custom_locations']
        if 'location_types' in ad_params:
            helper_geo['location_types'] = ad_params['location_types']
        geo = helper_geo
    if geo:
        targeting['geo_locations'] = geo
    # Exclusions for geo
    if 'excluded_geo_locations' in ad_params and 'excluded_geo_locations' not in targeting:
        targeting['excluded_geo_locations'] = ad_params['excluded_geo_locations']

    # Custom audiences include/exclude
    def _ensure_list_of_id_dicts(ids):
        if not ids:
            return []
        arr = []
        for i in ids:
            arr.append({'id': i} if isinstance(i, (str, int)) else i)
        return arr

    if 'custom_audience_ids' in ad_params or 'custom_audiences' in ad_params:
        targeting['custom_audiences'] = _ensure_list_of_id_dicts(ad_params.get('custom_audience_ids') or ad_params.get('custom_audiences'))
    if 'excluded_custom_audience_ids' in ad_params or 'excluded_custom_audiences' in ad_params:
        targeting['excluded_custom_audiences'] = _ensure_list_of_id_dicts(ad_params.get('excluded_custom_audience_ids') or ad_params.get('excluded_custom_audiences'))

    # Connections
    for key in ('connections', 'excluded_connections', 'friends_of_connections'):
        if key in ad_params and key not in targeting:
            targeting[key] = ad_params[key]

    # Lookalike spec builder
    if 'lookalike' in ad_params and 'lookalike_spec' not in targeting:
        ll = ad_params['lookalike'] or {}
        origin_id = ll.get('origin_audience_id') or ll.get('origin_id')
        if origin_id:
            targeting['lookalike_spec'] = {
                'type': ll.get('type', 'similarity'),
                'ratio': ll.get('ratio', 0.01),
                'country': ll.get('country') or (ad_params.get('countries')[0] if ad_params.get('countries') else None),
                'origin': [{'id': origin_id}],
            }

    # Interests/behaviors demography: support direct lists and flexible_spec
    flexible_spec: List[Dict[str, Any]] = list(targeting.get('flexible_spec') or [])

    # Direct IDs provided
    direct_interests = ad_params.get('interests') or []
    interest_ids = ad_params.get('interest_ids') or []
    if interest_ids and not direct_interests:
        direct_interests = [{'id': iid} for iid in interest_ids]

    if direct_interests:
        flexible_spec.append({'interests': direct_interests})

    # Resolve interest terms if requested
    if ad_params.get('interest_terms'):
        resolved = _resolve_interests_from_terms(ad_params['interest_terms'])
        if resolved:
            flexible_spec.append({'interests': resolved})

    # Behaviors, life events, industries etc.
    for key in ('behaviors', 'life_events', 'industries', 'politics', 'family_statuses', 'income', 'home_ownership', 'ethnic_affinity'):
        if key in ad_params:
            flexible_spec.append({key: ad_params[key]})

    # Education and work
    for key in ('education_statuses', 'college_years', 'education_majors', 'education_schools', 'work_employers', 'work_positions'):
        if key in ad_params:
            flexible_spec.append({key: ad_params[key]})

    # Exclusions helper
    exclusions = targeting.get('exclusions') or {}
    for key in ('exclude_interests', 'exclude_behaviors'):
        if key in ad_params:
            field = key.replace('exclude_', '')
            existing = exclusions.get(field) or []
            exclusions[field] = existing + ad_params[key]
    if exclusions:
        targeting['exclusions'] = exclusions

    if flexible_spec:
        targeting['flexible_spec'] = flexible_spec

    # Detailed targeting expansion flag passthroughs
    for key in ('targeting_expansion', 'targeting_optimization'):  # legacy and new-style
        if key in ad_params and key not in targeting:
            targeting[key] = ad_params[key]

    return targeting


def _is_lead_gen_flow(ad_params: Dict[str, Any]) -> bool:
    objective = (ad_params.get('objective') or '').upper()
    return objective == 'LEAD_GENERATION' or 'lead_form_id' in ad_params or 'lead_form' in ad_params


def _ensure_lead_form_id(ad_params: Dict[str, Any]) -> str:
    """
    Returns an existing lead_form_id or creates one if params provided and SDK/creds are available.
    """
    if ad_params.get('lead_form_id'):
        return ad_params['lead_form_id']
    lead_form_spec = ad_params.get('lead_form')
    if not lead_form_spec:
        return ''
    if not _can_use_real_facebook():
        # Cannot create in mock mode
        return ''
    page_id = ad_params.get('page_id') or FACEBOOK_PAGE_ID
    if not page_id:
        raise Exception('page_id is required to create a lead form')
    # Create the form on the Page
    created = Page(page_id).create_leadgen_form(params=lead_form_spec)
    return created.get('id') or created.get('leadgen_form_id') or ''


def _build_campaign_params(ad_params):
    # Defaults
    campaign_params = {
        'name': f"AI Campaign: {ad_params.get('ad_copy', 'Untitled')[:50]}",
        'objective': ad_params.get('objective') or ('LEAD_GENERATION' if _is_lead_gen_flow(ad_params) else 'LINK_CLICKS'),
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

    # Default optimization
    default_optimization = 'LEAD_GENERATION' if _is_lead_gen_flow(ad_params) else 'REACH'

    ad_set_defaults = {
        'name': f"AI Ad Set for {ad_params.get('target_audience', 'default audience')}",
        'campaign_id': campaign_id,
        'billing_event': ad_params.get('billing_event') or 'IMPRESSIONS',
        'status': ad_params.get('adset_status') or 'PAUSED',
        'optimization_goal': ad_params.get('optimization_goal') or default_optimization,
        'pacing_type': ad_params.get('pacing_type') or ['standard'],
    }
    if daily_budget is not None:
        ad_set_defaults['daily_budget'] = int(daily_budget)
    if lifetime_budget is not None:
        ad_set_defaults['lifetime_budget'] = int(lifetime_budget)

    # Build targeting from helpers + passthrough
    targeting = _build_targeting(ad_params)
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

    # Regulatory/compliance and advanced toggles
    passthrough_keys = [
        'is_autobid', 'attribution_spec', 'destination_type', 'daily_imps',
        'targeting_optimization_types', 'rf_prediction_id', 'contextual_bundling_spec',
        'adset_schedule', 'time_series', 'line_number', 'budget_remaining',
        'is_dynamic_creative', 'dsa_beneficiary', 'dsa_payor', 'multi_advertiser_ads_opt_in'
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


def _apply_leadgen_cta(creative_params: Dict[str, Any], ad_params: Dict[str, Any], lead_form_id: str) -> Dict[str, Any]:
    """Ensure object_story_spec.link_data.call_to_action is set for lead gen."""
    if not lead_form_id:
        return creative_params

    if 'object_story_spec' not in creative_params:
        creative_params['object_story_spec'] = {}
    oss = creative_params['object_story_spec']

    # Determine page_id fallback
    page_id = ad_params.get('page_id') or FACEBOOK_PAGE_ID
    if page_id and 'page_id' not in oss:
        oss['page_id'] = page_id

    link_data = oss.get('link_data') or {}
    link_data.setdefault('message', ad_params.get('ad_copy') or '')
    link_data.setdefault('link', ad_params.get('link_url') or 'https://www.facebook.com')

    cta_type = ad_params.get('call_to_action_type', 'LEARN_MORE')
    cta_value = ad_params.get('call_to_action_value') or {}
    link_data['call_to_action'] = {
        'type': cta_type,
        'value': {
            **cta_value,
            'lead_gen_form_id': lead_form_id
        }
    }
    oss['link_data'] = link_data
    # Ensure we are not mixing video_data when using link_data lead gen
    if 'video_data' in oss:
        oss.pop('video_data', None)
    return creative_params


def _build_carousel_link_data(account: Optional[Any], ad_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    items: List[Dict[str, Any]] = ad_params.get('carousel_items') or []
    if not items:
        return None

    message = ad_params.get('ad_copy') or ''
    top_link = ad_params.get('link_url') or 'https://www.facebook.com'
    child_attachments: List[Dict[str, Any]] = []

    for item in items:
        att: Dict[str, Any] = {}
        att['link'] = item.get('link') or top_link
        if item.get('name'):
            att['name'] = item['name']
        if item.get('description'):
            att['description'] = item['description']
        # CTA per card
        cta_type = item.get('call_to_action_type')
        cta_value = item.get('call_to_action_value') or ({'link': att['link']} if att.get('link') else {})
        if cta_type:
            att['call_to_action'] = {'type': cta_type, 'value': cta_value}

        # Image handling
        if item.get('image_hash'):
            att['image_hash'] = item['image_hash']
        else:
            # Try to upload if account present and image provided
            if account and (item.get('image_path') or item.get('image_url') or item.get('image_base64')):
                try:
                    if item.get('image_path'):
                        created = account.create_ad_image(params={'filename': item['image_path']})
                        image_hash = created['images'][0]['hash'] if 'images' in created else created.get('hash')
                        if image_hash:
                            att['image_hash'] = image_hash
                    elif item.get('image_base64'):
                        raw = base64.b64decode(item['image_base64'])
                        created = account.create_ad_image(params={'bytes': raw})
                        image_hash = created.get('hash')
                        if image_hash:
                            att['image_hash'] = image_hash
                    elif item.get('image_url'):
                        import requests
                        resp = requests.get(item['image_url'], timeout=20)
                        resp.raise_for_status()
                        created = account.create_ad_image(params={'bytes': resp.content})
                        image_hash = created.get('hash')
                        if image_hash:
                            att['image_hash'] = image_hash
                except Exception:
                    pass
        child_attachments.append(att)

    link_data: Dict[str, Any] = {
        'message': message,
        'link': top_link,
        'child_attachments': child_attachments,
    }
    # Optional carousel flags
    if 'multi_share_optimized' in ad_params:
        link_data['multi_share_optimized'] = ad_params['multi_share_optimized']
    if 'multi_share_end_card' in ad_params:
        link_data['multi_share_end_card'] = ad_params['multi_share_end_card']

    return link_data


def _build_creative_params(ad_params):
    # If using an existing post, honor object_story_id
    object_story_id = ad_params.get('object_story_id') or (ad_params.get('creative') or {}).get('object_story_id')
    if object_story_id:
        creative_params = {
            'name': ad_params.get('creative_name') or 'AI Creative',
            'object_story_id': object_story_id,
        }
        # Allow override via nested dict
        return _merge_params(creative_params, ad_params.get('creative'))

    # Provide a simple default object_story_spec if not provided
    object_story_spec = ad_params.get('object_story_spec') or ad_params.get('creative_object_story_spec')

    # Build carousel if requested
    if not object_story_spec and (ad_params.get('carousel_items')):
        page_id = (ad_params.get('page_id') or FACEBOOK_PAGE_ID)
        if page_id:
            link_data = _build_carousel_link_data(None, ad_params)
            if link_data:
                object_story_spec = {
                    'page_id': page_id,
                    'link_data': link_data
                }

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
                    **({'call_to_action': {'type': ad_params.get('call_to_action_type', 'LEARN_MORE'), 'value': (ad_params.get('call_to_action_value') or {'link': link_url})}} if ad_params.get('call_to_action_type') else {})
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
        'asset_feed_spec', 'object_url', 'applink_treatment', 'template_url_spec'
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
    for key in (
        'tracking_specs', 'bid_amount', 'redownload', 'execution_options', 'adlabels',
        'source_ad_id', 'conversion_domain'
    ):
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
                # Lead form creation if requested
                lead_form_id = ''
                if _is_lead_gen_flow(ad_params):
                    lead_form_id = _ensure_lead_form_id(ad_params)
                    if lead_form_id:
                        ad_params['lead_form_id'] = lead_form_id
                # Creative
                creative_params = _build_creative_params(ad_params)
                # Upload media for link_data and per-card if carousel
                creative_params = _maybe_upload_image_and_apply(account, creative_params, ad_params)
                creative_params = _maybe_upload_video_and_apply(account, creative_params, ad_params)
                # If carousel requested, build child attachments with uploads
                if ad_params.get('carousel_items') and 'object_story_spec' in creative_params:
                    link_data = _build_carousel_link_data(account, ad_params)
                    if link_data:
                        creative_params['object_story_spec']['link_data'] = link_data
                # If lead gen with freshly created lead_form_id, ensure CTA is applied
                if _is_lead_gen_flow(ad_params) and ad_params.get('lead_form_id'):
                    creative_params = _apply_leadgen_cta(creative_params, ad_params, ad_params['lead_form_id'])
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
