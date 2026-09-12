# Domain, hosting and contact-email setup

## Confirmed choices

- Owner registered `copperascovevotes.org` through Namecheap.
- Affordable paid hosting is acceptable; under USD 10/month is preferred.
- DigitalOcean is familiar to the owner. No new hosting or mail subscription
  has been purchased by the agent, and no DNS records have been changed.
- Owner configured Namecheap Private Email: xavier@copperascovevotes.org, with
  receiving aliases info@copperascovevotes.org and corrections@copperascovevotes.org.
- Owner confirmed email delivery and supplied a Gmail received-message screenshot
  showing SPF, DKIM and DMARC PASS for the mailbox. This verifies that sending
  path, not any future application-generated mail or strict DMARC enforcement.
- Website is explicitly NOT ready to deploy. Local contact/metadata changes are
  preparation only; no server, DNS or public deployment changes are authorized.

Website and mail hosting can be separate. The domain can remain registered at
Namecheap while web records point to DigitalOcean and mail records point to a
mail provider. Email can be configured before the website is deployed.

## Budget proposal, not a capacity guarantee

Prices checked 2026-09-11, before tax, domain renewal, extra storage or usage:

| Service | Regular cost |
| --- | --- |
| DigitalOcean Basic, 1 GiB / 1 vCPU | USD 6/month |
| DigitalOcean weekly image backups | USD 1.20/month (20% of that Droplet) |
| Namecheap Private Email Launch, one mailbox | USD 14.88/year, equivalent to USD 1.24/month |
| Combined monthly equivalent | USD 8.44 |

Sources: [Droplet pricing](https://www.digitalocean.com/pricing/droplets),
[backup pricing](https://www.digitalocean.com/pricing/backups),
[mail plan comparison](https://www.namecheap.com/support/knowledgebase/article.aspx/10789/2179/private-email-plans-comparison/).
Email is billed annually, not monthly at the equivalent amount. Do not mistake
a mail trial or introductory discount for the renewal price.

One GiB is a constrained pilot candidate, not a validated production size for
Next.js, FastAPI and PostgreSQL/PostGIS together. Build images outside the server,
measure memory during representative browsing, concurrent requests and imports,
and check for restarts/out-of-memory failures before launch. Swap is a safety
net, not a substitute for RAM. If testing fails, the 2 GiB DigitalOcean plan is
USD 12/month before backups/mail, or evaluate spare capacity on an existing host
with owner approval. Do not deploy onto the owner's other sites without checking
capacity, backups and isolation first.

Keep the existing modular monolith and Compose deployment. Kubernetes, separate
managed database services and a mail server on the web Droplet are not proposed
for this budget. Database dumps and restoration testing are still needed;
weekly machine images alone are not the complete database backup plan. Storage
and off-server backup destinations must be budgeted separately if not already
available.

Hetzner's low-cost CX23 offers more memory, but the official
[product page](https://www.hetzner.com/cloud/cost-optimized/) currently marks it
unavailable. Do not plan a launch around an unconfirmed stock/region price.

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
