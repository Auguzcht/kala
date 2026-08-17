# Blackboard / Anthology environment for LTI and REST

You need a Learn environment to register Kala as an LTI 1.3 tool and to read course data over REST. There are two paths. Prefer the first.

## Preferred: the school's existing test environment

Ask Sir Josh for access to the school's current Learn test or staging instance. What you need from the school side:

1. You register Kala once at the Anthology Developer Portal (`https://developer.anthology.com`) to get an Application (Client) ID. For an LTI 1.3 tool you provide your redirect URL (`<api_base_url>/lti/launch`), your OIDC login URL (`<api_base_url>/lti/login`), and your tool JWKS URL (`<api_base_url>/lti/jwks`). LTI 1.3 tools generate their own keys and JWKS.
2. The Learn administrator (Sir Josh) registers your tool on their instance under Admin, LTI Tool Providers, using your Client ID, and gives you back a Deployment ID.
3. You put the Client ID, the Deployment ID, and the instance's endpoints (OIDC auth login URL, OAuth token URL, and JWKS URL) into the backend secrets.

For Blackboard-issued launches the issuer is always `https://blackboard.com`. The platform's JWKS lets you verify launch signatures; the OAuth token endpoint is what you use later for Names and Roles and for Assignment and Grades service calls.

This path is fastest and most realistic, because it matches the version and configuration the school actually runs.

## Fallback: your own Learn developer AMI in AWS

If school access is delayed, Anthology provides a free developer image of Learn (Ultra) that you run in your own AWS account. It is now distributed as a downloadable VMDK that you convert to an AMI (the old AWS Marketplace listing is retired). High level:

1. Sign up at the Anthology Developer Portal and go to the Learn server download page. Accept the license and download the VMDK (it is large, several GB, and the image carries an expiration date; there is no in-place upgrade, so plan to move data before it expires).
2. In your AWS account, create an S3 bucket and upload the VMDK. Use the AWS CLI `import-snapshot` to import it, then register an AMI from the resulting snapshot.
3. Launch an EC2 instance from that AMI (t2.large or larger). The default login is user `administrator` with the password equal to the instance id; the startup log also prints it.
4. Register your tool at the Developer Portal as above, then, as the admin of your own Learn instance, register the tool and note the Deployment ID.

The developer AMI supports REST and LTI development against the Ultra experience. It does not support custom Building Blocks, which Kala does not need.

## Which endpoints go where

- `LTI_AUTH_LOGIN_URL` — the platform OIDC authorization endpoint (where `/lti/login` redirects the browser).
- `LTI_AUTH_TOKEN_URL` — the OAuth 2 token endpoint (for NRPS and AGS service calls, and for REST).
- `LTI_KEYSET_URL` — the platform JWKS (to verify the launch `id_token`).
- `LTI_CLIENT_ID`, `LTI_DEPLOYMENT_IDS` — from the registration exchange above.

Keep these in AWS Secrets Manager (see `infra/terraform/README.md`), not in code.
