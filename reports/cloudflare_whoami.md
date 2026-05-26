# Cloudflare account whoami — 2026-05-26T18:23Z

## /user (account holder)

```json
{
    "result": {
        "id": "820e4be7bdd8de9c8f048a2de8dc011b",
        "email": "tr6jz6v7wg@privaterelay.appleid.com",
        "username": "f87f8909c51035164074cf9c9db4d173",
        "first_name": null,
        "last_name": null,
        "telephone": null,
        "country": null,
        "zipcode": null,
        "two_factor_authentication_enabled": false,
        "two_factor_authentication_locked": false,
        "created_on": "2026-05-12T23:31:58.499259Z",
        "modified_on": "2026-05-12T23:31:58.520344Z",
        "organizations": [
            {
                "id": "0",
                "name": "Tr6jz6v7wg@privaterelay.appleid.com's Account",
                "status": "member",
                "permissions": [
                    "#access:edit",
                    "#access:read",
                    "#analytics:read",
                    "#api_gateway:edit",
                    "#api_gateway:read",
                    "#app:edit",
                    "#auditlogs:read",
                    "#billing:edit",
                    "#billing:read",
                    "#blocks:edit",
                    "#blocks:read",
                    "#cache_purge:edit",
                    "#casb:edit",
                    "#casb:read",
                    "#cds_compute_account:edit",
                    "#cds_compute_account:read",
                    "#cds:edit",
                    "#cds:read",
                    "#ces_analytics:read",
                    "#ces_integration:edit",
                    "#ces_integration:read",
                    "#ces_phishguard:read",
                    "#ces_policies:edit",
                    "#ces_policies:read",
                    "#ces_pra_report:edit",
                    "#ces_pra_report:read",
                    "#ces_search:action",
                    "#ces_search:preview",
                    "#ces_search:raw",
                    "#ces_search:read",
                    "#ces_search:trace",
                    "#ces_settings:edit",
                    "#ces_settings:read",
                    "#cf1_integration:casb_enroll",
                    "#cf1_integration:ces_enroll",
                    "#cf1_integration:edit",
                    "#cf1_integration:read",
                    "#cfone:edit",
                    "#cfone:read",
                    "#connectivity_edit",
                    "#connectivity_read",
                    "#d1:edit",
                    "#d1:read",
                    "#dash_sso:edit",
                    "#dash_sso:read",
                    "#dex:edit",
                    "#dex:read",
                    "#dns_records:edit",
                    "#dns_records:read",
                    "#fbm_acc:edit",
                    "#fbm:edit",
                    "#fbm:read",
                    "#healthchecks:edit",
                    "#healthchecks:read",
                    "#http_applications:edit",
                    "#http_applications:read",
                    "#image:edit",
                    "#image:read",
                    "#integration:edit",
                    "#integration:install",
                    "#integration:read",
                    "#lb:edit",
                    "#lb:read",
                    "#legal:edit",
                    "#legal:read",
                    "#logs:edit",
                    "#logs:read",
                    "#magic:edit",
                    "#magic:read",
                    "#member:edit",
                    "#member:read",
                    "#organization:edit",
                    "#organization:read",
                    "#page_shield:edit",
                    "#page_shield:read",
                    "#query_cache:edit",
                    "#query_cache:read",
                    "#r2_bucket:edit",
                    "#r2_bucket_item:edit",
                    "#r2_bucket_item:read",
                    "#r2_bucket:read",
                    "#r2_bucket_warehouse:edit",
                    "#r2_bucket_warehouse:read",
                    "#resilience:edit",
                    "#resilience:read",
                    "#ssl:edit",
                    "#ssl:read",
                    "#stream:edit",
                    "#stream:read",
                    "#subscription:edit",
                    "#subscription:read",
                    "#teams_device:read",
                    "#teams:edit",
                    "#teams:pii",
                    "#teams:read",
                    "#teams:report",
                    "#turnstile:edit",
                    "#turnstile:read",
                    "#vectorize:edit",
                    "#vectorize:read",
                    "#waf:edit",
                    "#waf:read",
                    "#waitingroom:edit",
                    "#waitingroom:read",
                    "#webhooks:edit",
                    "#webhooks:read",
                    "#worker:edit",
                    "#worker:read",
                    "#zaraz:edit",
                    "#zaraz:publish",
                    "#zaraz:read",
                    "#zone:edit",
                    "#zone:read",
                    "#zone_settings:edit",
                    "#zone_settings:read",
                    "#zone_versioning:edit",
                    "#zone_versioning:read"
                ],
                "roles": [
                    "Super Administrator - All Privileges"
                ]
            }
        ],
        "has_pro_zones": false,
        "has_business_zones": false,
        "has_enterprise_zones": false,
        "suspended": false,
        "betas": [
            "zone_level_access_beta"
        ]
    },
    "success": true,
    "errors": [],
    "messages": []
}
```

## /accounts (visible accounts)

```json
{
    "result": [
        {
            "id": "76598c8a5c8c7abbaed5c4292c363e09",
            "name": "Tr6jz6v7wg@privaterelay.appleid.com's Account",
            "type": "standard",
            "settings": {
                "enforce_twofactor": false,
                "api_access_enabled": null,
                "access_approval_expiry": null,
                "abuse_contact_email": null,
                "oauth_app_access_enabled": true
            },
            "legacy_flags": {
                "enterprise_zone_quota": {
                    "maximum": 0,
                    "current": 0,
                    "available": 0
                }
            },
            "created_on": "2026-05-12T23:31:58.499259Z"
        }
    ],
    "result_info": {
        "page": 1,
        "per_page": 10,
        "total_pages": 1,
        "count": 1,
        "total_count": 1
    },
    "success": true,
    "errors": [],
    "messages": []
}
```
