# Public wording and contribution readiness

The public voice is plain and personal: Xavier's local project, not a claim to
complete election coverage. Metadata, Open Graph and Twitter descriptions must
match the homepage. Do not invent a canonical domain, share image or contact URL.

The owner has now selected `copperascovevotes.org` (Namecheap registration).
The owner confirmed working Namecheap Private Email and supplied a received-message
check showing SPF, DKIM and DMARC PASS. Website hosting and HTTPS remain pending;
the owner explicitly says the website is not ready to deploy. See
[domain and mail setup](DOMAIN_AND_EMAIL_SETUP.md).

Current state: some reviewed area estimates are available; a complete local
ballot is not published. A private staff review workspace is implemented;
operator acceptance remains pending. Public uploads are not available.

`/contribute` explains evidence to include, privacy cautions, corrections, and
submitted → reviewed → published states. Its future-work language is deliberate.
Local pages now link info@copperascovevotes.org for contributions/questions and
corrections@copperascovevotes.org for mistakes. These are email links, not an
upload form or automatic intake. Messages and sender addresses remain in the
mailbox, unlike disposable ballot lookups. Do not turn emails or in-person reports into verified facts
without source comparison. Basic official facts need one human reviewer;
interviews, candidate statements and interpretation need two.

When capabilities launch, update `app/page.tsx`, `app/contribute/page.tsx`, page
metadata and this checkpoint together. Staff authentication is not public intake;
reviewed certification records are not an assembled or published ballot.

Site identity includes a code-native ballot favicon and generated social preview
images, with https://copperascovevotes.org as the metadata base. This does not
configure DNS, publish the site or establish canonical redirects. No deployment
is authorized. A live HTTPS/mobile/keyboard/contact/results check remains a
pre-launch task after the owner explicitly approves deployment.

Public API `status`, reason codes, source URLs, dates, IDs and confidence values
are unchanged by the wording pass. Messages and explanations use ordinary
language. Consumers should use status/reason codes, not compare message strings.

Browser release checks: desktop and mobile resolved, ambiguous, unavailable,
source-conflict, demonstration and area-browse results; keyboard navigation and
visible focus; no horizontal overflow; readable citations and demo warnings;
accurate rendered metadata. Synthetic or mocked checks do not establish that
real election data or a live submission channel works.

Engineering checkpoint: 78 API tests passed, seven database-backed tests skipped,
one existing warning. Production web build passed. Mocked browser checks passed
at 1440px and 390px for resolved, ambiguous, source-conflict, unavailable,
demonstration, empty-message fallback and network-error responses, plus area
browsing and contribution guidance. Keyboard traversal/activation, visible focus,
rendered share descriptions and horizontal overflow were checked. Desktop/mobile
screenshots were visually inspected. This is not a full screen-reader audit or
live election-data acceptance. Shared CSS and editorial styling were unchanged.

Contact/identity follow-up: production build passed with favicon and both social
image routes. Repeated local mocked desktop/mobile checks passed (14 resolution
state/viewport checks, browsing, contribution guidance, keyboard and metadata).
Separate browser checks confirmed both mailto destinations on home/contribute,
production-domain Open Graph image URLs on both pages, and HTTP 200 for both
preview images and favicon. Mobile contribution layout and social preview were
visually inspected. No email was sent by these tests. Live deployment/HTTPS QA
remains deliberately deferred, and no DNS or hosting configuration was changed.
