# -*- coding: utf-8 -*-
"""NumPy recarray functions.

.. References:
.. _rec_append_fields:
    https://www.numpy.org/devdocs/user/basics.rec.html

"""

__author__ = 'Patrick Michl'
__email__ = 'frootlab@gmail.com'
__license__ = 'GPLv3'
__docformat__ = 'google'

import abc
import dataclasses

# try:
#     import numpy as np
# except ImportError as err:
#     raise ImportError(
#         "requires package numpy: "
#         "https://pypi.org/project/numpy/") from err

from numpy.lib import recfunctions as nprf
from nemoa.base import check
from nemoa.base.container import BaseContainer, ContentAttr, InheritedAttr
from nemoa.base.container import TempAttr, VirtualAttr
from nemoa.types import NpFields, NpRecArray, Tuple, Iterable
from nemoa.types import Union, Optional, StrDict, StrTuple, Iterator, Any
from nemoa.types import OptIntList, OptCallable, CallableCI, Callable
from nemoa.types import OptStrTuple

# Module specific types
Field = dataclasses.Field
FieldTuple = Tuple[Field, ...]
Fields = Iterable[Union[str, Tuple[str, type], Tuple[str, type, Field]]]
FieldLike = Union[Fields, Tuple[str, type, StrDict]]
OptFieldLike = Optional[FieldLike]

# Module specific constants
ROW_STATE_CREATE = 0b001
ROW_STATE_UPDATE = 0b010
ROW_STATE_DELETE = 0b100

class Record(abc.ABC):
    """Record Base Class."""

    id: int
    state: int

    def __post_init__(self, *args: Any, **kwds: Any) -> None:
        self.id = self._create_row_id()
        self.state = ROW_STATE_CREATE

    def delete(self) -> None:
        """Mark record as deleted and remove it's ID from index."""
        if not self.state & ROW_STATE_DELETE:
            self.state |= ROW_STATE_DELETE
            self._delete_hook(self.id)

    def restore(self) -> None:
        """Mark record as not deleted and append it's ID to index."""
        if self.state & ROW_STATE_DELETE:
            self.state &= ~ROW_STATE_DELETE
            self._restore_hook(self.id)

    def update(self, **kwds: Any) -> None:
        """Mark record as updated and write the update to diff table."""
        if not self.state & ROW_STATE_UPDATE:
            self.state |= ROW_STATE_UPDATE
            self._update_hook(self.id, **kwds)

    def revoke(self) -> None:
        """Mark record as not updated and remove the update from diff table."""
        if self.state & ROW_STATE_UPDATE:
            self.state &= ~ROW_STATE_UPDATE
            self._revoke_hook(self.id)

    @abc.abstractmethod
    def _create_row_id(self) -> int:
        pass

    @abc.abstractmethod
    def _delete_hook(self, rowid: int) -> None:
        pass

    @abc.abstractmethod
    def _restore_hook(self, rowid: int) -> None:
        pass

    @abc.abstractmethod
    def _update_hook(self, rowid: int, **kwds: Any) -> None:
        pass

    @abc.abstractmethod
    def _revoke_hook(self, rowid: int) -> None:
        pass

class Cursor(BaseContainer):
    """Cursor Class."""

    _index: property = InheritedAttr()
    _getter: property = TempAttr(CallableCI)
    _mapper: property = TempAttr(CallableCI)
    _predicate: property = TempAttr(CallableCI)

    def __init__(
            self, index: OptIntList = None, getter: OptCallable = None,
            predicate: OptCallable = None, mapper: OptCallable = None,
            parent: Optional[BaseContainer] = None) -> None:
        """Initialize Cursor."""
        super().__init__(parent=parent)
        if index:
            self._index = index
        if getter:
            check.is_callable("argument 'getter'", getter)
            self._getter = getter
        if predicate:
            check.is_callable("argument 'predicate'", predicate)
            self._predicate = predicate
        if mapper:
            check.is_callable("argument 'mapper'", mapper)
            self._mapper = mapper

    def __iter__(self) -> Iterator:
        self._iter = iter(self._index)
        return self

    def __next__(self) -> Record:
        if not self._predicate:
            row = self._getter(next(self._iter))
            if self._mapper:
                return self._mapper(row)
            return row
        matches = False
        while not matches:
            row = self._getter(next(self._iter))
            matches = self._predicate(row)
        if self._mapper:
            return self._mapper(row)
        return row

class Table(BaseContainer):
    """Table Class."""

    _store: property = ContentAttr(list, default=[])

    _diff: property = TempAttr(list, default=[])
    _index: property = TempAttr(list, default=[])
    _iter_index: property = TempAttr()
    _Record: property = TempAttr(type)

    fields: property = VirtualAttr(getter='_get_fields', readonly=True)
    colnames: property = VirtualAttr(getter='_get_colnames', readonly=True)

    def __init__(self, columns: OptFieldLike = None) -> None:
        """ """
        super().__init__()
        if columns:
            self._create_header(columns)

    def __iter__(self) -> Iterator:
        self._iter_index = iter(self._index)
        return self

    def __next__(self) -> Record:
        return self.get_row(next(self._iter_index))

    def __len__(self) -> int:
        return len(self._index)

    def commit(self) -> None:
        """Apply changes to table."""
        # Delete and update rows in table store. The reversed order is required
        # to keep the position of the list index, when deleting rows
        for rowid in reversed(range(len(self._store))):
            state = self.get_row(rowid).state
            if state & ROW_STATE_DELETE:
                del self._store[rowid]
            elif state & (ROW_STATE_CREATE | ROW_STATE_UPDATE):
                self._store[rowid] = self._diff[rowid]
                self._store[rowid].state = 0

        # Reassign row IDs and recreate diff table and index
        self._create_index()

    def rollback(self) -> None:
        """Revoke changes from table."""
        # Delete new rows, that have not yet been commited. The reversed order
        # is required to keep the position of the list index, when deleting rows
        for rowid in reversed(range(len(self._store))):
            state = self.get_row(rowid).state
            if state & ROW_STATE_CREATE:
                del self._store[rowid]
            else:
                self._store[rowid].state = 0

        # Reassign row IDs and recreate diff table and index
        self._create_index()

    def get_cursor(
            self, predicate: OptCallable = None,
            mapper: OptCallable = None) -> Cursor:
        """ """
        return Cursor(
            index=self._index, getter=self.get_row, predicate=predicate,
            mapper=mapper)

    def get_row(self, rowid: int) -> Record:
        """ """
        return self._diff[rowid] or self._store[rowid]

    def get_rows(self, predicate: OptCallable = None) -> Cursor:
        """ """
        return self.get_cursor(predicate=predicate)

    def append_row(self, *args: Any, **kwds: Any) -> None:
        """ """
        row = self._create_row(*args, **kwds)
        self._store.append(None)
        self._diff.append(row)
        self._append_row_id(row.id)

    def delete_row(self, rowid: int) -> None:
        """ """
        self.get_row(rowid).delete()

    def delete_rows(self, predicate: OptCallable = None) -> None:
        """ """
        for row in self.get_rows(predicate):
            row.delete()

    def update_row(self, rowid: int, **kwds: Any) -> None:
        """ """
        self.get_row(rowid).update(**kwds)

    def update_rows(self, predicate: OptCallable = None, **kwds: Any) -> None:
        """ """
        for row in self.get_rows(predicate):
            row.update(**kwds)

    def select(
            self, columns: OptStrTuple = None,
            predicate: OptCallable = None) -> list:
        """ """
        if not columns:
            mapper = self._get_col_mapper_tuple(self.colnames)
        else:
            check.is_subset(
                "argument 'columns'", set(columns),
                "table column names", set(self.colnames))
            mapper = self._get_col_mapper_tuple(columns)
        return self.get_cursor( # type: ignore
            predicate=predicate, mapper=mapper)

    def _create_index(self) -> None:
        self._index = []
        self._diff = []
        for rowid in range(len(self._store)):
            self._store[rowid].id = rowid
            self._diff.append(None)
            self._index.append(rowid)

    def _get_col_mapper_tuple(self, columns: StrTuple) -> Callable:
        def mapper(row: Record) -> tuple:
            return tuple(getattr(row, col) for col in columns)
        return mapper

    def _get_fields(self) -> FieldTuple:
        return dataclasses.fields(self._Record)

    def _get_colnames(self) -> StrTuple:
        return tuple(field.name for field in self.fields)

    def _create_row_id(self) -> int:
        return len(self._store)

    def _append_row_id(self, rowid: int) -> None:
        self._index.append(rowid)

    def _remove_row_id(self, rowid: int) -> None:
        self._index.remove(rowid)

    def _update_row_diff(self, rowid: int, **kwds: Any) -> None:
        row = self.get_row(rowid)
        new = dataclasses.replace(row, **kwds)
        new.id = rowid
        new.state = row.state
        self._diff[rowid] = new

    def _remove_row_diff(self, rowid: int) -> None:
        self._diff[rowid] = None

    def _create_row(self, *args: Any, **kwds: Any) -> Record:
        return self._Record(*args, **kwds) # pylint: disable=E0110

    def _create_header(self, columns: FieldLike) -> None:
        # Check types of fieldlike column descriptors and convert them to field
        # descriptors, that are accepted by dataclasses.make_dataclass()
        fields: list = []
        for each in columns:
            if isinstance(each, str):
                fields.append(each)
                continue
            check.has_type(f"field {each}", each, tuple)
            check.has_size(f"field {each}", each, min_size=2, max_size=3)
            check.has_type("first arg", each[0], str)
            check.has_type("second arg", each[1], type)
            if len(each) == 2:
                fields.append(each)
                continue
            check.has_type("third arg", each[2], (Field, dict))
            if isinstance(each[2], Field):
                fields.append(each)
                continue
            field = dataclasses.field(**each[2])
            fields.append(each[:2] + (field,))

        # Create record namespace with table hooks
        namespace = {
            '_create_row_id': self._create_row_id,
            '_delete_hook': self._remove_row_id,
            '_restore_hook': self._append_row_id,
            '_update_hook': self._update_row_diff,
            '_revoke_hook': self._remove_row_diff}

        # Create Record dataclass and constructor
        self._Record = dataclasses.make_dataclass(
            'Row', fields, bases=(Record, ), namespace=namespace)

        # Create slots
        self._Record.__slots__ = ['id', 'state'] + [
            field.name for field in dataclasses.fields(self._Record)]

        # Reset store, diff and index
        self._store = []
        self._diff = []
        self._index = []

    # def as_tuples(self):
    #     """ """
    #     return [dataclasses.astuple(rec) for rec in self._store]
    #
    # def as_dicts(self):
    #     """ """
    #     return [dataclasses.asdict(rec) for rec in self._store]
    #
    # def as_array(self):
    #     """ """
    #     return np.array(self.as_tuples())

def addcols(
        base: NpRecArray, data: NpRecArray,
        cols: NpFields = None) -> NpRecArray:
    """Add columns from source table to target table.

    Wrapper function to numpy's `rec_append_fields`_.

    Args:
        base: Numpy record array with table like data
        data: Numpy record array storing the fields to add to the base.
        cols: String or sequence of strings corresponding to the names of the
            new columns. If cols is None, then all columns of the data table
            are appended. Default: None

    Returns:
        Numpy record array containing the base array, as well as the
        appended columns.

    """
    cols = cols or getattr(data, 'dtype').names
    check.has_type("argument 'cols'", cols, (tuple, str))
    cols = list(cols) # make cols mutable

    # Append fields
    return nprf.rec_append_fields(base, cols, [data[c] for c in cols])
