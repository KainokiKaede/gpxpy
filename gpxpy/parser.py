# -*- coding: utf-8 -*-

# Copyright 2011 Tomo Krajina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging as mod_logging
import re as mod_re

try:
    import lxml.etree as mod_etree  # Load LXML or fallback to cET or ET
except ImportError:
    try:
        import xml.etree.cElementTree as mod_etree
    except ImportError:
        import xml.etree.ElementTree as mod_etree

from . import gpx as mod_gpx
from . import utils as mod_utils
from . import gpxfield as mod_gpxfield

log = mod_logging.getLogger(__name__)

class GPXParser:
    """
    Parse the XML and provide new GPX instance.

    Methods:
        __init__: initialize new instance
        init: format XML
        parse: parse XML, build tree, build GPX

    Attributes:
        gpx: GPX instance of the most recently parsed XML
        xml: string containing the XML text

    """

    def __init__(self, xml_or_file=None):
        """
        Initialize new GPXParser instance.

        Arguments:
            xml_or_file: string or file object containing the gpx
                formatted xml

        """
        self.init(xml_or_file)
        self.gpx = mod_gpx.GPX()

    def init(self, xml_or_file):
        """
        Store the XML and remove utf-8 Byte Order Mark if present.

        Args:
            xml_or_file: string or file object containing the gpx
                formatted xml

        """
        text = xml_or_file.read() if hasattr(xml_or_file, 'read') else xml_or_file
        self.xml = mod_utils.make_str(text)

    def parse(self, version=None):
        """
        Parse the XML and return a GPX object.

        Args:
            version: str or None indicating the GPX Schema to use.
                Options are '1.0', '1.1' and None. When version is None
                the version is read from the file or falls back on 1.0.

        Returns:
            A GPX object loaded from the xml

        Raises:
            GPXXMLSyntaxException: XML file is invalid
            GPXException: XML is valid but GPX data contains errors

        """
        # Build prefix map for reserialization and extension handlings
        for namespace in mod_re.findall(r'\sxmlns:?[^=]*="[^"]+"', self.xml):
            prefix, _, URI = namespace[6:].partition('=')
            prefix = prefix.lstrip(':')
            if prefix == '':
                prefix = 'defaultns'  # alias default for easier handling
            else:
                if prefix.startswith("ns"):
                    mod_etree.register_namespace("noglobal_" + prefix, URI.strip('"'))
                else:
                    mod_etree.register_namespace(prefix, URI.strip('"'))
            self.gpx.nsmap[prefix] = URI.strip('"')

        # Remove default namespace to simplify processing later
        # TODO: change regex to accept ' also
        self.xml = mod_re.sub(r'\sxmlns="[^"]+"', '', self.xml, count=1)

        # Build tree
        try:
            if GPXParser.__library() == "LXML":
                # lxml does not like unicode strings when it's expecting
                # UTF-8. Also, XML comments result in a callable .tag().
                # Strip them out to avoid handling them later.
                if mod_utils.PYTHON_VERSION[0] >= '3':
                    self.xml = self.xml.encode('utf-8')
                root = mod_etree.XML(self.xml,
                                     mod_etree.XMLParser(remove_comments=True))
            else:
                root = mod_etree.XML(self.xml)

        except Exception as e:
            # The exception here can be a lxml or ElementTree exception.
            log.debug('Error in:\n%s\n-----------\n' % self.xml, exc_info=True)

            # The library should work in the same way regardless of the
            # underlying XML parser that's why the exception thrown
            # here is GPXXMLSyntaxException (instead of simply throwing the
            # original ElementTree or lxml exception e).
            #
            # But, if the user needs the original exception (lxml or ElementTree)
            # it is available with GPXXMLSyntaxException.original_exception:
            raise mod_gpx.GPXXMLSyntaxException('Error parsing XML: %s' % str(e), e)

        if root is None:
            raise mod_gpx.GPXException('Document must have a `gpx` root node.')

        if version is None:
            version = root.get('version')

        mod_gpxfield.gpx_fields_from_xml(self.gpx, root, version)
        return self.gpx

    @staticmethod
    def __library():
        """
        Return the underlying ETree.

        Provided for convenient unittests.
        """
        if "lxml" in str(mod_etree):
            return "LXML"
        return "STDLIB"
