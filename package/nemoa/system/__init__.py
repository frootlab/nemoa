#!/usr/bin/env python
# -*- coding: utf-8 -*-

import importlib

def new(*args, **kwargs):
    """Return new nemoa.system.[package].[class] instance."""
    config = kwargs['config'] if 'config' in kwargs \
        else {'package': 'base', 'class': 'empty'}
    module = importlib.import_module('nemoa.system.' + config['package'])
    if hasattr(module, config['class']):
        return getattr(module, config['class'])(*args, **kwargs)
    return None

def empty():
    """Return new nemoa.system.base.empty instance."""
    return new()
