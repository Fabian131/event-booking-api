```
To update your API contracts seamlessly using another AI, here is the detailed
summary of the required files, along with the specific modifications, field
merges, and rules needed for each contract.
```

```
This plan ensures you can feed these instructions directly into an AI prompt to
completely refactor your OpenAPI specifications, eliminating the decoupled
schedule files seen in `image_d3a6bf.png`.
```

```
---
```

```
## 1. Authentication Contracts (`auth` namespace)
```

```
### `login-user.yaml`
```

```
* **Purpose:** Handles administrative and customer authentication.
* **What it needs:**
```

```
* **Request Body (`LoginRequest`):** Must require `email` (string, format:
email) and `password` (string).
```

```
* **Success Response (`TokenResponse` - 200 OK):** Returns an `access_token`
(JWT string), `token_type` (bearer), and a `user` object containing `id`,
`email`, and `role` (`ENUM: ['business', 'customer']`) so the app can handle
conditional routing instantly.
```

```
* **Error States:** `401 Unauthorized` for invalid credentials and `422
Unprocessable Entity` for malformed inputs.
```

```
### `register-user.yaml`
```

- `**Purpose:** Handles account creation for standard customers.` 

- `**What it needs:**` 

```
* **Request Body (`RegisterRequest`):** Requires `first_name`, `last_name`,
`email`, `phone` (optional), and `password` (validated against a minimum of 8
characters, requiring numbers and letters).
```

```
* **Success Response (`UserResponse` - 201 Created):** Returns the newly
registered user object with an automatically generated UUID string and timestamp
records (`created_at`).
* **Error States:** `409 Conflict` (if email/phone already exists) and `422
Unprocessable Entity` (accumulating all field-validation errors at once).
```

```
### `get-current-user.yaml`
```

```
* **Purpose:** Validates persistent session lifecycle tokens on application
startup.
```

- `**What it needs:**` 

- `**Headers:** Expects a mandatory `Authorization: Bearer <token>` parameter.` 

```
* **Success Response (200 OK):** Returns the complete profile payload structure
identical to `UserResponse` along with their designated security `role`.
```

```
---
```

## `## 2. Refactored Event Contracts (`events` namespace)` 

`>` ⚠️� `**Global Refactoring Directive for AI:** Completely absorb the structural fields from the old `*-schedule.yaml` files. The entity "Schedule" no longer exists as an independent concept or secondary contract endpoint.` 

```
### `list-events.yaml`
```

```
* **Purpose:** Feeds the Business timeline dashboard and the Customer Infinite
```

```
Scroll feed.
```

```
* **What it needs:**
```

```
* **Query Parameters:**
```

```
* `date` (string, format: YYYY-MM-DD) -> Mandatory for the Business calendar
filter.
```

- ``search` (string) -> Optional text matcher for keywords.` 

```
* `category` (string, Enum) -> Optional category filter.
```

```
* `page` (integer) and `limit` (integer) -> Mandatory for customer paginated
fetching.
```

```
* **Success Response (200 OK):** An array of Event objects, plus pagination
metadata (`currentPage`, `hasNextPage`). Each Event item **must contain
integrated schedule fields**: `id`, `title`, `description`, `image_url`,
`max_capacity`, `remaining_capacity`, `category`, `date`, `start_time`, and
`end_time`.
```

```
### `get-event-by-id.yaml`
```

```
* **Purpose:** Fetches structural profiles to hydrate both administrative and
customer detail views.
```

```
* **What it needs:**
```

```
* **Path Parameters:** Expects an `id` matching a valid event entry token.
```

```
* **Success Response (200 OK):** Returns the absolute Event entity data
contract, explicitly including the live computing field: `remaining_capacity`
(Max Capacity minus total tickets currently booked across active customer
registrations).
```

```
### `create-event.yaml`
```

```
* **Purpose:** Admin-only transactional multi-part creator.
```

```
* **What it needs:**
```

```
* **Request Body:** Content-Type must support multi-part form data uploads to
accommodate image handling (`image` file stream parameter, max 5MB).
```

```
* **Payload Properties:** `title` (max 64 chars), `description` (max 255 chars),
`max_capacity` (integer), `category` (Enum), `date` (format: date), `start_time`
(format: time), and `end_time` (format: time).
```

```
* **Error States:** `409 Conflict` if the supplied `date` +
`start_time`/`end_time` range overlaps with any pre-existing venue block.
```

```
### `update-event.yaml`
```

- `**Purpose:** Admin workspace updates.` 

- `**What it needs:**` 

- `**Request Body:** Identical validation property rules as `create-event.yaml`, but all values become optional patch definitions.` 

- `**Error States:** Must run the exact same `409 Conflict` scheduling intersection evaluation checks during runtime modifications.` 

```
### `delete-event.yaml`
```

- `**Purpose:** Hard-delete trigger action.` 

- `**What it needs:**` 

- `**Path Parameters:** Expects target Event `id`.` 

- `**Behavior Rule:** Enforces a clean `204 No Content` response on success. This operation internally triggers the automatic cancel email dispatch system within` 

```
backend processors.
```

```
---
```

```
## 3. Reservation Contracts (`reservations` namespace)
```

```
### `create-reservation.yaml`
```

- `**Purpose:** Secures and locks down ticket slots for authenticated clients.` 

```
* **What it needs:**
```

- `**Request Body:** Requires an object supplying `event_id` (UUID format) and `ticket_quantity` (integer value).` 

```
* **Error States:** Must return an explicit `409 Conflict` block if
`ticket_quantity` exceeds the event entity's real-time `remaining_capacity`
metrics at transaction runtime.
```

```
### `list-reservations.yaml`
```

- `**Purpose:** Dual-role verification checklist.` 

- `**What it needs:**` 

- `**Query Parameters:**` 

- ``event_id` (optional, used by Business to check customer names, user emails, and ticket footprints for a specific activity).` 

- ``search` (optional text match string for business search optimization).` 

```
* **Behavior Rule:** If no `event_id` query parameter is provided, the backend
must scope results down automatically using the caller's contextual Token ID
(returning "My Reservations" for a customer).
```

```
* **Success Response (200 OK):** Returns a list array showing `reservation_id`,
`event_title`, `date`, `ticket_quantity`, and a user context object block
containing `user_name` and `user_email`.
```

```
### `cancel-reservation.yaml`
```

- `**Purpose:** Irreversible cancellation execution wrapper.` 

- `**What it needs:**` 

- `**Path Parameters:** Expects specific target `id` references.` 

```
* **Success Response:** Emits a `200 OK` or `204 No Content` payload layout,
triggering real-time structural data re-calculations so the capacity slot drops
straight back into the open public pool.
```

```
---
```

```
## 4. Notifications Contracts (`notifications` namespace)
```

```
### `list-notifications.yaml`
```

- `**Purpose:** Standard historical ledger display component.` 

- `**What it needs:**` 

```
* **Success Response (200 OK):** Array schema returning notification definitions
consisting of `id`, `title`, `message`, `is_read` (boolean), and `created_at`
timestamp metrics.
```

```
### `mark-notification-as-read.yaml`
```

- `**Purpose:** UI state manager.` 

- `**What it needs:**` 

- `**Path Parameters:** Targeted Notification ID.` 

- `**HTTP Method:** Use `PATCH` to cleanly flip the internal status tracker database field `is_read` straight to `true`.` 

```
---
```

```
### 🚀 Summary of Files to Delete
```

```
Instruct the refactoring AI to completely **remove and disregard** the following
legacy files from the old design folder shown in `image_d3a6bf.png`:
```

- ``create-event-schedule.yaml`` 

- ``delete-schedule.yaml`` 

- ``get-schedule-by-id.yaml`` 

- ``list-event-schedules.yaml`` 

- ``update-schedule.yaml`` 

- ``check-schedule-availability.yaml` (validation logic is now handled directly inside the event creation/update endpoints).` 

- ``confirm-reservation.yaml` (merged directly into the creation response payload workflow).` 

