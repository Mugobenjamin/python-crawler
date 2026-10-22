from __future__ import annotations

from urllib.robotparser import RobotFileParser


class RobotsPolicy:
    """A thin wrapper around urllib.robotparser with explicit handling of limitations."""

    def __init__(self, user_agent: str = "GoogleSearchCentralDocCrawler/1.0") -> None:
        self.user_agent = user_agent
        self._cache: dict[str, RobotFileParser] = {}

    def can_fetch(self, url: str) -> bool:
        import urllib.parse

        parsed = urllib.parse.urlsplit(url)
        robots_url = urllib.parse.urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
        parser = self._cache.get(robots_url)
        if parser is None:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            try:
                parser.read()
            except Exception:
                parser = None
            self._cache[robots_url] = parser

        if parser is None:
            return True
        return parser.can_fetch(self.user_agent, url)

    def explain_limitations(self) -> str:
        return (
            "urllib.robotparser provides a basic robots.txt check, but it does not handle every nuance of modern bot policy "
            "and cannot evaluate JS-based anti-bot protections or site-specific access restrictions."
        )
