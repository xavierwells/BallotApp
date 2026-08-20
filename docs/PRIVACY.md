# Privacy model

The product needs an address to determine a ballot. It does not need to retain that address.

## Address-resolution flow

1. The browser submits an address directly to the resolver over HTTPS.
2. The resolver derives applicable ballot geography.
3. The resolver discards the raw address before persistence, event creation, analytics, and logging.
4. The client receives only an opaque, short-lived result token or the ballot result itself.

Never use a GET query parameter for an address resolver: URLs can be retained in browser history and intermediary logs. The scaffold uses a POST-only preview endpoint to demonstrate the required interface. The future authoritative resolver must preserve that interface and use body-redacting logs.

Address lookup must work without an account. Accounts, if introduced for saved preferences or editorial roles, must be logically separate from ballot-resolution records.
