import os
import sys
import time
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional, Generator

from paa.tools import retryable
from paa.parser import (
    extract_related_questions,
    get_featured_snippet_parser,
)
from paa.exceptions import (
    GoogleSearchRequestFailedError,
    RelatedQuestionParserError,
    FeaturedSnippetParserError
)
from paa.tools import CallingSemaphore

from useragent import UserAgent
from proxy import Proxy

logging.basicConfig()

class Google:
    def __init__(self, header):
        self.URL = "https://www.google.com/search"
        self.HEADERS = {
            'User-Agent': header
        }
        self.proxy = Proxy()
        self.PROXIES = {
            'http': 'http://' + self.proxy.getProxy(),
            'https': 'http://' + self.proxy.getProxy(),
        }
        self.SESSION = requests.Session()
        self.NB_TIMES_RETRY = 3
        self.NB_REQUESTS_LIMIT = os.environ.get(
            "RELATED_QUESTION_NBREQUESTS_LIMIT", 25
        )
        self.NB_REQUESTS_DURATION_LIMIT = os.environ.get(
            "RELATED_QUESTION_DURATION_LIMIT", 60  # seconds
        )
        self.semaphore = CallingSemaphore(
            self.NB_REQUESTS_LIMIT, self.NB_REQUESTS_DURATION_LIMIT
        )

    @retryable(1)
    def search(self, keyword: str) -> Optional[BeautifulSoup]:
        """return html parser of google search result"""
        params = {"q": keyword, "gl": "us"}
        try:
            with self.semaphore:
                time.sleep(0.5)
                response = self.SESSION.get(self.URL, params=params, headers=self.HEADERS, proxies=self.PROXIES, timeout=3)
        except Exception:
            Exception
            #import traceback
            #traceback.print_exc()
            #raise GoogleSearchRequestFailedError(self.URL, keyword)
        #if response.status_code != 200:
            #print(response.content)
            #raise GoogleSearchRequestFailedError(self.URL, keyword)
        return BeautifulSoup(response.text, "html.parser")


    def _get_related_questions(self, text: str) -> List[str]:
        """
        return a list of questions related to text.
        These questions are from search result of text
        :param str text: text to search
        """
        document = self.search(text)
        if not document:
            return []
        try:
            return extract_related_questions(document)
        except Exception:
            raise RelatedQuestionParserError(text)


    def generate_related_questions(self, text: str) -> Generator[str, None, None]:
        """
        generate the questions related to text,
        these quetions are found recursively
        :param str text: text to search
        """
        questions = set(self._get_related_questions(text))
        searched_text = set(text)
        while questions:
            text = questions.pop()
            yield text
            searched_text.add(text)
            questions |= set(self._get_related_questions(text))
            questions -= searched_text


    def get_related_questions(self, text: str, max_nb_questions: Optional[int] = None):
        """
        return a number of questions related to text.
        These questions are found recursively.
        :param str text: text to search
        """
        if max_nb_questions is None:
            return self._get_related_questions(text)
        nb_question_regenerated = 0
        questions = set()
        for question in self.generate_related_questions(text):
            if nb_question_regenerated > max_nb_questions:
                break
            questions.add(question)
            nb_question_regenerated += 1
        return list(questions)


    def get_answer(self, question: str) -> Dict[str, Any]:
        """
        return a dictionary as answer for a question.
        :param str question: asked question
        """
        document = self.search(question)
        related_questions = extract_related_questions(document)
        featured_snippet = get_featured_snippet_parser(
                question, document)
        if not featured_snippet:
            res = dict(
                has_answer=False,
                question=question,
                related_questions=related_questions,
            )
        else:
            res = dict(
                has_answer=True,
                question=question,
                related_questions=related_questions,
            )
            try:
                res.update(featured_snippet.to_dict())
            except Exception:
                raise FeaturedSnippetParserError(question)
        return res


    def generate_answer(self, text: str) -> Generator[dict, None, None]:
        """
        generate answers of questions related to text
        :param str text: text to search
        """
        answer = self.get_answer(text)
        questions = set(answer["related_questions"])
        searched_text = set(text)
        if answer["has_answer"]:
            yield answer
        while questions:
            text = questions.pop()
            answer = self.get_answer(text)
            if answer["has_answer"]:
                yield answer
            searched_text.add(text)
            questions |= set(self.get_answer(text)["related_questions"])
            questions -= searched_text


    def get_simple_answer(self, question: str, depth: bool = False) -> str:
        """
        return a text as summary answer for the question
        :param str question: asked quetion
        :param bool depth: return the answer of first related question
            if no answer found for question
        """
        document = self.search(question)
        featured_snippet = get_featured_snippet_parser(
                question, document)
        if featured_snippet:
            return featured_snippet.response
        if depth:
            related_questions = self.get_related_questions(question)
            if not related_questions:
                return ""
            return self.get_simple_answer(related_questions[0])
        return ""


    if __name__ == "__main__":
        from pprint import pprint as print
        print(get_answer(sys.argv[1]))