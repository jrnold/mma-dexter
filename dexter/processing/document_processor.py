from itertools import chain

from ..models import Document, Entity, db

from .crawlers import MGCrawler
from .extractors import AlchemyExtractor

import logging

class DocumentProcessor:
    log = logging.getLogger(__name__)

    def __init__(self):
        self.crawlers = [MGCrawler()]
        self.extractors = [AlchemyExtractor()]


    def valid_url(self, url):
        """ Is this a URL we can process? """
        return any(c.offer(url) for c in self.crawlers)


    def canonicalise_url(self, url):
        """ Try to canonicalise this url. Strip anchors, etc. """
        for crawler in self.crawlers:
            if crawler.offer(url):
                return crawler.canonicalise_url(url)

        return url


    def process(self, url):
        """ Downloand and process an article at +url+ and return
        a Document instance. """
        doc = Document()
        doc.url = url

        self.crawl(doc)
        self.extract(doc)
        self.reconcile_entities(doc)

        return doc

    def crawl(self, doc):
        """ Run crawlers against a document's URL to fetch its
        content, updating any existing content. """
        for crawler in self.crawlers:
            if crawler.offer(doc.url):
                crawler.crawl(doc)


    def extract(self, doc):
        """ Run extraction routines on a document. """
        for extractor in self.extractors:
            extractor.extract(doc)


    def reconcile_entities(self, doc):
        """
        Reconcile this documents entities with the database.

        For all entities associated with the document, we check
        if it already exists and, if it does, replace
        that entity with the one from the database to prevent it
        from being created.

        Note: if an entity is new and another processor creates it at the same
        time, there is a race condition. The database is left intact and correct,
        but one processor will get a key violation exception.
        """
        entities = Entity.bulk_get((e.group, e.name) for e in chain(
            (de.entity for de in doc.entities),
            (u.entity for u in doc.utterances)))

        # reconcile entities in document with those in the db
        for de in doc.entities:
            de.entity = entities.get(
                    (de.entity.group.lower(), de.entity.name.lower()),
                    de.entity)

        for utterance in doc.utterances:
            utterance.entity = entities.get(
                    (utterance.entity.group.lower(), utterance.entity.name.lower()),
                    utterance.entity)
