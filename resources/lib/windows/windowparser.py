# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import copy
import os
import re
import xml.dom.minidom as minidom

import xbmc
import xbmcvfs
from lxml import etree as ET

import xpath
from common import *
from common.constants import Constants
from common.logger import *

#  import xml.etree.ElementTree as ET

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_module_logger(module_path=__file__)
else:
    module_logger = BasicLogger.get_module_logger()

USE_NEW_FUNCTIONS: Final[bool] = True
USE_OLD_FUNCTIONS: Final[bool] = False
VERBOSE_DEBUG: bool = False


def currentWindowXMLFile():
    base = xbmc.getInfoLabel('Window.Property(xmlfile)')
    if os.path.exists(base):
        return base
    path = getXBMCSkinPath(base)
    if os.path.exists(path):
        return path
    return None


def currentWindowIsAddon():
    path = xbmc.getInfoLabel('Window.Property(xmlfile)')
    if not path:
        return None
    return os.path.exists(path)


def getXBMCSkinPath(fname):
    for res in ('720p', '1080i'):
        skinpath = os.path.join(xbmcvfs.translatePath('special://skin'), res)
        if os.path.exists(skinpath):
            break
    else:
        aspect = xbmc.getInfoLabel('Skin.AspectRatio')
        addonXMLPath = os.path.join(
                xbmcvfs.translatePath('special://skin'), 'addon.xml')
        skinpath = ''
        if os.path.exists(addonXMLPath):
            with open(addonXMLPath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for l in lines:
                if 'aspect="{0}"'.format(aspect) in l:
                    folder = l.split('folder="', 1)[-1].split('"', 1)[0]
                    skinpath = os.path.join(
                            xbmcvfs.translatePath('special://skin'), folder)
    path = os.path.join(skinpath, fname)
    if os.path.exists(path):
        return path
    path = os.path.join(skinpath, fname.lower())
    if os.path.exists(path):
        return path
    return ''


def dump_dom(entries) -> str:

    dom_impl = minidom.getDOMImplementation()
    wrapper = dom_impl.createDocument(None, 'fake_root', None)
    fake_root = wrapper.documentElement
    dump: str = None
    if isinstance(entries, list):
        print(f'list of DOM entries len: {len(entries)}')
        for x in entries:
            fake_root.appendChild(x)
    else:
        # fake_root.appendChild(entries)
        dump = entries.toprettyxml(newl='')
    if dump is None:
        dump: str = fake_root.toprettyxml(newl='')

    return dump


# Compiler wants global flag (?i) at beginning
# tagRE = re.compile(r'\[/?(?:B|I|COLOR|UPPERCASE|LOWERCASE)[^\]]*\](?i)')


tagRE = re.compile(r'(?i)\[/?(?:B|I|COLOR|UPPERCASE|LOWERCASE)[^]]*]')
varRE = re.compile(r'\$VAR\[([^]]*)]')
localizeRE = re.compile(r'\$LOCALIZE\[([^]]*)]')
addonRE = re.compile(r'\$ADDON\[[\w+.]+ (\d+)]')
infoLableRE = re.compile(r'\$INFO\[([^]]*)]')


def getInfoLabel(info, container):
    if container:
        info = info.replace(
                'ListItem.', f'Container({container}).ListItem.')
    return xbmc.getInfoLabel(info)


def nodeParents(dom, node) -> List[Any] | None:
    parents = []
    try:
        parent = xpath.findnode('..', node)
        while parent and not isinstance(parent, minidom.Document):
            parents.append(parent)
            parent = xpath.findnode('..', parent)
        return parents
    except Exception:
        module_logger.exception('')
        return None


def new_nodeParents(dom: ET.ElementTree, node: ET.Element) -> List[ET.Element]:
    new_parents: List[ET.Element] = []
    new_parent: ET.Element = node.getparent()
    while new_parent is not None:
        new_parents.append(new_parent)
        new_parent = new_parent.getparent()
        #  module_logger.debug(f'parent: {parent} parent_new: {parent_new}')
    return new_parents


def extractInfos(text, container):
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

    def __init__(self, xml_path: str):
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        self.current_window_path: str = xml_path
        if USE_OLD_FUNCTIONS:
            self.xml = minidom.parse(xml_path)
        self.new_xml: ET.ElementTree = ET.parse(xml_path)
        self.root: ET.Element = self.new_xml.getroot()
        clz._logger.debug(f'xml: {xml_path}')
        self.currentControl = None
        if clz.includes is None:
            clz.includes = Includes()

        if not currentWindowIsAddon():
            self.processIncludes()

    #            import codecs
    #            with codecs.open(os.path.join(getXBMCSkinPath(''),'TESTCurrent.xml'),
    #            'w','utf-8') as f: f.write(self.soup.prettify())

    def processIncludes(self):
        if USE_OLD_FUNCTIONS:
            self.old_processIncludes()
        if USE_NEW_FUNCTIONS:
            self.new_processIncludes()

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
            clz._logger.debug(
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
                clz._logger.debug(f"include tag: {include.tagName}")
            parent = xpath.findnode('..', include)
            conditionAttr = include.attributes.get('condition')
            if conditionAttr and not xbmc.getCondVisibility(conditionAttr.value):
                # Not visible, include is not relevant
                if VERBOSE_DEBUG:
                    dump = dump_dom(parent)
                    clz._logger.debug(f'parent of include: {dump}')
                parent.removeChild(include)
                if VERBOSE_DEBUG:
                    dump = dump_dom(parent)
                    clz._logger.debug(
                        f'parent of include after removing child include: \n{dump}')
                continue

            # Does this include for this window refer to one in the
            # Include Tree?
            node_name: str = include.childNodes[0].data
            matchingInclude = clz.includes.get_old_include(node_name)

            #  if matchingInclude:
            #     child = include.childNodes[0]
            #     dump = dump_dom(include)
            #     clz._logger.debug(f'INCLUDE FOUND: {child}')
            #     clz._logger.debug(f'{dump}')

            if not matchingInclude:
                #  for child in include.childNodes:
                #  dump = dump_dom(child)
                #  clz._logger.debug(f'INCLUDE NOT FOUND: {child}\n{dump}')
                continue

            # Yes, the window refers to an include which our include tree
            # has the body of the include. Import that include into
            # our Window's tree.

            new = matchingInclude.cloneNode(True)
            if VERBOSE_DEBUG:
                dump = dump_dom(parent)
                clz._logger.debug(f'parent of include: {dump}')

            parent.replaceChild(new, include)
            if VERBOSE_DEBUG:
                dump = dump_dom(parent)
                clz._logger.debug(f'parent of include after expanding include: \n{dump}')

    def new_processIncludes(self):
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

        include: ET.Element
        includes: List[ET.Element] = self.new_xml.findall('//include')
        for include in includes:
            # Ignore any includes which are not relevant, due to it not
            # being visible. (Is it always true that an invisible
            # item has no impact on gui?)

            include_parent: ET.Element = include.getparent()
            conditionAttr: str | None = include.attrib.get('condition')
            if VERBOSE_DEBUG:
                clz._logger.debug(
                    f'include {include.tag} {include.attrib} {include.text}')
            if conditionAttr:  # and not xbmc.getCondVisibility(conditionAttr):
                name: str = include.attrib.get('name')
                if VERBOSE_DEBUG:
                    clz._logger.debug(f'{include.tag} {include.attrib}'
                                      f' text: {include.text} tail: {include.tail}')

                    dump: str = ET.tostring(include_parent, encoding='unicode')
                    clz._logger.debug(f'parent before removing include:\n {dump}')
                    clz._logger.debug(
                        f'removing include {include.text} from {include_parent.tag}')
                include_parent.remove(include)
                if VERBOSE_DEBUG:
                    dump: str = ET.tostring(include_parent, encoding='unicode')
                    clz._logger.debug(f'parent after removing include:\n {dump}')
                continue

            # Does this include for this window refer to one in the
            # Include Tree? getInclude uses the name attribute of an include
            # to find the body of the include_ref.

            matchingInclude: ET.Element = clz.includes.get_include(include.text)

            if matchingInclude is None:
                # clz._logger.debug(f'INCLUDE NOT FOUND: {include.text}')
                continue

            # Yes, the window refers to an include which our include tree
            # has the body of the include. Import that include into
            # our Window's tree.

            # print 'INCLUDE FOUND: %s' % i.string
            if VERBOSE_DEBUG:
                dump: str = ET.tostring(include_parent, encoding='unicode')
                clz._logger.debug(f'parent before replacing include:\n {dump}')
            include_parent.replace(include, matchingInclude)
            if VERBOSE_DEBUG:
                dump: str = ET.tostring(include_parent, encoding='unicode')
                clz._logger.debug(f'parent after replacing include:\n {dump}')

    def addonReplacer(self, m):
        return xbmc.getInfoLabel(m.group(0))

    def variableReplace(self, m):
        clz = type(self)
        try:
            return clz.includes.getVariable(m.group(1))
        except Exception as e:
            module_logger.exception(f'variableReplace Exception: {e}')

    def localizeReplacer(self, m):
        return xbmc.getLocalizedString(int(m.group(1)))

    def parseFormatting(self, text):
        text = varRE.sub(self.variableReplace, text)
        text = localizeRE.sub(self.localizeReplacer, text)
        text = addonRE.sub(self.addonReplacer, text)
        text = extractInfos(text, self.currentControl)
        text = tagRE.sub('', text).replace('[CR]', '... ').strip(' .')
        # text = infoLableRE.sub(self.infoReplacer,text)
        return text

    def getControl(self, controlID) -> ET.Element | None:
        clz = type(self)
        new_control: ET.Element = None
        old_control: ET.Element = None
        if USE_OLD_FUNCTIONS:
            old_control: minidom = self.old_getControl(controlID)
        if USE_NEW_FUNCTIONS:
            new_control = self.new_getControl(controlID)
            if USE_OLD_FUNCTIONS and old_control != new_control:
                clz._logger.debug(f'DIFFERENCE results old: {old_control} '
                                  f'new: {new_control}')
        if USE_OLD_FUNCTIONS:
            return old_control
        else:
            return new_control

    def old_getControl(self, controlID):
        control = xpath.findnode(f"//control[attribute::id='{controlID}']",
                                 self.xml)
        return control

    def new_getControl(self, controlID) -> ET.Element:
        new_control: ET.Element = self.new_xml.find(f".//control[@id='{controlID}']")
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
                clz._logger.debug(f'DIFFERENCE: results old: {old_text} '
                                  f'new: {new_text}')
        if USE_OLD_FUNCTIONS:
            return old_text
        return new_text

    def old_getLabelText(self, label) -> str | None:
        clz = type(self)
        if VERBOSE_DEBUG:
            module_logger.debug(f'In getLabelText')
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
                        text = '$LOCALIZE[{0}]'.format(text)
                    else:
                        text = '$INFO[{0}]'.format(text)

        if not text:
            return None
        value = tagRE.sub('', text).replace('[CR]', '... ').strip(' .')
        return value

    def new_getLabelText(self, label: ET.Element) -> str:
        clz = type(self)
        module_logger.debug(f'In new_getLabelText')
        new_label_id: str = label.attrib.get('id')
        new_text: str | None = None
        module_logger.debug(f'new_label_id: {new_label_id}')
        if new_label_id:
            # Try getting programmatically set label first.
            new_text = xbmc.getInfoLabel(f'Control.GetLabel({new_label_id})')

        if new_text is None or new_text == '-':
            new_text = None
            new_label_node: ET.Element = label.find('label')
            if new_label_node and new_label_node.find('*'):
                new_text = new_label_node.find('*').text
            if new_text:
                if new_text.isdigit():
                    new_text = f'$LOCALIZE[{new_text}]'
            else:
                i_new = new_label_node.find('info')
                if i_new and i_new.find('*'):
                    new_text = i_new.find('*')  # .data
                    if new_text.isdigit():
                        new_text = f'$LOCALIZE[{new_text}]'
                    else:
                        new_text = f'$INFO[{new_text}]'

        if not new_text:
            return None
        new_value = tagRE.sub('', new_text).replace('[CR]', '...').strip(' .')
        return new_value

    def processTextList(self, text_list: List[str]) -> List[str]:
        texts: List[str] = []
        check = []
        for t in text_list:
            parsed = self.parseFormatting(t)
            if parsed and t not in check:
                texts.append(parsed)
                check.append(t)
        return texts

    def getListItemTexts(self, controlID: int) -> List[str] | None:
        old_texts = None
        if USE_OLD_FUNCTIONS:
            old_texts = self.old_getListItemTexts(controlID)
        new_texts = None
        if USE_NEW_FUNCTIONS:
            new_texts = self.new_getListItemTexts(controlID)
            if USE_OLD_FUNCTIONS and old_texts != new_texts:
                clz = type(self)
                clz._logger.debug(f'DIFFERENCE: old != new old: {old_texts} '
                                  f'new: {new_texts}')
        if not USE_OLD_FUNCTIONS:
            return old_texts
        return new_texts

    def old_getListItemTexts(self, controlID: int) -> List[str] | None:
        if controlID < 0:
            controlID = - controlID
        self.currentControl = controlID
        try:
            clist = self.getControl(controlID)
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

    def new_getListItemTexts(self, controlID: int) -> List[str]:
        if controlID < 0:
            controlID = - controlID
        self.currentControl = controlID
        try:
            newclist = self.new_getControl(controlID)
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

    def getWindowTexts(self) -> List[str]:
        old: List[str] | None = None
        if USE_OLD_FUNCTIONS:
            old: List[str] = self.old_getWindowTexts()
        new: List[str] | None = None
        if USE_NEW_FUNCTIONS:
            new: List[str] = self.new_getWindowTexts()
            if USE_OLD_FUNCTIONS and old != new:
                clz = type(self)
                clz._logger.debug(f'DIFFERENCE: old != new old: {old} '
                                  f'new: {new}')
        if USE_OLD_FUNCTIONS:
            if old is None:
                old = []
            return old
        if new is None:
            new = []
        return new

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
        new_lt: List[ET.Element] = self.new_xml.findall(
                ".//control[@type='label' or @type='fadelabel' or "
                "@type='textbox']")
        new_texts: List[str] = []
        for new_l in new_lt:
            if not self.new_controlIsVisible(new_l):
                continue
            for new_parent in new_nodeParents(self.new_xml, new_l):
                if not self.new_controlIsVisible(new_parent):
                    break
                type_attr: str = new_parent.attrib.get('type')
                if type_attr in (
                        'list', 'fixedlist', 'wraplist', 'panel'):
                    break
            else:
                new_text = self.new_getLabelText(new_l)
                if new_text and new_text not in new_texts:
                    new_texts.append(new_text)
        return self.processTextList(new_texts)

    def controlGlobalPosition(self, control) -> Tuple[int, int]:
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
                    clz._logger.debug(f'DIFFERENCE: old_x != new_x old: {old_x} '
                                      f'new: {new_x}')
                if old_y != new_y:
                    clz._logger.debug(f'DIFFERENCE: old_y != new_y old: {old_y} '
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
        for p, new_parent in new_nodeParents(self.new_xml, control):
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
                clz._logger.debug(f'DIFFERENCE: old != new old: {old} new: {new}')
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
                clz._logger.debug(f'DIFFERENCE: Old != New old: {old} new: {new}')
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

    def new_controlIsVisibleGlobally(self, control: ET.Element) -> bool:
        for new_parent in new_nodeParents(self.new_xml, control):
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


class Includes:

    _logger: BasicLogger = None
    _old_includesFilesLoaded: bool = False
    _new_includesFilesLoaded: bool = False
    _old_includesMap = {}
    _new_includesMap: Dict[str, ET.Element] = {}

    def __init__(self):
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz.__class__.__name__)
        path = getXBMCSkinPath('Includes.xml')
        self.xml = minidom.parse(path)
        self.new_xml: ET.ElementTree = ET.parse(path)
        self.root: ET.Element = self.new_xml.getroot()
        self.loadIncludesFiles()

    def get_include(self, name: str) -> ET.Element | None:
        """
        Returns a copy of a named Include from a cache of all named Includes
        referenced by Includes.xml.

        :param name: name of include to get
        :return:
        """
        clz = type(self)
        self.loadIncludesFiles()
        found_entry: ET.Element = clz._new_includesMap.get(name)
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
        self.loadIncludesFiles()
        found_entry: ET.Element = clz._old_includesMap.get(key)
        if found_entry is not None:
            return copy.deepcopy(found_entry)
        return None

    def loadIncludesFiles(self):
        clz = type(self)
        if clz._old_includesFilesLoaded or clz._new_includesFilesLoaded:
            return

        self.old_loadIncludesFiles()
        if USE_NEW_FUNCTIONS:
            self.new_loadIncludesFiles()

            if len(clz._old_includesMap.keys()) != len(clz._new_includesMap.keys()):
                clz._logger.debug(f'Include maps of different size: old: '
                                  f'{len(clz._old_includesMap.keys())} new: '
                                  f'{len(clz._new_includesMap.keys())}')
            printed_one: bool = False
            for old_key, old_elements in clz._old_includesMap.items():
                old_xml: str = dump_dom(old_elements)
                from_old: ET = ET.fromstring(old_xml)
                from_new_elements: ET.Element = clz._new_includesMap.get(old_key)
                from_new: ET = from_new_elements.getroottree()
                old_canonical: str = ET.canonicalize(xml_data=old_xml,
                                                     strip_text=True)
                new_canonical: str = ET.canonicalize(
                        xml_data=ET.tostring(from_new, encoding='unicode'),
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

    def old_loadIncludesFiles(self):
        clz = type(self)
        if clz._old_includesFilesLoaded:
            return
        print(f'In old_loadIncludeFiles')
        basePath = getXBMCSkinPath('')
        # Start with each <Include> in Includes.xml
        for i in xpath.find('//include', xpath.findnode('//includes', self.xml)):
            fileAttr = i.attributes.get('file')
            if fileAttr:
                if VERBOSE_DEBUG:
                    clz._logger.debug(f'fileAttr: {fileAttr.value}')
                xmlName: str = fileAttr.value
                p = os.path.join(basePath, xmlName)
                if not os.path.exists(p):
                    continue
                xml = minidom.parse(p)
                includes = xpath.findnode('includes', xml)
                if VERBOSE_DEBUG:
                    clz._logger.debug(f"includes tag: {includes.tagName}")
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
                    nameAttr = sub_i.attributes.get('name')
                    if nameAttr:
                        if nameAttr in clz._old_includesMap.keys():
                            clz._logger.debug(
                                f'WARNING entry already in old map: {nameAttr}')
                        clz._old_includesMap[nameAttr.value] = sub_i
                        #  print(f'old_sub_i: {nameAttr} {sub_i.tagName} {
                        #  sub_i.attributes}')
                        #  print(f'{dump_dom(sub_i)}')
            else:
                nameAttr = i.attributes.get('name')
                if nameAttr:
                    if nameAttr in clz._old_includesMap.keys():
                        clz._logger.debug(f'WARNING entry already in old map: {nameAttr}')
                    clz._old_includesMap[nameAttr.value] = i.cloneNode(True)
                    # print(f'old name entry: {nameAttr.value}')
                    # print(f'{dump_dom(i)}')

        clz._old_includesFilesLoaded = True

    #        import codecs
    #        with codecs.open(os.path.join(getXBMCSkinPath(''),
    #        'Includes_Processed.xml'),'w','utf-8') as f: f.write(self.soup.prettify())

    def new_loadIncludesFiles(self):
        clz = type(self)
        if clz._new_includesFilesLoaded:
            return
        basePath = getXBMCSkinPath('')
        # Start with each <Include> in Includes.xml
        for i in self.new_xml.findall('.//include'):
            i: ET.Element
            fileAttr = i.attrib.get('file')
            if fileAttr:
                xmlName: str = fileAttr
                p = os.path.join(basePath, xmlName)
                if not os.path.exists(p):
                    continue
                new_xml: ET = ET.parse(p)
                root = new_xml.getroot()
                #
                # Should we replace a reference to the include file
                # or should every include in the tree be expanded?

                if VERBOSE_DEBUG:
                    clz._logger.debug(f'include_file: {p}')
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
                i.getparent().replace(i, root)
                for new_sub_i in root.findall('.//include'):
                    new_sub_i: ET.Element
                    nameAttr = new_sub_i.attrib.get('name')
                    if nameAttr:
                        if nameAttr in clz._new_includesMap.keys():
                            clz._logger.debug(
                                f'ERROR entry already in new map: {nameAttr}')
                        tmp_tree: ET = ET.ElementTree()
                        tmp_tree._setroot(copy.deepcopy(new_sub_i))
                        tmp_root = tmp_tree.getroot()
                        clz._new_includesMap[nameAttr] = tmp_root
            else:
                nameAttr = i.attrib.get('name')
                if nameAttr:
                    if nameAttr in clz._new_includesMap.keys():
                        clz._logger.debug(f'ERROR entry already in new map: {nameAttr}')
                    tmp_tree: ET = ET.ElementTree()
                    tmp_tree._setroot(copy.deepcopy(i))
                    tmp_root = tmp_tree.getroot()
                    clz._new_includesMap[nameAttr] = tmp_root
        '''
        for i in self.new_xml.findall('.//include'):
            if isinstance(i, list):
                clz._logger.debug('length i: ', len(i))
            else:
                clz._logger.debug(i.tag, i.attrib, i.text)
        '''

        clz._new_includesFilesLoaded = True

    #        import codecs
    #        with codecs.open(os.path.join(getXBMCSkinPath(''),
    #        'Includes_Processed.xml'),'w','utf-8') as f: f.write(self.soup.prettify())

    def getVariable(self, name: str):
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
        new_var = self.new_xml.find(f'.//variable[@name={name}')
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


def getWindowParser():
    path = currentWindowXMLFile()
    # module_logger.debug_extra_verbose(f'getWindowParser path: {path}')
    if not path:
        return
    return WindowParser(path)
