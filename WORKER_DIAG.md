# Worker deploy diagnostic — 2026-05-21T18:30:57Z

## 1. Upload response (PUT /content)

\`\`\`json
{
  "result": {
    "created_on": "2026-05-12T23:33:56.055046Z",
    "modified_on": "2026-05-21T18:30:49.933929Z",
    "id": "cool-darkness-dce5",
    "tag": "1ab1a4accdfc4c41b8c45fae56082b5f",
    "entry_point": "worker.js",
    "tags": [],
    "deployment_id": "ed90e3c7923d4d109121b5e14b564bae",
    "tail_consumers": null,
    "logpush": false,
    "observability": {
      "enabled": true,
      "head_sampling_rate": 1,
      "logs": {
        "enabled": true,
        "head_sampling_rate": 1,
        "persist": true,
        "invocation_logs": true
      },
      "traces": {
        "enabled": false,
        "persist": true,
        "head_sampling_rate": 1
      }
    },
    "has_assets": true,
    "has_modules": true,
    "etag": "569dbccf482e92fc54f45602ba66e485ed8b647bfc63552d2f081c08fe520eb7",
    "handlers": [
      "fetch"
    ],
    "last_deployed_from": "api",
    "compatibility_date": "2026-05-12",
    "usage_model": "standard",
    "startup_time_ms": 0
  },
  "success": true,
  "errors": [],
  "messages": []
}

\`\`\`

## 2. New version_id picked from /versions?per_page=1

VERSION_ID=ed90e3c7-923d-4d10-9121-b5e14b564bae

\`\`\`json
{
  "result": {
    "items": [
      {
        "id": "ed90e3c7-923d-4d10-9121-b5e14b564bae",
        "number": 39,
        "metadata": {
          "created_on": "2026-05-21T18:30:49.933929Z",
          "source": "api",
          "author_id": "820e4be7bdd8de9c8f048a2de8dc011b",
          "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
          "has_preview": true
        },
        "annotations": {
          "workers/triggered_by": "upload"
        }
      }
    ]
  },
  "success": true,
  "errors": null,
  "messages": null,
  "result_info": {
    "page": 1,
    "per_page": 1,
    "count": 1,
    "total_count": 39
  }
}

\`\`\`

## 3. All recent versions (last 10)

\`\`\`json
{
  "result": {
    "items": [
      {
        "id": "ed90e3c7-923d-4d10-9121-b5e14b564bae",
        "number": 39,
        "metadata": {
          "created_on": "2026-05-21T18:30:49.933929Z",
          "source": "api",
          "author_id": "820e4be7bdd8de9c8f048a2de8dc011b",
          "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
          "has_preview": true
        },
        "annotations": {
          "workers/triggered_by": "upload"
        }
      },
      {
        "id": "cdddc4f4-374d-415b-86ea-96c3426df387",
        "number": 38,
        "metadata": {
          "created_on": "2026-05-21T18:27:42.668927Z",
          "source": "api",
          "author_id": "820e4be7bdd8de9c8f048a2de8dc011b",
          "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
          "has_preview": true
        },
        "annotations": {
          "workers/triggered_by": "upload"
        }
      },
      {
        "id": "46c3821d-31bb-46ed-86a3-a76869dfa064",
        "number": 37,
        "metadata": {
          "created_on": "2026-05-21T13:32:05.502955Z",
          "source": "api",
          "author_id": "820e4be7bdd8de9c8f048a2de8dc011b",
          "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
          "has_preview": true
        },
        "annotations": {
          "workers/triggered_by": "upload"
        }
      },
      {
        "id": "e63b71df-df02-4104-a9e3-b8267fd2cfa3",
        "number": 36,
        "metadata": {
          "created_on": "2026-05-21T13:05:52.099019Z",
          "source": "api",
          "author_id": "820e4be7bdd8de9c8f048a2de8dc011b",
          "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
          "has_preview": true
        },
        "annotations": {
          "workers/triggered_by": "upload"
        }
      },
      {
        "id": "ee38720b-37da-4259-b435-e1ddb94fc213",
        "number": 35,
        "metadata": {
          "created_on": "2026-05-18T20:08:17.859065Z",
          "source": "api",
          "author_id": "820e4be7bdd8de9c8f048a2de8dc011b",
          "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
          "has_preview": true
        },
        "annotations": {
          "workers/triggered_by": "upload"
        }
      },
      {
        "id": "8ee6bf11-5396-42fa-b925-3593985e2a9a",
        "number": 34,
        "metadata": {
          "created_on": "2026-05-18T19:43:32.254063Z",
          "source": "api",
          "author_id": "820e4be7bdd8de9c8f048a2de8dc011b",
          "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
          "has_preview": true
        },
        "annotations": {
          "workers/triggered_by": "upload"
        }
      },
      {
        "id": "b65899ff-f735-48b6-a310-02dd060f2c12",
        "number": 33,
        "metadata": {
          "created_on": "2026-05-18T13:02:59.339088Z",
          "source": "dash",
          "author_id": "820e4be7bdd8de9c8f048a2de8dc011b",
          "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
          "has_preview": true
        },
        "annotations": {
          "workers/triggered_by": "upload"
        }
      },
      {
        "id": "3f8f6c72-df77-417e-b918-63211b9808e0",
        "number": 32,
        "metadata": {
          "created_on": "2026-05-17T21:45:49.219713Z",
          "source": "dash",
          "author_id": "820e4be7bdd8de9c8f048a2de8dc011b",
          "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
          "has_preview": true
        },
        "annotations": {
          "workers/triggered_by": "upload"
        }
      },
      {
        "id": "c3888114-9f8c-4d5c-8c2c-112a104f55ea",
        "number": 31,
        "metadata": {
          "created_on": "2026-05-17T21:41:27.452087Z",
          "source": "dash",
          "author_id": "820e4be7bdd8de9c8f048a2de8dc011b",
          "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
          "has_preview": true
        },
        "annotations": {
          "workers/triggered_by": "upload"
        }
      },
      {
        "id": "d887c99e-f924-41e6-a239-9486d1524283",
        "number": 30,
        "metadata": {
          "created_on": "2026-05-17T21:34:38.103414Z",
          "source": "dash",
          "author_id": "820e4be7bdd8de9c8f048a2de8dc011b",
          "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
          "has_preview": true
        },
        "annotations": {
          "workers/triggered_by": "upload"
        }
      }
    ]
  },
  "success": true,
  "errors": null,
  "messages": null,
  "result_info": {
    "page": 1,
    "per_page": 10,
    "count": 10,
    "total_count": 39
  }
}

\`\`\`

## 4. Activation response (POST /deployments)

\`\`\`json
{
  "result": {
    "id": "27c1ac9a-808e-4b1d-ab34-318f78852b00"
  },
  "success": true,
  "errors": [],
  "messages": []
}

\`\`\`

## 5. Current deployments after activation

\`\`\`json
{
  "result": {
    "deployments": [
      {
        "id": "27c1ac9a-808e-4b1d-ab34-318f78852b00",
        "source": "api",
        "strategy": "percentage",
        "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
        "annotations": {
          "workers/triggered_by": "deployment"
        },
        "versions": [
          {
            "version_id": "ed90e3c7-923d-4d10-9121-b5e14b564bae",
            "percentage": 100
          }
        ],
        "created_on": "2026-05-21T18:30:51.493091Z"
      },
      {
        "id": "06340927-4647-4ca7-8cba-1c796ba3327e",
        "source": "api",
        "strategy": "percentage",
        "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
        "annotations": {
          "workers/message": "Automatic deployment on upload.",
          "workers/triggered_by": "upload"
        },
        "versions": [
          {
            "version_id": "ed90e3c7-923d-4d10-9121-b5e14b564bae",
            "percentage": 100
          }
        ],
        "created_on": "2026-05-21T18:30:49.933929Z"
      },
      {
        "id": "06520d29-5186-4641-a023-971c0e2e45f6",
        "source": "api",
        "strategy": "percentage",
        "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
        "annotations": {
          "workers/triggered_by": "deployment"
        },
        "versions": [
          {
            "version_id": "cdddc4f4-374d-415b-86ea-96c3426df387",
            "percentage": 100
          }
        ],
        "created_on": "2026-05-21T18:27:45.585224Z"
      },
      {
        "id": "557a7aa1-58cb-4418-957d-25ea765aa8d2",
        "source": "api",
        "strategy": "percentage",
        "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
        "annotations": {
          "workers/message": "Automatic deployment on upload.",
          "workers/triggered_by": "upload"
        },
        "versions": [
          {
            "version_id": "cdddc4f4-374d-415b-86ea-96c3426df387",
            "percentage": 100
          }
        ],
        "created_on": "2026-05-21T18:27:42.668927Z"
      },
      {
        "id": "adcb384f-95c5-4d2a-8543-f4a3e8612649",
        "source": "api",
        "strategy": "percentage",
        "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
        "annotations": {
          "workers/message": "Automatic deployment on upload.",
          "workers/triggered_by": "upload"
        },
        "versions": [
          {
            "version_id": "46c3821d-31bb-46ed-86a3-a76869dfa064",
            "percentage": 100
          }
        ],
        "created_on": "2026-05-21T13:32:05.502955Z"
      },
      {
        "id": "20ecea33-ac96-44a5-a157-b1e7580471d1",
        "source": "api",
        "strategy": "percentage",
        "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
        "annotations": {
          "workers/message": "Automatic deployment on upload.",
          "workers/triggered_by": "upload"
        },
        "versions": [
          {
            "version_id": "e63b71df-df02-4104-a9e3-b8267fd2cfa3",
            "percentage": 100
          }
        ],
        "created_on": "2026-05-21T13:05:52.099019Z"
      },
      {
        "id": "14482502-7d95-499c-9dac-42030c911e4a",
        "source": "api",
        "strategy": "percentage",
        "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
        "annotations": {
          "workers/message": "Automatic deployment on upload.",
          "workers/triggered_by": "upload"
        },
        "versions": [
          {
            "version_id": "ee38720b-37da-4259-b435-e1ddb94fc213",
            "percentage": 100
          }
        ],
        "created_on": "2026-05-18T20:08:17.859065Z"
      },
      {
        "id": "643a4fab-6183-432f-ab3d-9b04cba0968d",
        "source": "api",
        "strategy": "percentage",
        "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
        "annotations": {
          "workers/message": "Automatic deployment on upload.",
          "workers/triggered_by": "upload"
        },
        "versions": [
          {
            "version_id": "8ee6bf11-5396-42fa-b925-3593985e2a9a",
            "percentage": 100
          }
        ],
        "created_on": "2026-05-18T19:43:32.254063Z"
      },
      {
        "id": "d1aaad53-89c4-4295-9fab-556ccc5ea642",
        "source": "dash",
        "strategy": "percentage",
        "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
        "annotations": {
          "workers/message": "Automatic deployment on upload.",
          "workers/triggered_by": "upload"
        },
        "versions": [
          {
            "version_id": "b65899ff-f735-48b6-a310-02dd060f2c12",
            "percentage": 100
          }
        ],
        "created_on": "2026-05-18T13:02:59.339088Z"
      },
      {
        "id": "fe67251c-0b2f-4cb9-bf8d-24373815e697",
        "source": "dash",
        "strategy": "percentage",
        "author_email": "tr6jz6v7wg@privaterelay.appleid.com",
        "annotations": {
          "workers/message": "Automatic deployment on upload.",
          "workers/triggered_by": "upload"
        },
        "versions": [
          {
            "version_id": "3f8f6c72-df77-417e-b918-63211b9808e0",
            "percentage": 100
          }
        ],
        "created_on": "2026-05-17T21:45:49.219713Z"
      }
    ]
  },
  "success": true,
  "errors": [],
  "messages": []
}

\`\`\`

## 6. LIVE worker GET / (first 1000 bytes)

\`\`\`
HTTP/2 200 
date: Thu, 21 May 2026 18:30:57 GMT
content-type: text/html
cf-cache-status: HIT
cache-control: public, max-age=0, must-revalidate
nel: {"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}
report-to: {"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=QplZIG7NqLleEVgZMAkx%2FmCjvBeZ8nDl5PZcGO4EmhcH%2BcmB%2FRmVkCkecxb3kJt6PgkYRna8eehHJroXuSbBXloaAWgvhQgBhtZccjFNYh3q8Nbu1ENoRPGG%2BdOBX2n2qUFHs6P3QEMS5KkvPe9gm3lh5M5wpROsIXG8vQ%3D%3D"}]}
server: cloudflare
cf-ray: 9ff5a7bf4e1ed66b-IAD
alt-svc: h3=":443"; ma=86400

<!doctype html>
<html><head><meta charset="utf-8"><title>HealthTech Jobs — Geetanjali</title>
<style>
  body { font: 14px -apple-system, system-ui, sans-serif; margin: 0; background: #f7f7f8; color: #222; }
  header { background: #1f3a5f; color: white; padding: 18px 28px; }
  header h1 { margin: 0; font-size: 20px; }
  header .sub { opacity: .85; font-size: 13px; margin-top: 4px; }
  .stats { display: 
\`\`\`

## 7. LIVE worker GET /api/auth/me (first 1000 bytes)

\`\`\`
HTTP/2 200 
date: Thu, 21 May 2026 18:30:57 GMT
content-type: application/json; charset=utf-8
content-length: 23
access-control-allow-origin: *
access-control-allow-headers: Content-Type, X-Edit-Key, X-Admin-Key, Authorization
access-control-allow-methods: GET, POST, OPTIONS
report-to: {"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=UhnDPs7ZbntnWRZ3vbbb6ZyQJtoBboRJ1oWLxlOArPpZ0Vb2lSSPjRFiNiH%2F%2BWXvMSxH%2FIWvIkkLp%2FG4MUOnszLcq77MTVQKYbPTdTxsg6CKKgmbhrdZQZ1j%2FHzgqkycD%2F4vpA9QXzSTlCD7mKtTdzN3CEIc6W913g%2BYLg%3D%3D"}]}
nel: {"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}
server: cloudflare
cf-ray: 9ff5a7c00f87d4a8-IAD
alt-svc: h3=":443"; ma=86400

{"authenticated":false}
\`\`\`
