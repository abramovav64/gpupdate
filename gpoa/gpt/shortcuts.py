import logging

from xml.etree import ElementTree
from xdg.DesktopEntry import DesktopEntry
import json

from util.windows import transform_windows_path

def read_shortcuts(shortcuts_file):
    '''
    Read shortcut objects from GPTs XML file
    '''
    shortcuts = list()
    xml_contents = ElementTree.parse(shortcuts_file)
    xml_root = xml_contents.getroot()

    for link in xml_root:
        props = link.find('Properties')
        dest = props.get('shortcutPath')
        path = transform_windows_path(props.get('targetPath'))
        arguments = props.get('arguments')
        sc = shortcut(dest, path, arguments, link.get('name'))
        sc.set_changed(link.get('changed'))
        sc.set_clsid(link.get('clsid'))
        sc.set_guid(link.get('uid'))
        sc.set_usercontext(link.get('userContext', False))
        shortcuts.append(sc)

    return shortcuts

def json2sc(json_str):
    '''
    Build shortcut out of string-serialized JSON
    '''
    json_obj = json.loads(json_str)

    sc = shortcut(json_obj['dest'], json_obj['path'], json_obj['arguments'], json_obj['name'])
    sc.set_changed(json_obj['changed'])
    sc.set_clsid(json_obj['clsid'])
    sc.set_guid(json_obj['guid'])

    if 1 == json_obj['is_in_user_context']:
        sc.set_usercontext(link.get('userContext', False))

    return sc

class shortcut:
    def __init__(self, dest, path, arguments, name=None):
        self.dest = dest
        self.path = path
        self.arguments = arguments
        self.name = name
        self.changed = ''
        self.is_in_user_context = self.set_usercontext()

    def __str__(self):
        result = self.to_json()
        return result

    def set_changed(self, change_date):
        '''
        Set object change date
        '''
        self.changed = change_date

    def set_clsid(self, clsid):
        self.clsid = clsid

    def set_guid(self, uid):
        self.guid = uid

    def set_usercontext(self, context=False):
        '''
        Perform action in user context or not
        '''
        self.is_in_user_context = context

    def to_json(self):
        '''
        Return shortcut's JSON for further serialization.
        '''
        content = dict()
        content['dest'] = self.dest
        content['path'] = self.path
        content['name'] = self.name
        content['arguments'] = self.arguments
        content['clsid'] = self.clsid
        content['guid'] = self.guid
        content['changed'] = self.changed
        content['is_in_user_context'] = self.is_in_user_context

        result = self.desktop()
        result.content.update(content)

        return json.dumps(result.content)

    def desktop(self):
        '''
        Returns desktop file object which may be written to disk.
        '''
        self.desktop_file = DesktopEntry()
        self.desktop_file.addGroup('Desktop Entry')
        self.desktop_file.set('Type', 'Application')
        self.desktop_file.set('Version', '1.0')
        self.desktop_file.set('Terminal', 'false')
        self.desktop_file.set('Exec', '{} {}'.format(self.path, self.arguments))
        self.desktop_file.set('Name', self.name)

        return self.desktop_file

    def write_desktop(self, dest):
        self.desktop().write(dest)
