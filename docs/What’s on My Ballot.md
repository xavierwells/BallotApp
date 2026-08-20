# Plan: Build a “What’s on My Ballot?” Platform for Copperas Cove

The core idea should be **not “a political website,” but a voter-information infrastructure layer**.

The user gives you an address. The system determines **every election, race, candidate, proposition, and relevant voting information that applies to that address**, then explains it in plain English and links every factual claim back to its source.

Copperas Cove is an excellent pilot because the city's election information is fragmented across the city, county, school district, candidate sites, and other election authorities. The city itself currently identifies City Council Places 6 and 7 for the November 3, 2026 election, while CCISD separately has Places 5, 6, and 7 open. ([Copperas Cove][1])

The important architectural principle is:

> **Determine the ballot first. Research the candidates second.**

That prevents the system from accidentally presenting someone with a generic “Copperas Cove election” rather than *their actual ballot*.

---

## 1. The finished product

The homepage should be extremely simple:

### **What's on your ballot?**

**Enter your address**

`[ 123 Main St, Copperas Cove, TX ]`

**→ Show My Ballot**

Then:

> **Your November 3, 2026 ballot**
>
> Based on your address, you are eligible to vote in **12 races and 3 propositions**.

And organize the result:

### 🏛️ Local — City of Copperas Cove

1. Mayor
2. City Council Place 6
3. City Council Place 7
4. Proposition A

### 🏫 School District

5. CCISD Place 5
6. CCISD Place 6
7. CCISD Place 7

### ⚖️ County

8. County Judge
9. County Commissioner
10. Justice of the Peace

### 🏛️ State

11. State Representative
12. State Senate

### 🇺🇸 Federal

13. U.S. House
14. U.S. Senate

### 📜 Propositions

15. State Proposition 1
16. Local Proposition A

The exact races would depend on the address.

**This is crucial because Copperas Cove isn't itself sufficient to determine a ballot.** The city crosses election jurisdictions, and historical official sample ballots demonstrate that Copperas Cove ballots can include city, county, state and judicial races depending on the relevant jurisdiction. ([Lampasas County, TX][2])

---

# 2. The system should have two fundamentally different pipelines

I'd build the product around two databases.

## Database A — **Ballot Intelligence**

Answers:

> **What is actually on this person's ballot?**

## Database B — **Candidate & Issue Intelligence**

Answers:

> **Who are these people, what do they say, and what can we independently verify about them?**

Keeping those separate will make the system considerably easier to maintain.

---

# 3. Pipeline #1 — Determine the user's exact ballot

This is the most important technical component.

### Input

User enters:

> 914 Example Street, Copperas Cove, TX 76522

The system resolves:

**Address → coordinates → precinct → county → school district → city → state legislative districts → judicial districts → other special districts**

Then creates something like:

```text
voter_location
 ├── City: Copperas Cove
 ├── County: Coryell
 ├── County precinct: 3
 ├── CCISD: Yes
 ├── State House: TX-59
 ├── State Senate: TX-24
 ├── Congressional District: XX
 └── Other districts:
       ├── ESD
       ├── water district
       └── etc.
```

### Data sources

Build a jurisdiction database containing:

* Texas Secretary of State
* County election administrators
* City election offices
* School districts
* Special districts
* Official GIS boundaries
* Election precinct maps
* Official sample ballots

The system should **never infer a ballot solely from ZIP code**.

---

# 4. The authoritative-ballot pipeline

Every election should progress through these states:

### Stage 1 — Election discovered

Example:

> November 3, 2026 General Election

### Stage 2 — Election authority identified

For Copperas Cove:

* City of Copperas Cove
* Coryell County
* Bell County, where applicable
* Lampasas County, where applicable
* CCISD
* Texas Secretary of State
* other applicable entities

The City of Copperas Cove already provides a dedicated election-information page containing its 2026 election documents. ([Copperas Cove][1])

### Stage 3 — Election order obtained

Collect:

* Order of Election
* Notice of Election
* candidate filing documents
* propositions
* jurisdictions participating

### Stage 4 — Candidate filing closes

Automatically update the candidate list.

For Copperas Cove, the city filing period ran July 18–August 17, 2026, for Places 6 and 7. ([Copperas Cove][3])

### Stage 5 — Official ballot generated

This is the gold standard.

Obtain:

> **Official Sample Ballot**

or equivalent certified ballot information.

### Stage 6 — Ballot parsed

Turn:

```text
Council Member, Place 6
Vote for none or one

Jay Manning
Jesus Mendez Jr.
```

into structured data.

### Stage 7 — Human verification

Before publication:

> **Two-person verification required**

One person confirms the ballot against the official document.

Only then:

**PUBLISHED**

---

# 5. Don't rely on OCR alone

Election documents are frequently PDFs, scans, images and bilingual documents.

Build a pipeline:

**PDF → text extraction → OCR if necessary → structured parser → human verification**

Every ballot race should retain:

* original document
* page number
* source URL
* extraction timestamp
* extraction method
* verification status

So your internal record might look like:

```text
Race:
Copperas Cove City Council Place 7

Source:
City of Copperas Cove

Document:
Notice of Election / Sample Ballot

Page:
2

Retrieved:
2026-08-19

Verified:
YES

Verified by:
Researcher #17
```

That gives you an audit trail.

---

# 6. Candidate discovery pipeline

Once the ballot is known:

### Candidate record is created

For each candidate:

```text
Candidate
 ├── Name
 ├── Office
 ├── Position
 ├── Incumbent?
 ├── Party
 ├── Campaign website
 ├── Email
 ├── Social media
 ├── Biography
 ├── Education
 ├── Occupation
 ├── Prior offices
 ├── Military/service
 ├── Policy positions
 ├── Endorsements
 ├── Campaign finance
 ├── Interviews
 ├── Debates
 └── Sources
```

But **every field should have a provenance status**.

For example:

### Occupation

**Property developer**

🟢 Candidate filing
🟢 Candidate website
🟡 News report

rather than simply:

> Property developer

---

# 7. Candidate research pipeline

This should be a repeatable research job.

For every candidate:

### Search Layer 1 — Official

Search:

* candidate campaign website
* official campaign social accounts
* candidate filing
* government biography
* previous government positions

### Search Layer 2 — Public record

Search:

* previous election results
* city council minutes
* school board minutes
* votes
* ordinances
* resolutions
* campaign finance reports
* public appointments

### Search Layer 3 — Journalism

Search local:

* newspapers
* television
* radio
* interviews
* candidate forums
* questionnaires

### Search Layer 4 — Candidate outreach

Contact the candidate directly.

This should be standardized.

---

# 8. Build a candidate questionnaire

This becomes one of the site's most important pieces of infrastructure.

Every candidate receives the **same questionnaire**.

For a Copperas Cove City Council candidate, for example:

### About you

1. What is your occupation?
2. What is your educational background?
3. What experience qualifies you for this office?
4. Have you previously held public office?

### Taxes & spending

5. Should Copperas Cove increase, decrease or maintain its current property-tax burden?
6. What areas of city spending should receive priority?
7. Are there areas where you believe spending should be reduced?

### Infrastructure

8. What are the city's three most important infrastructure needs?
9. How should the city pay for them?

### Public safety

10. What should Copperas Cove prioritize regarding police and fire services?

### Growth

11. Is Copperas Cove growing at an appropriate pace?
12. What development policies would you change?

### Utilities

13. What are your priorities regarding water/wastewater?
14. Do you support any particular infrastructure investments?

### Transparency

15. What should the city do differently regarding public access to information?

### Other

16. What is the single most important issue facing Copperas Cove?

Then:

> **Candidate response**

No editorial rewriting.

You can additionally provide:

> **Plain-English summary**

but the original response remains available.

---

# 9. Candidate communication pipeline

This should be partially automated.

### Initial email

> You are a candidate for Copperas Cove City Council Place 7.
>
> We are preparing a nonpartisan voter-information guide for the November 3, 2026 election.
>
> We would like to give every candidate the same opportunity to provide voters with information about their background and positions.

Then provide:

**[Complete candidate questionnaire]**

Candidate gets:

* 500–1,000 words
* deadline
* ability to attach photo
* website/social links
* correction mechanism

### Follow-ups

Automate:

**Day 0:** Initial request
**Day 7:** Reminder
**Day 14:** Final reminder
**Day 21:** Mark “Candidate did not respond”

Critically:

> **No response should never be represented as a negative statement about the candidate.**

Simply:

> **Candidate did not respond to our questionnaire as of August 30.**

---

# 10. Candidate verification pipeline

Candidates should also receive a **fact-check sheet**.

Before publication:

> We intend to publish the following information about you.

Example:

**Occupation:** Property developer
**Previous office:** Copperas Cove City Council, 2016–2022
**Education:** ______
**Military service:** ______

Candidate gets:

**Confirm / Correct**

This accomplishes two things:

1. Improves accuracy.
2. Gives candidates an incentive to participate.

But their response should be labeled:

> **Candidate-provided information**

rather than treated as independently verified fact.

---

# 11. Build an “Information Missing” system

This is essential.

Don't just leave blank spaces.

Instead:

### 🟡 We are still researching this candidate

**Policy positions:** No sufficiently sourced statements found.

**What we've done:**

* Searched candidate website
* Searched candidate social media
* Searched local news
* Sent candidate questionnaire
* Requested interview

**Last checked:** August 19, 2026

**Candidate response:** No response received.

That makes the absence of information transparent.

---

# 12. Research queues

Internally, every missing piece becomes a task.

For example:

### Jesus Mendez Jr.

* [x] Confirm candidacy
* [x] Confirm office
* [ ] Find campaign website
* [ ] Find biography
* [ ] Find prior public service
* [ ] Find policy positions
* [ ] Search local interviews
* [ ] Search social media
* [ ] Send questionnaire
* [ ] Request photograph
* [ ] Verify occupation
* [ ] Search campaign finance
* [ ] Candidate fact-check

The researcher dashboard should automatically prioritize:

> **Candidate with 17 missing fields**

rather than someone whose profile is already complete.

---

# 13. Local journalism pipeline

This is where the site can become much more useful than a simple candidate directory.

Create a database of relevant local reporting.

For every article:

```text
Article
 ├── Publication
 ├── Date
 ├── URL
 ├── Author
 ├── Candidates mentioned
 ├── Offices mentioned
 ├── Issues mentioned
 └── Claims extracted
```

Then connect articles to candidate profiles.

Example:

### Dana Wall

**Local coverage**

* Candidate announcement
* Interview
* Candidate forum
* Position on infrastructure
* Position on development

The user can click through to the original article.

---

# 14. Government-record pipeline

For **incumbents**, this becomes extremely valuable.

Automatically ingest:

* council agendas
* meeting minutes
* ordinances
* resolutions
* voting records where available
* budgets
* contracts
* public statements

Then build:

### Candidate: Incumbent

**Record while in office**

> Voted for Ordinance 2026-XX
> Sponsored Resolution XXXX
> Missed X% of meetings

But be careful:

**Voting record ≠ policy interpretation.**

The site should show:

> **What happened**

before:

> **What it means politically.**

---

# 15. Explain every office

This should be a separate database.

Every office gets a standardized explanation.

### City Council

**What it controls**

**What it doesn't control**

**Term length**

**Salary**

**How elected**

**Current officeholder**

**Powers**

**Major responsibilities**

**Recent major decisions**

**Relevant budget**

Then candidates are attached to that office.

This prevents users from expecting a city council member to solve something that actually belongs to the county, school district or state.

---

# 16. Propositions need their own pipeline

Do **not** treat propositions as an afterthought.

For every proposition:

### Official wording

Display the exact official language.

Then:

### What this means in plain English

A concise neutral explanation.

### Financial impact

If available:

* tax impact
* bond amount
* estimated repayment
* budget impact

### Who proposed it?

### What changes if YES?

### What changes if NO?

### Arguments FOR

Sourced.

### Arguments AGAINST

Sourced.

### Original documents

Linked.

And critically:

> **Never reduce a proposition to "Yes means X, No means Y" without checking the actual legal text.**

---

# 17. “Everything on the ballot” needs a hierarchy

The product should display **everything**, but prioritize elected offices.

I would use:

### Tier 1 — Elected offices

**Highest prominence**

* President
* Senate
* Congress
* Governor
* Legislature
* judges
* county
* city
* school board
* special districts

### Tier 2 — Propositions

Full explanations.

### Tier 3 — Administrative ballot information

Things like:

* voting instructions
* straight-ticket information if applicable
* write-in provisions
* local election notices

### Tier 4 — Voting logistics

* registration
* early voting
* Election Day
* polling locations
* ID requirements
* absentee/mail voting

For Coryell County, for example, the county already publishes detailed 2026 early-voting dates, polling locations and countywide vote-center information. ([Coryell County Tax Office][4])

Your system should **ingest that information rather than recreate it manually**.

---

# 18. The Copperas Cove geographic problem

This deserves special attention.

Copperas Cove is not simply:

> **Copperas Cove = one ballot**

Your architecture needs:

```text
Address
 ↓
Precinct
 ↓
County
 ↓
Municipality
 ↓
School district
 ↓
State districts
 ↓
Federal districts
 ↓
Special districts
 ↓
Ballot
```

The city itself points voters to both Coryell County and Lampasas County election information. ([Copperas Cove][1])

That means the platform should deliberately support **jurisdiction overlap** from day one.

---

# 19. Data architecture

I'd use a relational database.

Core tables:

```text
jurisdictions
elections
precincts
districts
offices
races
candidates
candidate_sources
candidate_statements
issues
propositions
ballot_items
ballot_versions
documents
news_articles
government_actions
candidate_outreach
research_tasks
source_claims
```

The critical relationship is:

```text
Address
   ↓
Precinct
   ↓
Ballot Version
   ↓
Ballot Item
   ↓
Race
   ↓
Candidate
   ↓
Evidence
```

That gives you a defensible data model.

---

# 20. Every piece of information gets provenance

This is probably the most important engineering decision.

Don't store:

```text
Dana Wall supports infrastructure spending.
```

Store:

```text
claim:
"Dana Wall supports infrastructure investment"

source:
campaign website

source_url:
...

source_date:
...

retrieved:
...

source_type:
candidate_statement

confidence:
high

verified:
yes
```

Then the UI can automatically display:

> **Dana Wall says she supports infrastructure investment.**
> 🔵 Candidate statement

---

# 21. Build an editorial AI layer — but don't let AI be the authority

AI is excellent for:

* finding candidate information
* extracting names
* summarizing documents
* detecting duplicate candidates
* extracting policy positions
* converting legal language into draft plain-English explanations
* identifying missing information
* suggesting follow-up research

AI should **not independently decide that a political claim is true**.

Instead:

### AI

> “I found this statement.”

### Researcher

> “Is the source legitimate?”

### Source

> “Here is the evidence.”

### Editor

> “Is our characterization fair?”

### Published

> “Here is exactly where this came from.”

That architecture would dramatically reduce hallucination and partisan framing.

---

# 22. Create a source hierarchy

I'd establish this formally.

### Level 1 — Primary authoritative

**Best**

* election authority
* government document
* candidate filing
* official ballot
* court record
* candidate's own statement

### Level 2 — High-quality secondary

* reputable local journalism
* established news organizations

### Level 3 — Other public sources

* campaign social media
* interviews
* community organizations

### Level 4 — Discovery only

* random social posts
* aggregators
* search snippets
* forums

Level 4 can help you **find leads**, but should generally never be the final source for an important factual claim.

---

# 23. Candidate fairness rules

Write these into the company's editorial policy before launching.

### Rule 1

Every candidate receives the same questionnaire.

### Rule 2

Every candidate receives the same opportunity to respond.

### Rule 3

Candidate-provided information is clearly labeled.

### Rule 4

The site never assigns a “good/bad” candidate rating.

### Rule 5

No ideological scoring.

### Rule 6

Negative information requires particularly strong sourcing.

### Rule 7

The site distinguishes:

**Fact**

from

**Candidate claim**

from

**Editorial analysis**

from

**User-submitted information.**

### Rule 8

Candidates can request factual corrections.

### Rule 9

Corrections are logged publicly.

### Rule 10

No candidate can pay for favorable treatment.

That last one is essential to the business model.

---

# 24. Candidate pages should eventually look like this

## Dana Wall

**Copperas Cove City Council — Place 7**

### At a glance

**Incumbent:** No
**Party:** Nonpartisan municipal race
**Occupation:** ...
**Previous public office:** ...

### Her priorities

| Issue          | Position            |
| -------------- | ------------------- |
| Infrastructure | Candidate statement |
| Taxes          | Candidate statement |
| Public safety  | Candidate statement |
| Development    | Candidate statement |
| Transparency   | Candidate statement |

### In her own words

[Candidate responses]

### Public record

[Government records]

### News coverage

[Articles]

### Candidate questionnaire

[Responses]

### Sources

[Everything]

That is a **research product**, not a campaign advertisement.

---

# 25. Build the Copperas Cove MVP manually first

I would strongly resist trying to automate everything initially.

### Phase 1 — Copperas Cove

Build:

**November 3, 2026**

with:

* City
* CCISD
* Coryell County
* applicable Bell/Lampasas jurisdictions
* state
* federal
* propositions
* voting information

The current city election is a particularly manageable starting point because the city has only two City Council positions scheduled for the 2026 election. ([Copperas Cove][3])

---

# 26. MVP research team

You could initially operate with:

### 1 founder/product person

Responsible for:

* product
* editorial standards
* partnerships

### 1 researcher

Responsible for:

* candidates
* government documents
* questionnaires
* local news

### 1 engineer

Responsible for:

* database
* address lookup
* frontend
* ingestion

AI handles a substantial portion of the research assistance.

---

# 27. Copperas Cove information-gathering campaign

Immediately after the MVP database is created:

### Government outreach

Contact:

**Copperas Cove City Secretary**

Ask for:

* final candidate list
* official sample ballot
* election notices
* candidate contact information
* campaign finance information
* any public candidate questionnaires

The city identifies Lisa Wilson as City Secretary and provides her office's contact information on its election page. ([Copperas Cove][3])

### County outreach

Contact:

* Coryell County Elections
* Bell County Elections, where relevant
* Lampasas County Elections, where relevant

Ask for:

* precinct maps
* sample ballots
* ballot styles
* participating entities
* election notices

### CCISD

Contact the district.

The district currently lists Places 5, 6 and 7 as open for the November 3 election. ([Copperas Cove ISD][5])

Ask:

* candidate applications
* candidate contact information
* biographies
* election documents

---

# 28. Candidate outreach campaign

Once the final candidate list is confirmed:

**Every candidate gets an email within 24 hours.**

Not just the candidates with websites.

For each:

> “We are creating a nonpartisan voter guide for Copperas Cove voters.”

Include:

* questionnaire
* deadline
* photo request
* biography request
* campaign website
* social media
* interview request

Then track every communication.

---

# 29. Candidate interviews

Eventually, offer every candidate a standardized 20-minute interview.

Same questions.

Record it.

Transcribe it.

Publish:

**Full interview**

plus:

**5-minute summary**

plus:

**Key positions**

This becomes especially valuable in tiny local races where candidates aren't appearing on television or major political podcasts.

---

# 30. Community submission pipeline

Add:

> **Know something we're missing?**

Users can submit:

* candidate website
* candidate interview
* public document
* correction
* campaign announcement
* missing race

But nothing becomes published automatically.

It enters:

**Research queue → verification → publication**

---

# 31. “Last verified” should appear everywhere

For example:

> **Ballot verified:** August 19, 2026
> **Candidate information:** August 19, 2026
> **Voting information:** August 19, 2026

As Election Day approaches, increase verification frequency.

### 90+ days out

Weekly.

### 60 days

Twice weekly.

### 30 days

Daily.

### Final week

Multiple times per day for ballot changes.

---

# 32. Election Day mode

On Election Day, the product changes.

Instead of:

> “Who is running?”

it becomes:

### **Go Vote**

**Your ballot**

**Where to vote**

**Hours**

**What you need**

**Your races**

**Your propositions**

**Official election results**

Then after polls close:

### Results mode

* unofficial results
* precinct results
* county results
* final certified results

The county already publishes historical results, early-voting totals, sample ballots and other election records, demonstrating that much of the underlying data infrastructure already exists publicly. ([Coryell County Tax Office][4])

---

# 33. After the election, don't throw the data away

This is where the product becomes dramatically more valuable.

Every election creates historical data.

For an elected official:

```text
Candidate
 ↓
Campaign
 ↓
Election
 ↓
Office
 ↓
Votes
 ↓
Actions while in office
```

Then four years later:

> **“You told voters X. What did you actually do?”**

That's an extraordinarily powerful longitudinal feature.

---

# 34. The long-term product

Eventually the site becomes:

## **A civic knowledge graph**

Not merely:

> “What's on my ballot?”

but:

> **“Help me understand my local government.”**

A user could click:

**City Council Place 7**

and see:

**Candidates → election → current officeholder → previous officeholders → votes → ordinances → budgets → issues → campaigns → outcomes**

That is much harder for competitors to replicate than a static voter guide.

---

# 35. Business model

I'd keep the voter-facing product free.

Potential revenue:

### Government / civic organizations

Paid tools for:

* candidate questionnaire management
* election data management
* civic engagement

### News organizations

API/data licensing.

### Foundations

Civic-information grants.

### Universities

Research/data subscriptions.

### Local media

White-label voter guides.

### Eventually

**Election intelligence API**

A newspaper could request:

```text
GET /ballot?address=...
```

and receive the complete ballot.

That could become the real business.

---

# 36. The first concrete build

If I were actually starting this project tomorrow, I would **not start by building the nationwide system**.

I'd build:

## **Copperas Cove 2026**

### Step 1

Create jurisdiction database.

### Step 2

Map Copperas Cove addresses to districts/precincts.

### Step 3

Acquire official November 3 ballot documents.

### Step 4

Create every ballot item.

### Step 5

Create every candidate.

### Step 6

Contact every candidate.

### Step 7

Research every candidate.

### Step 8

Write standardized office explanations.

### Step 9

Explain every proposition.

### Step 10

Add voting logistics.

### Step 11

Have two people independently verify every ballot item.

### Step 12

Launch publicly.

Then put a big button at the bottom:

> **“Something wrong or missing?”**

and let Copperas Cove residents help improve it.

---

# 37. The key metric

I would **not** measure success primarily by page views.

I'd measure:

### **Ballot Completion Rate**

> Percentage of users who can successfully identify every item appearing on their actual ballot.

Then:

### **Information Completeness**

> Percentage of candidates with verified biography + positions + sources.

Then:

### **Source Coverage**

> Percentage of claims backed by a primary or high-quality secondary source.

Then:

### **Candidate Participation**

> Percentage of candidates responding to the standardized questionnaire.

Those metrics directly measure whether the product is actually solving the problem.

---

# 38. What the Copperas Cove launch should ultimately promise

The homepage shouldn't promise:

> **“We'll tell you who to vote for.”**

It should promise:

> **“We'll tell you what you're voting on.”**

And underneath:

> **Every race. Every candidate. Every proposition. Explained. Sourced. Updated.**

That positioning is important.

You're not creating another political opinion site.

You're creating the **missing information layer between government election records and ordinary voters.**

And the Copperas Cove experiment suggests that layer has a legitimate reason to exist: the official information is already distributed among city election records, county election systems, school-district notices, candidate material, and local reporting. ([Copperas Cove][1])

**The first engineering milestone I'd target is therefore not the candidate profiles. It's the “address → exact ballot” engine.** Once that works reliably, everything else—candidate research, explanations, questionnaires, news aggregation and eventually nationwide expansion—can attach to that core.

[1]: https://www.copperascovetx.gov/188/Election-Information?utm_source=chatgpt.com "Election Information | Copperas Cove, TX"
[2]: https://www.co.lampasas.tx.us/upload/page/8715/WEB%20PAGE%20COLOR%20SAMPLE%20BALLOTS%20NOV5%202024.pdf?utm_source=chatgpt.com "•
General Election
(Eleccion General)
Lampasas Cou"
[3]: https://www.copperascovetx.gov/DocumentCenter/View/6664/Notice-of-Deadline-to-File-an-Application-for-Place-on-the-Ballot-PDF?utm_source=chatgpt.com "CITY OF 
COPPERAS COVE 
MEDIA RELEASE 
 
June 22,"
[4]: https://coryellcountytax.com/Elections/?utm_source=chatgpt.com "Elections - Coryell County Tax Office"
[5]: https://www.ccisd.com/page/election-2026?utm_source=chatgpt.com "Copperas Cove ISD Board of Trustees Election 2026"
