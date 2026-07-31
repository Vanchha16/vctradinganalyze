# API Contracts

Version: 1.0

---

# Standard Response

Success

Returned as-is (no envelope wrapper) - the resource itself, e.g.:

{
    ...resource fields
}

Failure

{
    error,
    message
}

Note (as of Phase 2C): this corrects an earlier draft of this document, which described a `{success, data, meta}` / `{success, error, code}` envelope that was never implemented and conflicted with a differently-worded draft in `docs/04`. The shape above matches the exception handler actually built in Phase 1 (`app/exceptions/handlers.py`) and is now the standard for all endpoints, current and future. See docs/37_AUTHENTICATION_FLOW.md and BACKLOG.md for the decision record.

---

# Pagination

page

page_size

total

total_pages

---

# Filtering

sort

filter

search

---

# Error Codes

400

401

403

404

409

422

429

500

503

---

# Versioning

/api/v1/

Future

/api/v2/

---

# WebSocket Events

price.update

signal.created

signal.updated

news.created

economic.updated

notification.created

system.health

---

# API Documentation

OpenAPI

Swagger

Redoc