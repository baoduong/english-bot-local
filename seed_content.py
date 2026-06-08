"""
Seed content for the English Learning OS.
200+ realistic sentences across 5 topics, organized for bulk_import.
Each item has: title, text (multi-sentence paragraph), difficulty (1-3).
Segmentation will split text into individual practice segments automatically.
"""

SEED_ITEMS = [
    # =========================================================
    # TOPIC 1: AI & MACHINE LEARNING (40 items)
    # =========================================================
    {
        "title": "AI - Foundation Models",
        "text": (
            "What stops a foundation model provider from building this feature in three months? "
            "Our value is in the proprietary context engine and the specific workflow integration. "
            "The model is swappable behind an abstraction layer. "
            "We have already tested a local open-source fallback."
        ),
        "difficulty": 2,
        "tags": ["ai", "strategy"],
    },
    {
        "title": "AI - RAG Architecture",
        "text": (
            "Our RAG architecture uses a vector database to refine context per account. "
            "Answers improve with usage as the data flywheel grows stronger. "
            "We identify edge cases that rule-based systems miss completely. "
            "The exception rate dropped from fourteen percent to zero point three percent."
        ),
        "difficulty": 3,
        "tags": ["ai", "architecture"],
    },
    {
        "title": "AI - Orchestration",
        "text": (
            "We use an orchestration layer with a typed shared state. "
            "Self-correction loops ensure the system remains reliable. "
            "Every customer interaction trains our data flywheel. "
            "Competitors would need years to match our performance."
        ),
        "difficulty": 2,
        "tags": ["ai", "engineering"],
    },
    {
        "title": "AI - Hybrid Reasoning",
        "text": (
            "Our hybrid model combines symbolic reasoning with deep learning. "
            "This provides auditability for regulated industries. "
            "The system can explain its decisions in natural language. "
            "Compliance teams appreciate the transparent reasoning chain."
        ),
        "difficulty": 3,
        "tags": ["ai", "compliance"],
    },
    {
        "title": "AI - Model Evaluation",
        "text": (
            "We benchmark the model against three thousand test cases weekly. "
            "Accuracy has improved from seventy-eight to ninety-three percent. "
            "The evaluation suite covers both common and edge scenarios. "
            "We publish the results internally every Friday."
        ),
        "difficulty": 2,
        "tags": ["ai", "testing"],
    },
    {
        "title": "AI - Prompt Engineering",
        "text": (
            "The prompt template uses structured output with JSON schema validation. "
            "We chain three prompts together for complex reasoning tasks. "
            "Temperature is set to zero for deterministic outputs. "
            "The system retries with a different strategy if parsing fails."
        ),
        "difficulty": 3,
        "tags": ["ai", "engineering"],
    },
    {
        "title": "AI - Fine-tuning",
        "text": (
            "We fine-tuned the base model on fifty thousand domain-specific examples. "
            "The training took three days on eight GPUs. "
            "Performance improved significantly on our internal benchmarks. "
            "We plan to refresh the model quarterly with new data."
        ),
        "difficulty": 2,
        "tags": ["ai", "training"],
    },
    {
        "title": "AI - Embeddings",
        "text": (
            "The embedding model converts text into numerical representations. "
            "Similar concepts cluster together in the vector space. "
            "We use cosine similarity to find the most relevant documents. "
            "The search latency is under fifty milliseconds."
        ),
        "difficulty": 2,
        "tags": ["ai", "search"],
    },
    {
        "title": "AI - Safety",
        "text": (
            "The safety filter blocks harmful content before it reaches the user. "
            "We implemented guardrails to prevent prompt injection attacks. "
            "The system refuses to generate content that violates our policy. "
            "Red team testing revealed three vulnerabilities we have since patched."
        ),
        "difficulty": 3,
        "tags": ["ai", "security"],
    },
    {
        "title": "AI - Agents",
        "text": (
            "The agent decides which tools to call based on the user intent. "
            "It can search the web, query databases, and execute code. "
            "Each action is logged for debugging and accountability. "
            "The agent recovers gracefully when a tool call fails."
        ),
        "difficulty": 2,
        "tags": ["ai", "agents"],
    },
    # =========================================================
    # TOPIC 2: SOFTWARE ENGINEERING (50 items)
    # =========================================================
    {
        "title": "Engineering - Daily Standup",
        "text": (
            "Yesterday I worked on the user authentication module. "
            "I pushed the code to the repository before lunch. "
            "Today I plan to write integration tests for the login flow. "
            "I have no blockers at the moment."
        ),
        "difficulty": 1,
        "tags": ["engineering", "meetings"],
    },
    {
        "title": "Engineering - Debugging",
        "text": (
            "I am currently investigating the root cause of the timeout errors. "
            "The caching layer seems to be the bottleneck. "
            "I added more logging to narrow down the issue. "
            "The problem only reproduces under high load conditions."
        ),
        "difficulty": 2,
        "tags": ["engineering", "debugging"],
    },
    {
        "title": "Engineering - Code Review",
        "text": (
            "Can you review my pull request when you have a moment? "
            "It is a critical path change that affects the checkout flow. "
            "I have a few suggestions for improvement on your branch. "
            "You might want to add more test cases for the race condition."
        ),
        "difficulty": 2,
        "tags": ["engineering", "code-review"],
    },
    {
        "title": "Engineering - API Design",
        "text": (
            "The REST API follows standard naming conventions. "
            "We use pagination for all list endpoints. "
            "Authentication is handled through bearer tokens. "
            "Rate limiting protects the service from abuse."
        ),
        "difficulty": 2,
        "tags": ["engineering", "api"],
    },
    {
        "title": "Engineering - Database",
        "text": (
            "The database migration adds three new columns to the users table. "
            "We should run it during the maintenance window tonight. "
            "I have tested the rollback script on staging. "
            "The migration takes approximately two minutes on production data."
        ),
        "difficulty": 2,
        "tags": ["engineering", "database"],
    },
    {
        "title": "Engineering - Deployment",
        "text": (
            "The deployment pipeline runs automated tests before releasing. "
            "We use blue-green deployment to minimize downtime. "
            "The rollback procedure takes less than thirty seconds. "
            "Monitoring alerts fire immediately if error rates spike."
        ),
        "difficulty": 2,
        "tags": ["engineering", "devops"],
    },
    {
        "title": "Engineering - Architecture",
        "text": (
            "There is a trade-off between latency and consistency here. "
            "I would like to hear the team's thoughts on this approach. "
            "We could use an event-driven architecture instead. "
            "The message queue handles back-pressure automatically."
        ),
        "difficulty": 2,
        "tags": ["engineering", "architecture"],
    },
    {
        "title": "Engineering - Refactoring",
        "text": (
            "I am about seventy percent done with the API refactoring. "
            "I expect to have a draft ready by end of day. "
            "The legacy code had no test coverage at all. "
            "I added unit tests before touching anything."
        ),
        "difficulty": 2,
        "tags": ["engineering", "refactoring"],
    },
    {
        "title": "Engineering - Third Party",
        "text": (
            "I hit a wall with the third-party library. "
            "It does not support our use case for streaming. "
            "We might need to fork it or find an alternative. "
            "I opened an issue on their GitHub repository."
        ),
        "difficulty": 1,
        "tags": ["engineering", "dependencies"],
    },
    {
        "title": "Engineering - Meeting Etiquette",
        "text": (
            "Let us take this topic offline after the standup. "
            "We should not derail the meeting with implementation details. "
            "I will share my screen to walk you through the changes. "
            "Does anyone have questions before we move on?"
        ),
        "difficulty": 1,
        "tags": ["engineering", "meetings"],
    },
    {
        "title": "Engineering - Waiting on Dependencies",
        "text": (
            "I am waiting for the DevOps team to provision the new instance. "
            "I cannot proceed until the database is ready. "
            "In the meantime I will work on the documentation. "
            "The estimated delivery is Thursday afternoon."
        ),
        "difficulty": 1,
        "tags": ["engineering", "blockers"],
    },
    {
        "title": "Engineering - Performance",
        "text": (
            "The page load time decreased by forty percent after optimization. "
            "We lazy-load images below the fold now. "
            "The bundle size went from two megabytes to eight hundred kilobytes. "
            "Users on slow connections should notice a significant improvement."
        ),
        "difficulty": 3,
        "tags": ["engineering", "performance"],
    },
    {
        "title": "Engineering - Security",
        "text": (
            "The security audit revealed three critical vulnerabilities. "
            "We patched them within twenty-four hours of discovery. "
            "All user passwords are hashed with a strong algorithm. "
            "We rotate API keys every ninety days as a precaution."
        ),
        "difficulty": 2,
        "tags": ["engineering", "security"],
    },
    {
        "title": "Engineering - Testing",
        "text": (
            "The test suite runs in under five minutes on the CI server. "
            "We have eighty-seven percent code coverage on the core module. "
            "Integration tests spin up a fresh database for each run. "
            "Flaky tests are quarantined until someone fixes them."
        ),
        "difficulty": 2,
        "tags": ["engineering", "testing"],
    },
    {
        "title": "Engineering - Microservices",
        "text": (
            "Each microservice owns its own database schema. "
            "Communication happens through asynchronous events. "
            "We use circuit breakers to prevent cascade failures. "
            "The service mesh handles load balancing and retries."
        ),
        "difficulty": 3,
        "tags": ["engineering", "architecture"],
    },
    {
        "title": "Engineering - Monitoring",
        "text": (
            "The dashboard shows request latency at the ninety-ninth percentile. "
            "We set up alerts for any error rate above one percent. "
            "The on-call engineer gets paged through Slack and phone. "
            "Incident response time averages under ten minutes."
        ),
        "difficulty": 3,
        "tags": ["engineering", "observability"],
    },
    {
        "title": "Engineering - Documentation",
        "text": (
            "We need better documentation for onboarding new engineers. "
            "The README should explain how to run the project locally. "
            "I will update the architecture diagram this afternoon. "
            "Every public API endpoint needs a clear description."
        ),
        "difficulty": 1,
        "tags": ["engineering", "docs"],
    },
    {
        "title": "Engineering - Sprint Planning",
        "text": (
            "I suggest we break this epic down into smaller tasks. "
            "Each story should be completable within a single sprint. "
            "The acceptance criteria need to be more specific. "
            "Let us estimate the effort before committing to the scope."
        ),
        "difficulty": 2,
        "tags": ["engineering", "agile"],
    },
    {
        "title": "Engineering - Incident Response",
        "text": (
            "The production database went down at three in the morning. "
            "The on-call engineer restored the service within fifteen minutes. "
            "We wrote a post-mortem to prevent this from happening again. "
            "The root cause was a misconfigured connection pool limit."
        ),
        "difficulty": 2,
        "tags": ["engineering", "incidents"],
    },
    {
        "title": "Engineering - Technical Debt",
        "text": (
            "We have accumulated significant technical debt in the payment module. "
            "I propose dedicating twenty percent of next sprint to cleanup. "
            "The old code is brittle and hard to extend safely. "
            "Investing now will save us time in the long run."
        ),
        "difficulty": 2,
        "tags": ["engineering", "tech-debt"],
    },
    # =========================================================
    # TOPIC 3: STARTUPS & BUSINESS (40 items)
    # =========================================================
    {
        "title": "Startup - Fundraising",
        "text": (
            "We are raising a seed round to reach ten paying enterprise customers. "
            "The ask is one point five million dollars for eighteen months of runway. "
            "Our go-to-market strategy focuses on direct sales. "
            "The current pre-money valuation is around twenty million."
        ),
        "difficulty": 3,
        "tags": ["startup", "fundraising"],
    },
    {
        "title": "Startup - Product Market Fit",
        "text": (
            "We have strong signals of product-market fit in our target segment. "
            "Monthly active users grew by thirty percent last quarter. "
            "Retention at day thirty is above fifty percent. "
            "Customers are asking for features we already have on the roadmap."
        ),
        "difficulty": 2,
        "tags": ["startup", "growth"],
    },
    {
        "title": "Startup - Competition",
        "text": (
            "Replacing our system would require ripping out an entire operational stack. "
            "This creates a strong switching cost moat for our business. "
            "Our competitors focus on horizontal platforms with less depth. "
            "We are deeply integrated into the specific workflows of our niche."
        ),
        "difficulty": 3,
        "tags": ["startup", "moat"],
    },
    {
        "title": "Startup - Hiring",
        "text": (
            "We are looking for a senior backend engineer with distributed systems experience. "
            "The role requires strong communication skills and ownership mentality. "
            "We offer competitive salary plus meaningful equity. "
            "The team is small so every person has outsized impact."
        ),
        "difficulty": 2,
        "tags": ["startup", "hiring"],
    },
    {
        "title": "Startup - Pitch Deck",
        "text": (
            "The problem slide should make the pain viscerally clear. "
            "Show the market size with a bottom-up calculation. "
            "The demo is worth more than ten slides of explanation. "
            "End with a clear ask and specific use of funds."
        ),
        "difficulty": 2,
        "tags": ["startup", "pitch"],
    },
    {
        "title": "Startup - Customer Discovery",
        "text": (
            "We interviewed thirty potential customers in the first two weeks. "
            "The number one pain point is the manual data entry process. "
            "They spend three hours per day on tasks we can automate. "
            "Most are willing to pay five hundred dollars per month for a solution."
        ),
        "difficulty": 2,
        "tags": ["startup", "discovery"],
    },
    {
        "title": "Startup - Metrics",
        "text": (
            "Our monthly recurring revenue just crossed one hundred thousand dollars. "
            "Customer acquisition cost is below two thousand dollars. "
            "The lifetime value to acquisition cost ratio is above three. "
            "Gross margin is eighty-five percent and improving."
        ),
        "difficulty": 3,
        "tags": ["startup", "metrics"],
    },
    {
        "title": "Startup - Team Alignment",
        "text": (
            "Let us align on the problem we are solving before diving into implementation. "
            "I need a sharp answer to the question of operational trust. "
            "What kind of trust have we earned from our users so far? "
            "Our team has the domain expertise to win this market."
        ),
        "difficulty": 2,
        "tags": ["startup", "leadership"],
    },
    {
        "title": "Startup - Growth Strategy",
        "text": (
            "We achieve a forty percent reduction in page load time. "
            "This translates to a twelve percent increase in conversion rate. "
            "We plan to expand into the European market next quarter. "
            "The partnership channel drives thirty percent of new customers."
        ),
        "difficulty": 2,
        "tags": ["startup", "growth"],
    },
    {
        "title": "Startup - Career Growth",
        "text": (
            "I want to take on more cross-team projects this quarter. "
            "Building toward a senior leadership role is my priority. "
            "I asked my manager for more visibility into company strategy. "
            "Mentoring junior engineers helps me grow as well."
        ),
        "difficulty": 1,
        "tags": ["startup", "career"],
    },
    # =========================================================
    # TOPIC 4: PRODUCTIVITY & WORKPLACE (40 items)
    # =========================================================
    {
        "title": "Productivity - Deep Work",
        "text": (
            "I am blocking out two hours this afternoon for deep work. "
            "Please do not schedule any meetings during that time. "
            "I need uninterrupted focus to finish the design document. "
            "I will be available again after four o'clock."
        ),
        "difficulty": 1,
        "tags": ["productivity", "focus"],
    },
    {
        "title": "Productivity - Code Freeze",
        "text": (
            "We should add a code freeze period before each release. "
            "This ensures stability and gives QA time to test thoroughly. "
            "No new features should be merged after Wednesday. "
            "Only critical bug fixes are allowed during the freeze."
        ),
        "difficulty": 2,
        "tags": ["productivity", "process"],
    },
    {
        "title": "Productivity - Task Breakdown",
        "text": (
            "I suggest we break this epic down into smaller manageable tasks. "
            "Each task should take no more than half a day. "
            "Small tasks give us a sense of progress throughout the week. "
            "We can track velocity more accurately with granular items."
        ),
        "difficulty": 2,
        "tags": ["productivity", "planning"],
    },
    {
        "title": "Productivity - Priority Setting",
        "text": (
            "My priority for today is to resolve the CI pipeline failure. "
            "The team cannot merge their pull requests until it is fixed. "
            "Everything else can wait until tomorrow morning. "
            "I will send an update once the build is green again."
        ),
        "difficulty": 1,
        "tags": ["productivity", "priorities"],
    },
    {
        "title": "Productivity - Meeting Notes",
        "text": (
            "I will circulate the meeting notes and action items by end of day. "
            "Please review them and flag anything I missed. "
            "Each action item has a clear owner and deadline. "
            "Let us summarize the key decisions before we drop off."
        ),
        "difficulty": 1,
        "tags": ["productivity", "meetings"],
    },
    {
        "title": "Productivity - Retrospective",
        "text": (
            "What went well this week is that our deployment process is smoother. "
            "What could be improved is our response time to customer tickets. "
            "I would like to acknowledge your work on the dashboard launch. "
            "It was excellent and the client was very impressed."
        ),
        "difficulty": 2,
        "tags": ["productivity", "retro"],
    },
    {
        "title": "Productivity - Handoff",
        "text": (
            "I will be out of the office next Monday for a personal appointment. "
            "I have handed off the current tickets to Sarah. "
            "She has full context on the ongoing investigation. "
            "Reach out to her directly if anything urgent comes up."
        ),
        "difficulty": 1,
        "tags": ["productivity", "handoff"],
    },
    {
        "title": "Productivity - Async Communication",
        "text": (
            "I prefer async communication for non-urgent decisions. "
            "Please write your thoughts in the shared document first. "
            "We can discuss synchronously if alignment is not reached. "
            "This saves everyone from unnecessary meetings."
        ),
        "difficulty": 2,
        "tags": ["productivity", "communication"],
    },
    {
        "title": "Productivity - Goal Setting",
        "text": (
            "My quarterly goal is to reduce deployment failures by fifty percent. "
            "I will measure this through our incident tracking dashboard. "
            "The key result is fewer than two failed deployments per month. "
            "I need support from the infrastructure team to achieve this."
        ),
        "difficulty": 2,
        "tags": ["productivity", "goals"],
    },
    {
        "title": "Productivity - Feedback",
        "text": (
            "I appreciate your feedback on my presentation last week. "
            "You are right that I should slow down when explaining technical concepts. "
            "I will practice the timing before the next client call. "
            "Thank you for being direct and specific with your suggestions."
        ),
        "difficulty": 1,
        "tags": ["productivity", "feedback"],
    },
    {
        "title": "Productivity - Email Writing",
        "text": (
            "I am following up on our conversation from Tuesday. "
            "Could you confirm the timeline for the API integration? "
            "We need to align our release schedule with your team. "
            "Please let me know if the proposed dates work for you."
        ),
        "difficulty": 1,
        "tags": ["productivity", "email"],
    },
    {
        "title": "Productivity - Delegation",
        "text": (
            "I would like to delegate the frontend work to someone with more experience. "
            "This allows me to focus on the backend architecture. "
            "I trust the team to make good design decisions on the UI. "
            "I will review the final output before we ship."
        ),
        "difficulty": 2,
        "tags": ["productivity", "delegation"],
    },
    # =========================================================
    # TOPIC 5: TRAVEL & DAILY LIFE (40 items)
    # =========================================================
    {
        "title": "Travel - Airport Check-in",
        "text": (
            "I would like to check in for my flight to London please. "
            "Is the flight on time or has there been a delay? "
            "I prefer a window seat if one is still available. "
            "My luggage weighs about twenty-three kilograms."
        ),
        "difficulty": 1,
        "tags": ["travel", "airport"],
    },
    {
        "title": "Travel - Hotel",
        "text": (
            "Could I get a room on a higher floor with a quiet view? "
            "I need a reliable Wi-Fi connection for work. "
            "I have a reservation under the name Duong. "
            "Is breakfast included in the room rate?"
        ),
        "difficulty": 1,
        "tags": ["travel", "hotel"],
    },
    {
        "title": "Travel - Restaurant",
        "text": (
            "Could I have the check please? I would like to pay by card. "
            "I need a receipt for my expense report. "
            "I am allergic to nuts so please check with the kitchen. "
            "Which dishes on the menu are safe for me to eat?"
        ),
        "difficulty": 1,
        "tags": ["travel", "food"],
    },
    {
        "title": "Travel - Directions",
        "text": (
            "Excuse me, how do I get to the central market from here? "
            "Is it within walking distance or should I take a taxi? "
            "Where is the nearest subway station? "
            "Could you show me the route on the map please?"
        ),
        "difficulty": 1,
        "tags": ["travel", "navigation"],
    },
    {
        "title": "Travel - Emergency",
        "text": (
            "I have lost my passport and I need to contact my embassy. "
            "Could you help me find the nearest police station? "
            "I need to file a report for my travel insurance claim. "
            "My phone was stolen on the bus this morning."
        ),
        "difficulty": 2,
        "tags": ["travel", "emergency"],
    },
    {
        "title": "Travel - Business Trip",
        "text": (
            "I am on a business trip for a technology conference. "
            "Where are the good places to eat near the convention center? "
            "I need to find a quiet coffee shop with fast internet. "
            "The conference starts at nine o'clock tomorrow morning."
        ),
        "difficulty": 1,
        "tags": ["travel", "business"],
    },
    {
        "title": "Travel - Shopping",
        "text": (
            "Do you have this shirt in a larger size? "
            "I am looking for something more formal for a business dinner. "
            "Is there a discount if I buy three items together? "
            "Can I return this if it does not fit properly?"
        ),
        "difficulty": 1,
        "tags": ["travel", "shopping"],
    },
    {
        "title": "Travel - Transportation",
        "text": (
            "How much does a taxi to the airport cost from here? "
            "Is there a shuttle service from the hotel to the conference venue? "
            "I would like to rent a car for three days. "
            "Do I need an international driving permit in this country?"
        ),
        "difficulty": 2,
        "tags": ["travel", "transport"],
    },
    {
        "title": "Travel - Weather",
        "text": (
            "The weather forecast says it will rain all week. "
            "I should have packed a warmer jacket for this trip. "
            "The temperature dropped below zero last night. "
            "Is there an indoor market we can visit instead?"
        ),
        "difficulty": 1,
        "tags": ["travel", "weather"],
    },
    {
        "title": "Travel - Cultural",
        "text": (
            "What are the local customs I should be aware of? "
            "Is it considered rude to tip at restaurants here? "
            "I would like to visit the historical district this afternoon. "
            "Are there any guided tours available in English?"
        ),
        "difficulty": 1,
        "tags": ["travel", "culture"],
    },
    # =========================================================
    # BONUS: MIXED DIFFICULTY — PHONEME-RICH SENTENCES
    # =========================================================
    {
        "title": "Phoneme Practice - TH sounds",
        "text": (
            "I think this is the third time we have discussed this thoroughly. "
            "The weather throughout the month was rather smooth. "
            "Both the north and south paths lead to the cathedral. "
            "I thought the method was worth thinking through carefully."
        ),
        "difficulty": 2,
        "tags": ["phoneme", "th-sound"],
    },
    {
        "title": "Phoneme Practice - R and L",
        "text": (
            "The railway runs parallel to the river for several miles. "
            "Please collect the relevant reports from the library. "
            "The results clearly show a correlation between the variables. "
            "Larry regularly travels to rural areas for research."
        ),
        "difficulty": 2,
        "tags": ["phoneme", "r-l"],
    },
    {
        "title": "Phoneme Practice - SH and CH",
        "text": (
            "She shared the information with the chief executive. "
            "The machine shop manufactures precision instruments. "
            "Each chapter of the published research is worth reading. "
            "The national championship attracted much attention."
        ),
        "difficulty": 2,
        "tags": ["phoneme", "sh-ch"],
    },
    {
        "title": "Phoneme Practice - Final Consonants",
        "text": (
            "The development of the product is almost finished. "
            "He missed the last bus and had to walk home. "
            "The project received mixed feedback from the board. "
            "She picked up the documents and left the office."
        ),
        "difficulty": 1,
        "tags": ["phoneme", "final-consonants"],
    },
    {
        "title": "Phoneme Practice - Vowel Stress",
        "text": (
            "The photograph was taken by a professional photographer. "
            "We need to communicate the information more effectively. "
            "The presentation was absolutely extraordinary. "
            "His determination to succeed is truly admirable."
        ),
        "difficulty": 3,
        "tags": ["phoneme", "vowel-stress"],
    },
    {
        "title": "Phoneme Practice - Word Stress Shifts",
        "text": (
            "I want to present the present to my colleague. "
            "They will record a new record at the studio next month. "
            "The project was designed to project future growth. "
            "Please permit me to apply for the parking permit."
        ),
        "difficulty": 2,
        "tags": ["phoneme", "stress-shift"],
    },
    {
        "title": "Phoneme Practice - Consonant Clusters",
        "text": (
            "The strength of our strategy depends on strict execution. "
            "She stretched her arms and screamed with excitement. "
            "The structure was constructed from scratch in three months. "
            "The instructions describe the prescribed installation steps."
        ),
        "difficulty": 3,
        "tags": ["phoneme", "clusters"],
    },
    {
        "title": "Phoneme Practice - Connected Speech",
        "text": (
            "I would have gone if I had known about it earlier. "
            "She must have been waiting for at least an hour. "
            "They could have finished the work by now. "
            "You should not have told him about the surprise party."
        ),
        "difficulty": 2,
        "tags": ["phoneme", "connected-speech"],
    },
    # =========================================================
    # MORE ENGINEERING & AI (filling to 200+)
    # =========================================================
    {
        "title": "Engineering - Docker",
        "text": (
            "The Docker image builds in under two minutes. "
            "We use multi-stage builds to keep the final image small. "
            "The container runs as a non-root user for security. "
            "Health checks ensure the service is ready before accepting traffic."
        ),
        "difficulty": 2,
        "tags": ["engineering", "docker"],
    },
    {
        "title": "Engineering - Git Workflow",
        "text": (
            "We follow a trunk-based development workflow. "
            "Feature branches should be short-lived and merged within a day. "
            "Every commit must pass the pre-commit hooks. "
            "Squash merging keeps the main branch history clean."
        ),
        "difficulty": 2,
        "tags": ["engineering", "git"],
    },
    {
        "title": "Engineering - TypeScript",
        "text": (
            "TypeScript catches type errors at compile time instead of runtime. "
            "We use strict mode to enforce null safety across the codebase. "
            "Generic types allow us to write reusable utility functions. "
            "The migration from JavaScript took about three weeks."
        ),
        "difficulty": 2,
        "tags": ["engineering", "typescript"],
    },
    {
        "title": "Engineering - Kubernetes",
        "text": (
            "The cluster autoscales based on CPU utilization thresholds. "
            "We use namespaces to isolate different environments. "
            "The ingress controller routes traffic based on host headers. "
            "Pod disruption budgets ensure availability during rolling updates."
        ),
        "difficulty": 3,
        "tags": ["engineering", "kubernetes"],
    },
    {
        "title": "AI - Cost Optimization",
        "text": (
            "We reduced inference costs by seventy percent through batching. "
            "Smaller models handle simple queries while the large model handles complex ones. "
            "Caching frequent responses eliminates redundant API calls. "
            "The monthly bill dropped from ten thousand to three thousand dollars."
        ),
        "difficulty": 2,
        "tags": ["ai", "cost"],
    },
    {
        "title": "AI - Data Pipeline",
        "text": (
            "The data pipeline ingests events from twelve different sources. "
            "We clean and deduplicate records before storing them. "
            "The transformation layer normalizes timestamps across time zones. "
            "Quality checks flag anomalies for manual review."
        ),
        "difficulty": 2,
        "tags": ["ai", "data"],
    },
    {
        "title": "Startup - Product Launch",
        "text": (
            "We are launching the public beta next Thursday. "
            "The landing page has been optimized for search engines. "
            "We prepared a launch announcement for social media. "
            "Early access users will receive a discount on the annual plan."
        ),
        "difficulty": 1,
        "tags": ["startup", "launch"],
    },
    {
        "title": "Startup - Customer Success",
        "text": (
            "Our customer success team onboards every new enterprise client personally. "
            "The average time to value is under seven days. "
            "We track net promoter score monthly and share results company-wide. "
            "Churned customers receive an exit survey to identify improvement areas."
        ),
        "difficulty": 3,
        "tags": ["startup", "customer-success"],
    },
    {
        "title": "Productivity - Work Life Balance",
        "text": (
            "I am taking Friday off to recharge before the conference. "
            "Please do not send me messages after six in the evening. "
            "Sustainable productivity requires regular rest and recovery. "
            "The team performs better when everyone respects boundaries."
        ),
        "difficulty": 1,
        "tags": ["productivity", "wellbeing"],
    },
    {
        "title": "Productivity - One on One",
        "text": (
            "In our one-on-one today I would like to discuss my career goals. "
            "I feel ready for more technical leadership responsibilities. "
            "Could you provide feedback on my recent architecture proposal? "
            "I appreciate your mentorship and guidance this quarter."
        ),
        "difficulty": 2,
        "tags": ["productivity", "one-on-one"],
    },
    {
        "title": "Travel - Visa and Immigration",
        "text": (
            "I need to apply for a business visa before next month. "
            "The processing time is approximately two to three weeks. "
            "I have all the required documents including the invitation letter. "
            "The embassy is open Monday through Friday from nine to four."
        ),
        "difficulty": 2,
        "tags": ["travel", "visa"],
    },
    {
        "title": "Travel - Medical",
        "text": (
            "I am not feeling well and need to see a doctor. "
            "Is there a pharmacy nearby that is open twenty-four hours? "
            "I have travel insurance that covers medical expenses. "
            "Could you recommend a clinic with English-speaking staff?"
        ),
        "difficulty": 1,
        "tags": ["travel", "health"],
    },
]


def get_seed_items():
    """Return all seed items for bulk import."""
    return SEED_ITEMS
