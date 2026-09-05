"""Seven async generators. Each builds a prompt, calls the LLM, returns dict."""
from __future__ import annotations

from ai_client import generate_structured


# ---------- per-format schemas ---------------------------------------------


SCHEMA_ADVISORY = {
    "type": "object",
    "properties": {
        "severity": {"type": "string"},
        "affected_systems": {"type": "array", "items": {"type": "string"}},
        "iocs": {"type": "array", "items": {"type": "string"}},
        "action_items": {"type": "array", "items": {"type": "string"}},
        "references": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "severity",
        "affected_systems",
        "iocs",
        "action_items",
        "references",
    ],
}

SCHEMA_INFOGRAPHIC = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
        "layout": {"type": "string"},
        "color_scheme": {"type": "string"},
        "call_to_action": {"type": "string"},
    },
    "required": ["title", "key_points", "layout", "color_scheme", "call_to_action"],
}

SCHEMA_EXEC = {
    "type": "object",
    "properties": {
        "risk_level": {"type": "string"},
        "business_impact": {"type": "string"},
        "timeline": {"type": "string"},
        "recommendations": {"type": "array", "items": {"type": "string"}},
        "decision_needed": {"type": "string"},
    },
    "required": [
        "risk_level",
        "business_impact",
        "timeline",
        "recommendations",
        "decision_needed",
    ],
}

SCHEMA_PRESENTATION = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "slides": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["heading", "bullets"],
            },
        },
        "speaker_notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "slides", "speaker_notes"],
}

SCHEMA_LINKEDIN = {
    "type": "object",
    "properties": {
        "hook": {"type": "string"},
        "body": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "cta": {"type": "string"},
    },
    "required": ["hook", "body", "hashtags", "cta"],
}

SCHEMA_TWITTER = {
    "type": "object",
    "properties": {
        "thread": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tweet": {"type": "string"},
                    "media_suggestion": {"type": "string"},
                },
                "required": ["tweet", "media_suggestion"],
            },
        },
    },
    "required": ["thread"],
}

SCHEMA_VIDEO = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "script": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp": {"type": "string"},
                    "visual": {"type": "string"},
                    "description": {"type": "string"},
                    "narration": {"type": "string"},
                },
                "required": ["timestamp", "visual", "narration"],
            },
        },
    },
    "required": ["title", "script", "scenes"],
}


# ---------- prompt helpers -------------------------------------------------


def _ctx(params: dict) -> str:
    return (
        f"Audience: {params.get('audience', 'general')}. "
        f"Tone: {params.get('tone', 'formal')}. "
        f"Detail: {params.get('detail', 'medium')}. "
        f"Objective: {params.get('objective', 'inform')}. "
        f"Language: {params.get('language', 'en')}."
    )


def _schema_brief(schema: dict) -> str:
    """Render a schema as 'field: type, ...' so the LLM returns exactly those keys."""
    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
    req = set(schema.get("required", []) or [])
    parts = []
    for name, sub in props.items():
        t = sub.get("type", "string") if isinstance(sub, dict) else "string"
        if t == "array":
            item = sub.get("items", {}) if isinstance(sub, dict) else {}
            it = item.get("type", "string") if isinstance(item, dict) else "string"
            t = f"array of {it}"
        elif t == "object":
            t = "object"
        parts.append(f"{name}: {t}{'' if name in req else ' (optional)'}")
    return ", ".join(parts)


def _fmt_prompt(instruction: str, schema: dict, params: dict, source_text: str) -> str:
    return (
        f"{instruction}\n"
        f"Context: {_ctx(params)}\n"
        f"Return a FLAT JSON object with EXACTLY these fields: {_schema_brief(schema)}\n"
        "Do NOT wrap the JSON in a parent key. Do NOT include prose or markdown fences.\n\n"
        f"SOURCE:\n{source_text[:6000]}"
    )


# ---------- 7 generator functions -----------------------------------------


async def generate_advisory(source_text: str, params: dict) -> dict:
    prompt = _fmt_prompt(
        "Produce a structured security advisory from the source.",
        SCHEMA_ADVISORY, params, source_text,
    )
    return await generate_structured(prompt, SCHEMA_ADVISORY)


async def generate_infographic(source_text: str, params: dict) -> dict:
    prompt = _fmt_prompt(
        "Produce infographic content (title, key points, layout, palette, CTA).",
        SCHEMA_INFOGRAPHIC, params, source_text,
    )
    return await generate_structured(prompt, SCHEMA_INFOGRAPHIC)


async def generate_exec_summary(source_text: str, params: dict) -> dict:
    prompt = _fmt_prompt(
        "Produce an executive summary (risk, impact, timeline, recs, decision).",
        SCHEMA_EXEC, params, source_text,
    )
    return await generate_structured(prompt, SCHEMA_EXEC)


async def generate_presentation(source_text: str, params: dict) -> dict:
    prompt = _fmt_prompt(
        "Produce a 5-7 slide presentation with speaker notes.",
        SCHEMA_PRESENTATION, params, source_text,
    )
    return await generate_structured(prompt, SCHEMA_PRESENTATION)


async def generate_linkedin(source_text: str, params: dict) -> dict:
    base = _fmt_prompt(
        "Produce a LinkedIn post from the source.",
        SCHEMA_LINKEDIN, params, source_text,
    )
    extra = (
        "\nCONTENT RULES (strict):\n"
        "- `hook`: a single sharp opening line that creates curiosity or tension. Not a summary.\n"
        "- `body`: 4-8 short paragraphs (line-broken). Lead with the insight, not the news. "
        "Add a personal/professional reframe the source doesn't state. Use 1-2 emojis max.\n"
        "- DO NOT copy sentences verbatim from the source. Rephrase and synthesise.\n"
        "- `hashtags`: 4-7, niche + broad mix, no #spam.\n"
        "- `cta`: one short question or prompt that invites comments.\n"
        "- Total body <= 1300 characters."
    )
    return await generate_structured(base + extra, SCHEMA_LINKEDIN)


async def generate_twitter(source_text: str, params: dict) -> dict:
    base = _fmt_prompt(
        "Produce a Twitter/X thread from the source.",
        SCHEMA_TWITTER, params, source_text,
    )
    extra = (
        "\nCONTENT RULES (strict):\n"
        "- Tweet 1 MUST be a hook: a bold, surprising or contrarian angle pulled from the source.\n"
        "- Tweets 2-N MUST add new insight: a takeaway, reframe, consequence, or expert-style observation the source does NOT state explicitly.\n"
        "- Final tweet MUST be a call to action (RT / reply / click link / bookmark).\n"
        "- DO NOT copy sentences from the source verbatim. Rephrase and synthesise.\n"
        "- Each tweet <= 250 characters (strict). Total thread 4-6 tweets.\n"
        "- `media_suggestion` should be an image/infographic/quote-card idea for that tweet (or 'None' if not useful)."
    )
    return await generate_structured(base + extra, SCHEMA_TWITTER)


async def generate_video_package(source_text: str, params: dict) -> dict:
    base = _fmt_prompt(
        "Produce a video package: title, full script, and 5-7 scenes.",
        SCHEMA_VIDEO, params, source_text,
    )
    extra = (
        "\nFor each scene's `timestamp` field, return an MM:SS string "
        "(e.g. \"00:00\", \"00:15\", \"00:30\") in ascending order."
    )
    return await generate_structured(base + extra, SCHEMA_VIDEO)


# ---------- registry ------------------------------------------------------


GENERATORS = {
    "advisory": generate_advisory,
    "infographic": generate_infographic,
    "executive_summary": generate_exec_summary,
    "presentation": generate_presentation,
    "linkedin": generate_linkedin,
    "twitter": generate_twitter,
    "video_package": generate_video_package,
}