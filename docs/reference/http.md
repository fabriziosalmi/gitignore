# HTTP endpoints

See also [Guide → HTTP API](../guide/api).

## `GET /healthz`

Liveness probe. Always returns `200 OK`.

```json
{ "status": "ok" }
```

## `GET /version`

```json
{
  "core_version": "0.0.1",
  "rules_table_version": "sha256:72fd0c323cc1"
}
```

## `POST /generate`

### Request body

```ts
{
  tree?: string[];               // file paths to fingerprint
  features?: string[];           // bypass fingerprinting and supply features directly
  include_comments?: boolean;    // default: true
  include_provenance?: boolean;  // default: false
  extras?: string[];             // user patterns
}
```

Either `tree` or `features` (or both) must be provided.

### Response body

```ts
{
  content: string;
  output_hash: string;            // "sha256:<hex>"
  rules_table_version: string;
  core_version: string;
  rules: Array<{
    pattern: string;
    source: "template" | "mined" | "user_extra";
    feature: string | null;
  }>;
}
```

### Response headers

| Header             | Value                            |
|--------------------|----------------------------------|
| `Content-Type`     | `application/json`               |
| `ETag`             | `"sha256:<hex>"` (= output_hash) |
| `X-Core-Version`   | core version                     |
| `X-Rules-Version`  | rules table version              |

### Caching

`ETag` is content-addressed. A client that sends `If-None-Match` with the
hash will receive `304 Not Modified` when the inputs are unchanged.

## `POST /diff_against`

```ts
// Request
{
  existing: string;          // content of the existing .gitignore
  tree?: string[];
  features?: string[];
  // ... same generation knobs as /generate
}

// Response
{
  added:   string[];   // patterns the generator would add
  removed: string[];   // patterns in existing that the generator would not emit
}
```

## Error model

All errors return a JSON body:

```json
{ "detail": "<human-readable message>" }
```

| Code | Cause                                        |
|------|----------------------------------------------|
| 400  | Missing both `tree` and `features`           |
| 404  | Unknown feature with no template available   |
| 422  | FastAPI validation error                     |
| 500  | Unexpected internal error (always logged)    |
