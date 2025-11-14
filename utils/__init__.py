"""
Utils package for BKDict application
Contains XML parser and other utility functions
"""

from .xml_parser import VocabularyXMLParser, parse_and_import_xml, XMLParserError

__all__ = ['VocabularyXMLParser', 'parse_and_import_xml', 'XMLParserError']
