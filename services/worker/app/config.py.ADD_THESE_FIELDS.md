# services/worker/app/config.py — add the LMS REST fields

The worker Lambda **already has** everything it needs at the AWS level: it runs
under the same `kala-lambda-role`, reads the same `kala/app` secrets bundle via
the same `KALA_SECRETS_ARN`, and that bundle already contains the LMS REST
values because the api uses them. The only reason the worker "has no LMS creds"
today is that this slim config never *declared* the fields. Add them.

Paste these four fields into the `Settings` class in
`services/worker/app/config.py`, right after the `openai_*` block, mirroring
`services/api/app/config.py`'s "Blackboard Learn REST API" block **exactly**
(same aliases, same defaults) so the two never drift:

```python
    # Blackboard Learn REST API. DELIBERATE DUPLICATE of the api's config
    # (services/api/app/config.py, "Blackboard Learn REST API" block). The
    # worker now runs the incremental course walk (app/jobs/ingest_walk.py), so
    # it needs the same REST credentials the api connector uses. These come
    # from the SAME kala/app secret the worker already loads — no new secret,
    # no IAM change. If the api's copy changes, change this one too; grep both
    # for the alias before editing either (same contract as openrouter_model_fast).
    lms_rest_base_url: str = Field(default="", alias="LMS_REST_BASE_URL")
    lms_rest_client_id: str = Field(default="", alias="LMS_REST_CLIENT_ID")
    lms_rest_client_secret: str = Field(default="", alias="LMS_REST_CLIENT_SECRET")
    lms_verify_tls: bool = Field(default=True, alias="LMS_VERIFY_TLS")
    lti_auth_token_url: str = Field(default="", alias="LTI_AUTH_TOKEN_URL")
```

Note `lti_auth_token_url` is included because the connector's `_get_token()`
posts to it for the client-credentials grant. That's five fields, all already
present in `kala/app`.

**Why a `.md` and not a finished `config.py`:** the worker's real `config.py`
carries comment blocks and field ordering that matter, and this repo's
convention is that a human applies each change deliberately. Pasting the block
in by hand keeps the surrounding comments intact rather than clobbering them
with a machine-regenerated file. DeepSeek: verify the aliases match the api's
copy character-for-character after pasting.
