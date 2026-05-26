# Digest diagnostic — 2026-05-26T17:47Z

## /users (public)

```json
{"users":[{"slug":"geetu","name":"Geetanjali Arora"},{"slug":"amit-arora","name":"Amit Arora"},{"slug":"ishika-arora","name":"Ishika Arora"},{"slug":"radhika-kalra","name":"Radhika KAlra"},{"slug":"test","name":"test"}]}
```

## /admin/digest-trigger?user=geetu (verbose)

```
HTTP/2 200 
date: Tue, 26 May 2026 17:47:25 GMT
content-type: application/json
content-length: 213
access-control-allow-origin: *
access-control-allow-headers: Content-Type, X-Edit-Key, X-Admin-Key, Authorization
access-control-allow-methods: GET, POST, OPTIONS
report-to: {"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=Lc%2F9jUtWLr3joiqVgRrCyFoPeTpTnxl6zlFhy4jJDJdVY8qL9GSSRo7lJhLnFS4xGBTKV6Y8mT3vbiAgyTxp%2BoMeDZh8THdSHSauOn6LeX38rnr%2F%2FAZmet2qTzbYgu6nBu5E6AprDMzrA6iLq76WgpqO01Na2PJh1UMIng%3D%3D"}]}
nel: {"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}
server: cloudflare
cf-ray: a01e9ad7df06e60d-IAD
alt-svc: h3=":443"; ma=86400

{"ok":false,"status":403,"error":"{\"statusCode\":403,\"message\":\"The officebeatllc.com domain is not verified. Please, add and verify your domain on https://resend.com/domains\",\"name\":\"validation_error\"}"}
```

## /admin/digest-trigger?user=amit-arora (verbose)

```
HTTP/2 200 
date: Tue, 26 May 2026 17:47:25 GMT
content-type: application/json
content-length: 213
access-control-allow-origin: *
access-control-allow-headers: Content-Type, X-Edit-Key, X-Admin-Key, Authorization
access-control-allow-methods: GET, POST, OPTIONS
report-to: {"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=tbaLPLXX%2Fa8sgKXpXgYON9Db2FQ872md3UUAxwEBOOagYBbBobfa0ftY84Jh9DzCGTC7DJUJYRhr18pJw5A1uioxYsWvOVOIX6j0bfqtta0kmbBN5tzaKlygGK4zYR9B367jTwEbvlOcQl%2F%2Fa8AwvGpThiCCcQEn1Nx2YA%3D%3D"}]}
nel: {"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}
server: cloudflare
cf-ray: a01e9adb6923e605-IAD
alt-svc: h3=":443"; ma=86400

{"ok":false,"status":403,"error":"{\"statusCode\":403,\"message\":\"The officebeatllc.com domain is not verified. Please, add and verify your domain on https://resend.com/domains\",\"name\":\"validation_error\"}"}
```
