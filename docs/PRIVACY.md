# Privacy model

The product needs an address to determine a ballot. It does not need to retain that address.

## Address-resolution flow

1. The browser submits an address directly to the resolver over HTTPS.
2. The resolver derives applicable ballot geography.
3. The resolver discards the raw address before persistence, event creation, analytics, and logging.
4. The client receives only an opaque, short-lived result token or the ballot result itself.

Never use a GET query parameter for an address resolver: URLs can be retained in browser history and intermediary logs. The scaffold uses a POST-only preview endpoint to demonstrate the required interface. The future authoritative resolver must preserve that interface and use body-redacting logs.

Address lookup must work without an account. Accounts, if introduced for saved preferences or editorial roles, must be logically separate from ballot-resolution records.

## Voluntary email contributions and corrections

The public contact links open the visitor's email client. Messages, sender email
addresses and attachments sent to info@copperascovevotes.org or
corrections@copperascovevotes.org are retained in the Namecheap project mailbox.
They are not disposable address lookups and are not automatically imported into
the ballot database, verified or published. No automatic deletion schedule is
promised. Request only relevant public evidence; discourage voter addresses,
registration details, signatures, private contact data and identity documents.
Editors must exclude unnecessary personal data before creating source-backed
drafts. Email receipt does not authorize public redistribution of attachments.

## Staff account storage

The private editorial workspace now uses provisioned staff usernames, salted
password hashes, expiring sessions (stored as token hashes), and review audit
identities. No staff email, voter profile, address, or browser coordinate is
required. Review notes must not contain voter data or credentials. Authenticated
private API responses are not cached and private source PDFs are publication-scoped.
