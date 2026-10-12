"""
Configurable text cleaning pipeline.

Each cleaning step is a small, independently testable pure function. The
pipeline itself is just an ordered list of which steps to apply — this is
what "configurable preprocessing pipeline" means in practice: callers pick
a `CleaningConfig`, not a hardcoded sequence.
"""

import html
import re
import unicodedata
from dataclasses import dataclass

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
_MENTION_PATTERN = re.compile(r"@\w+")
_HASHTAG_PATTERN = re.compile(r"#(\w+)")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # symbols, pictographs, emoji blocks
    "\U00002600-\U000027BF"  # misc symbols & dingbats
    "\U0001F1E6-\U0001F1FF"  # regional indicators (flags)
    "]+",
    flags=re.UNICODE,
)


@dataclass
class CleaningConfig:
    normalize_unicode: bool = True
    remove_html: bool = True
    normalize_whitespace: bool = True
    handle_urls: str = "replace"  # "replace" | "remove" | "keep"
    handle_mentions: str = "replace"  # "replace" | "remove" | "keep"
    handle_hashtags: str = "unwrap"  # "unwrap" (#nlp -> nlp) | "remove" | "keep"
    handle_emoji: str = "remove"  # "remove" | "keep"


class TextCleaner:
    def clean(self, text: str, config: CleaningConfig = CleaningConfig()) -> str:
        result = text

        if config.remove_html:
            result = html.unescape(result)
            result = _HTML_TAG_PATTERN.sub(" ", result)

        if config.normalize_unicode:
            # NFKC folds visually-identical characters (full-width digits,
            # ligatures, etc.) to a canonical form — the single most
            # common source of silent duplicate-looking-different text.
            result = unicodedata.normalize("NFKC", result)

        if config.handle_urls == "replace":
            result = _URL_PATTERN.sub(" [URL] ", result)
        elif config.handle_urls == "remove":
            result = _URL_PATTERN.sub(" ", result)

        if config.handle_mentions == "replace":
            result = _MENTION_PATTERN.sub(" [MENTION] ", result)
        elif config.handle_mentions == "remove":
            result = _MENTION_PATTERN.sub(" ", result)

        if config.handle_hashtags == "unwrap":
            result = _HASHTAG_PATTERN.sub(r"\1", result)
        elif config.handle_hashtags == "remove":
            result = _HASHTAG_PATTERN.sub(" ", result)

        if config.handle_emoji == "remove":
            result = _EMOJI_PATTERN.sub(" ", result)

        if config.normalize_whitespace:
            result = _WHITESPACE_PATTERN.sub(" ", result).strip()

        return result


text_cleaner = TextCleaner()
