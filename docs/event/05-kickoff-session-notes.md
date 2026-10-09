# Kickoff Session Notes

**Session:** "AI Builder Cup | Introductory & Problem Statement Explainer Session", Hack2skill, 11 Sep 2026, 47 min. [Recording](https://www.youtube.com/live/mhDd6qSBMg4)
**Speakers:** Shweta (Hack2skill, host) and Prashant (Developer Relations Engineering, Google)

## Programme

- Registrations are approved in batches. "Waitlisted" is normal until approval email arrives.
- Build phase teams have up to 4 members, but **only 2 travel** to the finale. Teams handle their own visas.
- Top **50** teams get sponsored travel to Singapore. The shortlist is out on 7 Nov and the finale is 4 Dec, which leaves about 3 weeks for visas.
- Team finalised (2–4 members) by **11 Oct**. Prototype built and submitted by **18 Oct**.
- Prize categories: winner and 2 runners-up, plus best use of Google Cloud AI tools, most impactful, jury choice, and best UI/UX. *"Maybe you can integrate a few more Google Cloud AI tools and services."*
- **IP stays with the participant/team.**
- More AMA sessions were promised closer to the deadline. Watch Discord and email.

## Who it's for

- Working professionals, entrepreneurs and startups. *"Bring your expertise, your experience, what you are seeing in the industry."*
- **Not open to students** in this edition.

## Themes: the speaker's hints for Retail & Commerce

- *"All of this is about the experience and it is about the customer."*
- Engaging, delightful experiences; operational efficiency; quick turnarounds.
- Make processes like **checkout and returns** seamless.
- **Hyper-personalisation** and **conversational experiences** (*"you're not waiting through long phone calls, IVRs"*).
- Back-office side: inventory management and demand planning (seasonality, festivals).
- Themes common to every track: **personalisation, security, good user experience**.

## What to build

- *"Not just an idea… build something functional… that we can touch and feel and play around."*
- Use Google AI models: **Gemini** (hosted) or **Gemma** (local).
- Build with agentic concepts and platforms: **Agent Platform** on Google Cloud, **ADK** (Agent Development Kit), **Antigravity** as an AI harness for building, **AI Studio** for UIs.
- Other APIs and frameworks are allowed, *"but you should be featuring and leveraging the Google technologies in the right way."*
- **Deploy on Cloud Run or Firebase.**

## Submission artefacts (as explained)

1. **Documentation** (PPT → PDF):
   - what the solution does and its impact
   - **how it aligns with the chosen theme**: *"the themes are pretty vast"*, so explain which specific area you address
   - how what you built solves the problem: *"Not just I built this but I built this because this is the problem"*
   - **longevity and scalability**: how it could run in production for hundreds of thousands of users
   - an optional **user guide** (features, how to use the prototype)
2. **Functional prototype** deployed on Cloud Run or Firebase. *"Ensure the prototype is demonstrating whatever ideas that you are trying to solve."*
3. **Demo video** with voice-over on YouTube, Vimeo or Drive, **public**.
4. **Public GitHub repo**, so judges can confirm *"you're using this hackathon time period to build out your solution."*
5. **English** for everything.
6. *"This is not just vibe coding… How is it going to run in production? How is it reliable?"*

## Judging, in the speaker's words

- **Technical merit (40%):** *"It's not just a simple send a prompt to the AI, get a response and say I've used AI, I'm done."*
- **Alignment (25%):** if the project isn't aligned to one of the six themes, *"your alignment is not there at all."* The specific problem inside the theme is yours to define.
- **Innovation (25%):** *"Don't redo a solution that has already been built."* Making an existing idea better is fine.
- **UX (10%):** *"Not just a flashy UI."*

## Q&A: technical recommendations from Google

- **Minimum architecture:** AI API + runtime + database. Start simple, deploy, then evolve: *"have a progressive architecture."* Add load balancer, CDN or caching only when needed.
- **Gemini directly vs agents:** either works; *"yes to both."* ADK makes agents easy.
- **RAG:** every Google Cloud database has vector/embedding support (DIY RAG with LangChain/LlamaIndex/ADK), or use the managed **Vector Search** on Agent Platform. With a single small document, put it in the context instead.
- **Recommended starter stack:** **Gemini Flash** (the speaker named "3.8 Flash") → **ADK** → **Cloud Run** → **Firestore** (Cloud SQL for relational needs, BigQuery for analytics). SQLite locally is fine during development.
- **Prompting:** read Gemini's "prompting best practices" docs, and **write evals** to validate outputs.
- *"Start from the problem statement, not from the 150+ products."* With just Gemini plus the SDK *"you can go almost 70–75% of the way."*
