# Domain, hosting and contact-email setup

## Confirmed choices

- Owner registered `copperascovevotes.org` through Namecheap.
- Owner selected a minimal US-based DigitalOcean Droplet for the public pilot,
  with the option to resize or add capacity only if measurements require it.
  The intended public-hosting window currently runs through November 2026.
- The pilot target is the 1 GiB / 1 shared-vCPU Basic Droplet. This is a selected
  starting point, not a proven capacity requirement or a claim that it has been
  purchased. No server has been provisioned and no web DNS records have changed.
- Owner configured Namecheap Private Email: xavier@copperascovevotes.org, with
  receiving aliases info@copperascovevotes.org and corrections@copperascovevotes.org.
- Owner confirmed email delivery and supplied a Gmail received-message screenshot
  showing SPF, DKIM and DMARC PASS for the mailbox. This verifies that sending
  path, not any future application-generated mail or strict DMARC enforcement.
- Website is explicitly NOT ready to deploy. Local contact/metadata changes are
  preparation only; no server, DNS or public deployment changes are authorized.
- Owner set a USD 50 maximum pilot budget and prefers annual domain/email costs
  to be amortized across their service lives. Static hosting after the dynamic
  pilot is expected to be free. Cash paid and amortized cost must still be shown
  separately because both the domain and mailbox are billed annually.

Website and mail hosting can be separate. The domain can remain registered at
Namecheap while web records point to DigitalOcean and mail records point to a
mail provider. Email can be configured before the website is deployed.

## Budget decision, not a capacity guarantee

Prices checked 2026-09-12, before tax, future renewal changes, extra storage or usage:

| Service | Billing/cash price | Amortized monthly cost |
| --- | ---: | ---: |
| Namecheap domain (owner-reported first-year cost) | USD 9/year | USD 0.75 |
| Namecheap Private Email Launch, one mailbox | USD 14.88/year | USD 1.24 |
| DigitalOcean Basic, 1 GiB / 1 vCPU while running | USD 6/month | USD 6.00 |
| DigitalOcean weekly image backups while running | 20% of Droplet cost | USD 1.20 at the full monthly cap |
| Static hosting after cutover | Target USD 0 | USD 0.00 |

At approximately two months of dynamic runtime, the planned amortized pilot
allocation is about USD 18.38: domain USD 1.50, email USD 2.48, compute USD 12,
and weekly backups USD 2.40. Actual first-year cash outlay is about USD 38.28
because the USD 9 domain and USD 14.88 mailbox are annual purchases. Partial
DigitalOcean calendar months are usage-billed, so exact compute/backup cost
depends on provisioning and destruction times. Reserve the full USD 50 ceiling
until the Droplet is destroyed rather than treating the estimate as a guarantee.

Sources: [Droplet pricing](https://www.digitalocean.com/pricing/droplets),
[backup pricing](https://www.digitalocean.com/pricing/backups),
[mail plan comparison](https://www.namecheap.com/support/knowledgebase/article.aspx/10789/2179/private-email-plans-comparison/).
Email is billed annually, not monthly at the equivalent amount. Do not mistake
a mail trial or introductory discount for the renewal price.

### Mail after the dynamic pilot

Recommended default: keep Private Email through its first paid annual term. The
USD 1.24/month amortized cost preserves project-branded replies and a stable
correction channel while certified-result updates may still occur.

At a future renewal checkpoint, the owner may instead cancel Private Email and,
while the domain remains on Namecheap BasicDNS, configure free forwarding for
`info@copperascovevotes.org` and `corrections@copperascovevotes.org` to an
owner-approved Gmail address. Forwarding preserves the public receiving address
but cannot send as the project domain; replies ordinarily reveal the Gmail
address. Private Email and Namecheap free forwarding cannot operate together,
so this requires a planned MX/SPF transition and delivery testing. Do not publish
the owner's Gmail address unless the owner explicitly selects it as public contact
information. Do not cancel a paid term expecting a prorated refund.

One GiB is the selected pilot starting size, not a validated production size for
Next.js, FastAPI and PostgreSQL/PostGIS together. The expected common workload is
low-volume public ballot lookup, not builds, test suites or source preparation.
Build images, run tests/security scans, and prepare large source/import artifacts
locally or in CI. Production pulls versioned, prebuilt images and performs only
serving, controlled migrations/imports, editorial writes and backups.

Before launch, measure idle memory and representative concurrent ballot lookups;
check response time, disk use and restarts/out-of-memory failures. Do not size for
rare editorial activity without evidence. Swap may provide emergency headroom but
is not a substitute for RAM. If measured behavior is unsafe, resize to the 2 GiB
DigitalOcean plan (USD 12/month before backups/mail) or add capacity. Do not move
the database to a separate managed service or introduce multi-host failover unless
availability evidence justifies the additional cost and state-management work.

Keep the existing modular monolith and Compose deployment. Kubernetes, separate
managed database services and a mail server on the web Droplet are not proposed
for this budget. Database dumps and restoration testing are still needed;
weekly machine images alone are not the complete database backup plan. Storage
and off-server backup destinations must be budgeted separately if not already
available.

Hetzner's low-cost CX23 offers more memory, but the official
[product page](https://www.hetzner.com/cloud/cost-optimized/) currently marks it
unavailable. Do not plan a launch around an unconfirmed stock/region price.

Valkey is currently reserved for a future queue/cache and is not used by the
application request path. The minimal production deployment should omit it until
a real consumer is implemented and tested. This is a deployment optimization;
the local development service may remain available. Do not remove another runtime
component based on assumptions—measure it or establish that nothing uses it.

The dynamic-host exit is predetermined: target a static-archive cutover on
November 16, retain rollback through November 18, and destroy the pilot Droplet
on November 19 only after the static site, final exports and a restoration test
pass. Later certification updates the versioned static artifact without restoring
public address lookup. See [`POST_ELECTION_TRANSITION_2026.md`](POST_ELECTION_TRANSITION_2026.md).
Ending the public server must not delete the only copy of provenance records or
retained source documents.

## Mail setup reference (initial mailbox setup completed by owner)

1. Confirm the domain is active in Namecheap and inspect its current nameservers
   and mail records. An early public DNS check from this workspace returned
   NXDOMAIN; that is not proof of failed registration. Check status and spelling
   in the registrar account before editing DNS.
2. The selected public aliases are `info` and `corrections`, both delivered to
   the `xavier` mailbox. Aliases do not have separate logins.
3. If choosing Namecheap Private Email, activate the selected plan in the owner's
   account and create the mailbox. The owner handles checkout and passwords;
   never put account credentials in chat or the repository.
4. At the authoritative DNS provider, apply the provider's current domain-specific
   MX and authentication records. Use its generated DKIM value; don't invent one.
   Preserve unrelated website records, avoid duplicate SPF records, and review
   existing mail routing before replacing anything. Configure DMARC after the
   authorized senders and authentication are checked.
5. Test incoming mail from an unrelated account, replies from the new domain,
   and SPF/DKIM/DMARC results in the received headers. A correct-looking MX record
   alone does not establish that delivery works.
6. Only after delivery is confirmed, put the chosen public address on `/contribute`
   and update its submission instructions. Describe the email route as email,
   not a functioning file-upload or automatic verification system.

Alternative: [Namecheap free forwarding](https://www.namecheap.com/support/knowledgebase/article.aspx/308/2214/how-to-set-up-free-email-forwarding/)
can receive messages into an existing inbox when using its supported DNS service,
but it does not provide sending from the domain. Do not enable forwarding and
Private Email simultaneously for the same domain.

DigitalOcean [blocks SMTP ports 25, 465 and 587 on Droplets](https://docs.digitalocean.com/support/why-is-smtp-blocked/).
Human replies can use the mail provider's webmail independently of the server.
Future automatic app notifications need a separately reviewed delivery service
and supported transport; buying a human mailbox does not implement notifications.

## Website launch checklist

- Select and validate hosting; keep the existing websites out of scope.
- Run isolated migration/integration tests and provision the private document store.
- Prepare HTTPS routing, production cookie/origin settings, firewall rules and
  private database ports. Existing Compose files are a foundation, not a complete
  internet-facing deployment. Don't expose the raw API/web ports publicly.
- Validate the public API base URL against actual routing; browser code already
  appends `/api/v1`, so a proxy prefix must not duplicate `/api`.
- Back up the database and retained documents, then test restoration.
- Point web DNS to the selected server only when ready; verify HTTPS and the
  chosen apex/www redirect. Add canonical URLs matching the final routing.
- Recheck public states and staff authentication over HTTPS; keep unreviewed
  material private and preserve the incomplete-coverage notices.

No DNS, server provisioning, purchase, mailbox creation or live delivery has
been completed by writing this plan.
