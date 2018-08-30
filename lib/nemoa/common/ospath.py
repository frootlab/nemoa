# -*- coding: utf-8 -*-

__author__  = 'Patrick Michl'
__email__   = 'patrick.michl@gmail.com'
__license__ = 'GPLv3'

import os

from typing import Any, Dict, Optional, Union

PathLike = Union['PathLike', tuple, list, str]
PathLikeDict = Dict[str, PathLike]

def copytree(sdir: str, tdir: str) -> bool:
    """Copy sub directories from given source directory to target directory.

    Args:
        sdir (string): path of source directory
        tdir (string): path of target directory

    Returns:
        True if the operation was successful.

    """

    import glob
    import shutil

    for s in glob.glob(os.path.join(sdirc, '*')):
        t = os.path.join(tdir, basename(s))
        if os.path.exists(t): shutil.rmtree(t)
        try: shutil.copytree(s, t)
        except Exception as e:
            raise OSError("Could not copy directory")

    return True

def cwd() -> str:
    """Path of current working directory.

    Returns:
        String containing path of current working directory.

    """

    return os.getcwd() + os.path.sep

def home() -> str:
    """Path of current users home directory.

    Returns:
        String containing path of home directory.

    """

    return os.path.expanduser('~')

def get(key: str, appname: Optional[str] = None,
    appauthor: Optional[Union[str, bool]] = None, version: Optional[str] = None,
    **kwargs: Any) -> Optional[str]:
    """Path of environmental directory.

    This function returns environmental directories by platform independent
    keys to allow platform independent storage. This is a wrapper function to
    the package 'appdirs' [1].

    [1] http://github.com/ActiveState/appdirs

    Args:
        key (string): Environmental directory key name. Allowed values are:
            'user_cache_dir' -- Cache directory of user
            'user_config_dir' -- Configuration directory of user
            'user_data_dir' -- Data directory of user
            'user_log_dir' -- Logging directory of user
            'site_config_dir' -- Site specific configuration directory
            'site_data_dir' -- Site specific data directory
            'home' -- Home directory of user
            'cwd' -- Current working directory of user
        appname (str, optional): is the name of application.
            If None, just the system directory is returned.
        appauthor (str, optional): is the name of the appauthor or distributing
            body for this application. Typically it is the owning company name.
            You may pass False to disable it. Only applied in windows.
        version (str, optional): is an optional version path element to append
            to the path. You might want to use this if you want multiple
            versions of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
            Only applied when appname is present.
        **kwargs (Any, optional): Optional additional keyword arguments,
            that depend on the given key. For more information see [1].

    Returns:
        String containing path of environmental directory or None if
        the key is not supported.

    """

    try: import appdirs
    except ImportError as e: raise ImportError(
        "nemoa.common.ospath requires appdirs: "
        "http://github.com/ActiveState/appdirs") from e

    dkey = {'appname': appname, 'appauthor': appauthor, 'version': version}

    if key == 'user_cache_dir': return appdirs.user_cache_dir(**dkey, **kwargs)
    if key == 'user_config_dir':
        return appdirs.user_config_dir(**dkey, **kwargs)
    if key == 'user_data_dir': return appdirs.user_data_dir(**dkey, **kwargs)
    if key == 'user_log_dir': return appdirs.user_log_dir(**dkey, **kwargs)
    if key == 'cwd': return cwd()
    if key == 'home': return home()
    if key == 'site_config_dir':
        return appdirs.site_config_dir(**dkey, **kwargs)
    if key == 'site_data_dir':
        return appdirs.site_data_dir(**dkey, **kwargs)

    return None

def clear(fname: str) -> str:
    """Clear filename from invalid characters.

    Args:
        fname (str):

    Returns:
        String containing valid path syntax.

    """

    import string

    valid = "-_.() " + string.ascii_letters + string.digits
    fname = ''.join(c for c in fname if c in valid).replace(' ', '_')

    return fname

def join(*args: PathLike) -> str:
    """Join and normalize path like structure.

    Args:
        *args (PathLike): Path like structure, which is given by a tree of
            strings, which can be joined to a path.

    Returns:
        String containing valid path syntax.

    Examples:
        >>> join(('a', ('b', 'c')), 'd')
        'a\\b\\c\\d'

    """

    # flatten tree of strings to list and join list using os path seperators
    if len(args) == 0: return ''
    if len(args) == 1 and isinstance(args[0], str): path = args[0]
    else:
        l = list(args)
        i = 0
        while i < len(l):
            while isinstance(l[i], (list, tuple)):
                if not l[i]:
                    l.pop(i)
                    i -= 1
                    break
                else: l[i:i + 1] = l[i]
            i += 1
        try: path = os.path.sep.join(list(l))
        except Exception as e:
            raise ValueError("Path like tree structure is not valid") from e
    if not path: return ''

    # normalize path
    path = os.path.normpath(path)

    return path

def expand(*args: PathLike, udict: PathLikeDict = {}, expapp: bool = True,
    expenv: bool = True) -> str:
    """Iteratively expand path variables.

    Args:
        *args (PathLike): Path like structure, which is given by a tree of
            strings, which can be joined to a path.
        udict (PathLikeDict, optional): dictionary for user variables.
            Thereby the keys in the dictionary are encapsulated
            by the symbol '%'. The user variables may also include references.
        expapp (bool, optional): determines if application path variables are
            expanded. For a full list of valid application variables see
            nemoa.common.ospath.get. Default is True
        expenv (bool, optional): determines if environmental path variables are
            expanded. For a full list of valid application variables see
            nemoa.common.ospath.get. Default is True

    Returns:
        String containing valid path syntax.

    Examples:
        >>> .expand('%var1%/c', 'd', udict = {'var1': 'a/%var2%', 'var2': 'b'})
        'a\\b\\c\\d'

     """

    import sys

    path = join(*args)

    # create dictionary with variables
    d = udict.copy()
    for key, val in d.items(): d[key] = join(val)
    if expapp:
        dkey = {'appname': 'nemoa', 'appauthor': 'Froot'}
        for key in ['user_cache_dir', 'user_config_dir', 'user_data_dir',
            'user_log_dir', 'home', 'cwd', 'site_config_dir', 'site_data_dir']:
            d[key] = get(key, **dkey)

    # itereratively expand variables in path
    update = True
    i = 0
    limit = sys.getrecursionlimit()
    while update:
        update = False
        for key, val in list(d.items()):
            if '%' + key + '%' not in path: continue
            try: path = path.replace('%' + key + '%', val)
            except TypeError: del d[key]
            update = True
        i += 1
        if i > limit:
            raise RecursionError('cyclic dependency in variables detected')
        path = os.path.normpath(path)

    # expand environmental paths
    if not expenv: return path
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)

    return path

def dirname(*args: PathLike) -> str:
    """Extract directory name from a path like structure.

    Args:
        *args (PathLike): Path like structure, given by a tree of strings,
            which can be joined to a path.

    Returns:
        String containing normalized directory path of file.

    Examples:
        >>> dirname(('a', ('b', 'c')), 'base.ext')
        'a\\b\\c'

    """

    path = expand(*args)
    if os.path.isdir(path): return path
    name = os.path.dirname(path)

    return name

def filename(*args: PathLike) -> str:
    """Extract file name from a path like structure.

    Args:
        *args (PathLike): Path like structure, given by a tree of strings,
            which can be joined to a path.

    Returns:
        String containing normalized directory path of file.

    Examples:
        >>> filename(('a', ('b', 'c')), 'base.ext')
        'base.ext'

    """

    path = expand(*args)
    if os.path.isdir(path): return ''
    name = os.path.filename(path)

    return name

def basename(*args: PathLike) -> str:
    """Extract file basename from a path like structure.

    Args:
        *args (PathLike): Path like structure, given by a tree of strings,
            which can be joined to a path.

    Returns:
        String containing basename of file.

    Examples:
        >>> filename(('a', ('b', 'c')), 'base.ext')
        'base'

    """

    path = expand(*args)
    if os.path.isdir(path): return ''
    name = os.path.basename(path)
    base = os.path.splitext(name)[0].rstrip('.')

    return base

def fileext(*args: PathLike) -> str:
    """Fileextension of file.

    Args:
        *args (PathLike): Path like structure, given by a tree of strings,
            which can be joined to a path.

    Returns:
        String containing fileextension of file.

    Examples:
        >>> fileext(('a', ('b', 'c')), 'base.ext')
        'ext'

    """

    path = expand(*args)
    if os.path.isdir(path): return ''
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1].lstrip('.')

    return ext
