"""Deterministic log evidence and TF-IDF retrieval; no LLM or external calls."""
import math
import re
from collections import Counter

RULES = [
    {"id": "database", "name": "Database connection failure", "pattern": r"ECONNREFUSED|connection refused|too many connections|connection pool exhausted",
     "cause": "The service may be unable to reach its database, or the connection pool may be exhausted.",
     "steps": ["Check the database host and port against the application configuration.", "Verify database health and connectivity from the application environment.", "Inspect pool usage and connection leaks before changing limits."],
     "verify": "Repeat the failed request and confirm the database query succeeds without new connection errors."},
    {"id": "memory", "name": "Memory exhaustion", "pattern": r"OutOfMemoryError|MemoryError|heap out of memory|OOMKilled",
     "cause": "The process may have exceeded its memory limit or retained too many objects.",
     "steps": ["Inspect memory usage around the failure and check the process limit.", "Look for large batches, unbounded caches, or objects retained across requests.", "Reproduce with a smaller workload and compare memory profiles."],
     "verify": "Repeat the workload and confirm stable memory use with no process restart."},
    {"id": "timeout", "name": "Upstream timeout", "pattern": r"ETIMEDOUT|ReadTimeout|connect timeout|request timed out|upstream timed out|gateway timeout",
     "cause": "An upstream dependency may be too slow or unreachable; the log alone cannot establish why.",
     "steps": ["Identify the upstream endpoint and compare its response latency with the timeout.", "Check dependency health, network connectivity, and recent changes.", "Use bounded retries with backoff only for safe, idempotent operations."],
     "verify": "Repeat a representative request and confirm response time is below the configured timeout."},
    {"id": "auth", "name": "Authentication failure", "pattern": r"invalid token|token expired|expired token|Unauthorized|authentication failed",
     "cause": "The request may contain an expired, invalid, or missing credential.",
     "steps": ["Check credential expiry, issuer, and intended audience without exposing the credential.", "Verify service clock synchronization and authentication configuration.", "Renew the credential through the approved login or secret-management flow."],
     "verify": "Confirm an authorized request succeeds and an invalid credential is still rejected."},
    {"id": "disk", "name": "Disk capacity exhausted", "pattern": r"ENOSPC|No space left on device|disk full",
     "cause": "The filesystem may have run out of space or available inodes.",
     "steps": ["Inspect filesystem capacity and inode usage.", "Identify growing logs, temporary files, and retention configuration.", "Archive or rotate approved disposable files; do not delete application data blindly."],
     "verify": "Confirm available capacity and repeat the failed write operation."},
]

def redact(text: str) -> str:
    text = re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/-]+=*", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)((?:password|passwd|api[_-]?key|access[_-]?token|secret)\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]", text)
    return text

def analyze(logs: str) -> dict:
    lines = logs.splitlines()
    findings = []
    for rule in RULES:
        evidence = [{"line": i + 1, "text": line} for i, line in enumerate(lines)
                    if re.search(rule["pattern"], line, re.I)]
        if evidence:
            findings.append({k: v for k, v in rule.items() if k != "pattern"} |
                            {"evidence": evidence[:20], "matched_lines": len(evidence)})
    error_lines = sum(bool(re.search(r"\b(error|fatal|critical|exception)\b", line, re.I)) for line in lines)
    return {"method": "Pattern rules + TF-IDF cosine similarity", "line_count": len(lines),
            "error_lines": error_lines, "findings": findings,
            "summary": f"{len(findings)} possible failure pattern(s) found." if findings else
            "No supported failure pattern found. Inspect the logs manually; absence of a match does not mean the service is healthy."}

STOP = {"the", "and", "for", "with", "from", "this", "that", "info", "error", "warn", "debug"}
def tokens(text):
    return [w for w in re.findall(r"[a-z][a-z0-9_]{2,}", text.lower()) if w not in STOP]

def retrieve(query: str, candidates: list, limit=3):
    """Fit IDF on candidate incidents only; cosine score is not a probability."""
    documents = [tokens(f"{x['title']} {x['description']} {x['logs']}") for x in candidates]
    if not documents:
        return []
    df = Counter(w for d in documents for w in set(d))
    idf = {w: math.log((1 + len(documents)) / (1 + count)) + 1 for w, count in df.items()}
    def vector(words):
        counts = Counter(words)
        return {w: (1 + math.log(n)) * idf[w] for w, n in counts.items() if w in idf}
    q = vector(tokens(query))
    qnorm = math.sqrt(sum(v*v for v in q.values()))
    result = []
    for item, words in zip(candidates, documents):
        v = vector(words)
        denom = qnorm * math.sqrt(sum(x*x for x in v.values()))
        score = sum(value*v.get(w, 0) for w, value in q.items()) / denom if denom else 0
        if score >= 0.08:
            result.append({"id": item["id"], "title": item["title"], "score": round(score, 4), "resolution": item["resolution"]})
    return sorted(result, key=lambda x: (-x["score"], x["id"]))[:limit]
