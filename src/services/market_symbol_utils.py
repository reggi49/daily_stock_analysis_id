# -*- coding: utf-8 -*-
"""Shared market-symbol helpers for suffix-only offshore markets.

Keep this module dependency-light so it can be used by data providers, market
context, trading calendars, stock-index loading, and API input normalization
without introducing import cycles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SuffixMarketSpec:
    """A suffix-only Yahoo Finance market rule.

    A base is accepted when it is all digits with a length in ``digit_lengths``
    OR all letters with a length in ``alpha_lengths``. Digit-based markets
    (CN offshore listings, JP/KR/TW) use ``digit_lengths``; alphabetic markets
    such as Indonesia (IDX, ``.JK``) use ``alpha_lengths``.
    """

    market: str
    suffixes: tuple[str, ...]
    digit_lengths: tuple[int, ...] = ()
    alpha_lengths: tuple[int, ...] = ()


_SUFFIX_MARKET_SPECS: tuple[SuffixMarketSpec, ...] = (
    SuffixMarketSpec("jp", ("T",), (4, 5)),
    SuffixMarketSpec("kr", ("KS", "KQ"), (6,)),
    # Taiwan support mirrors the same suffix-only pattern; keep it here so the
    # shared helpers stay complete for all yfinance-only offshore markets.
    SuffixMarketSpec("tw", ("TW", "TWO"), (4, 5, 6)),
    # Indonesia (IDX / Bursa Efek Indonesia). Yahoo Finance lists Indonesian
    # equities with the `.JK` suffix and alphabetic tickers, e.g. BBCA.JK,
    # TLKM.JK, GOTO.JK. IDX tickers are 4 letters in practice; allow 2-5 to
    # stay resilient without introducing ambiguity (the `.JK` suffix is
    # required for detection).
    SuffixMarketSpec("id", ("JK",), alpha_lengths=(2, 3, 4, 5)),
)

_MARKET_TO_SPEC = {spec.market: spec for spec in _SUFFIX_MARKET_SPECS}
_SUFFIX_TO_SPEC = {
    suffix: spec
    for spec in _SUFFIX_MARKET_SPECS
    for suffix in spec.suffixes
}


def _base_matches_spec(base: str, spec: SuffixMarketSpec) -> bool:
    """Return True when ``base`` is a valid ticker body for ``spec``."""

    if base.isdigit() and len(base) in spec.digit_lengths:
        return True
    if base.isalpha() and len(base) in spec.alpha_lengths:
        return True
    return False


def split_suffix_symbol(stock_code: str) -> tuple[str, str] | None:
    """Return ``(base, suffix)`` for dotted symbols, upper-cased and stripped."""

    code = (stock_code or "").strip().upper()
    if "." not in code:
        return None
    base, suffix = code.rsplit(".", 1)
    if not base or not suffix:
        return None
    return base, suffix


def get_suffix_market(stock_code: str) -> Optional[str]:
    """Return jp/kr/tw/id for supported suffix-only Yahoo symbols, else None."""

    parts = split_suffix_symbol(stock_code)
    if parts is None:
        return None
    base, suffix = parts
    spec = _SUFFIX_TO_SPEC.get(suffix)
    if spec is None:
        return None
    if not _base_matches_spec(base, spec):
        return None
    return spec.market


def is_suffix_market_symbol(stock_code: str, market: Optional[str] = None) -> bool:
    """Return whether a stock code is a supported suffix-only Yahoo symbol."""

    detected = get_suffix_market(stock_code)
    if market is None:
        return detected is not None
    return detected == (market or "").strip().lower()


def is_jp_suffix_symbol(stock_code: str) -> bool:
    return is_suffix_market_symbol(stock_code, "jp")


def is_kr_suffix_symbol(stock_code: str) -> bool:
    return is_suffix_market_symbol(stock_code, "kr")


def is_tw_suffix_symbol(stock_code: str) -> bool:
    return is_suffix_market_symbol(stock_code, "tw")


def is_id_suffix_symbol(stock_code: str) -> bool:
    return is_suffix_market_symbol(stock_code, "id")


def normalize_suffix_market_symbol(stock_code: str) -> Optional[str]:
    """Normalize supported suffix-only symbols to upper-case Yahoo form."""

    parts = split_suffix_symbol(stock_code)
    if parts is None:
        return None
    base, suffix = parts
    if get_suffix_market(f"{base}.{suffix}") is None:
        return None
    return f"{base}.{suffix}"


def suffix_base_lookup_allowed(canonical_code: str) -> bool:
    """Return True when a suffix-market code may be resolved from its bare base.

    JP/KR intentionally allow stock-index-backed bare-code lookup to support the
    existing MVP behavior. TW/ID remain strict suffix-only: TW because its
    follow-up index work is not part of this issue, ID because Indonesian tickers are
    alphabetic and only unambiguous with the `.JK` suffix.
    """

    return get_suffix_market(canonical_code) in {"jp", "kr"}


def market_suffixes(market: str) -> tuple[str, ...]:
    spec = _MARKET_TO_SPEC.get((market or "").strip().lower())
    return spec.suffixes if spec else ()
