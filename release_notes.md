# News Digest — Edition 2026.10.25


### 🌟 Access the Dashboard
* **[Open Live Web Dashboard](https://gyu977.github.io/news-agg/)**

---

### 🎣 What's New: Fresh weekly catch

We refreshed our sources this week—including *Dear Architects #313*, *Token by Token #28*, *Andriy Burkov AI #349*, *Editor's Radar*, and our regular engineering blogs—and pulled together practical reads on how teams are actually building, reviewing, and paying for software right now:

- **[Redesigning source control at Anthropic](https://www.anthropic.com/research/redesigning-source-control)** — Anthropic *(Token by Token #28 · Spotlight)*
  > When daily merges grew more than tenfold, Git started getting in the way. Here is how Anthropic built an internal version control system called Scion and moved their monorepo over in five months, alongside their own code review and search tools.
- **[From Microservices to Agents: the Next Evolution of Distributed Systems](https://www.infoq.com/articles/distributed-systems-microservices-agentic-ai/)** — Mallika Rao *(Dear Architects #313 · Spotlight)*
  > A clear look at what changes in system boundaries, ownership, and failure modes when agents start calling services alongside traditional microservices.
- **[What’s the ROI of software engineers’ spending on AI?](https://newsletter.pragmaticengineer.com/p/whats-the-roi-of-software-engineers)** — Gergely Orosz *(The Pragmatic Engineer)*
  > Looking at data from 27 companies to ask a straightforward question: now that engineering teams are spending heavily on AI tools, are they actually shipping faster?
- **[Supervisory Engineering Work](https://annievella.com/posts/supervisory-engineering-work/)** — Annie Vella & **[On the Death of Amazon’s Writing Culture](https://alifeengineered.substack.com/p/on-the-death-of-amazons-writing-culture)** — Steve Huynh *(Editor's Radar)*
  > Annie Vella on the new "middle loop" of software engineering—directing AI, verifying output, and fixing what it gets wrong—paired with former Amazon Principal Engineer Steve Huynh on how generative AI broke the guarantee that writing a six-page memo forces clear thinking.
- **[Someone behind the software](https://karrisaarinen.com/posts/someone-behind-the-software/)** — Karri Saarinen & **[Uncle Bob: Why I Stopped Reading Code and Building Harnesses](https://www.aviator.co/podcast/uncle-bob-martin-ai-clean-code)** — Robert C. Martin *(Editor's Radar)*
  > Two grounded takes on the human side of the job: Linear's co-founder on why good software still feels like a person cared about the details, paired with Uncle Bob on why engineers remain responsible for what ships even when agents write the code.
- **[LLMs are making formal software verification feasible at a much larger scale](https://www.anthropic.com/research/formal-verification)** — Anthropic *(Dear Architects #313)*
  > Formal verification used to take years of specialist work for even small codebases. This piece looks at how LLMs can do the heavy lifting of writing proofs to catch bugs before code hits production.
- **[How To Use Decision Models for Evals](https://x.com/HamelHusain/status/2112588257104216294)** — Hamel Husain & Antaripa Saha *(Token by Token #28)*
  > A practical walkthrough on why leaving your eval classifier threshold at `0.50` is usually a mistake, and how to tune cutoffs against cost and accuracy.
- **[1.5 years of RAG in fintech, what actually worked after screwups](https://www.reddit.com/r/Rag/comments/1so0m3n/15_years_of_rag_in_fintech_what_actually_worked/)** — r/Rag & **[Tokenomics: Quantifying where tokens are used in agentic software engineering](https://www.chapterpal.com/s/a77ad8a0/tokenomics-quantifying-where-tokens-are-used-in-agentic-software-engineering)** — ChapterPal *(Burkov AI #349)*
  > Hard-won lessons from eighteen months of running RAG in financial services (what broke and what stuck), plus a breakdown of where tokens actually go during agentic coding sessions.

---

### 🛠️ Net & Tackle Maintenance

- **Cleaner Sources & Categories Guide**: Sources that have aged past the 90-day dashboard window (like July's *Thoughtworks FOSE* retreat notes) are now automatically left out of the Guide instead of sitting there with a `0` badge, and items that temporarily hit `0` under narrow filters are gently dimmed.
- **MailerLite Scraper Fixes**: Fixed a `robots.txt` check and campaign timestamp fallback so new *Dear Architects* and *Token by Token* issues pull in cleanly.

---

# News Digest — Edition 2026.10.18


### 🌟 Access the Dashboard
* **[Open Live Web Dashboard](https://gyu977.github.io/news-agg/)**

---

### 🎣 What's New: Fresh weekly catch

We cast our nets across 12 sources this week—including *Dear Architects #312*, *Token by Token #27*, *Andriy Burkov AI #348*, *The Week Ahead #43*, and our usual blogs—and hauled in some standout reads on verification, agent harnesses, and the craft of thinking:

- **[How the Claude Code team does code review](https://claude.dev/blog/solving-code-review-at-anthropic/)** — Addy Osmani, Morgan Westlee Lunt & Qing Wang *(Dear Architects #312 · Editor's Radar)*
  > When agents write code at scale, human review time becomes the bottleneck. Here is how the Claude Code team keeps review effort minimal without driving up reverts or incidents.
- **[Are Harnesses Worth the Cost?](https://martinfowler.com/articles/are-harnesses-worth-the-cost.html)** — Naresh Jain *(Token by Token #27 · Martin Fowler · Spotlight)*
  > Testing whether complex agent harnesses actually improve acceptance rates—or just burn extra time and tokens when frontier models can already solve the task on the first try.
- **[Take My Toil, Leave Me My Struggle](https://newsletter.kentbeck.com/p/take-my-toil-leave-me-my-struggle)** — Kent Beck *(Editor's Radar)*
  > A short, sharp reflection using "RoboGym"—a gym machine that lifts the weights for you at the press of a button—to ask what happens when AI tools take away the mental struggle that actually makes us stronger engineers.
- **[How to Find Resilience Bugs in Systems that Don't Exist](https://www.infoq.com/presentations/formal-methods-principles/)** & **[What TLA+ can and can't check](https://buttondown.com/hillelwayne/archive/what-tla-can-and-cant-check/)** — Hillel Wayne *(Dear Architects #312 · Editor's Radar)*
  > A great double-feature from Hillel Wayne: a talk on using formal methods thinking to catch architectural bugs early, paired with a grounded reality check on what TLA+ can (and cannot) verify in the age of AI.
- **[Everything I know about good system design](https://www.seangoedecke.com/good-system-design/)** — Sean Goedecke *(Dear Architects #312)*
  > Skipping the LinkedIn-style "have you heard of queues?" advice in favor of practical lessons on how real production systems are designed and kept simple.
- **[State of AI Report 2026](https://www.stateof.ai/2026-explore/)** — Nathan Benaich *(Burkov AI #348)*
  > The annual data-heavy look across AI research, industry, safety, and compute trends.
- **[Uber’s AI infra, from the inside](https://newsletter.pragmaticengineer.com/p/ubers-ai-infra-from-the-inside)** — Gergely Orosz & Uday Kiran Medisetty *(The Pragmatic Engineer)*
  > A look inside how Uber builds internal developer tooling, wires AI agents into daily workflows, and measures what actually helps engineers.

---

### 🛠️ Net & Tackle Maintenance

- **Working Newsletter Preview Links**: Fixed a quirk where our link cleaner was stripping the `?signature=` token off MailerLite webview URLs, so clicking issue badges on *Dear Architects* and *Token by Token* opens the full original newsletter issue again.
- **Upcoming Conferences Radar**: Added *The Week Ahead (Week 43)* events—including **NVIDIA GTC (Berlin)** and **Money20/20 (Las Vegas)**—visible whenever you flip on the **Future Events** switch.

---

# News Digest — Edition 2026.10.11


### 🌟 Access the Dashboard
* **[Open Live Web Dashboard](https://gyu977.github.io/news-agg/)**

---

### 🎣 What's New: Fresh weekly catch

- **[Designing MCP Gateway: Uber's MCP Management Platform](https://www.uber.com/gb/en/blog/designing-mcp-gateway/)** — Uber *(Dear Architects #311 · Spotlight)*
  > How Uber built a centralized Model Context Protocol (MCP) management platform to enable secure, governed tool execution, authentication, and context streaming across hundreds of autonomous internal agents.
- **[The AI SDLC Transformation Playbook](https://www.atlassian.com/blog/ai-at-work/ai-sdlc-transformation-playbook)** — Atlassian *(Dear Architects #311)*
  > Practical strategies from Atlassian on redesigning continuous delivery, pull request reviews, and engineering team boundaries when AI agents generate the bulk of implementation code.
- **[Introducing System One Models and Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)** — TypeSafe AI *(Token by Token #24)*
  > A new frontier model class designed for fast, calibrated, typed decisions with zero generation latency, built specifically for real-time software systems and deterministic execution pipelines.
- **[Which tools do Claude Code, Codex and Cursor choose?](https://armature.tech/blog/which-tools-coding-agents-install)** — Armature Tech *(Burkov AI #347)*  
  > An empirical benchmark analyzing 16,893 agentic coding sessions measuring tool selection frequencies, terminal inspection habits, and execution harnesses.
- **[Automating Feature-Flag Cleanup at Scale with a Multi-Agent LLM System](https://careersatdoordash.com/blog/automating-feature-flag-cleanup-at-scale-with-a-multi-agent-llm-system/)** — DoorDash *(Dear Architects #311)*  
  > How DoorDash coordinated multi-agent LLM systems to safely identify, verify, and clean up over 1,000 stale feature flags across 623 repositories.
- **[OpenAI published 719 mathematical manuscripts produced by an internal AI model](https://github.com/openai/math/tree/main)** — OpenAI *(Burkov AI #347)*  
  > Breakthrough exploration in automated formal reasoning, unveiling 719 novel mathematical proofs generated by an unreleased internal model.

---

### 🛠️ Experience & Dashboard Improvements

- **Precision Multi-Event Scheduling**: *The Week Ahead* now supports item-specific conference start dates, ensuring upcoming events are accurately positioned and sorted chronologically when the **Future Events** toggle is enabled.
- **Canonical Reading Archive**: The interactive dashboard ([news.html](news.html)) now features **374 curated, deduplicated articles** across 12 premier technical publications, with 40 cross-source duplicates seamlessly grouped via the `🏷️ Also In` badge.

---

# News Digest — Edition 2026.09.30

## 🌟 Headline: Onboarding "The Week Ahead" — Forward-Looking Tech & Architecture Event Radar

This release marks a major evolutionary milestone for **News Catch (`news-agg`)**: onboarding **The Week Ahead** (`the-week-ahead`), transforming the application from a purely retrospective reading archive into a **forward-looking radar** for software architects, engineering leaders, and AI practitioners.

---

### 1. High-Impact Content: Global Tech & Architecture Conferences
Curated from *Above* (Above Impacts, Issue #40), this edition introduces landmark conferences and industry summits with strict editorial filtering (non-engineering marketing events filtered out):

- 🏛️ **[GOTO Copenhagen 2026](https://gotocph.com/2026)** *(The Week Ahead #40 · Spotlight)*  
  > 28 Sep–2 Oct 2026 · Copenhagen. Five days of masterclasses and talks on software architecture, distributed systems, AI engineering, and resilient system design featuring Sam Newman, Alex Ewerlöf, and Kevlin Henney.
- 🏛️ **[CoreWeave Fully Connected (San Francisco)](https://www.coreweave.com/)** *(The Week Ahead #40)*  
  > 29 Sep–1 Oct 2026 · San Francisco. A summit for infrastructure leaders building AI clusters at scale, focusing on compute, high-speed networking, distributed storage, and developer experience with Michael Intrator, Ian Buck, and Fei-Fei Li.
- 🏛️ **[The AI Conference (San Francisco)](https://aiconference.com/)** *(The Week Ahead #40)*  
  > 29 Sep–1 Oct 2026 · San Francisco. Researchers, builders, and infrastructure architects meet around production model deployments, featuring Brian Yang (OpenAI) on rapid product building.
- 🏛️ **[Boston AI Week](https://www.linkedin.com/company/bostonaiweek)** *(The Week Ahead #40)*  
  > 28 Sep–2 Oct 2026 · Boston. Community-wide deep dive into real-world business and healthcare AI transformation.

---

### 2. Transformative Impact on the Application

The onboarding of **The Week Ahead** drove several high-leverage architectural and UI innovations across the platform:

1. **First-Class Conference Event Modeling (`type: "conference"`)**:
   - Introduced dedicated event metadata (`dates`, `location`) and the high-contrast auditorium icon (`🏛️`) for crisp visual recognition at 14px on dark backgrounds.
2. **Accessible "Future Events" Switch Control**:
   - Added a modern animated pill switch control (`#futureEventsToggle`, `role="switch"`, `aria-checked`) directly in the header controls toolbar. Users can seamlessly filter or isolate future event dates without disrupting the default chronological reading flow.
3. **Dedicated Source Identity & Faceted Filtering**:
   - Styled with a custom teal publication badge (`.badge-week-ahead` for `#40 The Week Ahead`).
   - Fully wired into the multi-select source filter dropdown with real-time article counts and zero-count dimming.
4. **Offline Normalization & Pipeline Hardening**:
   - Registered prefix `"the-week-ahead": "twa"` in `code/tools/normalize_data.py`.
   - Comprehensive test assertions added in `tests/test_filter_matrix.py` and `tests/test_scraper_infrastructure.py`.

---

## 🛠️ Ingestion Engineering: Multi-Channel Article Contract

- **Dual-Syndication Solution**: Creators publishing across both personal blogs and Substack (e.g., Addy Osmani) no longer produce duplicate entries.
- **Contract Rules**:
  - Personal blogs are declared as `primary_channel`; Substack is queried strictly as a fallback.
  - Articles are matched by semantic identity `(normalized_title, author)`.
  - Automatic promotion: Fallback Substack links are auto-promoted to canonical personal blog links upon publication, while strictly preserving manual `user_overrides`.
- **Deduplication Results**: Collapsed 21 duplicate syndication pairs in Addy Osmani down to **60 clean, canonical records** (0 duplicates).

---

## 📚 Selected Articles & Editorial Category Highlights

### 🤖 AI-Native & Agentic Software Engineering
- [Brownfield Agentic Engineering](https://addyosmani.com/blog/brownfield-agentic-engineering/) — Addy Osmani
  > What it takes to run coding agents in a codebase older than the team.
- [Agentic Skill Decay](https://addyosmani.com/blog/agentic-skill-decay/) — Addy Osmani
  > Agents can finish the task without teaching you anything. Building expertise now has to be deliberate.
- [How Good Is AI at Coding React (Really)?](https://newsletter.pragmaticengineer.com/) — Gergely Orosz (*The Pragmatic Engineer*)
  > Evaluating real-world developer productivity and code correctness with modern AI assistance.

### 🧠 Large Language Models & Evaluation Infrastructure
- [GLM-5.3 and the spread of advanced cyber capabilities](https://www.anthropic.com/research/glm-5-3-and-the-spread-of-advanced-cyber-capabilities) (*Anthropic · Ingested via Inbox*)
  > Autonomous exploit synthesis capabilities across frontier models and the urgent need for defensive safeguards.
- [2026 in LLMs (so far)](https://simonwillison.net/) — Simon Willison (*Simon Willison's Weblog*)
  > Mid-year retrospective examining reasoning architectures, local open weights, and eval infrastructure.

### 🏛️ Software Architecture & Distributed Systems
- [Bliki: Sensible Default](https://martinfowler.com/bliki/SensibleDefault.html) — Martin Fowler
  > Selecting architecture baselines that minimize decision fatigue while maintaining modular evolvability.
- [Why has Shopify dropped React Native?](https://www.infoq.com/news/) — InfoQ Architecture
  > An in-depth architectural post-mortem on Shopify's strategic migration back to native mobile stacks.

### 🧪 Software Testing, Quality & Observability
- [The Code Nobody Reads](https://addyosmani.com/blog/the-code-nobody-reads/) — Addy Osmani
  > Line-by-line human review is evolving. Whatever replaces it must earn the trust reading once provided.

---

*The complete interactive dashboard featuring 359 canonical articles from the last 3 months is attached as `news.html`.*
