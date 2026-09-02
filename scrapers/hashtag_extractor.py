"""
Hashtag extractor — pulls #hashtags from scraped post captions.
Writes frequency data to the hashtag_tracking table.
"""

import re
import logging
from collections import Counter
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def extract_hashtags(text: str) -> List[str]:
    """Extract all #hashtags from a text string, lowercased."""
    if not text:
        return []
    return [tag.lower() for tag in re.findall(r'#(\w+)', text)]


def extract_hashtags_from_captions(
    captions: List[str],
) -> Dict[str, int]:
    """
    Given a list of caption strings, return a Counter-like dict
    of {hashtag: frequency} across all captions.
    """
    all_tags: List[str] = []
    for caption in captions:
        all_tags.extend(extract_hashtags(caption))
    return dict(Counter(all_tags))


def extract_hashtags_from_raw_data(raw_data: dict) -> Dict[str, int]:
    """
    Extract hashtags from a ScraperResult's raw_data dict.
    Looks for 'captions' key containing a list of strings.
    """
    captions = raw_data.get("captions", [])
    return extract_hashtags_from_captions(captions)
