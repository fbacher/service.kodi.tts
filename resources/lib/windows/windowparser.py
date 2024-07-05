# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import copy
import os
import sys
import xml.dom.minidom as minidom
from _ast import List
from pathlib import Path

import xbmc
import xbmcgui
import xbmcvfs

from common.monitor import Monitor
from common.phrases import PhraseList
from gui.base_tags import WindowType
from windows.ui_constants import UIConstants
from windows.window_state_monitor import WinDialog, WinDialogState

USE_LXML: bool = False
try:
    from lxml import etree as lxml_ET
except ImportError:
    USE_LXML = False

import xpath
from common import *
from common.logger import *

import xml.etree.ElementTree as ET

module_logger = BasicLogger.get_module_logger(module_path=__file__)


USE_NEW_FUNCTIONS: Final[bool] = True
USE_OLD_FUNCTIONS: Final[bool] = False
VERBOSE_DEBUG: bool = False
REVERSE_ATTRIB: Final[str] = '__REVERSE__'


def currentWindowXMLFile() -> Path | None:
    """
    Find the path for the current window's xml file. The file may be in one
    of serveral paths.

    :return:
    """
    Monitor.exception_on_abort()
    simple_path: Path = Path(xbmc.getInfoLabel('Window.Property(xmlfile)'))
    skin_path: Path = get_xbmc_skin_path(simple_path)
    possible_paths: Tuple[Path, Path] = simple_path, skin_path
    module_logger.debug(f'simple_path: {simple_path} skin_path: {skin_path} '
                        f'cwd: {Path.cwd()}')
    for path in possible_paths:
        if path.is_file():
            module_logger.debug(f'path_is_file: {path.absolute()}')
            return path.absolute()
    return None


def currentWindowIsAddon():
    path = xbmc.getInfoLabel('Window.Property(xmlfile)')
    if not path:
        return None
    return os.path.exists(path)


def get_xbmc_skin_path(fname) -> Path:
    Monitor.exception_on_abort()
    skin_path: Path
    base_path: Path = Path(xbmcvfs.translatePath('special://skin'))
    for res in ('720p', '1080i'):
        skin_path = base_path / res
        if skin_path.is_file():
            break
    else:
        aspect = xbmc.getInfoLabel('Skin.AspectRatio')
        addonXMLPath: Path = base_path / 'addon.xml'
        skin_path: Path = Path('')
        if addonXMLPath.is_file():
            with open(addonXMLPath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for l in lines:
                if f'aspect="{aspect}"' in l:
                    folder = l.split('folder="', 1)[-1].split('"', 1)[0]
                    skin_path = base_path / folder
    path: Path = skin_path / fname
    if not path.is_file():
        path = Path('')
    if module_logger.isEnabledFor(DEBUG_VERBOSE):
        module_logger.debug_verbose(f'Including: {path}')
    return path


def getInfoLabel(info, container):
    Monitor.exception_on_abort()
    if container:
        info = info.replace(
                'ListItem.', f'Container({container}).ListItem.')
    return xbmc.getInfoLabel(info)


def dump_dom(entries) -> str:
    dom_impl = minidom.getDOMImplementation()
    wrapper = dom_impl.createDocument(None, 'fake_root', None)
    fake_root = wrapper.documentElement
    dump: str | None = None
    if isinstance(entries, list):
        if module_logger.isEnabledFor(DEBUG_VERBOSE):
            module_logger.debug_verbose(f'list of DOM entries len: {len(entries)}')
        for x in entries:
            fake_root.appendChild(x)
    else:
        # fake_root.appendChild(entries)
        dump = entries.toprettyxml(newl='')
    if dump is None:
        dump: str = fake_root.toprettyxml(newl='')

    return dump


def dump_subtree(entry: ET.Element) -> str:
    xmlstr: str = ''
    try:
        if entry is None:
            return 'None'
        xmlstr = ET.tostring(entry, encoding='unicode')
        xmlstr = ET.canonicalize(xml_data=xmlstr, strip_text=True)
        mini_something = minidom.parseString(xmlstr)
        xmlstr = mini_something.toprettyxml(indent="   ")
    except AbortException:
        reraise(*sys.exc_info())
    except Exception as e:
        xmlstr = ''
    return xmlstr

# Compiler wants global flag (?i) at beginning
# tagRE = re.compile(r'\[/?(?:B|I|COLOR|UPPERCASE|LOWERCASE)[^\]]*\](?i)')

def nodeParents(dom, node) -> List[Any] | None:
    parents = []
    Monitor.exception_on_abort()
    try:
        parent = xpath.findnode('..', node)
        while parent and not isinstance(parent, minidom.Document):
            parents.append(parent)
            parent = xpath.findnode('..', parent)
        return parents
    except AbortException:
        reraise(*sys.exc_info())
    except Exception:
        module_logger.exception('')
        return None


def new_get_ancestors(dom: ET.ElementTree, node: ET.Element) -> List[ET.Element]:
    parents: List[ET.Element] = []
    parent: ET.Element = node.find('..')
    while parent is not None:
        parents.append(parent)
        next_parent = parent.find("..")
        if module_logger.isEnabledFor(DEBUG_EXTRA_VERBOSE):
            module_logger.debug_extra_verbose(f'parent: {parent}'
                                              f' parent_new: {next_parent}')
        parent = next_parent
    return parents


def lxml_get_ancestors(dom: lxml_ET.ElementTree,
                       node: lxml_ET.Element) -> List[lxml_ET.Element]:
    new_parents: List[lxml_ET.Element] = []
    new_parent: lxml_ET.Element = node.getparent()
    while new_parent is not None:
        new_parents.append(new_parent)
        new_parent = new_parent.getparent()
        #  module_logger.debug_verbose(f'parent: {parent} parent_new: {parent_new}')
    return new_parents


def extractInfos(text, container):
    Monitor.exception_on_abort()
    pos = 0
    while pos > -1:
        pos = text.find('$INFO[')
        if pos < 0:
            break
        lbracket = pos + 6
        i = lbracket
        depth = 1
        for c in text[pos + 6:]:
            if c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
            if depth < 1:
                break
            i += 1
        middle = text[lbracket:i]

        parts = middle.split(',')
        if len(parts) > 2:
            info = getInfoLabel(parts[0], container)
            if info:
                middle = parts[1] + info + parts[2]
            else:
                middle = ''
        elif len(parts) > 1:
            info = getInfoLabel(parts[0], container)
            if info:
                middle = parts[1] + info
            else:
                middle = ''
        else:
            middle = getInfoLabel(middle, container)

        if middle:
            middle += '... '
        text = text[:pos] + middle + text[i + 1:]
    return text.strip(' .')


class WindowParser:
    """
    Each Window is represented by an .xml document. Each .xml document
    is a tree of Elements (xml.etree.ElementTree). Each has its own
    top-level root Element.
    """
    _logger: BasicLogger = None
    includes: ForwardRef('Includes') = None
    forest_map: Dict[str, Dict[ET.Element, ET.Element]] = {}

    def __init__(self, xml_path: Path):
        clz = type(self)
        self.xml_path = xml_path
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        clz._logger.debug(f'Parsing: {xml_path}')
        self.current_window_path: Path = xml_path
        if USE_OLD_FUNCTIONS:
            self.xml = minidom.parse(str(xml_path))
        if USE_LXML:
            self.lxml_includes_xml: lxml_ET.ElementTree = lxml_ET.parse(xml_path)
            self.lxml_root: lxml_ET.Element = self.lxml_includes_xml.getroot()
        self.et_includes_xml: ET.ElementTree = ET.parse(xml_path)
        self.et_root: ET.Element = self.et_includes_xml.getroot()
        #  clz._logger.debug(f'window_type: {dump_subtree(self.et_root)}')
        self.build_reverse_tree_map(self.et_root, xml_path)

        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(f'xml: {xml_path}')
        self.currentControl = None
        if clz.includes is None:
            clz.includes = Includes()

        clz._logger.debug(f'{xml_path} isAddon: {currentWindowIsAddon()}')
        if not currentWindowIsAddon():
            self.processIncludes()

    #            import codecs
    #            with codecs.open(os.path.join(get_xbmc_skin_path(''),'TESTCurrent.xml'),
    #            'w','utf-8') as f: f.write(self.soup.prettify())

    def get_xml_root(self) -> ET.Element:
        return self.et_root

    def get_window_type(self) -> WindowType:
        """
        Window type is an attribute of Window element.

        :return: value of type attribute
        """
        clz = type(self)
        if module_logger.isEnabledFor(DEBUG_VERBOSE):
            clz._logger.debug_verbose(f'Calling get_window_element')
        window_element: ET.Element = self.get_window_element()
        attrib_type: str | None = window_element.attrib.get(f'type')
        window_type: WindowType = WindowType.UNKNOWN
        try:
            window_type = WindowType[attrib_type.upper()]
        except Exception:
            clz._logger.exception(f'Incorrect window type: {attrib_type}'
                                  f' name: {WindowType.DIALOG.name}')
        return window_type

    def get_default_control(self) -> int | None:
        clz = type(self)
        window_element: ET.Element = self.get_window_element()
        child: ET.Element = window_element.find('./defaultcontrol')
        try:
            default_control = int(child.text)
        except Exception:
            clz._logger.exception('Invalid defaultcontrol')
            default_control = None

        return default_control


    def get_window_element(self) -> ET.Element:
        # Get root element of current xml file
        return self.et_root

    def build_reverse_tree_map(self, root: ET.Element, xml_file_path: Path):
        """
        Creates an ancestor map of elements for a given xml source file.
        Used to quickly find the parents of any node. Note that
        the map is created for tine initial xml with include files not yet
        processed. It may mean that it is useless to persist.

        :param root:
        :param xml_file_path:
        :return:
        """
        clz = type(self)
        if clz.forest_map.get(str(xml_file_path)) is not None:
            return

        reverse_tree_map: Dict[ET.Element, ET.Element]
        reverse_tree_map = {c: p for p in root.iter() for c in p}
        clz.forest_map[str(xml_file_path)] = reverse_tree_map

    @classmethod
    def get_parent(cls, tree_name: str, child: ET.Element) -> ET.Element | None:
        reverse_tree_map: Dict[ET.Element, ET.Element]
        reverse_tree_map = cls.forest_map.get(tree_name)
        if reverse_tree_map is None:
            return None
        return reverse_tree_map.get(child)

    @classmethod
    def get_ancestors(cls, tree_name: str, child: ET.Element) -> List[ET.Element]:
        reverse_tree_map: Dict[ET.Element, ET.Element]
        reverse_tree_map = cls.forest_map.get(tree_name)
        if reverse_tree_map is None:
            return None
        ancestors: List[ET.Element] = []
        for ancestor in reverse_tree_map.get(child):
            if ancestor is None:
                return ancestors
            ancestors.append(ancestor)
        return ancestors

    def processIncludes(self):
        clz = type(self)
        dummy_root: ET.Element = ET.Element(f'dummy_root')
        dummy_root.append(self.et_root)
        result_dummy_root: ET.Element = self.expand_includes(dummy_root)
        result: ET.Element = result_dummy_root.find('./*')
        if VERBOSE_DEBUG:
            clz._logger.debug_verbose(f'expanded result: {dump_subtree(result)}')
        self.et_root = result

    def expand_includes(self, parent: ET.Element) -> ET.Element:
        Monitor.exception_on_abort()
        clz = type(self)
        result_dummy_root: ET.Element = ET.Element('dummy_root')
        try:
            result: ET.Element = result_dummy_root
            for child in parent.findall('./*'):
                if child.tag in IGNORED_TAGS:
                    continue
                if child.tag == 'include':
                    if child.attrib.get('file') is not None:
                        include_file_name: str = child.attrib.get('file')
                        included_file_path: Path = get_xbmc_skin_path(include_file_name)
                        if module_logger.isEnabledFor(DEBUG_VERBOSE):
                            clz._logger.debug_verbose(f'Ignoring Include file import:'
                                                      f' {included_file_path}')
                        # included_xml: ET = ET.parse(str(included_file_path))
                        # root = included_xml.getroot()
                        # new_dest: ET.Element = ET.Element('dummy_root')
                        # new_dest_tree: ET.ElementTree = ET.ElementTree(new_dest)
                        # self.parse_includes_tree(root, new_dest)
                        # Nothing to put in new ElementTree. All includes were
                        # put into parse_includes_tree by call.
                        continue
                    else:
                        # If node is <include name=include_name>, then parse the
                        # include definition, then place in map.

                        include_name: str = child.attrib.get('name')
                        if include_name is not None:
                            if module_logger.isEnabledFor(DEBUG_VERBOSE):
                                clz._logger.debug_verbose(f'Ignoring Include file '
                                                          f'definition: {include_name}')
                            # new_parent: ET.Element = child
                            # include_root: ET.Element = ET.Element('dummy_root')
                            # include_tree: ET.ElementTree = ET.ElementTree(include_root)
                            # self.parse_includes_tree(new_parent, include_root)

                            # Add this include definition into a dictionary
                            # for quick access
                            # if include_name in clz._new_includes_map.keys():
                            #     clz._logger.debug_verbose(
                            #         f'ERROR entry already in new map: {include_name}')
                            # else:
                            #     text: str = dump_subtree(new_parent)
                            #     clz._logger.debug_verbose(f'ORIG: {text}')
                            #     text: str = dump_subtree(include_root)
                            #     clz._logger.debug_verbose(f'COMPLETE: {text}')
                            #     include_child: ET.Element = include_root.find('.*')
                            #     if include_child is not None:
                            #         clz._new_includes_map[include_name] = include_child
                            #     else:
                            #         clz._logger.debug_verbose(f'Include: {
                            #         include_name} omitted due to empty')
                            continue
                    if child.attrib.get('content') is not None or child.text is not None:
                        include_name: str = child.attrib.get('content')
                        if include_name is None:
                            include_name = child.text
                        include_root: ET.Element = clz.includes.get_include(include_name)
                        if include_root is None:
                            if module_logger.isEnabledFor(DEBUG):
                                clz._logger.debug(f'Could not find definition '
                                                  f'for include: {include_name}')
                        else:
                            if VERBOSE_DEBUG:
                                clz._logger.debug_verbose(f'found definition for '
                                                          f'include: {include_name}')
                                clz._logger.debug_verbose(dump_subtree(include_root))
                            expanded_dummy: ET.Element
                            expanded_dummy = self.expand_includes(include_root)
                            if VERBOSE_DEBUG:
                                clz._logger.debug_verbose(f'Expanded includes: '
                                                          f'{include_name} '
                                                          f'{dump_subtree(expanded_dummy)}')
                            result.extend(expanded_dummy.findall(''))
                        x = result.findall('.//include')
                        if x is not None and len(x) > 0:
                            if module_logger.isEnabledFor(DEBUG_VERBOSE):
                                clz._logger.debug_verbose(f'include FOUND in result')
                                clz._logger.debug_verbose(f'{dump_subtree(include_root)}')
                        continue
                    if module_logger.isEnabledFor(DEBUG):
                        clz._logger.debug(
                            f'Unexpected include element without "file" or "name".')
                    continue
                # Probably don't need to do this. Kodi probably expands this in any
                # expression that we send it for evaluation.
                '''
                if child.tag == 'constant':
                    if child.attrib.get('name'):
                        constant_name: str = child.attrib.get('name')
                        value: Any = child.text
                        if constant_name in clz.constant_definitions.keys():
                            clz._logger.debug_verbose(f'ERROR: constant already defined: '
                                              f'{constant_name} value: {value}')
                        else:
                            clz.constant_definitions[constant_name] = value
                    continue

                # Probably don't need to do this. Kodi probably expands this in any
                # expression that we send it for evaluation.
                if child.tag == 'expression':
                    if child.attrib.get('name'):
                        expression_name: str = child.attrib.get('name')
                        value: str = child.text
                        if expression_name in clz.expression_definitions.keys():
                            clz._logger.debug_verbose(f'ERROR: constant already defined: '
                                              f'{expression_name} value: {value}')
                        else:
                            clz.expression_definitions[expression_name] = value
                    continue
                '''
                # x = result_dummy_root.findall('.//include')
                # if x is not None and len(x) > 0:
                #     clz._logger.debug_verbose(f'include FOUND in result')
                dummy_root: ET.Element | None = self.expand_other(child)
                # x = dummy_root.findall('.//include')
                # if x is not None and len(x) > 0:
                #     clz._logger.debug_verbose(f'include FOUND in result')
                result_dummy_root.extend(dummy_root.findall('./*'))

        except StopIteration:
            pass
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('Boom!')

        if VERBOSE_DEBUG:
            clz._logger.debug_verbose(
                f'expand includes: {dump_subtree(result_dummy_root)}')
        return result_dummy_root

    def expand_other(self, child: ET.Element) -> ET.Element | None:
        clz = type(self)
        # Copy this non-handled or excluded child node to the new tree
        dummy_root: ET.Element = ET.Element('dummy_root')
        try:
            # Recurse to deal with grandchildren
            # orig_text: str = dump_subtree(child)
            new_child: ET.Element = ET.SubElement(dummy_root, child.tag, child.attrib)
            new_child.text = child.text
            if VERBOSE_DEBUG and new_child.tag == 'include':
                clz._logger.debug_verbose(f'include FOUND in result')
            result_dummy_root: ET.Element = self.expand_includes(child)
            new_child.extend(result_dummy_root.findall('./*'))

            # clz._logger.debug_verbose(f'orig: {orig_text}')
            text: str = ''
            # text = dump_subtree(dest_node)
            # clz._logger.debug_verbose(f'changed: {text}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('Boom!')
        if VERBOSE_DEBUG:
            clz._logger.debug_verbose(f'expand_other: {dump_subtree(dummy_root)}')
            x = dummy_root.findall('.//include')
            if x is not None and len(x) > 0:
                clz._logger.debug_verbose(f'include FOUND in result')
        return dummy_root

    def old_processIncludes(self):
        """
        Includes provides a means to import Elements from the same or
        other ElementTrees.

        Includes is a tree of includes from all of the Include files,
        starting with Includes.xml.
        :return:
        """
        clz = type(self)
        if VERBOSE_DEBUG:
            clz._logger.debug_verbose(
                    f'In old_processIncludes xml file: {self.current_window_path}')

        # Now, for the current window, examine the includes, pruning
        # irrelevant includes.
        include: Any
        includes = xpath.find('//include', self.xml)
        for include in includes:
            # Ignore any includes which are not relevant, due to it not
            # being visible. (Is it always true that an invisible
            # item has no impact on gui?)
            if VERBOSE_DEBUG:
                clz._logger.debug_verbose(f"include tag: {include.tagName}")
            parent = xpath.findnode('..', include)
            conditionAttr = include.attributes.get('condition')
            if conditionAttr and not xbmc.getCondVisibility(conditionAttr.value):
                # Not visible, include is not relevant
                if VERBOSE_DEBUG:
                    dump = dump_dom(parent)
                    clz._logger.debug_verbose(f'parent of include: {dump}')
                parent.removeChild(include)
                if VERBOSE_DEBUG:
                    dump = dump_dom(parent)
                    clz._logger.debug_verbose(
                            f'parent of include after removing child include: \n{dump}')
                continue

            # Does this include for this window refer to one in the
            # Include Tree?
            node_name: str = include.childNodes[0].data
            matchingInclude = clz.includes.get_old_include(node_name)

            #  if matchingInclude:
            #     child = include.childNodes[0]
            #     dump = dump_dom(include)
            #     clz._logger.debug_verbose(f'INCLUDE FOUND: {child}')
            #     clz._logger.debug_verbose(f'{dump}')

            if not matchingInclude:
                #  for child in include.childNodes:
                #  dump = dump_dom(child)
                #  clz._logger.debug_verbose(f'INCLUDE NOT FOUND: {child}\n{dump}')
                continue

            # Yes, the window refers to an include which our include tree
            # has the body of the include. Import that include into
            # our Window's tree.

            new = matchingInclude.cloneNode(True)
            if VERBOSE_DEBUG:
                dump = dump_dom(parent)
                clz._logger.debug_verbose(f'parent of include: {dump}')

            parent.replaceChild(new, include)
            if VERBOSE_DEBUG:
                dump = dump_dom(parent)
                clz._logger.debug_verbose(
                    f'parent of include after expanding include: \n{dump}')

    def lxml_processIncludes(self):
        """
        Includes provides a means to import Elements from the same or
        other ElementTrees.

        Includes is a tree of includes from all of the Include files,
        starting with Includes.xml.
        :return:
        """
        clz = type(self)

        # Now, for the current window, examine the include
        # references, pruning irrelevant references.

        include: lxml_ET.Element
        includes: List[lxml_ET.Element] = self.lxml_includes_xml.findall('//include')
        for include in includes:
            # Ignore any includes which are not relevant, due to it not
            # being visible. (Is it always true that an invisible
            # item has no impact on gui?)

            include_parent: lxml_ET.Element = include.getparent()
            conditionAttr: str | None = include.attrib.get('condition')
            if VERBOSE_DEBUG:
                clz._logger.debug_verbose(
                        f'include {include.tag} {include.attrib} {include.text}')
            if conditionAttr:  # and not xbmc.getCondVisibility(conditionAttr):
                name: str = include.attrib.get('name')
                if VERBOSE_DEBUG:
                    clz._logger.debug_verbose(f'{include.tag} {include.attrib}'
                                              f' text: {include.text} tail:'
                                              f' {include.tail}')

                    dump: str = lxml_ET.tostring(include_parent, encoding='unicode')
                    clz._logger.debug_verbose(f'parent before removing include:\n {dump}')
                    clz._logger.debug_verbose(
                            f'removing include {include.text} from {include_parent.tag}')
                include_parent.remove(include)
                if VERBOSE_DEBUG:
                    dump: str = lxml_ET.tostring(include_parent, encoding='unicode')
                    clz._logger.debug_verbose(f'parent after removing include:\n {dump}')
                continue

            # Does this include for this window refer to one in the
            # Include Tree? getInclude uses the name attribute of an include
            # to find the body of the include_ref.

            matchingInclude: lxml_ET.Element = clz.includes.get_include(include.text)

            if matchingInclude is None:
                # clz._logger.debug_verbose(f'INCLUDE NOT FOUND: {include.text}')
                continue

            # Yes, the window refers to an include which our include tree
            # has the body of the include. Import that include into
            # our Window's tree.

            # print 'INCLUDE FOUND: %s' % i.string
            if VERBOSE_DEBUG:
                dump: str = lxml_ET.tostring(include_parent, encoding='unicode')
                clz._logger.debug_verbose(f'parent before replacing include:\n {dump}')
            include_parent.replace(include, matchingInclude)
            if VERBOSE_DEBUG:
                dump: str = lxml_ET.tostring(include_parent, encoding='unicode')
                clz._logger.debug_verbose(f'parent after replacing include:\n {dump}')

    def new_processIncludes(self):
        """
        Called to expand any includes in the current active document
        (self.lxml_includes_xml). Since there can be includes which are
        conditionally included, this function is called each time the
        window could have changed. It is possible to add logic to
        handle the conditional includes during evaluation, but for now
        it builds it on each reference. An advantage to building on
        demand is that it can reduce the memory footprint (should measure).

        Prior to coming here, a map of all includes was built by
        Includes.loadIncludesFiles(). Here, we substitute any include references
        (that pass any condition test) in the current window's xml with the expanded
        definition of the include. Finally, the returned document is a copy of
        the original elements so that it can be freely altered without impacting
        any cached elements.

        Notes: an include definition can contain references to other includes which
        requires
               expanding these includes that were just included. Basically any branch
               in the document must be traversed and have includes expanded.

        Example xml for a window:

        <window>
            <defaultcontrol always="true">9000</defaultcontrol>
            <onunload condition="Container(9000).Hasfocus(10) | Container(
            9000).Hasfocus(11) | ControlGroup(9010).HasFocus | ControlGroup(
            9016).HasFocus | ControlGroup(9017).HasFocus">SetProperty(VideosDirectLink,
            True)</onunload>
                <controls>
                    <control type="list" id="90160">
                        <left>-10</left>
                        <top>-10</top>
                        <visible>Library.HasContent(Movies)</visible>
                    </control>
                    <include condition="!Skin.HasSetting(
                    HomepageHideRecentlyAddedVideo) | !Skin.HasSetting(
                    HomepageHideRecentlyAddedAlbums)">HomeRecentlyAddedInfo</include>
                    <control type="image">
                        <depth>DepthFloor</depth>
                        <left>-20</left>
                        <texture>floor.png</texture>
                    </control>
                </controls>
            </window>

        The include element has a condition. The contents of the include is ignored
        when the condition evaluates to False at run-time.

        When an include is expanded, the <include> element is replaced with the
        contents of the include.

        :return:
        """
        clz = type(self)

        # Expand the current window's xml by replacing include references
        # with the XML that they represent. Finally, prune irrelevant xml

        # A parent element may contain multiple include elements.

        include_parent: ET.Element
        include_parents: List[ET.Element] = self.et_includes_xml.findall('//include/..')
        for include_parent in include_parents:
            # Ignore any includes which are not relevant, due to it not
            # being visible. (Is it always true that an invisible
            # item has no impact on gui?)

            # We just need the name of the include and any condition
            include: ET.Element = include_parent.find('include')
            condition: str | None = include.attrib.get('condition')
            if VERBOSE_DEBUG:
                clz._logger.debug_verbose(
                        f'include {include.tag} {include.attrib} {include.text}')
            if condition and not xbmc.getCondVisibility(condition):
                # Purge this inactive branch
                include_name: str = include.text
                if VERBOSE_DEBUG:
                    clz._logger.debug_verbose(f'{include.tag} {include.attrib}'
                                              f' text: {include.text} tail: '
                                              f'{include.tail}')

                    dump: str = ET.tostring(include_parent, encoding='unicode')
                    clz._logger.debug_verbose(f'parent before removing include:\n {dump}')
                    clz._logger.debug_verbose(
                            f'removing include {include.text} from {include_parent.tag}')
                include_parent.remove(include)
                if VERBOSE_DEBUG:
                    dump: str = ET.tostring(include_parent, encoding='unicode')
                    clz._logger.debug_verbose(f'parent after removing include:\n {dump}')
                continue
            else:
                #  The include stays. Replace the include element with it's
                #  reference.

                # Does this include for this window refer to one in the
                # Include Tree? getInclude uses the name attribute of an include
                # to find the body of the include_ref.

                expanded_include: ET.Element = clz.includes.get_include(include.text)
                if expanded_include is None:
                    # clz._logger.debug_verbose(f'INCLUDE NOT FOUND: {include.text}')
                    continue

                # Yes, the window refers to an include which our include tree
                # has the body of the include. Import that include into
                # our Window's tree.

                # print 'INCLUDE FOUND: %s' % i.string
                if VERBOSE_DEBUG:
                    dump: str = ET.tostring(include_parent, encoding='unicode')
                    clz._logger.debug_verbose(
                        f'parent before replacing include:\n {dump}')
                include_parent.remove(include)
                if VERBOSE_DEBUG:
                    dump: str = ET.tostring(include, encoding='unicode')
                    clz._logger.debug_verbose(f'removed include: \n{dump}')
                    dump: str = ET.tostring(expanded_include, encoding='unicode')
                    clz._logger.debug_verbose(f'expanded_include to append: \n{dump}')
                include_parent.append(expanded_include)  # Order should not matter
                if VERBOSE_DEBUG:
                    dump: str = ET.tostring(include_parent, encoding='unicode')
                    clz._logger.debug_verbose(f'parent after replacing include:\n {dump}')

    def addonReplacer(self, m):
        return xbmc.getInfoLabel(m.group(0))

    def variableReplace(self, m):
        clz = type(self)
        try:
            return clz.includes.getVariable(m.group(1))
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            module_logger.exception(f'variableReplace Exception: {e}')

    def localizeReplacer(self, m):
        return xbmc.getLocalizedString(int(m.group(1)))

    def parseFormatting(self, text):
        # If the window/control is not reachable from Includes.xml, then
        # variables are not likely known to this module

        text = UIConstants.VAR_RE.sub(self.variableReplace, text)
        text = UIConstants.LOCALIZE_RE.sub(self.localizeReplacer, text)
        text = UIConstants.ADDON_RE.sub(self.addonReplacer, text)
        text = extractInfos(text, self.currentControl)
        text = UIConstants.TAG_RE.sub('', text).replace('[CR]', '... ').strip(' .')
        # text = infoLabelRE.sub(self.infoReplacer,text)
        return text

    def getControl(self, control_id) -> ET.Element | None:
        clz = type(self)
        new_control: ET.Element = None
        old_control: ET.Element = None
        if USE_OLD_FUNCTIONS:
            old_control: minidom = self.old_getControl(control_id)
        if USE_NEW_FUNCTIONS:
            new_control = self.new_getControl(control_id)
            if USE_OLD_FUNCTIONS and old_control != new_control:
                clz._logger.debug_verbose(f'DIFFERENCE results old: {old_control} '
                                          f'new: {new_control}')
        if USE_OLD_FUNCTIONS:
            return old_control
        else:
            return new_control

    def old_getControl(self, control_id):
        control = xpath.findnode(f"//control[attribute::id='{control_id}']",
                                 self.xml)
        return control

    def new_getControl(self, control_id) -> ET.Element:
        Monitor.exception_on_abort()
        new_control: ET.Element = self.et_includes_xml.find(
            f".//control[@id='{control_id}']")
        return new_control

    def lxml_getControl(self, control_id) -> lxml_ET.Element:
        new_control: lxml_ET.Element = self.lxml_includes_xml.find(
            f".//control[@id='{control_id}']")
        return new_control

    def getLabelText(self, label) -> str | None:
        clz = type(self)
        old_text = None
        if USE_OLD_FUNCTIONS:
            old_text: str = self.old_getLabelText(label)
        new_text = None
        if USE_NEW_FUNCTIONS:
            new_text: str = self.new_getLabelText(label)
            if USE_OLD_FUNCTIONS and old_text != new_text:
                clz._logger.debug_verbose(f'DIFFERENCE: results old: {old_text} '
                                          f'new: {new_text}')
        if USE_OLD_FUNCTIONS:
            return old_text
        return new_text

    def old_getLabelText(self, label) -> str | None:
        clz = type(self)
        if VERBOSE_DEBUG:
            module_logger.debug_verbose(f'In getLabelText')
        text = None
        label_id = label.attributes.get('id')
        if label_id:
            # Try getting programmatically set label first.
            text = xbmc.getInfoLabel(f'Control.GetLabel({label_id.value})')

        if not text or text == '-':
            text = None
            label_node = xpath.findnode('label', label)
            if label_node and label_node.childNodes:
                text = label_node.childNodes[0].data
            if text:
                if text.isdigit():
                    text = f'$LOCALIZE[{text}]'
            else:
                i = xpath.findnode('info', label)
                if i and i.childNodes:
                    text = i.childNodes[0].data
                    if text.isdigit():
                        text = f'$LOCALIZE[{text}]'
                    else:
                        text = f'$INFO[{text}]'

        if not text:
            return None
        value = UIConstants.TAG_RE.sub('', text).replace('[CR]', '... ').strip(' .')
        return value

    def new_getLabelText(self, label: ET.Element) -> str:
        clz = type(self)
        Monitor.exception_on_abort()
        if module_logger.isEnabledFor(DEBUG_VERBOSE):
            module_logger.debug_verbose(f'In new_getLabelText')
        new_label_id: str = label.attrib.get('id')
        new_text: str | None = None
        if module_logger.isEnabledFor(DEBUG_VERBOSE):
            module_logger.debug_verbose(f'new_label_id: {new_label_id}')
        if new_label_id:
            # Try getting programmatically set label first.
            new_text = xbmc.getInfoLabel(f'Control.GetLabel({new_label_id})')

        if new_text is None or new_text == '-':
            new_text = None
            new_label_node: ET.Element = label.find('label')
            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                clz._logger.debug_verbose(f'new_label_node: {new_label_node.tag} '
                                          f'text: {new_label_node.text}')
            if new_label_node is not None and new_label_node.text:
                new_text = new_label_node.text
                if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                    clz._logger.debug_verbose(f'new_text: {new_text}')
            if new_text:
                if new_text.isdigit():
                    new_text = f'$LOCALIZE[{new_text}]'
            else:
                i_new: ET.Element = new_label_node.find('info')
                if i_new is not None and i_new.find('*'):
                    new_text: str = i_new.find('*').text
                    if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                        clz._logger.debug_verbose(f'i_new text: {new_text}')
                    if new_text.isdigit():
                        new_text = f'$LOCALIZE[{new_text}]'
                    else:
                        new_text = f'$INFO[{new_text}]'

        if not new_text:
            return None
        #  new_value = tagRE.sub('', new_text).replace('[CR]', '...').strip(' .')
        return new_text

    def processTextList(self, text_list: List[str]) -> List[str]:
        texts: List[str] = []
        check: List[str] = []
        for t in text_list:
            parsed = self.parseFormatting(t)
            if parsed and t not in check:
                texts.append(parsed)
                check.append(t)
        return texts

    def getListItemTexts(self, control_id: int) -> List[str] | None:
        old_texts = None
        if USE_OLD_FUNCTIONS:
            old_texts = self.old_getListItemTexts(control_id)
        new_texts = None
        if USE_NEW_FUNCTIONS:
            new_texts = self.new_getListItemTexts(control_id)
            if USE_OLD_FUNCTIONS and old_texts != new_texts:
                clz = type(self)
                if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                    clz._logger.debug_verbose(f'DIFFERENCE: old != new old: {old_texts} '
                                              f'new: {new_texts}')
        if USE_OLD_FUNCTIONS:
            return old_texts
        return new_texts

    def old_getListItemTexts(self, control_id: int) -> List[str] | None:
        if control_id < 0:
            control_id = - control_id
        self.currentControl = control_id
        try:
            clist = self.getControl(control_id)
            if not clist:
                return None
            fl = xpath.findnode("focusedlayout", clist)
            if not fl:
                return None
            lt = xpath.find(
                    "//control[attribute::type='label' or attribute::type='fadelabel' "
                    "or attribute::type='textbox']",
                    fl)
            texts = []
            for l in lt:
                if not self.controlIsVisibleGlobally(l):
                    continue
                text = self.getLabelText(l)
                if text and text not in texts:
                    texts.append(text)
            value = self.processTextList(texts)
            return value
        finally:
            self.currentControl = None

    def lxl_getListItemTexts(self, control_id: int) -> List[str]:
        if control_id < 0:
            control_id = - control_id
        self.currentControl = control_id
        try:
            newclist = self.new_getControl(control_id)
            if newclist is None:
                return None
            new_lts: List[Any] = []
            new_lt: List[ET.Element] = []
            new_fl = newclist.find('focusedlayout')
            if new_fl is None:
                return None
            new_lt = new_fl.findall(".//control[@type='label']")
            if new_lt is not None:
                new_lts.extend(new_lt)
            new_lt = new_fl.findall(".//control[@type='fadelabel']")
            if new_lt is not None:
                new_lts.extend(new_lt)
            new_lt = new_fl.findall(".//control[@type='textbox']")
            if new_lt is not None:
                new_lts.extend(new_lt)
            new_texts: List[str] = []
            for new_l in new_lts:
                if not self.new_controlIsVisibleGlobally(new_l):
                    continue
                new_text: str = self.new_getLabelText(new_l)
                if new_text and new_text not in new_texts:
                    new_texts.append(new_text)
            new_value: List[str] = self.processTextList(new_texts)
            return new_value
        finally:
            self.currentControl = None

    def new_getListItemTexts(self, control_id: int) -> List[str]:
        clz = type(self)
        if control_id < 0:
            control_id = - control_id
        self.currentControl = control_id
        try:
            newclist = self.new_getControl(control_id)
            if newclist is None:
                return None

            fl: ET.Element
            fl: ET.Element = newclist.find('focusedlayout')
            if fl is None:
                return None

            parents: List[ET.Element] = []
            texts: Dict[str, str] = {}
            for pat in ('label',
                        'fadelabel',
                        'textbox'):

                parent_pat: str = f".//control[@type='{pat}']/.."
                some_parents: List[ET.Element] = fl.findall(parent_pat)
                if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                    clz._logger.debug_verbose(f'control_id: {control_id} '
                                              f'xml: {self.current_window_path} '
                                              f'parent_pat: {parent_pat}')
                if some_parents is None:
                    continue

                parents.extend(some_parents)
                child_pat = f"./control[@type='{pat}']"
                for parent in some_parents:
                    parent: ET.Element
                    if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                        clz._logger.debug_verbose(
                            f'control_id: {control_id} child_pat: {child_pat} '
                            f'parent: {parent.tag}')
                    some_children = parent.findall(child_pat)
                    some_children: List[ET.Element] | None
                    if some_children is None:
                        continue
                    for child in some_children:
                        child: ET.Element
                        # <label>$INFO[ListItem.Label2]</label>
                        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                            clz._logger.debug_verbose(f'control_id: {control_id} '
                                                      f'child_id: {child.attrib.get("id")} ')
                        if not self.new_controlIsVisibleGlobally(parent,
                                                                 child):
                            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                                clz._logger.debug_verbose(f'child not visible')
                            continue
                        text: str = self.new_getLabelText(child)
                        if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                            clz._logger.debug_verbose(f'child text: {text}')
                        if text and text not in texts:
                            texts[text] = text
            all_texts: List[str] = self.processTextList(texts.values())
            # clz._logger.debug_verbose(f'texts: {texts}')
            if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                clz._logger.debug_verbose(f'all_texts {all_texts}')
            return all_texts
        finally:
            self.currentControl = None

    def getWindowTexts(self, phrases: PhraseList) -> bool:
        old: List[str] | None = None
        if USE_OLD_FUNCTIONS:
            old: List[str] = self.old_getWindowTexts()
        new: List[str] | None = None
        if USE_NEW_FUNCTIONS:
            new: List[str] = self.new_getWindowTexts()
            if USE_OLD_FUNCTIONS and old != new:
                clz = type(self)
                if clz._logger.isEnabledFor(DEBUG_VERBOSE):
                    clz._logger.debug_verbose(f'DIFFERENCE: old != new old: {old} '
                                              f'new: {new}')
        if USE_OLD_FUNCTIONS:
            if old is None:
                old = []
            phrases.add_text(texts=old)
            return True
        if new is None:
            new = []
        phrases.add_text(texts=new)
        return True

    def old_getWindowTexts(self) -> List[str]:
        lt = xpath.find(
                "//control[attribute::type='label' or attribute::type='fadelabel' or "
                "attribute::type='textbox']",
                self.xml)
        texts: List[str] = []
        for l in lt:
            if not self.controlIsVisible(l):
                continue
            for p in nodeParents(self.xml, l):
                if not self.controlIsVisible(p):
                    break
                typeAttr = p.attributes.get('type')
                if typeAttr and typeAttr.value in (
                        'list', 'fixedlist', 'wraplist', 'panel'):
                    break
            else:
                text = self.getLabelText(l)
                if text and text not in texts:
                    texts.append(text)
        list_1 = self.processTextList(texts)
        return list_1

    def new_getWindowTexts(self) -> List[str]:
        clz = type(self)
        Monitor.exception_on_abort()
        query: str = ".//control[@type='label' or @type='fadelabel' or " \
                     "@type='textbox' or @type='slider']"
        # We need the parent nodes that match they query
        parents: List[ET.Element] = self.et_includes_xml.findall(query + "/..")
        new_texts: List[str] = []
        parent: ET.Element
        clz._logger.debug(f'In getWindowTexts')
        for parent in parents:
            # If parent is not visible, then neither is branch of children
            if not self.new_controlIsVisible(parent):
                clz._logger.debug(f'file: {self.xml_path} Skipping Parent: {parent.tag}')
                continue
            # Now query to find the children that match the query
            children: List[ET.Element] = parent.findall(query)
            for child in children:
                clz._logger.debug(f'child: {child.tag} attrib: {child.attrib} '
                                  f'text: {child.text}')
                # Omit any branches that don't apply to the state of this control

                if not self.new_controlIsVisible(child):
                    clz._logger.debug(f'child NOT visible')
                    continue

                type_attr: str = child.attrib.get('type')
                if type_attr in ('list', 'fixedlist', 'wraplist', 'panel'):
                    break
                elif type_attr == 'slider':
                    #  win: xbmcgui.Window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
                    win = None
                    if WinDialogState.current_windialog == WinDialog.WINDOW:
                        win: xbmcgui.Window = WinDialogState.current_window_instance
                    else:
                        win: xbmcgui.WindowDialog = WinDialogState.current_dialog_instance
                    #  win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
                    label_id = win.getProperty('SliderLabel')
                    new_text = xbmc.getInfoLabel(f'Control.GetLabel({label_id})')
                    if new_text and new_text not in new_texts:
                        new_texts.append(f'{new_text}. You fucker')
                    clz._logger.debug(f'SliderLabel found. Added text: {new_texts}')
                else:
                    new_text = self.new_getLabelText(child)
                    if new_text and new_text not in new_texts:
                        new_texts.append(new_text)
        return self.processTextList(new_texts)

    def lxml_getWindowTexts(self) -> List[str]:
        query: str = ".//control[@type='label' or @type='fadelabel' or " \
                     "@type='textbox']"
        children: List[ET.Element] = self.lxml_includes_xml.findall(query)
        new_texts: List[str] = []
        for child in children:
            if not self.new_controlIsVisible(child):
                continue
            for parent in lxml_get_ancestors(self.lxml_includes_xml, child):
                if not self.new_controlIsVisible(parent):
                    break
                type_attr: str = parent.attrib.get('type')
                if type_attr in (
                        'list', 'fixedlist', 'wraplist', 'panel'):
                    break
            else:
                new_text = self.new_getLabelText(child)
                if new_text and new_text not in new_texts:
                    new_texts.append(new_text)
        return self.processTextList(new_texts)

    def controlGlobalPosition(self, control) -> Tuple[int, int]:
        """
        Get the position of this control within its window. This requires
        Calculating the position from the control + all ancestors up to the root.
        Non-trivial.

        :param control:
        :return:
        """
        clz = type(self)
        new_x = None
        new_y = None
        old_x = None
        old_y = None
        if USE_OLD_FUNCTIONS:
            old_x, old_y = self.old_controlGlobalPosition(control)
        if USE_NEW_FUNCTIONS:
            new_x, new_y = self.new_controlGlobalPosition(control)
            if USE_OLD_FUNCTIONS:
                if old_x != new_x:
                    clz._logger.debug_verbose(f'DIFFERENCE: old_x != new_x old: {old_x} '
                                              f'new: {new_x}')
                if old_y != new_y:
                    clz._logger.debug_verbose(f'DIFFERENCE: old_y != new_y old: {old_y} '
                                              f'new: {new_y}')
        if USE_OLD_FUNCTIONS:
            return old_x, old_y
        return new_x, new_y

    def old_controlGlobalPosition(self, control) -> Tuple[int, int]:
        x, y = self.controlPosition(control)
        for p in nodeParents(self.xml, control):
            if p.get('type') == 'group':
                px, py = self.controlPosition(p)
                x += px
                y += py
        return x, y

    def new_controlGlobalPosition(self, control) -> Tuple[int, int]:
        new_x: int
        new_y: int
        new_x, new_y = self.controlPosition(control)
        for p, new_parent in new_get_ancestors(self.et_includes_xml, control):
            if new_parent.get('type') == 'group':
                new_parent_x, new_parent_y = self.controlPosition(new_parent)
                new_x += new_parent_x
                new_y += new_parent_y
        return new_x, new_y

    def lxml_controlGlobalPosition(self, control) -> Tuple[int, int]:
        new_x: int
        new_y: int
        new_x, new_y = self.controlPosition(control)
        for p, new_parent in lxml_get_ancestors(self.lxml_includes_xml, control):
            if new_parent.get('type') == 'group':
                new_parent_x, new_parent_y = self.controlPosition(new_parent)
                new_x += new_parent_x
                new_y += new_parent_y
        return new_x, new_y

    def controlPosition(self, control):
        posx = control.find('posx')
        x = posx and posx.string or '0'
        if 'r' in x:
            x = int(x.strip('r')) * -1
        else:
            x = int(x)
        posy = control.find('posy')
        y = int(posy and posy.string or '0')
        return x, y

    def controlIsVisibleGlobally(self, control) -> bool:
        old = None
        if USE_OLD_FUNCTIONS:
            old: bool = self.old_controlIsVisibleGlobally(control)
        new = None
        if USE_NEW_FUNCTIONS:
            new: bool = self.new_controlIsVisibleGlobally(control)
            if USE_OLD_FUNCTIONS and old != new:
                clz = type(self)
                clz._logger.debug_verbose(f'DIFFERENCE: old != new old: {old} new: {new}')
        if USE_OLD_FUNCTIONS:
            return old
        return new

    def old_controlIsVisibleGlobally(self, control):
        for p in nodeParents(self.xml, control):
            if not self.old_controlIsVisible(p):
                return False
        return self.old_controlIsVisible(control)

    def controlIsVisible(self, control) -> bool:
        old: bool = self.old_controlIsVisible(control)
        new = None
        if USE_NEW_FUNCTIONS:
            new: bool = self.new_controlIsVisible(control)
            if old != new:
                clz = type(self)
                clz._logger.debug_verbose(f'DIFFERENCE: Old != New old: {old} new: {new}')
        if USE_OLD_FUNCTIONS:
            return old
        return new

    def old_controlIsVisible(self, control) -> bool:
        visible = xpath.findnode('visible', control)
        if not visible:
            return True
        if not visible.childNodes:
            return True
        condition = visible.childNodes[0].data
        if self.currentControl:
            condition = condition.replace(
                    'ListItem.Property',
                    'Container({0}).ListItem.Property'.format(self.currentControl))
        if not xbmc.getCondVisibility(condition):
            return False
        else:
            return True

    def new_controlIsVisibleGlobally(self, parent: ET.Element,
                                     control: ET.Element) -> bool:
        for new_parent in new_get_ancestors(self.et_includes_xml, control):
            if not self.new_controlIsVisible(new_parent):
                return False
        return self.new_controlIsVisible(control)

    def new_controlIsVisible(self, control: ET.Element):
        visible = control.find('visible')
        if not visible:
            return True
        if visible.find('.//') is None:
            return True
        condition = visible.find('.//').text
        if self.currentControl:
            condition = condition.replace(
                    'ListItem.Property',
                    f'Container({self.currentControl}).ListItem.Property')
        if not xbmc.getCondVisibility(condition):
            return False
        else:
            return True

    def lxml_controlIsVisibleGlobally(self, parent: ET.Element,
                                      control: ET.Element) -> bool:
        for new_parent in lxml_get_ancestors(self.lxml_includes_xml, control):
            if not self.new_controlIsVisible(new_parent):
                return False
        return self.new_controlIsVisible(control)

    def lxml_controlIsVisible(self, control: lxml_ET.Element):
        visible = control.find('visible')
        if not visible:
            return True
        if visible.find('.//') is None:
            return True
        condition = visible.find('.//').text
        if self.currentControl:
            condition = condition.replace(
                    'ListItem.Property',
                    f'Container({self.currentControl}).ListItem.Property')
        if not xbmc.getCondVisibility(condition):
            return False
        else:
            return True


class Includes:
    _logger: BasicLogger = None
    _old_includes_files_loaded: bool = False
    _new_includes_files_loaded: bool = False
    _lxml_includes_files_loaded: bool = False
    _old_includes_map = {}
    _new_includes_map: Dict[str, ET.Element] = {}
    _lxml_includes_map: Dict[str, lxml_ET.Element] = {}
    constant_definitions: Dict[str, Any] = {}
    expression_definitions: Dict[str, str] = {}

    def __init__(self):
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        path = get_xbmc_skin_path('Includes.xml')
        clz._logger.debug(f'includes path: {path}')
        self.xml = minidom.parse(str(path))
        if USE_LXML:
            self.lxml_includes_xml: lxml_ET.ElementTree = lxml_ET.parse(path)
            self.lxml_root: lxml_ET.Element = self.lxml_includes_xml.getroot()
        self.et_includes_xml: ET.ElementTree = ET.parse(path)
        self.et_root: ET.Element = self.et_includes_xml.getroot()
        self.load_includes_files()

    def get_include(self, name: str) -> ET.Element | None:
        """
        Returns a copy of a named Include from a cache of all named Includes
        referenced by Includes.xml.

        :param name: name of include to get
        :return:
        """
        clz = type(self)
        self.load_includes_files()
        found_entry: ET.Element = clz._new_includes_map.get(name)
        if found_entry is not None:
            return copy.deepcopy(found_entry)
        return None

    def lxml_get_include(self, name: str) -> ET.Element | None:
        """
        Returns a copy of a named Include from a cache of all named Includes
        referenced by Includes.xml.

        :param name: name of include to get
        :return:
        """
        clz = type(self)
        self.lxml_load_includes_files()
        found_entry: lxml_ET.Element = clz._lxml_includes_map.get(name)
        if found_entry is not None:
            return copy.deepcopy(found_entry)
        return None

    def new_get_include(self, name: str) -> ET.Element | None:
        """
        Returns a copy of a named Include from a cache of all named Includes
        referenced by Includes.xml.

        :param name: name of include to get
        :return:
        """
        clz = type(self)
        self.new_load_includes_files()
        found_entry: ET.Element = clz._new_includes_map.get(name)
        if found_entry is not None:
            return copy.deepcopy(found_entry)
        return None

    def get_old_include(self, key: str) -> ET.Element:
        """
        Returns a copy of a named Include from a cache of all named Includes
        referenced by Includes.xml.

        :param key: name of include to get
        :return:
        """
        clz = type(self)
        self.load_includes_files()
        found_entry: ET.Element = clz._old_includes_map.get(key)
        if found_entry is not None:
            return copy.deepcopy(found_entry)
        return None

    def load_includes_files(self):
        clz = type(self)
        clz._logger.debug_verbose(f'in load_includes_files')
        if clz._old_includes_files_loaded or clz._new_includes_files_loaded:
            return

        if USE_OLD_FUNCTIONS:
            self.old_load_includes_files()
        if USE_NEW_FUNCTIONS:
            xbmc.log(f'Calling new_load_includes_files')
            self.new_load_includes_files()
            xbmc.log(f' Returned from new_load_includes_files')

        if USE_LXML:
            self.lxml_load_includes_files()

        if USE_OLD_FUNCTIONS and USE_NEW_FUNCTIONS:
            if len(clz._old_includes_map.keys()) != len(clz._new_includes_map.keys()):
                clz._logger.debug_verbose(f'Include maps of different size: old: '
                                          f'{len(clz._old_includes_map.keys())} new: '
                                          f'{len(clz._new_includes_map.keys())}')
            printed_one: bool = False
            for old_key, old_elements in clz._old_includes_map.items():
                old_xml: str = dump_dom(old_elements)
                from_old: ET = ET.fromstring(old_xml)
                from_new_elements: ET.Element = clz._new_includes_map.get(old_key)
                old_canonical: str = ET.canonicalize(xml_data=old_xml,
                                                     strip_text=True)
                new_canonical: str = ET.canonicalize(
                        xml_data=ET.tostring(from_new_elements, encoding='unicode'),
                        strip_text=True)
                if old_canonical != new_canonical:
                    clz._logger.debug_verbose(f'old != new key: {old_key}')
                    if not printed_one:
                        clz._logger.debug_verbose(f'Old canonical')
                        clz._logger.debug_verbose(f'{old_canonical}')
                        clz._logger.debug_verbose('New canonical')
                        clz._logger.debug_verbose(f'{new_canonical}')
                        printed_one = True
                # else:
                #    clz._logger.debug_verbose(f'old == new key: {old_key}')

    def old_load_includes_files(self):
        clz = type(self)
        if clz._old_includes_files_loaded:
            return
        print(f'In old_load_includes_files')
        # Start with each <Include> in Includes.xml
        for i in xpath.find('//include', xpath.findnode('//includes', self.xml)):
            file_attrib = i.attributes.get('file')
            if file_attrib:
                if VERBOSE_DEBUG:
                    clz._logger.debug_verbose(f'fileAttr: {file_attrib.value}')
                included_file_name: str = file_attrib.value
                included_file_path: Path = get_xbmc_skin_path(included_file_name)
                if not included_file_path.is_file():
                    continue
                xml = minidom.parse(included_file_path)
                includes = xpath.findnode('includes', xml)
                if VERBOSE_DEBUG:
                    clz._logger.debug_verbose(f"includes tag: {includes.tagName}")
                x = xpath.findnode('..', i)
                # print(f"type x: {type(x)}")
                # print(f"parent tag: {x.tagName}")
                # print(f"child tag: {i.tagName}")
                # print(f"old findnode .., i: {xpath.findnode('includes', i).tag}")
                # children = x.childNodes
                # for child in children:
                #     if child.nodeType == child.TEXT_NODE:
                #         print(f'pre-new child text: {child}')
                #     else:
                #         print(f'pre-new child tag: {child.tagName}')
                # if includes.isSameNode(x):
                #     print(f'includes is same as x')
                # dump: str = dump_dom(includes)
                # print(f'old pre-includes: {dump}')
                # dump: str = dump_dom(i)
                # print(f'old pre-i: {dump}')
                # root = xpath.findnode('..', i)
                #  dump: str = dump_dom(root)
                #  print(f'old pre-root: {dump}')
                xpath.findnode('..', i).replaceChild(includes, i)
                # dump: str = dump_dom(includes)
                # print(f'old post-includes: {dump}')
                # dump: str = dump_dom(i)
                # print(f'old post-i: {dump}')
                # root = xpath.findnode('..', i)
                #  dump: str = dump_dom(root)
                # print(f'old post-root: {dump}')

                # print(f'parent tag: {x.tagName}')
                # children = x.childNodes
                # for child in children:
                #     if child.nodeType == child.TEXT_NODE:
                #         print(f'post-new child text: {child}')
                #     else:
                #         print(f'post-new child tag: {child.tagName}')

                for sub_i in xpath.find('.//include', includes):
                    name_attrib = sub_i.attributes.get('name')
                    if name_attrib:
                        if name_attrib in clz._old_includes_map.keys():
                            clz._logger.debug_verbose(
                                    f'WARNING entry already in old map: {name_attrib}')
                        clz._old_includes_map[name_attrib.value] = sub_i
                        #  print(f'old_sub_i: {nameAttr} {sub_i.tagName} {
                        #  sub_i.attributes}')
                        #  print(f'{dump_dom(sub_i)}')
            else:
                name_attrib = i.attributes.get('name')
                if name_attrib:
                    if name_attrib in clz._old_includes_map.keys():
                        clz._logger.debug_verbose(
                            f'WARNING entry already in old map: {name_attrib}')
                    clz._old_includes_map[name_attrib.value] = i.cloneNode(True)
                    # print(f'old name entry: {name_attrib.value}')
                    # print(f'{dump_dom(i)}')

        clz._old_includes_files_loaded = True

    def new_load_includes_files(self):
        clz = type(self)
        if clz._new_includes_files_loaded:
            return
        """
        Includes.xml specifies a list xml files which in turn define fragments
        of xml which can be 'included' as 'macros' in other xml which reference
        the include by name. This method merges all of the include definitions
        into the Includes.xml element tree. This simplifies and speeds up the
        lookup of elements and attributes related to a control (or controls)
        which need to be voiced.
            
        Here, Includes.xml defines files which in turn define includes. Other
        elements are defined in Includes.xml, but they are left alone.
        
            <includes>
            <include file="Defaults.xml" />
            <include file="Includes_DialogSelect.xml" />
            <include file="ViewsVideoLibrary.xml" />
            <include file=.... />
            </includes>
            
        An individual includes file defines xml fragments which can be referenced
        by name.
           
        <includes>
            <include name="OSDButton">
                <width>76</width>
                <animation center="38,38" effect="zoom" end="100" reversible="false" 
                start="95" time="480" tween="back">Focus</animation>
                <height>76</height>
            </include>
            <include name="InfoDialogMetadata">
                <param name="onclick_condition">false</param>
                <definition>
                    <control type="togglebutton" id="$PARAM[control_id]">
                        <width>472</width>
                        <height>49</height>
                        <label>$PARAM[label]</label>
                        <altlabel>$PARAM[altlabel]</altlabel>
                        <visible>$PARAM[visible]</visible>
                    </control>
                </definition>
            </include>
            <include name="DefaultSettingButton">
                <param name="height">70</param>
                <definition>
                    <textoffsetx>$PARAM[textoffsetx]</textoffsetx>
                    <top>0</top>
                </definition>
            </include>
            </includes>
            
        This method merges all of this into the Includes.xml's ElementTree:
        
            <includes>
            <!-- The contents of "Defaults.xml" replace "<include file="Defaults.xml"
                 Note that "<Includes> element from the included file is omitted./> -->
            <include name="OSDButton">
                <width>76</width>
                <animation center="38,38" effect="zoom" end="100" reversible="false" 
                start="95" time="480" tween="back">Focus</animation>
                <height>76</height>
            </include>
            <include name="InfoDialogMetadata">
                <param name="onclick_condition">false</param>
                <definition>
                    <control type="togglebutton" id="$PARAM[control_id]">
                        <width>472</width>
                        <height>49</height>
                        <label>$PARAM[label]</label>
                        <altlabel>$PARAM[altlabel]</altlabel>
                        <visible>$PARAM[visible]</visible>
                    </control>
                </definition>
            </include>
            <include name="DefaultSettingButton">
                <param name="height">70</param>
                <definition>
                    <textoffsetx>$PARAM[textoffsetx]</textoffsetx>
                    <top>0</top>
                </definition>
            </include>
            <!-- Similarly, the contents of the other include files are added -->
            ...
            </includes>
         
        """
        clz._logger.debug_verbose(f'In new_load_includes_files')
        # Start with each <Include> in Includes.xml
        includes_root: ET.Element = self.et_includes_xml.getroot()

        '''
        Iterate over the raw xml from Includes.xml. Copy what we want to keep to
        a new xml document (omit color and position info, for example.). Also, 
        parse referenced include files, prune and insert their contents into 
        Includes.xml in-line, as well as in _new_includes_map.

        '''
        try:
            new_includes_tree: ET.ElementTree = ET.ElementTree()

            self.parse_includes_tree(includes_root, new_includes_tree.getroot())
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.debug_verbose(f'Exception: {e}')
        clz._new_includes_files_loaded = True
        return

    def parse_includes_tree(self, parent: ET.Element,
                            dest_node: ET.Element) -> None:
        clz = type(self)
        try:
            for child in parent.findall('./*'):
                if child.tag in IGNORED_TAGS:
                    continue
                if child.tag == 'include':
                    if child.attrib.get('file') is not None:
                        include_file_name: str = child.attrib.get('file')
                        included_file_path: Path = get_xbmc_skin_path(include_file_name)
                        included_xml: ET = ET.parse(str(included_file_path))
                        root = included_xml.getroot()
                        new_dest: ET.Element = ET.Element('dummy_root')
                        new_dest_tree: ET.ElementTree = ET.ElementTree(new_dest)
                        self.parse_includes_tree(root, new_dest)
                        # Nothing to put in new ElementTree. All includes were
                        # put into parse_includes_tree by call.
                        continue
                    else:
                        # If node is <include name=include_name>, then parse the
                        # include definition, then place in map.

                        include_name: str = child.attrib.get('name')
                        if include_name is not None:
                            new_parent: ET.Element = child
                            include_root: ET.Element = ET.Element('dummy_root')
                            self.parse_includes_tree(new_parent, include_root)

                            # Add this include definition into a dictionary
                            # for quick access
                            if include_name in clz._new_includes_map.keys():
                                clz._logger.debug_verbose(
                                        f'ERROR entry already in new map: {include_name}')
                            else:
                                # text: str = dump_subtree(new_parent)
                                # clz._logger.debug_verbose(f'ORIG: {text}')
                                # text: str = dump_subtree(include_root)
                                # clz._logger.debug_verbose(f'COMPLETE: {text}')
                                if VERBOSE_DEBUG:
                                    include_child: ET.Element = include_root.find('.*')
                                    if include_child is None:
                                        clz._logger.debug_verbose(
                                            f'Include: {include_name} omitted due to '
                                            f'empty')

                                clz._new_includes_map[include_name] = include_root
                                if VERBOSE_DEBUG:
                                    clz._logger.debug_verbose(
                                        f'Include {include_name} is:')
                                    clz._logger.debug_verbose(
                                        f'{dump_subtree(include_root)}')
                            continue
                    if child.attrib.get('content') is not None or child.text is not None:
                        # This is a reference to an include Just leave as is
                        self.parse_other(child, dest_node)
                        continue

                    clz._logger.debug_verbose(
                        f'Unexpected include element without "file" or "name".')
                    continue
                # Probably don't need to do this. Kodi probably expands this in any
                # expression that we send it for evaluation.
                if child.tag == 'constant':
                    if child.attrib.get('name'):
                        constant_name: str = child.attrib.get('name')
                        value: Any = child.text
                        if constant_name in clz.constant_definitions.keys():
                            clz._logger.debug_verbose(f'ERROR: constant already defined: '
                                                      f'{constant_name} value: {value}')
                        else:
                            clz.constant_definitions[constant_name] = value
                    continue
                # Probably don't need to do this. Kodi probably expands this in any
                # expression that we send it for evaluation.
                if child.tag == 'expression':
                    if child.attrib.get('name'):
                        expression_name: str = child.attrib.get('name')
                        value: str = child.text
                        if expression_name in clz.expression_definitions.keys():
                            clz._logger.debug_verbose(
                                f'ERROR: expression already defined: '
                                f'{expression_name} value: {value}')
                        else:
                            clz.expression_definitions[expression_name] = value
                    continue
                self.parse_other(child, dest_node)

        except StopIteration:
            pass
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('Boom!')
        return

    def parse_other(self, child: ET.Element, dest_node: ET.Element) -> None:
        clz = type(self)
        # Copy this non-handled or excluded child node to the new tree

        try:
            new_child: ET.Element
            new_child = ET.SubElement(dest_node, child.tag, child.attrib)
            new_child.text = child.text

            # Recurse to deal with grandchildren
            # orig_text: str = dump_subtree(child)
            include_root: ET.Element = ET.Element('dummy_root')
            self.parse_includes_tree(child, new_child)

            # clz._logger.debug_verbose(f'orig: {orig_text}')
            text: str = ''
            # text = dump_subtree(dest_node)
            # clz._logger.debug_verbose(f'changed: {text}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('Boom!')

    def new_load_includes_files_save(self):
        clz = type(self)
        if clz._new_includes_files_loaded:
            return
        """
        Includes.xml specifies a list xml files which in turn define fragments
        of xml which can be 'included' as 'macros' in other xml which reference
        the include by name. This method merges all of the include definitions
        into the Includes.xml element tree. This simplifies and speeds up the
        lookup of elements and attributes related to a control (or controls)
        which need to be voiced.

        Here, Includes.xml defines files which in turn define includes. Other
        elements are defined in Includes.xml, but they are left alone.

            <includes>
            <include file="Defaults.xml" />
            <include file="Includes_DialogSelect.xml" />
            <include file="ViewsVideoLibrary.xml" />
            <include file=.... />
            </includes>

        An individual includes file defines xml fragments which can be referenced
        by name.

        <includes>
            <include name="OSDButton">
                <width>76</width>
                <animation center="38,38" effect="zoom" end="100" reversible="false" 
                start="95" time="480" tween="back">Focus</animation>
                <height>76</height>
            </include>
            <include name="InfoDialogMetadata">
                <param name="onclick_condition">false</param>
                <definition>
                    <control type="togglebutton" id="$PARAM[control_id]">
                        <width>472</width>
                        <height>49</height>
                        <label>$PARAM[label]</label>
                        <altlabel>$PARAM[altlabel]</altlabel>
                        <visible>$PARAM[visible]</visible>
                    </control>
                </definition>
            </include>
            <include name="DefaultSettingButton">
                <param name="height">70</param>
                <definition>
                    <textoffsetx>$PARAM[textoffsetx]</textoffsetx>
                    <top>0</top>
                </definition>
            </include>
            </includes>

        This method merges all of this into the Includes.xml's ElementTree:

            <includes>
            <!-- The contents of "Defaults.xml" replace "<include file="Defaults.xml"
                 Note that "<Includes> element from the included file is omitted./> -->
            <include name="OSDButton">
                <width>76</width>
                <animation center="38,38" effect="zoom" end="100" reversible="false" 
                start="95" time="480" tween="back">Focus</animation>
                <height>76</height>
            </include>
            <include name="InfoDialogMetadata">
                <param name="onclick_condition">false</param>
                <definition>
                    <control type="togglebutton" id="$PARAM[control_id]">
                        <width>472</width>
                        <height>49</height>
                        <label>$PARAM[label]</label>
                        <altlabel>$PARAM[altlabel]</altlabel>
                        <visible>$PARAM[visible]</visible>
                    </control>
                </definition>
            </include>
            <include name="DefaultSettingButton">
                <param name="height">70</param>
                <definition>
                    <textoffsetx>$PARAM[textoffsetx]</textoffsetx>
                    <top>0</top>
                </definition>
            </include>
            <!-- Similarly, the contents of the other include files are added -->
            ...
            </includes>

        """
        clz._logger.debug_verbose(f'In new_load_includes_files')
        # Start with each <Include> in Includes.xml
        includes_root: ET.Element = self.et_includes_xml.getroot()
        include_parent: ET.Element  # should be the same as root node (no nesting)
        # Assume that an include definition does not contain more include definitions
        # (nested).
        try:
            for include_parent in self.et_includes_xml.findall('.//include/..'):
                clz._logger.debug_verbose(f'parent: {include_parent.tag}')
                assert (include_parent == includes_root)
                include_element: ET.Element
                for include_element in include_parent.findall('.//include'):
                    clz._logger.debug_verbose(
                        f'child (include_element): {include_element.tag} '
                        f'file: {include_element.attrib.get("file")}')
                    #
                    # Replace the include_element from the includes_root with
                    # the list of include elements defined in the included file,
                    # or in-line.
                    xml_data = ET.tostring(include_element, encoding='unicode')
                    clz._logger.debug_verbose(f'include_element: {xml_data}')
                    xml_data = ET.tostring(includes_root, encoding='unicode')
                    clz._logger.debug_verbose(f'includes_root: {xml_data}')
                    includes_root.remove(include_element)

                    included_file_name: str = include_element.attrib.get('file')
                    if included_file_name:
                        included_file_path: Path = get_xbmc_skin_path(included_file_name)
                        if not included_file_path.is_file():
                            continue

                        included_xml: ET = ET.parse(included_file_path)
                        included_root: ET.Element = included_xml.getroot()

                        if DEBUG:
                            clz._logger.debug_verbose(
                                f'included_file: {included_file_path}')
                        # new_includes: List[ET.Element] = root.find('includes')
                        # i.getparent().replace(i, root)
                        # Replace reference to include file with actual include(s)
                        # i.clear()
                        # if len(new_includes) == 1:
                        #     i.append(new_includes[0])
                        # else:
                        #    i.extend(new_includes)

                        # clz._logger.debug_verbose('new_includes', len(new_includes))
                        #  clz._logger.debug_verbose('i', len(i))
                        for include_definition in included_root.findall('.//include'):
                            include_definition: ET.Element
                            name_attrib: str
                            name_attrib = include_definition.attrib.get('name')
                            if name_attrib:
                                # Add this include definition into a dictionary
                                # for quick access
                                if name_attrib in clz._new_includes_map.keys():
                                    clz._logger.debug_verbose(
                                            f'ERROR entry already in new map: '
                                            f'{name_attrib}')
                                tmp_tree: ET = ET.ElementTree()
                                tmp_tree._setroot(copy.deepcopy(include_definition))
                                tmp_root = tmp_tree.getroot()
                                clz._new_includes_map[name_attrib] = tmp_root
                                includes_root.append(tmp_root)
                    else:
                        # Include element does not have a file attribute, but a name.
                        # This makes this an in-line include definition

                        include_definition: ET.Element = include_element
                        name_attrib: str = include_definition.attrib.get('name')
                        if name_attrib:
                            # Add this include definition into a dictionary
                            # for quick access
                            if name_attrib in clz._new_includes_map.keys():
                                clz._logger.debug_verbose(
                                        f'ERROR entry already in new map: {name_attrib}')
                            tmp_tree: ET = ET.ElementTree()
                            tmp_tree._setroot(copy.deepcopy(include_definition))
                            tmp_root = tmp_tree.getroot()
                            clz._new_includes_map[name_attrib] = tmp_root
                            includes_root.append(tmp_root)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.debug_verbose(f'Exception: {e}')
        clz._new_includes_files_loaded = True

    def lxml_load_includes_files(self):
        clz = type(self)
        if clz._lxml_includes_files_loaded:
            return

        # Start with each <Include> in Includes.xml
        for child in self.lxml_includes_xml.findall('.//include'):
            child: lxml_ET.Element
            # Load each include file
            #     <include file="ViewsVideoLibrary.xml" />
            include_file_name: str = child.attrib.get('file')
            if include_file_name:
                # for each include defined in the included file, link the
                # included fragment to the root element of Includes.xml
                included_file: Path
                included_file = get_xbmc_skin_path(include_file_name)
                if not included_file.is_file():
                    continue
                includes_xml: lxml_ET = lxml_ET.parse(included_file)
                includes_root = includes_xml.getroot()
                #
                # Should we replace a reference to the include file
                # or should every include in the tree be expanded?

                if VERBOSE_DEBUG:
                    clz._logger.debug_verbose(f'include_file: {included_file}')
                # new_includes: List[ET.Element] = root.find('includes')
                # i.getparent().replace(i, root)
                # Replace reference to include file with actual include(s)
                # name_attrib.clear()
                # if len(new_includes) == 1:
                #     i.append(new_includes[0])
                # else:
                #    i.extend(new_includes)

                # clz._logger.debug_verbose('new_includes', len(new_includes))
                #  clz._logger.debug_verbose('i', len(i))
                child.getparent().replace(child, includes_root)
                for new_sub_i in includes_root.findall('.//include'):
                    new_sub_i: lxml_ET.Element
                    name_attrib = new_sub_i.attrib.get('name')
                    if name_attrib:
                        if name_attrib in clz._new_includes_map.keys():
                            clz._logger.debug_verbose(
                                    f'ERROR entry already in new map: {name_attrib}')
                        tmp_tree: lxml_ET = lxml_ET.ElementTree()
                        tmp_tree._setroot(copy.deepcopy(new_sub_i))
                        tmp_root = tmp_tree.getroot()
                        clz._new_includes_map[name_attrib] = tmp_root
            else:
                name_attrib: str = child.attrib.get('name')
                if name_attrib:
                    if name_attrib in clz._new_includes_map.keys():
                        clz._logger.debug_verbose(
                            f'ERROR entry already in new map: {name_attrib}')
                    tmp_tree: lxml_ET = lxml_ET.ElementTree()
                    tmp_tree._setroot(copy.deepcopy(child))
                    tmp_root = tmp_tree.getroot()
                    clz._new_includes_map[name_attrib] = tmp_root
        '''
        for i in self.lxml_includes_xml.findall('.//include'):
            if isinstance(i, list):
                clz._logger.debug_verbose('length i: ', len(i))
            else:
                clz._logger.debug_verbose(i.tag, i.attrib, i.text)
        '''

        clz._lxml_includes_files_loaded = True

        #        import codecs
        #        with codecs.open(os.path.join(get_xbmc_skin_path(''),
        #        'Includes_Processed.xml'),'w','utf-8') as f: f.write(
        #        self.soup.prettify())

    def get_variable(self, name: str):
        """
        var = xpath.findnode(
                ".//variable[attribute::name='{0}']".format(name),
                xpath.findnode('includes', self.xml))
        if not var:
            return ''
        for val in xpath.find('.//value', var):
            conditionAttr = val.attributes.get('condition')
            if not conditionAttr:
                return val.childNodes[0].data or ''
            else:
                if xbmc.getCondVisibility(conditionAttr.value):
                    # print condition
                    # print repr(val.string)
                    return val.childNodes[0].data or ''
        """
        new_var = self.lxml_includes_xml.find(f'.//variable[@name={name}')
        if not new_var:
            return ''

        for new_val in new_var.find('.//value'):
            new_val: ET.Element
            condition_attr = new_val.get('condition')
            if not condition_attr:
                x = new_val.find('*')
            else:
                if xbmc.getCondVisibility(condition_attr):
                    return new_val
        return ''


IGNORED_TAGS: Set[str] = {'default',  # I think we don't care
                          'onclick',  # I think we don't care
                          'centertop', 'centerleft', 'width', 'height',
                          'top', 'bottom', 'left', 'right',  # 'description',
                          'scrolltime', 'itemlayout', 'aspectratio',
                          'align', 'aligny', 'font', 'scroll',
                          'shadowcolor', 'texture', 'angle', 'textcolor',
                          'wrapmultiline', 'scrollspeed', 'centerright',
                          'centerbottom', 'camera', 'colordiffuse',
                          'hitrect', 'hitrectcolor', 'pulseonselect',
                          'textcolor', 'textoffsetx', 'scrollout',
                          'pauseatend', 'scrollspeed', 'randomize',
                          'focusedcolor', 'disabledcolor', 'invalidcolor',
                          'shadowcolor', 'textoffsety', 'textwidth',
                          'background', 'fadetime', 'bordersize',
                          'imagepath', 'timeperimage', 'pauseatend',
                          'loop', 'texturenofocus', 'texturefocus',
                          'textureradioonfocus', 'textureradioon',
                          'textureradioondisabled', 'textureradioofffucus',
                          'textureradiooffnofocus', 'textureradiooff',
                          'textureradioondisabled',
                          'focusedcolor', 'disabledcolor', 'textoffsetx',
                          'textoffsety', 'textwidth', 'radioposx', 'radioposy',
                          'radioheight', 'alttexturefocus', 'alttexturenofocus',
                          'usealttexture', 'texturefocusdowndisabled',
                          'spincolor', 'reverse',  # 'orientation',
                          'itemgap', 'ondown', 'onup', 'usecontrolcoords',
                          'thumb', 'backgroundcolor', 'animation', 'onfocus',
                          'onclick'
                          }


def getWindowParser() -> WindowParser:
    path: Path = currentWindowXMLFile()
    module_logger.debug_extra_verbose(f'getWindowParser path: {path}')
    module_logger.debug(f'getWindowParser path: {path}')
    if not path:
        return
    return WindowParser(path)


def getWindowParser2(xml_path: Path) -> WindowParser:
    module_logger.debug_extra_verbose(f'getWindowParser2 path: {xml_path}')
    return WindowParser(xml_path)
