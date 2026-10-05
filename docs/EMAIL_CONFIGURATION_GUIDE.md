# Email Configuration Guide

**Location in app:** Settings → Email tab

---

## Overview

The Email tab has five independent sections. Each section has its own **Save** button — changes in one section do not affect others until you save.

| Section | Purpose |
|---|---|
| Sending Identity | Default From name and address |
| Email Provider | SMTP or API backend for sending |
| Domain Authentication | SPF / DKIM DNS records |
| Compliance | CAN-SPAM physical address, footer, unsubscribe URL |
| Sending Limits & Thresholds | Volume caps and auto-pause rules |

---

## Section 1 — Sending Identity

Defines the default **From** name and address that appears in every email across campaigns, sequences, and workflows.

1. Navigate to **Settings → Email**.
2. Fill in the **Sending Identity** card:
   - **From Name** — display name recipients see, e.g. `Acme Marketing`
   - **From Email** — sender address, e.g. `hello@acme.com`
   - **Reply-To Email** *(optional)* — if replies should go to a different address than the From address; leave blank to default to From Email
3. Click **Save Identity**.

> The From Email should match your authenticated domain (Section 3). Using a Gmail or Yahoo address while sending through custom SMTP will likely trigger spam filters.

---

## Section 2 — Email Provider

Chooses the backend that physically delivers emails. Five options are available.

---

### Option A — Platform Default (shared SMTP)

Best for development or testing. Not recommended for production.

1. Select **Platform Default (shared SMTP)** from the Provider dropdown.
2. Click **Save Provider**.

No credentials are required.

---

### Option B — Custom SMTP

Use any SMTP server (Gmail Workspace, Outlook 365, Mailjet, Postmark, etc.).

1. Select **Custom SMTP** from the Provider dropdown.
2. Fill in the fields:

   | Field | Notes |
   |---|---|
   | SMTP Host | e.g. `smtp.mailjet.com` |
   | Port | `587` for TLS, `465` for SSL, `25` for unencrypted |
   | Username | Usually your email address |
   | Password | SMTP password or app password. If already saved, leave blank to keep existing. |
   | Use TLS | Enable for port 587 (recommended) |
   | Use SSL | Enable for port 465. Mutually exclusive with TLS. |

3. Send a test email (see **Testing** below), then click **Save Provider**.

---

### Option C — SendGrid

1. Select **SendGrid** from the Provider dropdown.
2. Paste your **SendGrid API Key** (SendGrid dashboard → Settings → API Keys).
3. Send a test email, then click **Save Provider**.

> Your From Email domain must also be verified inside your SendGrid account under Sender Authentication.

---

### Option D — Mailgun

1. Select **Mailgun** from the Provider dropdown.
2. Paste your **Mailgun API Key** (Mailgun → Settings → API Keys → Private API key).
3. Enter your **Mailgun Domain** — the sending domain created inside Mailgun, e.g. `mg.acme.com`.
4. Send a test email, then click **Save Provider**.

---

### Option E — Amazon SES

1. Select **Amazon SES** from the Provider dropdown.
2. Enter **SMTP Credentials** in the format `SMTP_USER::SMTP_PASS`:
   - In AWS Console → SES → SMTP Settings → Create SMTP Credentials
   - Download the credentials file and combine as: `AKIAIOSFODNN7EXAMPLE::wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY`
3. Select your **AWS Region** — must match the region where SES is configured (e.g. `us-east-1`).
4. Send a test email, then click **Save Provider**.

> New SES accounts start in sandbox mode and can only send to verified addresses. Request production access in the AWS Console before sending to real contacts.

---

### Testing the Connection

Before saving, verify credentials work:

1. Type any email address into **Send test email to** (e.g. your own address).
2. Click **Test**.
3. A success or error toast appears with the result.
4. Confirm the test email arrived in your inbox before clicking Save Provider.

---

## Section 3 — Domain Authentication

SPF and DKIM records tell receiving mail servers that the platform is authorized to send on behalf of your domain. This is critical for inbox placement.

### Adding a Domain

1. Type your sending domain into the input field (e.g. `mail.acme.com` or `acme.com`).
2. Click **Add Domain**. The domain appears with status **Pending**.

### Configuring DNS Records

3. Click **DNS Records** on the domain row to expand the records panel.
4. Two records are shown:

   **SPF Record (TXT)**
   - Record type: `TXT`
   - Host/Name: the root domain shown (e.g. `acme.com`)
   - Value: the SPF string, e.g. `v=spf1 include:platform.example.com ~all`
   - Use **Copy** to copy the exact value

   **DKIM Record (TXT)**
   - Record type: `TXT`
   - Host/Name: the subdomain shown (e.g. `selector._domainkey.acme.com`)
   - Value: the public key string shown
   - Use **Copy** to copy the exact value

5. Log in to your DNS provider (Cloudflare, GoDaddy, Route 53, etc.) and create both records.
6. Wait for DNS propagation — typically 5–30 minutes, up to 48 hours.

### Verifying

7. Return to **Settings → Email → Domain Authentication**.
8. Click **Verify** on the domain row.
9. The platform performs a live DNS TXT lookup:
   - **Verified** (green) — records found, domain is authenticated
   - **Failed** (red) — records not found; expand DNS Records to see the error

### Common Verification Failures

| Issue | Fix |
|---|---|
| DNS not yet propagated | Wait 30 minutes and retry |
| Extra spaces or quotes around the value | Paste the exact copied value with no surrounding quotes |
| DKIM record added to root domain instead of subdomain | The DKIM host must be the full subdomain (e.g. `selector._domainkey.acme.com`) |
| SPF record conflicts with an existing SPF record | Merge both `include:` clauses into a single TXT record — a domain can only have one SPF record |

To remove a domain, click the red trash icon on its row and confirm the dialog.

---

## Section 4 — Compliance

Required by CAN-SPAM (US), CASL (Canada), and recommended by GDPR (EU).

1. Fill in the **Compliance** card:

   - **Physical Mailing Address** *(required)* — your organization's postal address, appended to the footer of every email:
     ```
     123 Main Street, Suite 100
     San Francisco, CA 94105, USA
     ```
   - **Email Footer Text** *(optional)* — additional footer content such as a copyright line:
     ```
     © 2025 Acme Inc. All rights reserved.
     ```
   - **Custom Unsubscribe Redirect URL** *(optional)* — the page contacts land on after clicking Unsubscribe. Must start with `https://`. Leave blank to use the platform's default unsubscribe confirmation page.

2. Click **Save Compliance**.

> Leaving the physical address blank does not block sending, but violates CAN-SPAM. Always fill this in before sending to real recipients.

---

## Section 5 — Sending Limits & Thresholds

Controls maximum sending volume and automatic safety pausing if deliverability metrics spike.

### Volume Limits

| Field | Description | Example |
|---|---|---|
| Daily Send Limit | Maximum emails sent in a 24-hour period. `0` = unlimited. | `5000` |
| Hourly Send Limit | Maximum emails sent per hour. `0` = unlimited. | `500` |

### Deliverability Thresholds

| Field | Default | Recommendation |
|---|---|---|
| Bounce Rate Threshold (%) | `5.00` | Set to `2.00` or lower |
| Complaint Rate Threshold (%) | `0.10` | Set to `0.08` or lower |

If either threshold is exceeded, **all outgoing email is automatically paused** until manually resumed.

Click **Save Limits** after making changes.

---

## Resuming Paused Sending

When sending is paused due to a threshold breach, a red alert banner appears at the top of the Email tab:

> **Sending paused** — Bounce or complaint rate exceeded the configured threshold. Review your list quality before resuming.

**Steps to resume:**

1. Investigate the root cause — identify the campaign that caused the spike.
2. Clean your contact list: remove invalid addresses, hard bounces, and unengaged contacts.
3. Optionally lower the thresholds to prevent future pauses.
4. Click **Resume Sending** in the red banner.

Sending resumes immediately for all queued campaigns and sequences.

---

## Recommended Setup Order

For a production deployment, complete the sections in this order:

1. **Sending Identity** — set From Name and From Email
2. **Domain Authentication** — add domain, copy DNS records, wait for propagation, verify
3. **Email Provider** — configure SMTP or API provider, run a test send
4. **Compliance** — add physical address and footer text
5. **Sending Limits** — set volume caps appropriate for your plan and provider

---

## Provider Comparison

| Provider | Best For | Requires |
|---|---|---|
| Platform Default | Development / testing | Nothing |
| Custom SMTP | Existing mail infrastructure | SMTP host, port, credentials |
| SendGrid | Transactional + marketing at scale | API key, sender domain verified in SendGrid |
| Mailgun | Developer-focused sending | API key, Mailgun sending domain |
| Amazon SES | High volume, AWS ecosystem | SES SMTP credentials, production access approved |
