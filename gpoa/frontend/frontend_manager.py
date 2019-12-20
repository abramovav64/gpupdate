from storage import registry_factory

from .control_applier import control_applier
from .polkit_applier import polkit_applier
from .systemd_applier import systemd_applier
from .firefox_applier import firefox_applier
from .chromium_applier import chromium_applier
from .shortcut_applier import (
    shortcut_applier,
    shortcut_applier_user
)
from util.windows import get_sid
from util.users import (
    is_root,
    get_process_user,
    username_match_uid
)

import logging

def determine_username(username=None):
    '''
    Checks if the specified username is valid in order to prevent
    unauthorized operations.
    '''
    name = username

    # If username is not set then it will be the name
    # of process owner.
    if not username:
        name = get_process_user()
        logging.debug('Username is not specified - will use username of current process')

    if not username_match_uid(name):
        if not is_root():
            raise Exception('Current process UID does not match specified username')

    logging.debug('Username for frontend is set to {}'.format(name))

    return name

class frontend_manager:
    '''
    The frontend_manager class decides when and how to run appliers
    for machine and user parts of policies.
    '''

    def __init__(self, username, target):
        self.storage = registry_factory('registry')
        self.username = determine_username(username)
        self.target = target
        self.process_uname = get_process_user()
        self.sid = get_sid(self.storage.get_info('domain'), self.username)

        self.machine_appliers = dict({
            'control':  control_applier(self.storage),
            'polkit':   polkit_applier(self.storage),
            'systemd':  systemd_applier(self.storage),
            'firefox':  firefox_applier(self.storage, self.sid, self.username),
            'chromium': chromium_applier(self.storage, self.sid, self.username),
            'shortcuts': shortcut_applier(self.storage)
        })

        # User appliers are expected to work with user-writable
        # files and settings, mostly in $HOME.
        self.user_appliers = dict({
            'shortcuts': shortcut_applier_user(self.storage, self.sid, self.username)
        })

    def machine_apply(self):
        '''
        Run global appliers with administrator privileges.
        '''
        if not is_root():
            logging.error('Not sufficient privileges to run machine appliers')
            return
        logging.debug('Applying computer part of settings')
        self.machine_appliers['systemd'].apply()
        self.machine_appliers['control'].apply()
        self.machine_appliers['polkit'].apply()
        self.machine_appliers['firefox'].apply()
        self.machine_appliers['chromium'].apply()
        self.machine_appliers['shortcuts'].apply()

    def user_apply(self):
        '''
        Run appliers for users.
        '''
        if is_root():
            logging.debug('Running user appliers from administrator context')
            self.user_appliers['shortcuts'].admin_context_apply()
        else:
            logging.debug('Running user appliers from user context')
            self.user_appliers['shortcuts'].user_context_apply()

    def apply_parameters(self):
        '''
        Decide which appliers to run.
        '''
        if 'All' == self.target or 'Computer' == self.target:
            self.machine_apply()

        # Run user appliers when user's SID is specified
        if self.storage.get_info('machine_sid') != self.sid:
            if 'All' == self.target or 'User' == self.target:
                self.user_apply()
