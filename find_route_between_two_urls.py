import logging
from typing import List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from nltk import download, tokenize

download('punkt')
logging.basicConfig(
    filename='logs.txt', filemode='a', encoding='utf-8', level=logging.INFO,
)


class RouteFinder(object):
    """Finder can help with search a route between two urls."""

    parser_type = 'html.parser'
    http_timeout = 30

    def __init__(self, from_url: str, to_url: str, max_depth: int = 3) -> None:
        """Create route finder.

        Args:
            from_url: is the first url from which the search starts.
            to_url: is the last url where the search ends.
            max_depth: is the maximum search depth.
        """
        self._from_url = from_url
        self._to_url = to_url
        self._max_depth = max_depth
        self._base_url = self._get_base_url()
        self._sentences = {}
        self._stack = [(self._from_url, [])]
        self._visited = set()

    def find_route(self) -> str:
        """Find route between two urls.

        Returns:
            str: description how to find route from the first url to
                the last one.
        """
        while self._stack:
            url, route = self._stack.pop()
            if url == self._to_url:
                break
            if url in self._visited or len(route) == self._max_depth:
                continue
            self._visited.add(url)
            self._visit_url(url, route)
        return self._restore_route(route)

    def _get_base_url(self) -> str:
        parsed = urlparse(self._from_url)
        return f'{parsed.scheme}://{parsed.hostname}'

    def _visit_url(self, url: str, route: List[str]) -> None:
        logging.info(f'Visited the {url} URL...')
        html = requests.get(url, timeout=self.http_timeout).content
        soup = BeautifulSoup(html, self.parser_type)
        for nested_url in soup.find_all('a', href=True, string=True):
            href = nested_url.attrs['href']
            parent = nested_url.parent
            if not (href.startswith('/wiki/') and parent.name == 'p'):
                continue
            try:
                sentence = self._get_sentence(nested_url)
            except ValueError:
                continue
            full_nested_url = f'{self._base_url}{href}'
            self._stack.append((full_nested_url, route + [full_nested_url]))
            self._sentences.setdefault(full_nested_url, sentence)

    @staticmethod
    def _get_sentence(node: Tag) -> str:
        text = node.get_text()
        parent_sentences = tokenize.sent_tokenize(node.parent.get_text())
        for sentece in parent_sentences:
            if text in sentece:
                return sentece
        logging.error(
            f"Child text wasn't found in the parent text: {parent_sentences};"
            + f'child text: {text}!',
        )
        raise ValueError("Child text wasn't found in the parent text!")

    def _restore_route(self, urls: List[str]) -> str:
        return '\n\n'.join(
            f'#{index}\n{self._sentences.get(url)}\n{url}'
            for index, url in enumerate(urls, start=1)
        )


if __name__ == '__main__':
    from_url = input('Input the URL from where you want to find the route: ')
    to_url = input('Input the URL where you want to get to: ')
    finder = RouteFinder(from_url, to_url)
    print(finder.find_route())
