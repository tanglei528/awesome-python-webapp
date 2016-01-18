#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Layne'
'''
Database operation module. This module is independent with web module.
''''''
'''
import time, logging

import db
class Field(object):
    _count = 0
    
    def __init__(self, **kw):
        self.name = kw.get('name', None)
        self._default = kw.get('default', None)
        self.primary_key = kw.get('primary_key', None)
        self.nullable = kw.get('nullable', None)
        self.updatable = kw.get('updatable', True)
        self.insertable = kw.get('insertable', True)
        self.ddl = kw.get('ddl', '')
        self._order = Field._count
        Field._count = Field._count + 1

    @property
    def default(self):
        d = self._default
        return d() if callable(d) else d

    def __str__(self):
        s = ['<%s:%s,%s,default(%s),' % (self.__class_.__name__, self.name, self.ddl, self._default)]
        self.nullable and s.append('N')
        self.updatable and s.append('U')
        self.insertable and s.append('E')
        s.append('>')
        return ''.join(s)


class StringField(Field):
    def __init__(self, **kw):
        if not 'default' in kw:
            kw['default'] = 'varchar(255)'
        super(StringField, self).__init__(**kw)


class IntegerField(Field):
    def __init__(self, **kw):
        if not 'default' in kw:
            kw['default'] = 0
        if not 'ddl' in kw:
            kw['ddl'] = 'bigint'
        super(IntegerField, self).__init__(**kw)

class FloatField(Field):
    def __init__(self, **kw):
        if not 'default' in kw:
            kw['default'] = 0.0
        if not 'ddl' in kw:
            kw['ddl'] = 'real'
        super(FloatField, self).__init__(**kw)


class BooleanField(Field):
    def __init__(self, **kw):
        if not 'default' in kw:
            kw['default'] = False
        if not 'ddl' in kw:
            kw['ddl'] = 'bool'
        super(BooleanField, self).__init__(**kw)


class TextField(Field):
    def __init__(self, **kw):
        if not 'default' in kw:
            kw['default'] = ''
        if not 'ddl' in kw:
            kw['ddl'] = 'text'
        super(TextField, self).__init__(**kw)


class BlobField(Field):
    def __init__(self, **kw):
        if not 'default' in kw:
            kw['default'] = ''
        if not 'ddl' in kw:
            kw['ddl'] = 'blob'
        super(BlobField, self).__init__(**kw)


class VersionField(Field):

    def __init__(self, name=None):
        super(VersionField, self).__init__(name=name, default=0, ddl='bigint')

_triggers = frozenset(['pre_insert', 'pre_update', 'pre_delete'])

class ModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)

        if not hasattr(cls, 'subclasses'):
            cls.subclasses[name] = name
        else:
            logging.warning('Redefine class: %s' % name)

        logging.info('Scan ORMapping %s...' % name)
        mappings = dict()
        primary_key = None
        for k,v in attrs.iteritems():
            if isinstance(v, Field):
                if not v.name:
                    v.name = k
                    logging.info('Found mapping %s => %s' % (k, v))
                    if v.primary_key:
                        if primary_key:
                            raise TypeError('Cannot define more than 1 primary key in class: %s' % name)
                        if v.updatable:
                            logging.warning('NOTE: change primary key to non-updatable.')
                            v.updatable = False
                        if v.nullable:
                            logging.warning('NOTE:change primary key to non-nullable.')
                            v.nullable = False
                        primary_key = v
                    mappings[k] = v
        if not primary_key:
            raise TypeError('Primary key not defined in class: %s' % name)
        for k in mapping.iterkeys():
            attrs.pop(k)
        if not '__table__' in attrs:
            attrs['__table__'] = name.lower()
            
        attrs['__mapping__'] = mapping
        attrs['__primary_key__'] = primary_key
        attrs['__sql__'] = lambda self: _gen_sql(attrs['__table__'], mappings)
        for trigger in _triggers:
            if not trigger in attrs:
                attrs[trigger] = None
        return type.__new__(cls, name, bases, attrs)


class Model(dict):
    __metaclass__ = ModelMetaclass

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' 0bject has no attribude 's%'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    @classmethod
    def get(cls, pk):
        d = db.select_one('select * from %s where %s=?' % (cls.__table__, cls.__primary__key__.name), pk)
        return cls(**d) if d else None

    @classmethod
    def find_first(cls, where, *args):
        d = db.select_one('select * from %s %s' % (cls.__table__, where), *args)
        return cls(**d) if d else None

    @classmethod
    def find_all(cls, *args):
        L = db.select('select * from %s' % cls.__table__)
        return [cls(**d) for d in L]

    @classmethod
    def find_by(cls, where, *args):
        L = db.select('select * from %s %s' % (cls.__table__, where), *args)
        return [cls(**d) for d in L]

    @classmethod
    def count_all(cls):
        return db.select_int('select count(%s) from %s' % (cls.__primary_key__.name, cls.__table__)) 

    def update(self):
        self.pre_update and self.pre_update()
        L = []
        args = []
        for k,v in self.__mappings__.iteritems():
            if v.updatable:
                if hasattr(self, k):
                    arg = getattr(self, k)
                else:
                    arg = v.default
                    setattr(self, k, arg)
                L.append('%s = ?' k)
                args.append(arg)
        pk = self.__primary_key__.name
        args.append(getattr(self, pk))
        db.update('update %s set %s where %s=?' % (cls.__table__, ','.join(L), pk), *args)

    def delete(self):
        self.pre_delete and self.pre_delete()
        pk = self.__primary_key__.name
        args = (getattr(self, pk), )
        db.update('delete from %s where %s = ?' % (self.__table__, pk), *args)
        return self

    def insert(self):
        params = {}
        for k,v in sellf.__mappings__.iteritems():
            params[v.name] = getattr(self, k)
        db.insert(self.__table__, **params)
        return self



if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    db.create_engine('www-data', 'www-data', 'test')
    db.update('drop table if exists user')
    db.update('create table user (id int primary key, name text, email text, passwd text, last_modified real)')

