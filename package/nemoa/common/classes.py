# -*- coding: utf-8 -*-

__author__  = 'Patrick Michl'
__email__   = 'patrick.michl@gmail.com'
__license__ = 'GPLv3'

import nemoa

class BaseObject:

    _attr_meta = {'fullname': 'r', 'type': 'r', 'name': 'rw',
                'branch': 'rw', 'version': 'rw', 'about': 'rw',
                'author': 'rw', 'email': 'rw', 'license': 'rw',
                'path': 'rw'}
    _attr    = {}

    def __init__(self, *args, **kwargs):
        """Import object from dictionary."""

        #nemoa.common.dict_merge(self._attr_meta, self._attr)
        self._set_copy(**kwargs)

    def __getattr__(self, key):
        """Attribute wrapper to method get(key)."""

        if key in self._attr_meta:
            if 'r' in self._attr_meta[key]:
                return self._get_meta(key)
            return nemoa.log('warning',
                "attribute '%s' is not readable.")

        if key in self._attr:
            if 'r' in self._attr[key]: return self.get(key)
            return nemoa.log('warning',
                "attribute '%s' is not readable.")

        raise AttributeError('%s instance has no attribute %r'
            % (self.__class__.__name__, key))

    def __setattr__(self, key, val):
        """Attribute wrapper to method set(key, val)."""

        if key in self._attr_meta:
            if 'w' in self._attr_meta[key]:
                return self._set_meta(key, val)
            return nemoa.log('warning',
                "attribute '%s' is not writeable.")

        if key in self._attr:
            if 'w' in self._attr[key]: return self.set(key, val)
            return nemoa.log('warning',
                "attribute '%s' is not writeable.")

        self.__dict__[key] = val

    def _get_meta(self, key):
        """Get meta information like 'author' or 'version'."""

        if key == 'about':    return self._get_about()
        if key == 'author':   return self._get_author()
        if key == 'branch':   return self._get_branch()
        if key == 'email':    return self._get_email()
        if key == 'fullname': return self._get_fullname()
        if key == 'license':  return self._get_license()
        if key == 'name':     return self._get_name()
        if key == 'path':     return self._get_path()
        if key == 'type':     return self._get_type()
        if key == 'version':  return self._get_version()

        return nemoa.log('warning', "unknown key '%s'" % (key))

    def _get_fullname(self):
        """Get full name including 'branch' and 'version'."""

        fullname = ''
        name = self._get_name()
        if name: fullname += name
        branch = self._get_branch()
        if branch: fullname += '.' + branch
        version = self._get_version()
        if version: fullname += '.' + str(version)

        return fullname

    def _get_name(self):
        """Get name."""

        if 'name' in self._config: return self._config['name']

        return None

    def _get_path(self):
        """Get path of file."""

        if 'path' in self._config: return self._config['path']

        return None

    def _get_branch(self):
        """Get branch."""

        if 'branch' in self._config: return self._config['branch']

        return None

    def _get_version(self):
        """Get version number of branch."""

        if 'version' in self._config: return self._config['version']

        return None

    def _get_about(self):
        """Get description."""

        if 'about' in self._config: return self._config['about']

        return None

    def _get_author(self):
        """Get author."""

        if 'author' in self._config: return self._config['author']

        return None

    def _get_email(self):
        """Get email of author."""

        if 'email' in self._config: return self._config['email']

        return None

    def _get_license(self):
        """Get license."""

        if 'license' in self._config: return self._config['license']

        return None

    def _get_type(self):
        """Get object type, using module name and class name."""

        mname = self.__module__.split('.')[-1]
        cname = self.__class__.__name__

        return mname + '.' + cname

    def _get_config(self, key = None, *args, **kwargs):
        """Get configuration or configuration value."""

        if key == None: return copy.deepcopy(self._config)

        if isinstance(key, str) and key in self._config.keys():
            if isinstance(self._config[key], dict):
                return self._config[key].copy()
            return self._config[key]

        return nemoa.log('error', """could not get configuration:
            unknown key '%s'.""" % (key))

    def _get_algorithm(self, algorithm = None, *args, **kwargs):
        """Get algorithm."""
        algorithms = self._get_algorithms(*args, **kwargs)
        if not algorithm in algorithms: return None
        return algorithms[algorithm]

    def _set_meta(self, key, *args, **kwargs):
        """Set meta information like 'author' or 'version'."""

        if key == 'about':   return self._set_about(*args, **kwargs)
        if key == 'author':  return self._set_author(*args, **kwargs)
        if key == 'name':    return self._set_name(*args, **kwargs)
        if key == 'branch':  return self._set_branch(*args, **kwargs)
        if key == 'version': return self._set_version(*args, **kwargs)
        if key == 'email':   return self._set_email(*args, **kwargs)
        if key == 'license': return self._set_license(*args, **kwargs)
        if key == 'path':    return self._set_path(*args, **kwargs)

        return nemoa.log('warning', "unknown key '%s'" % (key))

    def _set_about(self, val):
        """Set description."""

        if not isinstance(val, basestring): return False
        self._config['about'] = val

        return True

    def _set_author(self, val):
        """Set author."""

        if not isinstance(val, basestring): return False
        self._config['author'] = val

        return True

    def _set_branch(self, val):
        """Set branch."""
        if not isinstance(val, basestring): return False
        self._config['branch'] = val
        return True

    def _set_name(self, val):
        """Set name."""

        if not isinstance(val, basestring): return False
        self._config['name'] = val

        return True

    def _set_version(self, val):
        """Set version number of branch."""

        if not isinstance(val, int): return False
        self._config['version'] = val

        return True

    def _set_email(self, val):
        """Set email of author."""

        if not isinstance(val, str): return False
        self._config['email'] = val

        return True

    def _set_license(self, val):
        """Set license."""

        if not isinstance(val, str): return False
        self._config['license'] = val

        return True

    def _set_path(self, val):
        """Set path."""

        if not isinstance(val, basestring): return False
        self._config['path'] = val

        return True
