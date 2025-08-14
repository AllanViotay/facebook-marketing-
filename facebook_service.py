# In a real app, you would install the facebook_business SDK
# pip install facebook-business

try:
    from config import FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, FACEBOOK_ACCESS_TOKEN, FACEBOOK_AD_ACCOUNT_ID
except Exception:
    import os
    FACEBOOK_APP_ID = os.environ.get("FACEBOOK_APP_ID")
    FACEBOOK_APP_SECRET = os.environ.get("FACEBOOK_APP_SECRET")
    FACEBOOK_ACCESS_TOKEN = os.environ.get("FACEBOOK_ACCESS_TOKEN")
    FACEBOOK_AD_ACCOUNT_ID = os.environ.get("FACEBOOK_AD_ACCOUNT_ID")

# Optional Facebook SDK imports
try:
    from facebook_business.api import FacebookAdsApi  # type: ignore
    from facebook_business.adobjects.adaccount import AdAccount  # type: ignore
    _FB_SDK_AVAILABLE = True
except Exception:
    _FB_SDK_AVAILABLE = False


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


def create_facebook_ad(ad_params):
    """
    Takes ad parameters and creates a Facebook ad if credentials/SDK are configured.
    Otherwise, simulates the process and returns mock IDs.

    Returns a dict with keys: success, message, campaign_id, ad_set_id
    """
    print(f"--- Starting Facebook Ad Creation ({'Real' if _can_use_real_facebook() else 'Mock'}) ---")
    print(f"Received ad parameters: {ad_params}")

    try:
        initialize_facebook_api()

        campaign_id = None
        ad_set_id = None

        # Prepare common params
        campaign_params = {
            'name': f"AI Campaign: {ad_params.get('ad_copy', 'Untitled')[:50]}",
            'objective': 'LINK_CLICKS',
            'status': 'PAUSED',
            'special_ad_categories': [],
        }

        daily_budget_cents = _parse_budget_to_cents(ad_params.get('budget'))
        ad_set_params = {
            'name': f"AI Ad Set for {ad_params.get('target_audience', 'default audience')}",
            'billing_event': 'IMPRESSIONS',
            'daily_budget': daily_budget_cents,
            'targeting': {
                'geo_locations': {'countries': ['US']},
                'publisher_platforms': ['facebook', 'instagram'],
                'facebook_positions': ['feed'],
                'instagram_positions': ['stream'],
            },
            'status': 'PAUSED',
        }

        if _can_use_real_facebook():
            # Create campaign
            account = AdAccount(FACEBOOK_AD_ACCOUNT_ID)
            campaign = account.create_campaign(params=campaign_params)
            campaign_id = campaign.get('id') or campaign.get('campaign_id')

            # Create ad set
            # Note: The SDK may require additional fields (start_time, end_time, optimization_goal)
            # For MVP, we set minimal fields and keep status PAUSED
            ad_set_params_with_campaign = dict(ad_set_params)
            ad_set_params_with_campaign['campaign_id'] = campaign_id
            ad_set = account.create_ad_set(params=ad_set_params_with_campaign)
            ad_set_id = ad_set.get('id') or ad_set.get('adset_id')

            print(f"Created Campaign ID: {campaign_id}")
            print(f"Created Ad Set ID: {ad_set_id}")
        else:
            # Mock behavior
            campaign_id = "campaign_12345_mock"
            ad_set_id = "ad_set_67890_mock"
            print(f"Mock Campaign created with ID: {campaign_id}")
            print(f"Mock Ad Set created with ID: {ad_set_id}")

        print(f"--- Facebook Ad Creation Finished ---")

        return {
            "success": True,
            "message": (
                "Created Facebook campaign and ad set." if _can_use_real_facebook() else "Successfully simulated creating a Facebook ad."
            ),
            "campaign_id": campaign_id,
            "ad_set_id": ad_set_id,
        }

    except Exception as e:
        print(f"An error occurred during Facebook ad creation: {e}")
        return {"success": False, "message": str(e), "campaign_id": None, "ad_set_id": None}
