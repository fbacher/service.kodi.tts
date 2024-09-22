# -*- coding: utf-8 -*-
from __future__ import annotations
from common.exceptions import reraise
import copy
import os
import pathlib
import sys
from xml.dom import minidom
import logging

import xml.etree.ElementTree as lxml_ET
from xml.etree import ElementTree as ET
from typing import Any, Dict, ForwardRef, List, Set
from pathlib import Path

import xpath
from common import AbortException

USE_OLD_FUNCTIONS: bool = False
USE_NEW_FUNCTIONS: bool = True
USE_LXML_FUNCTIONS: bool = False
USE_XML_ELEMENTS: bool = True
USE_LXML: bool = False

VERBOSE_DEBUG: bool = False
DEBUG: bool = True

logging.basicConfig(filename='c:/Users/fbacher/mylog.log',  filemode='w', level=logging.DEBUG)
logger: logging = logging.getLogger('root')


def get_xbmc_skin_path(file_name: str) -> pathlib.Path:
    base_path: pathlib.Path = pathlib.Path('c:/Users/fbacher/kodi.new/addons/skin.estuary/xml')
    # 'c:/Users/fbacher/AppData/Roaming/Kodi/addons/skin.estuary/xml')
    return base_path / file_name


def dump_dom(entries) -> str:

    dom_impl = minidom.getDOMImplementation()
    wrapper = dom_impl.createDocument(None, 'fake_root', None)
    fake_root = wrapper.documentElement
    dump: str | None = None
    if isinstance(entries, list):
        logger.debug(f'list of DOM entries len: {len(entries)}')
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
        logger.exception('Narf!')
        xmlstr = ''
    return xmlstr

WINDOWS: list[str] = ['Home.xml',
                      'FileBrowser.xml',
                      'DialogMusicInfo.xml']



class Foo:
    _logger: logging = None
    includes: Includes = None

    def __init__(self, xml_path: str):
        xml_path: Path = get_xbmc_skin_path(str(xml_path))
        clz = type(self)
        if clz._logger is None:
            clz._logger = logger
        if VERBOSE_DEBUG:
            clz._logger.debug(f'Initializing {clz}')
        self.current_window_path: Path = xml_path
        # if USE_OLD_FUNCTIONS:
        #     self.xml = minidom.parse(str(xml_path))
        # if USE_LXML:
        #     self.lxml_includes_xml: lxml_ET.ElementTree = lxml_ET.parse(xml_path)
        #     self.lxml_root: lxml_ET.Element = self.lxml_includes_xml.getroot()
        self.et_includes_xml: ET.ElementTree = ET.parse(xml_path)
        self.et_root: ET.Element = self.et_includes_xml.getroot()

        # self.build_reverse_tree_map(self.et_root, xml_path)

        clz._logger.debug(f'xml: {xml_path}')
        self.currentControl = None
        if clz.includes is None:
            clz.includes = Includes()

        dummy_root: ET.Element = ET.Element(f'dummy_root')
        dummy_root.append(self.et_root)
        result_dummy_root: ET.Element = clz.includes.expand_includes(dummy_root)
        result: ET.Element = result_dummy_root.find('./*')
        if VERBOSE_DEBUG:
            clz._logger.debug(f'expanded result: {dump_subtree(result)}')
        self.et_root = result

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

        Notes: an include definition can contain references to other includes which requires
               expanding these includes that were just included. Basically any branch
               in the document must be traversed and have includes expanded.

        Example xml for a window:

        <window>
            <defaultcontrol always="true">9000</defaultcontrol>
            <onunload condition="Container(9000).Hasfocus(10) | Container(9000).Hasfocus(11) | ControlGroup(9010).HasFocus | ControlGroup(9016).HasFocus | ControlGroup(9017).HasFocus">SetProperty(VideosDirectLink,True)</onunload>
                <controls>
                    <control type="list" id="90160">
                        <left>-10</left>
                        <top>-10</top>
                        <visible>Library.HasContent(Movies)</visible>
                    </control>
                    <include condition="!Skin.HasSetting(HomepageHideRecentlyAddedVideo) | !Skin.HasSetting(HomepageHideRecentlyAddedAlbums)">HomeRecentlyAddedInfo</include>
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
        include_parents: List[ET.Element] = self.et_includes_xml.findall('.//include/..')
        for include_parent in include_parents:
            # Ignore any includes which are not relevant, due to it not
            # being visible. (Is it always true that an invisible
            # item has no impact on gui?)

            # We just need the name of the include and any condition
            include: ET.Element = include_parent.find('include')
            condition: str | None = include.attrib.get('condition')
            if VERBOSE_DEBUG:
                clz._logger.debug(
                    f'include {include.tag} {include.attrib} {include.text}')
            include_name: str = ''
            if condition and False:  # and not xbmc.getCondVisibility(condition):
                # Purge this inactive branch
                include_name: str = include.text
                if VERBOSE_DEBUG:
                    clz._logger.debug(f'{include.tag} {include.attrib}'
                                      f' text: {include.text} tail: {include.tail}')

                    dump: str = ET.tostring(include_parent, encoding='unicode')
                    clz._logger.debug(f'parent before removing include:\n {dump}')
                    clz._logger.debug(
                        f'removing include {include_name} from {include_parent.tag}')
                include_parent.remove(include)
                if VERBOSE_DEBUG:
                    dump: str = ET.tostring(include_parent, encoding='unicode')
                    clz._logger.debug(f'parent after removing include:\n {dump}')
                continue
            else:
                #  The include stays. Replace the include element with it's
                #  reference.

                # Does this include for this window refer to one in the
                # Include Tree? get_include uses the name attribute of an include
                # to find the body of the include_ref.

                expanded_include: ET.Element = clz.includes.get_include(include_name)
                if expanded_include is None:
                    clz._logger.debug(f'INCLUDE NOT FOUND: {include.text}')
                    continue

                # Yes, the window refers to an include which our include tree
                # has the body of the include. Import that include into
                # our Window's tree.

                # print 'INCLUDE FOUND: %s' % i.string
                if VERBOSE_DEBUG:
                    dump: str = dump_subtree(include_parent)
                    clz._logger.debug(f'parent before replacing include:\n {dump}')
                include_parent.remove(include)
                if VERBOSE_DEBUG:
                    dump: str = ET.tostring(include, encoding='unicode')
                    clz._logger.debug(f'removed include: \n{dump}')
                    dump: str = dump_subtree(expanded_include)
                    clz._logger.debug(f'expanded_include to append: \n{dump}')
                include_parent.append(expanded_include)  # Order should not matter
                if VERBOSE_DEBUG:
                    dump: str = dump_subtree(include_parent)
                    clz._logger.debug(f'parent after replacing include:\n {dump}')

class Includes:
    _logger: logging.Logger = logger
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
        path = get_xbmc_skin_path('c:/Users/fbacher/kodi.new/addons/skin.estuary/xml/Includes.xml')
        self.xml = minidom.parse(str(path))
        if USE_LXML:
            self.lxml_includes_xml: lxml_ET.ElementTree = lxml_ET.parse(str(path))
            self.lxml_root: lxml_ET.Element = self.lxml_includes_xml.getroot()
        self.et_includes_xml: ET.ElementTree = ET.parse(str(path))
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
        # clz._logger.debug(f'In load_includes_files')
        # clz._logger.debug(f'Also in load_includes_files')
        if clz._old_includes_files_loaded or clz._new_includes_files_loaded:
            return

        if USE_OLD_FUNCTIONS:
            self.old_load_includes_files()
        if USE_NEW_FUNCTIONS:
            self.new_load_includes_files()

        if USE_LXML:
            self.lxml_load_includes_files()

        if USE_OLD_FUNCTIONS and USE_NEW_FUNCTIONS and False:
            try:
                if len(clz._old_includes_map.keys()) != len(clz._new_includes_map.keys()):
                    clz._logger.debug(f'Include maps of different size: old: '
                                      f'{len(clz._old_includes_map.keys())} new: '
                                      f'{len(clz._new_includes_map.keys())}')
                printed_one: bool = False
                for old_key, old_elements in clz._old_includes_map.items():
                    old_xml: str = dump_dom(old_elements)
                    from_old: ET = ET.fromstring(old_xml)
                    from_new_elements: ET.Element = clz._new_includes_map.get(old_key)
                    old_canonical: str = ET.canonicalize(xml_data=old_xml,
                                                         strip_text=True)
                    new_canonical: str = ''
                    if from_new_elements is None:
                        clz._logger.debug(f'Can not find {old_key} in new_includes_map')
                        continue
                    new_canonical: str = ET.canonicalize(
                        xml_data=ET.tostring(from_new_elements, encoding='unicode'),
                        strip_text=True)
                    if old_canonical != new_canonical:
                        clz._logger.debug(f'old != new key: {old_key}')
                        if not printed_one:
                            clz._logger.debug(f'Old canonical')
                            clz._logger.debug(f'{old_canonical}')
                            clz._logger.debug('New canonical')
                            clz._logger.debug(f'{new_canonical}')
                            printed_one = True
                    # else:
                    #    clz._logger.debug(f'old == new key: {old_key}')
            except AbortException:
                reraise(*sys.exc_info())
            except Exception as e:
                clz._logger.exception('Boom Boom!')

    def old_load_includes_files(self):
        clz = type(self)
        if clz._old_includes_files_loaded:
            return
        try:
            clz._logger.debug(f'In old_load_includes_files')
            base_path = get_xbmc_skin_path('')
            # Start with each <Include> in Includes.xml
            for i in xpath.find('//include', xpath.findnode('//includes', self.xml)):
                file_attrib = i.attributes.get('file')
                if file_attrib:
                    if VERBOSE_DEBUG:
                        clz._logger.debug(f'file_attrib: {file_attrib.value}')
                    xml_name: str = file_attrib.value
                    p = os.path.join(base_path, xml_name)
                    if not os.path.exists(p):
                        continue
                    xml = minidom.parse(p)
                    includes = xpath.findnode('includes', xml)
                    if VERBOSE_DEBUG:
                        clz._logger.debug(f"includes tag: {includes.tagName}")
                    x = xpath.findnode('..', i)
                    # clz._logger.debug(f"type x: {type(x)}")
                    # clz._logger.debug(f"parent tag: {x.tagName}")
                    # clz._logger.debug(f"child tag: {i.tagName}")
                    # clz._logger.debug(f"old findnode .., i: {xpath.findnode('includes', i).tag}")
                    # children = x.childNodes
                    # for child in children:
                    #     if child.nodeType == child.TEXT_NODE:
                    #         clz._logger.debug(f'pre-new child text: {child}')
                    #     else:
                    #         clz._logger.debug(f'pre-new child tag: {child.tagName}')
                    # if includes.isSameNode(x):
                    #     clz._logger.debug(f'includes is same as x')
                    # dump: str = dump_dom(includes)
                    # clz._logger.debug(f'old pre-includes: {dump}')
                    # dump: str = dump_dom(i)
                    # clz._logger.debug(f'old pre-i: {dump}')
                    # root = xpath.findnode('..', i)
                    #  dump: str = dump_dom(root)
                    #  clz._logger.debug(f'old pre-root: {dump}')
                    xpath.findnode('..', i).replaceChild(includes, i)
                    # dump: str = dump_dom(includes)
                    # clz._logger.debug(f'old post-includes: {dump}')
                    # dump: str = dump_dom(i)
                    # clz._logger.debug(f'old post-i: {dump}')
                    # root = xpath.findnode('..', i)
                    #  dump: str = dump_dom(root)
                    # clz._logger.debug(f'old post-root: {dump}')

                    # clz._logger.debug(f'parent tag: {x.tagName}')
                    # children = x.childNodes
                    # for child in children:
                    #     if child.nodeType == child.TEXT_NODE:
                    #         clz._logger.debug(f'post-new child text: {child}')
                    #     else:
                    #         clz._logger.debug(f'post-new child tag: {child.tagName}')

                    for sub_i in xpath.find('.//include', includes):
                        name_attrib = sub_i.attributes.get('name')
                        if name_attrib:
                            if name_attrib in clz._old_includes_map.keys():
                                clz._logger.debug(
                                    f'WARNING entry already in old map: {name_attrib}')
                            clz._old_includes_map[name_attrib.value] = sub_i
                            #  clz._logger.debug(f'old_sub_i: {name_attrib} {sub_i.tagName} {
                            #  sub_i.attributes}')
                            #  clz._logger.debug(f'{dump_dom(sub_i)}')
                else:
                    name_attrib = i.attributes.get('name')
                    if name_attrib:
                        if name_attrib in clz._old_includes_map.keys():
                            clz._logger.debug(f'WARNING entry already in old map: {name_attrib}')
                        clz._old_includes_map[name_attrib.value] = i.cloneNode(True)
                        # clz._logger.debug(f'old name entry: {name_attrib.value}')
                        # clz._logger.debug(f'{dump_dom(i)}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('Boom!')

        clz._old_includes_files_loaded = True

    '''
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
                <animation center="38,38" effect="zoom" end="100" reversible="false" start="95" time="480" tween="back">Focus</animation>
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
                <animation center="38,38" effect="zoom" end="100" reversible="false" start="95" time="480" tween="back">Focus</animation>
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
        clz._logger.debug(f'In new_load_includes_files')
        base_path: pathlib.Path = get_xbmc_skin_path('')
        # Start with each <Include> in Includes.xml
        includes_root: ET.Element = self.et_includes_xml.getroot()
        include_parent: ET.Element  # should be the same as root node (no nesting)
        # Assume that an include definition does not contain more include definitions
        # (nested).
        try:
            for include_parent in self.et_includes_xml.findall('.//include/..'):
                clz._logger.debug(f'parent: {include_parent.tag}')
                assert (include_parent == includes_root)
                include_element: ET.Element
                for include_element in include_parent.findall('.//include'):
                    clz._logger.debug(f'child (include_element): {include_element.tag} '
                                      f'file: {include_element.attrib.get("file")}')
                    #
                    # Replace the include_element from the includes_root with
                    # the list of include elements defined in the included file,
                    # or in-line.
                    xml_data = ET.tostring(include_element, encoding='unicode')
                    clz._logger.debug(f'include_element: {xml_data}')
                    xml_data = ET.tostring(includes_root, encoding='unicode')
                    clz._logger.debug(f'includes_root: {xml_data}')
                    includes_root.remove(include_element)

                    included_file_name: str = include_element.attrib.get('file')
                    if included_file_name:
                        included_file_path: Path = base_path / included_file_name
                        if not included_file_path.is_file():
                            continue

                        included_xml: ET = ET.parse(included_file_path)
                        included_root: ET.Element = included_xml.getroot()

                        if DEBUG:
                            clz._logger.debug(f'included_file: {included_file_path}')
                        # new_includes: List[ET.Element] = root.find('includes')
                        # i.getparent().replace(i, root)
                        # Replace reference to include file with actual include(s)
                        # i.clear()
                        # if len(new_includes) == 1:
                        #     i.append(new_includes[0])
                        # else:
                        #    i.extend(new_includes)

                        # clz._logger.debug('new_includes', len(new_includes))
                        #  clz._logger.debug('i', len(i))
                        for include_definition in included_root.findall('.//include'):
                            include_definition: ET.Element
                            name_attrib: str
                            name_attrib = include_definition.attrib.get('name')
                            if name_attrib:
                                # Add this include definition into a dictionary
                                # for quick access
                                if name_attrib in clz._new_includes_map.keys():
                                    clz._logger.debug(
                                        f'ERROR entry already in new map: {name_attrib}')
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
                                clz._logger.debug(
                                    f'ERROR entry already in new map: {name_attrib}')
                            tmp_tree: ET = ET.ElementTree()
                            tmp_tree._setroot(copy.deepcopy(include_definition))
                            tmp_root = tmp_tree.getroot()
                            clz._new_includes_map[name_attrib] = tmp_root
                            includes_root.append(tmp_root)
        except Exception as e:
            clz._logger.debug(f'Exception: {e}')
        clz._new_includes_files_loaded = True

    '''
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
                <animation center="38,38" effect="zoom" end="100" reversible="false" start="95" time="480" tween="back">Focus</animation>
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
                <animation center="38,38" effect="zoom" end="100" reversible="false" start="95" time="480" tween="back">Focus</animation>
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
        # clz._logger.debug(f'In new_load_includes_files')
        # Start with each <Include> in Includes.xml
        includes_root: ET.Element = self.et_includes_xml.getroot()

        """
        Iterate over the raw xml from Includes.xml. Copy what we want to keep to
        a new xml document (omit color and position info, for example.). Also,
        parse referenced include files, prune and insert their contents into
        Includes.xml in-line, as well as in _new_includes_map.

        """
        try:
            new_includes_root: ET.Element = ET.Element('dummy_root')
            new_includes_tree: ET.ElementTree = ET.ElementTree(new_includes_root)

            self.parse_includes_tree(includes_root, new_includes_tree.getroot())
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.debug(f'Exception: {e}')
        clz._new_includes_files_loaded = True
        return

    def expand_includes(self, parent: ET.Element) -> ET.Element:
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
                        clz._logger.debug(f'Ignoring Include file import: {included_file_path}')
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
                            clz._logger.debug(f'Ignoring Include file definition: {include_name}')
                            # new_parent: ET.Element = child
                            # include_root: ET.Element = ET.Element('dummy_root')
                            # include_tree: ET.ElementTree = ET.ElementTree(include_root)
                            # self.parse_includes_tree(new_parent, include_root)

                            # Add this include definition into a dictionary
                            # for quick access
                            # if include_name in clz._new_includes_map.keys():
                            #     clz._logger.debug(
                            #         f'ERROR entry already in new map: {include_name}')
                            # else:
                            #     text: str = dump_subtree(new_parent)
                            #     clz._logger.debug(f'ORIG: {text}')
                            #     text: str = dump_subtree(include_root)
                            #     clz._logger.debug(f'COMPLETE: {text}')
                            #     include_child: ET.Element = include_root.find('.*')
                            #     if include_child is not None:
                            #         clz._new_includes_map[include_name] = include_child
                            #     else:
                            #         clz._logger.debug(f'Include: {include_name} omitted due to empty')
                            continue
                    if child.attrib.get('content') is not None or child.text is not None:
                        include_name: str = child.attrib.get('content')
                        if include_name is None:
                            include_name = child.text
                        include_root: ET.Element = self.get_include(include_name)
                        if include_root is None:
                            clz._logger.debug(f'Could not find definition for include: {include_name}')
                        else:
                            if VERBOSE_DEBUG:
                                clz._logger.debug(f'found definition for include: {include_name}')
                                clz._logger.debug(dump_subtree(include_root))
                            expanded_dummy: ET.Element = self.expand_includes(include_root)
                            if VERBOSE_DEBUG:
                                clz._logger.debug(f'Expanded includes: {include_name} {dump_subtree(expanded_dummy)}')
                            result.extend(expanded_dummy.findall(''))
                        x = result.findall('.//include')
                        if x is not None and len(x) > 0:
                            clz._logger.debug(f'include FOUND in result')
                            clz._logger.debug(f'{dump_subtree(include_root)}')
                        continue

                    clz._logger.debug(f'Unexpected include element without "file" or "name".')
                    continue
                # Probably don't need to do this. Kodi probably expands this in any
                # expression that we send it for evaluation.
                '''
                if child.tag == 'constant':
                    if child.attrib.get('name'):
                        constant_name: str = child.attrib.get('name')
                        value: Any = child.text
                        if constant_name in clz.constant_definitions.keys():
                            clz._logger.debug(f'ERROR: constant already defined: '
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
                            clz._logger.debug(f'ERROR: constant already defined: '
                                              f'{expression_name} value: {value}')
                        else:
                            clz.expression_definitions[expression_name] = value
                    continue
                '''
                # x = result_dummy_root.findall('.//include')
                # if x is not None and len(x) > 0:
                #     clz._logger.debug(f'include FOUND in result')
                dummy_root: ET.Element | None = self.expand_other(child)
                # x = dummy_root.findall('.//include')
                # if x is not None and len(x) > 0:
                #     clz._logger.debug(f'include FOUND in result')
                result_dummy_root.extend(dummy_root.findall('./*'))

        except StopIteration:
            pass
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('Boom!')

        if VERBOSE_DEBUG:
            clz._logger.debug(f'expand includes: {dump_subtree(result_dummy_root)}')
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
                clz._logger.debug(f'include FOUND in result')
            result_dummy_root: ET.Element = self.expand_includes(child)
            new_child.extend(result_dummy_root.findall('./*'))

            # clz._logger.debug(f'orig: {orig_text}')
            text: str = ''
            # text = dump_subtree(dest_node)
            # clz._logger.debug(f'changed: {text}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('Boom!')
        if VERBOSE_DEBUG:
            clz._logger.debug(f'expand_other: {dump_subtree(dummy_root)}')
            x = dummy_root.findall('.//include')
            if x is not None and len(x) > 0:
                clz._logger.debug(f'include FOUND in result')
        return dummy_root

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
                                clz._logger.debug(
                                    f'ERROR entry already in new map: {include_name}')
                            else:
                                # text: str = dump_subtree(new_parent)
                                # clz._logger.debug(f'ORIG: {text}')
                                # text: str = dump_subtree(include_root)
                                # clz._logger.debug(f'COMPLETE: {text}')
                                if VERBOSE_DEBUG:
                                    include_child: ET.Element = include_root.find('.*')
                                    if include_child is None:
                                        clz._logger.debug(f'Include: {include_name} omitted due to empty')

                                clz._new_includes_map[include_name] = include_root
                                if VERBOSE_DEBUG:
                                    clz._logger.debug(f'Include {include_name} is:')
                                    clz._logger.debug(f'{dump_subtree(include_root)}')
                            continue
                    if child.attrib.get('content') is not None or child.text is not None:
                        # This is a reference to an include Just leave as is
                        self.parse_other(child, dest_node)
                        continue

                    clz._logger.debug(f'Unexpected include element without "file" or "name".')
                    continue
                # Probably don't need to do this. Kodi probably expands this in any
                # expression that we send it for evaluation.
                if child.tag == 'constant':
                    if child.attrib.get('name'):
                        constant_name: str = child.attrib.get('name')
                        value: Any = child.text
                        if constant_name in clz.constant_definitions.keys():
                            clz._logger.debug(f'ERROR: constant already defined: '
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
                            clz._logger.debug(f'ERROR: expression already defined: '
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

            # clz._logger.debug(f'orig: {orig_text}')
            text: str = ''
            # text = dump_subtree(dest_node)
            # clz._logger.debug(f'changed: {text}')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('Boom!')

    def lxml_load_includes_files(self):
        clz = type(self)
        if clz._lxml_includes_files_loaded:
            return
        base_path: Path = get_xbmc_skin_path('')
        # Start with each <Include> in Includes.xml
        for child in self.lxml_includes_xml.findall('.//include'):
            child: lxml_ET.Element
            # Load each include file
            #     <include file="ViewsVideoLibrary.xml" />
            file_attrib: str = child.attrib.get('file')
            if file_attrib is not None:
                # for each include defined in the included file, link the
                # included fragment to the root element of Includes.xml
                xml_name: str = file_attrib
                included_file: Path
                included_file = base_path / xml_name
                if not (included_file.is_file() and included_file.exists()):
                    continue
                includes_xml: lxml_ET = lxml_ET.parse(str(included_file))
                includes_root = includes_xml.getroot()
                #
                # Should we replace a reference to the include file
                # or should every include in the tree be expanded?

                if VERBOSE_DEBUG:
                    clz._logger.debug(f'include_file: {included_file}')
                # new_includes: List[ET.Element] = root.find('includes')
                # i.getparent().replace(i, root)
                # Replace reference to include file with actual include(s)
                # i.clear()
                # if len(new_includes) == 1:
                #     i.append(new_includes[0])
                # else:
                #    i.extend(new_includes)

                # clz._logger.debug('new_includes', len(new_includes))
                #  clz._logger.debug('i', len(i))
                child.getparent().replace(child, includes_root)
                for new_sub_i in includes_root.findall('.//include'):
                    new_sub_i: lxml_ET.Element
                    name_attrib = new_sub_i.attrib.get('name')
                    if name_attrib:
                        if name_attrib in clz._new_includes_map.keys():
                            clz._logger.debug(
                                f'ERROR entry already in new map: {name_attrib}')
                        tmp_tree: lxml_ET = lxml_ET.ElementTree()
                        tmp_tree._setroot(copy.deepcopy(new_sub_i))
                        tmp_root = tmp_tree.getroot()
                        clz._new_includes_map[name_attrib] = tmp_root
            else:
                name_attrib = child.attrib.get('name')
                if name_attrib:
                    if name_attrib in clz._new_includes_map.keys():
                        clz._logger.debug(f'ERROR entry already in new map: {name_attrib}')
                    tmp_tree: lxml_ET = lxml_ET.ElementTree()
                    tmp_tree._setroot(copy.deepcopy(child))
                    tmp_root = tmp_tree.getroot()
                    clz._new_includes_map[name_attrib] = tmp_root
        '''
        for i in self.lxml_includes_xml.findall('.//include'):
            if isinstance(i, list):
                clz._logger.debug('length i: ', len(i))
            else:
                clz._logger.debug(i.tag, i.attrib, i.text)
        '''

        clz._lxml_includes_files_loaded = True

        #        import codecs
        #        with codecs.open(os.path.join(get_xbmc_skin_path(''),
        #        'Includes_Processed.xml'),'w','utf-8') as f: f.write(self.soup.prettify())

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
                    # clz._logger.debug condition
                    # clz._logger.debug repr(val.string)
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
                if True:
                    return new_val
        return ''


IGNORED_TAGS: Set[str] = {'default',  # I think we don't care
                          'onclick',  # I think we don't care
                          'centertop', 'centerleft', 'width', 'height',
                          'top', 'bottom', 'left', 'right', 'description',
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
                          'spincolor', 'reverse', 'orientation',
                          'itemgap', 'ondown', 'onup', 'usecontrolcoords',
                          'thumb', 'backgroundcolor', 'animation', 'onfocus',
                          'onclick'
                          }


if __name__ == '__main__':
    Foo(WINDOWS[0])

    # sys.exit()
    #
    # includes = Includes()
    # includes.load_includes_files()
    #  WindowParser('c:/Users/fbacher/AppData/Roaming/Kodi/addons/skin.estuary/xml/Home.xml')

    sys.exit()
