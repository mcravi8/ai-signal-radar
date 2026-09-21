# Public-data boundary

This repository is public. Privacy is therefore an architectural boundary, not a convention.

## Public allowlist

Public records may contain:

- public source title, publisher, publication date, and canonical URL;
- short original summaries and classifications;
- project and theme names;
- score components and methodology;
- sponsorship or commercial-bias labels;
- brief source excerpts only when redistribution is appropriate.

## Blocked data

- raw email bodies or HTML;
- email addresses, mailbox IDs, private message IDs, or account-specific Gmail links;
- OAuth tokens, cookies, authorization headers, API secrets, or `.env` values;
- full paper, newsletter, post, or transcript text;
- private annotations or unrelated mailbox content.

## Controls

1. Raw local data is confined to `data/private/`, which is ignored by Git.
2. `export_public.py` emits only allowlisted fields.
3. `validate-public` scans serialized public data for blocked keys and sensitive patterns.
4. Tests exercise known leakage cases.
5. Deployment stops if validation fails; the last valid Pages deployment remains available.
6. AgentMail processing happens in runner memory. The workflow persists only sanitized source items and a timestamp cursor, and the API key is stored as an encrypted GitHub Actions secret.
