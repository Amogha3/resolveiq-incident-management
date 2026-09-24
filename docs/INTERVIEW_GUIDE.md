# Interview and demo guide — v2

## Explain it in 30 seconds

ResolveIQ is an incident investigation workspace built with React, FastAPI, and SQLite. It has authenticated team roles, explainable log analysis, and TF-IDF retrieval of previous resolutions. A background monitor checks a separate local checkout service, creates incidents after repeated HTTP failures, and records recovery. Optional local Ollama explanations help interpret matched evidence; the core system does not depend on an LLM.

Say that the service and incidents are synthetic. The monitoring HTTP requests are real, but this is not a real company deployment. Mention AI assistance honestly when asked how you developed it.

## Five-minute demonstration

1. Sign in as Admin; show the team role table.
2. In a separate Incognito window, sign in as Viewer and demonstrate read-only access.
3. Back as Admin, open Live monitoring. Show Up status and HTTP 200 checks.
4. Trigger database failure, wait for two probes, and open the generated incident.
5. Explain the matched log evidence, hypothesis, and similar historical resolution.
6. Restore the service. Wait for Up, reopen the incident, assign an engineer, add a verification note, and resolve.
7. Show Activity, export JSON, refresh, and demonstrate persistence.
8. If you installed a local model, request an explanation and discuss why it still needs review. Otherwise state that optional integration is disabled.

## Questions you should answer

- Why are session tokens hashed in the database? Why are passwords hashed with scrypt rather than encrypted?
- What does CSRF protection do, and why is HttpOnly alone insufficient?
- How do API permissions differ from disabling a frontend button?
- Why are roles checked on every request? What happens when an admin deactivates an account?
- Why does monitoring wait for two failures? How are duplicate incidents prevented?
- What happens when a service recovers? Why is closure a human step?
- How does an incident version prevent one engineer from overwriting another engineer's changes?
- Why is the monitored URL fixed? What would arbitrary URL support require?
- What is TF-IDF cosine similarity, and why isn't 80% similarity 80% accuracy?
- What does the AI receive? Can it execute a repair? Can you trust its citations?
- Why is SQLite appropriate here, and what changes are needed for a larger deployed team?
- How would you evaluate retrieval with a held-out labeled dataset rather than repeating the seed cases?

## Resume bullet after you understand and demonstrate the code

Developed ResolveIQ, a React/FastAPI incident workspace with role-based access, SQLite persistence, evidence-linked log analysis, TF-IDF incident retrieval, and background HTTP monitoring with failure deduplication and recovery tracking.

Mention optional local LLM integration only after you have enabled and demonstrated it yourself. Do not call the detector a trained ML model or claim an unmeasured reduction in downtime.

## Next engineering improvements

- Add a new DNS rule, including a false-positive example and a test.
- Compare TF-IDF against an embedding baseline on separately labeled data.
- Add bounded pagination and performance measurements on larger incident collections.
- Design authenticated remote probes, TLS hosting, backup/restore, and MFA before public deployment.
