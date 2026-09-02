"""
Content idea templates organized by format type.

Each template has placeholder slots filled from trending data.
These produce structured idea skeletons, not publish-ready copy.
"""

from typing import Dict, List
import random

# ── Static Post Templates ────────────────────────────────────────────
STATIC_TEMPLATES: List[Dict[str, str]] = [
    {
        "hook": "Did you know? {stat_or_fact} — and most SMEs in the GCC still aren't leveraging {topic}.",
        "body": "• The problem: {pain_point}\n• Why it matters: {why_it_matters}\n• What leading companies do differently: {solution_hint}\n• How {topic} solves this at scale",
        "cta": "Comment 'READY' if you want to see how this works for your business 👇",
    },
    {
        "hook": "Stop doing {old_way}. Start doing {topic} instead.",
        "body": "• The old way costs you {cost_point}\n• {topic} changes the game because {reason}\n• Real results: {result_claim}\n• 3 steps to get started today",
        "cta": "Save this post and share it with someone who needs to hear this 🔖",
    },
    {
        "hook": "3 signs your business needs {topic} (yesterday).",
        "body": "• Sign 1: {sign_1}\n• Sign 2: {sign_2}\n• Sign 3: {sign_3}\n• The fix: How {topic} automates what's slowing you down",
        "cta": "DM us 'AUDIT' for a free assessment of your workflow 📩",
    },
    {
        "hook": "We analyzed 50+ SMEs using {topic} — here's what we found.",
        "body": "• {stat_1}\n• {stat_2}\n• The #1 mistake businesses make with {topic}\n• What the top 10% do differently",
        "cta": "Follow us for more insights like this. Link in bio for the full breakdown.",
    },
]

# ── Carousel Templates ───────────────────────────────────────────────
CAROUSEL_TEMPLATES: List[Dict[str, str]] = [
    {
        "hook": "The Ultimate Guide to {topic} for SMEs in 2025 🧵",
        "body": "Slide 1 (Cover): {topic} — Everything You Need to Know\nSlide 2: What is {topic}?\nSlide 3: Why SMEs need it now\nSlide 4: Top 3 use cases\nSlide 5: Common mistakes to avoid\nSlide 6: Getting started checklist\nSlide 7 (CTA): Ready to implement?",
        "cta": "Save this carousel and send it to your team. Follow for Part 2!",
    },
    {
        "hook": "{topic}: Before vs After for your business 📊",
        "body": "Slide 1 (Cover): The {topic} Transformation\nSlide 2: Before — manual processes, slow response, high costs\nSlide 3: After — automated workflows, instant response, lower costs\nSlide 4: Case study snapshot\nSlide 5: 5 quick wins with {topic}\nSlide 6 (CTA): Your turn",
        "cta": "Book a free demo → Link in bio",
    },
    {
        "hook": "5 ways {topic} is transforming businesses in UAE, KSA & Egypt 🌍",
        "body": "Slide 1 (Cover): {topic} Across the GCC\nSlide 2: Way #1 — {use_case_1}\nSlide 3: Way #2 — {use_case_2}\nSlide 4: Way #3 — {use_case_3}\nSlide 5: Way #4 — {use_case_4}\nSlide 6: Way #5 — {use_case_5}\nSlide 7 (CTA): Which one does your business need?",
        "cta": "Comment your pick below! We'll send you a tailored resource 👇",
    },
]

# ── Short-Form Video Templates ───────────────────────────────────────
SHORT_FORM_TEMPLATES: List[Dict[str, str]] = [
    {
        "hook": "POV: Your business just automated {task} with {topic} 🤯 (0-3s)",
        "body": "• Problem setup (3-5s): Show the manual pain\n• The 'aha' moment (5-10s): {topic} in action\n• Result reveal (10-15s): Time saved, cost reduced\n• Quick demo or screen recording (15-25s)",
        "cta": "Follow for more {topic} tips. Link in bio for a free trial.",
    },
    {
        "hook": "This is how {topic} works in 30 seconds ⚡ (0-3s)",
        "body": "• What it does (3-8s): One-sentence explanation\n• Live demo (8-20s): Screen capture of the workflow\n• Results (20-25s): What you get at the end",
        "cta": "Want to try it? Comment 'DEMO' and we'll set you up 🚀",
    },
    {
        "hook": "The {topic} hack that nobody talks about 👀 (0-3s)",
        "body": "• Setup context (3-7s): Why this matters\n• The hack explained (7-18s): Step-by-step walkthrough\n• The result (18-25s): Before/after comparison",
        "cta": "Share this with someone who needs to see it 📤",
    },
]

# ── Long-Form Video Templates ────────────────────────────────────────
LONG_FORM_TEMPLATES: List[Dict[str, str]] = [
    {
        "hook": "Complete Guide: How to Set Up {topic} for Your Business [Tutorial]",
        "body": "• Intro (0-1 min): What we'll cover and why\n• Section 1 (1-4 min): Understanding {topic} fundamentals\n• Section 2 (4-8 min): Step-by-step implementation\n• Section 3 (8-11 min): Advanced tips and common pitfalls\n• Recap (11-12 min): Summary checklist",
        "cta": "Subscribe + hit the bell for weekly {topic} tutorials. Download the checklist from the description.",
    },
    {
        "hook": "{topic} in 2025: What Changed and What You Need to Know",
        "body": "• Intro (0-1 min): State of {topic} in 2025\n• Section 1 (1-4 min): Key changes and new capabilities\n• Section 2 (4-7 min): Impact on SMEs in UAE/KSA/Egypt\n• Section 3 (7-10 min): Actionable steps for your business\n• Recap (10-12 min): Top takeaways",
        "cta": "Let us know in the comments: which feature excites you most? Don't forget to subscribe.",
    },
]

# ── Instagram Story Templates ────────────────────────────────────────
STORY_TEMPLATES: List[Dict[str, str]] = [
    {
        "hook": "Quick Poll: Do you use {topic} in your business?",
        "body": "Story 1: Poll — Yes / No / What is that?\nStory 2: The answer reveal + quick stat\nStory 3: One tip to get started",
        "cta": "Swipe up / tap link for our free guide",
    },
    {
        "hook": "🧠 Did you know this about {topic}?",
        "body": "Story 1: Surprising fact or stat\nStory 2: Why it matters for your business\nStory 3: Quick tip",
        "cta": "Reply to this story with your biggest challenge",
    },
    {
        "hook": "This or That: {topic} Edition ⚡",
        "body": "Story 1: Option A vs Option B (interactive slider)\nStory 2: The winner + why\nStory 3: How to implement the winner",
        "cta": "DM us for a personalized recommendation",
    },
    {
        "hook": "Ask Me Anything: {topic} 💬",
        "body": "Story 1: Question sticker — 'What do you want to know about {topic}?'\nStory 2: Answer teaser\nStory 3: 'We'll answer the top questions in our next post!'",
        "cta": "Follow us so you don't miss the answers!",
    },
]


def get_templates(format_type: str) -> List[Dict[str, str]]:
    """Return template list for a given format type."""
    mapping = {
        "static": STATIC_TEMPLATES,
        "carousel": CAROUSEL_TEMPLATES,
        "short-form": SHORT_FORM_TEMPLATES,
        "long-form": LONG_FORM_TEMPLATES,
        "story": STORY_TEMPLATES,
    }
    return mapping.get(format_type, STATIC_TEMPLATES)


def fill_template(template: Dict[str, str], topic: str, keyword: str = "") -> Dict[str, str]:
    """
    Fill a template's placeholders with topic and keyword data.
    Unfilled placeholders get generic GCC B2B defaults.
    """
    defaults = {
        "topic": topic,
        "keyword": keyword or topic,
        "stat_or_fact": f"73% of GCC businesses plan to adopt {topic} by 2026",
        "pain_point": f"manual processes that {topic} could automate in minutes",
        "why_it_matters": f"early adopters of {topic} see 40% efficiency gains",
        "solution_hint": f"they use {topic} to automate repetitive tasks",
        "old_way": "handling everything manually",
        "cost_point": "hours of team time every week",
        "reason": "it removes bottlenecks and scales without hiring",
        "result_claim": "SMEs save 15+ hours/week on average",
        "sign_1": "Your team spends more time on admin than on clients",
        "sign_2": "You're losing leads because response time is too slow",
        "sign_3": "Your competitors are already using it",
        "stat_1": "62% reduced customer response time by 80%",
        "stat_2": "45% saw ROI within the first 30 days",
        "task": "customer follow-ups",
        "use_case_1": "Automated customer support",
        "use_case_2": "Lead qualification and routing",
        "use_case_3": "Invoice and document processing",
        "use_case_4": "Social media management",
        "use_case_5": "Sales pipeline automation",
    }

    result = {}
    for key in ("hook", "body", "cta"):
        text = template.get(key, "")
        for placeholder, value in defaults.items():
            text = text.replace(f"{{{placeholder}}}", value)
        result[key] = text

    return result
