"""Local evidence selection and validated-result reuse. No model calls here."""
import hashlib
import json
import math
import re
from pathlib import Path

VERSION = "evidence-v1"
COUNT_METHOD = "utf8_bytes_div_3_estimate"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def count_tokens(text):
    """Explicit estimate, not an exact model tokenizer or provider usage."""
    return math.ceil(len(text.encode("utf-8")) / 3)


def measurement(text):
    return {"tokens": count_tokens(text), "bytes": len(text.encode("utf-8")),
            "method": COUNT_METHOD, "exact": False}


# Selection keeps introduction plus every paragraph with qualifications. If those
# alone exceed the budget, the article is not safe to compress automatically.
QUALIFICATION = re.compile(
    r"\b(?:however|limitation\w*|except|only|not|cannot|can't|restricted|"
    r"preview|beta|availability|available|rollout|roll.out|pricing|cost|"
    r"risk\w*|caveat\w*|may|might|require\w*)\b", re.I)
RELEVANCE = re.compile(
    r"\b(?:announc\w*|launch\w*|releas\w*|model|agent\w*|API|"
    r"improv\w*|evaluat\w*|benchmark\w*|develop\w*)\b", re.I)


def packet_for(article, limit=1200, mode="compact"):
    paragraphs = [dict(p) for p in article.get("paragraphs", [])
                  if isinstance(p.get("text"), str) and p["text"].strip()]
    if not paragraphs:
        raise ValueError("missing_article_text")
    if len({p["id"] for p in paragraphs}) != len(paragraphs):
        raise ValueError("duplicate_paragraph_ids")
    base = {"article_id": article["article_id"], "title": article["title"],
            "published_at": article["published_at"]}
    if mode == "full":
        return dict(base, evidence=paragraphs)
    required = {0}
    required.update(i for i, p in enumerate(paragraphs)
                    if QUALIFICATION.search(p["text"]))
    selected = set(required)
    def size(indices):
        return count_tokens(canonical([paragraphs[i] for i in sorted(indices)]))
    if size(selected) > limit:
        raise ValueError("essential_evidence_exceeds_budget")
    priority = sorted((i for i in range(len(paragraphs)) if i not in selected),
                      key=lambda i: (-len(RELEVANCE.findall(paragraphs[i]["text"])), i))
    # Do not fill the context just because space remains: choose at most three
    # additional topical paragraphs, avoiding long low-information background.
    extras = 0
    for i in priority:
        if extras >= 3 or not RELEVANCE.search(paragraphs[i]["text"]):
            continue
        if size(selected | {i}) <= limit:
            selected.add(i)
            extras += 1
    return dict(base, evidence=[paragraphs[i] for i in sorted(selected)])


def cache_key(article, packet, identity, prompt_hash, schema_hash):
    return fingerprint({
        "version": VERSION, "url": article["url"],
        "published_at": article["published_at"],
        "date_precision": article.get("date_precision"),
        "content_hash": article["content_hash"], "packet": packet,
        "parser_version": article.get("parser_version", "source-v1"),
        "identity": identity, "prompt_hash": prompt_hash, "schema_hash": schema_hash,
        "audience": "CS student", "language": "English"})


class SummaryCache:
    def __init__(self, directory):
        self.directory = Path(directory)
        if self.directory.is_symlink():
            raise ValueError("unsafe_cache_path")
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, key):
        if not re.fullmatch(r"[0-9a-f]{64}", key):
            raise ValueError("invalid_cache_key")
        path = self.directory / (key + ".json")
        if path.is_symlink():
            raise ValueError("unsafe_cache_entry")
        return path

    def get(self, key):
        path = self._path(key)
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(record, dict) and record.get("key") == key and record.get("validated") is True:
                return record["item"]
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return None

    def put(self, key, item):
        path = self._path(key)
        temporary = path.with_suffix(".tmp")
        if temporary.is_symlink():
            raise ValueError("unsafe_cache_entry")
        temporary.write_text(canonical({"key": key, "validated": True, "item": item}),
                             encoding="utf-8")
        temporary.replace(path)
