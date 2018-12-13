# -*- coding: utf-8 -*-
"""Table and Table Proxy for Data Integration."""

__author__ = 'Patrick Michl'
__email__ = 'frootlab@gmail.com'
__license__ = 'GPLv3'
__docformat__ = 'google'

import abc
import itertools
import random
from typing import NewType
import dataclasses
from nemoa.base import attrib, check, operator, pattern
from nemoa.errors import RowLookupError, CursorModeError, ProxyError
from nemoa.errors import InvalidTypeError
from nemoa.types import Tuple, StrDict, StrList, StrTuple, void
from nemoa.types import OptIntList, OptOp, Callable
from nemoa.types import OptStrTuple, OptInt, List, OptStr, Iterator, Any, Type
from nemoa.types import Mapping, MappingProxy, OptMapping, Union, Optional
from nemoa.types import TypeHint

#
# Structural Types
#

# Various
OrderByType = Optional[Union[str, StrList, StrTuple, Callable]]
OptContainer = Optional[attrib.Container]
OptMappingProxy = Optional[MappingProxy]

# Fields
Field = dataclasses.Field
FieldTuple = Tuple[Field, ...]
OptFieldTuple = Optional[FieldTuple]

# Columns
ColDefA = str # Column name
ColDefB = Tuple[str, type] # Column name and type
ColDefC = Tuple[str, type, StrDict] # Column name, type and constraints
ColDefD = Tuple[str, type, Field] # Column name, type and constraints
ColDef = Union[ColDefA, ColDefB, ColDefC, ColDefD]
ColsDef = Tuple[ColDef, ...]
OptColsDef = Optional[ColsDef]

# Rows
Row = NewType('Row', 'Record')
OptRow = Optional[Row]
RowList = List[Row]
RowLike = Union[tuple, Mapping, Row]
RowLikeList = Union[RowList, List[tuple], List[Mapping]]
ValuesType = Optional[Union[RowLike, RowLikeList]]

#
# Constants
#

# Record State
RECORD_STATE_FLAG_CREATE = 0b0001
RECORD_STATE_FLAG_UPDATE = 0b0010
RECORD_STATE_FLAG_DELETE = 0b0100

# Cursor Mode
CURSOR_MODE_FLAG_BUFFERED = 0b0001
CURSOR_MODE_FLAG_INDEXED = 0b0010
CURSOR_MODE_FLAG_SCROLLABLE = 0b0100
CURSOR_MODE_FLAG_RANDOM = 0b1000

# Proxy Mode
PROXY_MODE_FLAG_CACHE = 0b0001
PROXY_MODE_FLAG_INCREMENTAL = 0b0010
PROXY_MODE_FLAG_READONLY = 0b0100

#
# Record Base Class and Class Constructor
#

class Record(abc.ABC):
    """Abstract base class for :mod:`dataclasses` based records.

    Args:
        *args: Arguments, that are valid with respect to the column definitions
            of derived :mod:'dataclasses'.
        **kwds: Keyword arguments, that are valid with respect to the column
            definitions of derived :mod:'dataclasses'.

    """

    __slots__: StrTuple = ('_id', '_name', '_state')

    _id: int
    _name: str
    _state: int

    def __post_init__(self, *args: Any, **kwds: Any) -> None:
        self._validate()
        self._id = self._get_newid()
        self._state = RECORD_STATE_FLAG_CREATE

    def _validate(self) -> None:
        """Check validity of the field types."""
        fields = getattr(self, '__dataclass_fields__', {})
        for name, field in fields.items():
            if isinstance(field.type, str):
                continue # Do not type check structural types like 'typing.Any'
            value = getattr(self, name)
            check.has_type(f"field '{name}'", value, field.type)

    def _delete(self) -> None:
        """Mark record as deleted and remove it's ID from index."""
        if not self._state & RECORD_STATE_FLAG_DELETE:
            self._state |= RECORD_STATE_FLAG_DELETE
            self._delete_hook(self._id)

    def _update(self, **kwds: Any) -> None:
        """Mark record as updated and write the update to diff table."""
        if not self._state & RECORD_STATE_FLAG_UPDATE:
            self._state |= RECORD_STATE_FLAG_UPDATE
            self._update_hook(self._id, **kwds)

    def _restore(self) -> None:
        """Mark record as not deleted and append it's ID to index."""
        if self._state & RECORD_STATE_FLAG_DELETE:
            self._state &= ~RECORD_STATE_FLAG_DELETE
            self._restore_hook(self._id)

    def _revoke(self) -> None:
        """Mark record as not updated and remove the update from diff table."""
        if self._state & RECORD_STATE_FLAG_UPDATE:
            self._state &= ~RECORD_STATE_FLAG_UPDATE
            self._revoke_hook(self._id)

    @abc.abstractmethod
    def _get_newid(self) -> int:
        raise NotImplementedError()

    @abc.abstractmethod
    def _delete_hook(self, rowid: int) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _restore_hook(self, rowid: int) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _update_hook(self, rowid: int, **kwds: Any) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _revoke_hook(self, rowid: int) -> None:
        raise NotImplementedError()

def create_record_class(
        columns: ColsDef, newid: OptOp = None,
        **kwds: Any) -> Type[Record]:
    """Create a new subclass of the Record class.

    Args:
        columns: Tuple of *column definitions*. All column definitions
            independent from each other can be given in one of the following
            formats: (1) In order to only specify the name of the column,
            without further information, the colum definition has to be given as
            a string `<name>`. Thereby the choice of `<name>` is restricted to
            valid identifiers, described by [UAX31]_. (2) If, additionally to
            the name, also the data type of the column shall be specified, then
            the column definition has to be given as a tuple `(<name>, <type>)`.
            Thereby `<type>` is required to by a valid :class:`type`, like
            like :class:`str`, :class:`int`, :class:`float` or :class:`Date
            <datetime.datetime>`. (3) Finally the column definition may also
            contain supplementary constraints and metadata. In this case the
            definition has to be given as a tuple `(<name>, <type>, <dict>)`,
            where `<dict>` is dictionary which comprises any items, documented
            by the function :func:`dataclasses.fields`.
        newid: Optional reference to a method, which returns the current ID of
            a new instance of the Record class. By default the Record class
            uses an internal Iterator.
        **kwds: Optional references to methods, which are bound to specific
            events of the new Record class. These events are: 'delete',
            'restore', 'update' and 'revoke'. By default no events are hooked.

    Returns:
        New subclass of the Record class.

    """
    # Check column defnitions and convert them to field descriptors, as required
    # by dataclasses.make_dataclass()
    check.has_type("'columns'", columns, tuple)
    fields: list = []
    names: StrList = []
    for column in columns:
        if isinstance(column, str):
            fields.append(column)
            names.append(column)
            continue
        check.has_type(f'column {column}', column, tuple)
        check.has_size(f'column {column}', column, min_size=2, max_size=3)
        check.has_type('first argument', column[0], str)
        check.has_type('second argument', column[1], TypeHint)
        if len(column) == 2:
            fields.append(column)
            names.append(column[0])
            continue
        check.has_type('third argument', column[2], (Field, dict))
        if isinstance(column[2], Field):
            fields.append(column)
            names.append(column[0])
            continue
        field = dataclasses.field(**column[2])
        names.append(column[0])
        fields.append(column[:2] + (field,))

    # Dynamically create a dataclass, which is inherited from Record class.
    # Thereby create an ampty '__slots__' attribute to avoid collision with
    # default values (which in dataclasses are stored as class variables),
    # while avoiding the creation of a '__dict__' attribute
    namespace: StrDict = {}
    if newid and callable(newid):
        namespace['_get_newid'] = newid
    else:
        counter = itertools.count() # Infinite iterator
        namespace['_get_newid'] = lambda obj: next(counter)
    hooks = {
        'delete': '_delete_hook', 'restore': '_restore_hook',
        'update': '_update_hook', 'revoke': '_revoke_hook'}
    for key in hooks:
        namespace[hooks[key]] = kwds.get(key, void)
    namespace['__slots__'] = tuple()
    dataclass = dataclasses.make_dataclass(
        Record.__name__, fields, bases=(Record, ), namespace=namespace)

    # Dynamically create a new class, which is inherited from dataclass,
    # with corrected __slots__ attribute.
    return type(dataclass.__name__, (dataclass,), {'__slots__': names})

#
# Cursor Class
#

class Cursor(attrib.Container):
    """Cursor Class.

    Args:
        index: List of row IDs, that are traversed by the cursor. By default the
            attribute '_index' of the parent object is used.
        mode: Named string identifier for the cursor :py:attr:`.mode`. The
            default cursor mode is 'forward-only indexed'. Note: After
            initializing the curser, it's mode can not be changed anymore.
        batchsize: Integer, that specifies the default number of rows which is
            to be fetched by the method :meth:`.fetch`. It defaults to 1,
            meaning to fetch a single row at a time. Whether and which batchsize
            to use depends on the application and should be considered with
            care. The batchsize can also be adapted during the lifetime of the
            cursor, which allows dynamic performance optimization.
        getter: Method which is used to fetch single rows by their row ID.
        predicate: Optional filter operator, which determines, if a row is
            included within the result set or not. By default all rows are
            included within the result set
        sorter: Optional sorting operator, which determines the order of the
            rows withon the result set. By default the order is determined by
            the creation of the rows.
        parent: Reference to parent :class:'attribute group
            <nemoa.base.attrib.Group>', which is used for inheritance and
            shared attributes. By default no parent is referenced.

    """

    #
    # Public Attributes
    #

    mode: property = attrib.Virtual('_get_mode')
    mode.__doc__ = """
    The read-only attribute :term:`cursor mode` provides information about the
    *scrolling type* and the *operation mode* of the cursor.
    """

    batchsize: property = attrib.MetaData(dtype=int, default=1)
    """
    The read-writable integer attribute *batchsize* specifies the default number
    of rows which is to be fetched by the method :meth:`.fetch`. It defaults
    to 1, meaning to fetch a single row at a time. Whether and which batchsize
    to use depends on the application and should be considered with care. The
    batchsize can also be adapted during the lifetime of the cursor, which
    allows dynamic performance optimization.
    """

    rowcount: property = attrib.Virtual('_get_rowcount')
    """
    The read-only integer attribute *rowcount* identifies the current number of
    rows within the cursor.
    """

    #
    # Protected Attributes
    #

    _mode: property = attrib.MetaData(dtype=int, factory='_default_mode')
    _index: property = attrib.MetaData(dtype=list, inherit=True)
    _getter: property = attrib.Temporary(dtype=Callable)
    _sorter: property = attrib.Temporary(dtype=Callable)
    _filter: property = attrib.Temporary(dtype=Callable)
    _buffer: property = attrib.Temporary(dtype=list, default=[])

    #
    # Special Methods
    #

    def __init__(
            self, index: OptIntList = None, mode: OptStr = None,
            batchsize: OptInt = None, getter: OptOp = None,
            predicate: OptOp = None, sorter: OptOp = None,
            parent: OptContainer = None) -> None:
        # Initialize Attribute Container with parent Attribute Group
        super().__init__(parent=parent)

        # Get cursor parameters from arguments
        if index is not None:
            self._index = index
        self._getter = getter
        self._filter = predicate
        self._sorter = sorter
        if mode:
            self._set_mode(mode)
        if batchsize:
            self.batchsize = batchsize

        # Check validity of cursor parameters
        self._check_validity()

        # Initialize cursor
        if self._mode & CURSOR_MODE_FLAG_INDEXED:
            self._create_index() # Initialize index
        if self._mode & CURSOR_MODE_FLAG_BUFFERED:
            self._create_buffer() # Initialize buffer
        self.reset() # Initialize iterator

    def __iter__(self) -> Iterator:
        self.reset()
        return self

    def __next__(self) -> Row:
        return self.next()

    def __len__(self) -> int:
        return self.rowcount

    #
    # Public Methods
    #

    def fetch(self, size: OptInt = None) -> RowList:
        """Fetch rows from the result set.

        Args:
            size: Integer value, which represents the number of rows, which is
                fetched from the result set. For the given size -1 all remaining
                rows from the result set are fetched. By default the number of
                rows is given by the cursors attribute :attr:`.batchsize`.

        Returns:
            Result set given by a list of :term:`row like` data.

        """
        # TODO: Scrollable cursors are defined on sequences not on iterables:
        # the cursor can use operations, such as FIRST, LAST, PRIOR, NEXT,
        # RELATIVE n, ABSOLUTE n to navigate the results
        if size is None:
            size = self.batchsize
        if self._mode & CURSOR_MODE_FLAG_RANDOM and size <= 0:
            raise CursorModeError(self.mode, 'fetching all rows')
        finished = False
        rows: RowList = []
        while not finished:
            try:
                rows.append(self.next())
            except StopIteration:
                finished = True
            else:
                finished = 0 < size <= len(rows)
        return rows

    def next(self) -> Row:
        """Return next row that matches the given filter."""
        mode = self._mode
        if mode & CURSOR_MODE_FLAG_BUFFERED:
            return self._get_next_from_buffer()
        if mode & CURSOR_MODE_FLAG_INDEXED:
            return self._get_next_from_fixed_index()
        # TODO: For dynamic cursors implement _get_next_from_dynamic_index()
        return self._get_next_from_fixed_index()

    def reset(self) -> None:
        """Reset cursor position before the first record."""
        mode = self._mode
        if mode & CURSOR_MODE_FLAG_BUFFERED: # Iterate over fixed result set
            self._iter_buffer = iter(self._buffer)
        elif mode & CURSOR_MODE_FLAG_INDEXED: # Iterate over fixed index
            self._iter_index = iter(self._index)
        else: # TODO: handle case for dynamic cursors by self._iter_table
            self._iter_index = iter(self._index)

    #
    # Protected Methods
    #

    def _check_validity(self) -> None:
        mode = self._mode

        # Sorting rows requires a buffered cursor
        if self._sorter and not mode & CURSOR_MODE_FLAG_BUFFERED:
            raise CursorModeError(self.mode, 'sorting rows')

        # Sorting rows is not supported by random cursors
        if self._sorter and mode & CURSOR_MODE_FLAG_RANDOM:
            raise CursorModeError(self.mode, 'sorting rows')

    def _create_index(self) -> None:
        if isinstance(self._index, list):
            self._index = self._index.copy()
        else:
            self._index = []

    def _create_buffer(self) -> None:
        cur = self.__class__(
            index=self._index, getter=self._getter, predicate=self._filter)
        buffer = cur.fetch(-1) # Create result set from dynamic cursor
        if self._sorter:
            buffer = self._sorter(buffer) # Sort result set
        self._buffer = buffer

    def _default_mode(self) -> int:
        if self._sorter:
            return CURSOR_MODE_FLAG_BUFFERED
        return CURSOR_MODE_FLAG_INDEXED

    def _get_next_from_fixed_index(self) -> Row:
        is_random = self._mode & CURSOR_MODE_FLAG_RANDOM
        matches = False
        while not matches:
            if is_random:
                rowid = random.randrange(len(self._index))
            else:
                rowid = next(self._iter_index)
            row = self._getter(rowid)
            if self._filter:
                matches = self._filter(row)
            else:
                matches = True
        return row

    def _get_next_from_buffer(self) -> Row:
        if self._mode & CURSOR_MODE_FLAG_RANDOM:
            rowid = random.randrange(len(self._buffer))
            return self._buffer[rowid]
        return next(self._iter_buffer)

    def _get_mode(self) -> str:
        mode = self._mode
        tokens = []

        # Add name of traversal mode
        if mode & CURSOR_MODE_FLAG_RANDOM:
            tokens.append('random')
        elif mode & CURSOR_MODE_FLAG_SCROLLABLE:
            tokens.append('scrollable')

        # Add name of operation mode
        if mode & CURSOR_MODE_FLAG_BUFFERED:
            tokens.append('static')
        elif mode & CURSOR_MODE_FLAG_INDEXED:
            tokens.append('indexed')
        else:
            tokens.append('dynamic')

        return ' '.join(tokens)

    def _set_mode(self, name: str) -> None:
        mode = 0
        name = name.strip(' ').lower()

        # Set traversal mode flags
        if 'random' in name:
            mode |= CURSOR_MODE_FLAG_RANDOM
        elif 'scrollable' in name:
            mode |= CURSOR_MODE_FLAG_SCROLLABLE

        # Set operation mode flags
        if 'static' in name:
            mode |= CURSOR_MODE_FLAG_BUFFERED | CURSOR_MODE_FLAG_INDEXED
        elif 'indexed' in name:
            mode |= CURSOR_MODE_FLAG_INDEXED

        self._mode = mode

    def _get_rowcount(self) -> int:
        mode = self._mode
        if mode & CURSOR_MODE_FLAG_RANDOM:
            raise CursorModeError(self.mode, 'counting rows')
        if mode & CURSOR_MODE_FLAG_BUFFERED:
            return len(self._buffer)
        if self._filter:
            raise CursorModeError(self.mode, 'counting filtered rows')
        return len(self._index)

#
# Table Class
#

class Table(attrib.Container):
    """Table Class.

    Args:
        name: Optional table name. If provided, the choice of the table name is
            restricted to valid identifiers, described by [UAX31]_.
        columns: Optionl tuple of *column definitions*. All column definitions
            independent from each other can be given in one of the following
            formats: (1) In order to only specify the name of the column,
            without further information, the colum definition has to be given as
            a string `<name>`. Thereby the choice of `<name>` is restricted to
            valid identifiers, described by [UAX31]_. (2) If, additionally to
            the name, also the data type of the column shall be specified, then
            the column definition has to be given as a tuple `(<name>, <type>)`.
            Thereby `<type>` is required to by a valid :class:`type`, like
            like :class:`str`, :class:`int`, :class:`float` or :class:`Date
            <datetime.datetime>`. (3) Finally the column definition may also
            contain supplementary constraints and metadata. In this case the
            definition has to be given as a tuple `(<name>, <type>, <dict>)`,
            where `<dict>` is dictionary which comprises any items, documented
            by the function :func:`dataclasses.fields`.
        metadata: Optional dictionary, with supplementary metadata of the table.
            This does not comprise metadata of the fields, which has to be
            included within the field declarations.
        parent: Reference to parent :class:`attribute group
            <nemoa.base.attrib.Group>`, which is used for inheritance and
            shared attributes. By default no parent is referenced.

    """

    #
    # Public Attributes
    #

    name: property = attrib.Virtual(fget='_get_name', fset='_set_name')
    name.__doc__ = "Name of the table."

    metadata: property = attrib.Virtual(fget='_get_metadata_proxy')
    metadata.__doc__ = """
    Read-only attribute, that provides an access to the tables metadata by a
    :class:`MappingProxy <types.MappingProxyType>`. Individual entries can be
    accessed and changed by the methods :meth:`.get_metadata` and
    :meth:`.set_metadata`. This attribute is not used by the :class:`Table class
    <nemoa.db.table.Table>` itself, but intended for data integration by
    third-party extensions.
    """

    fields: property = attrib.Virtual(fget='_get_fields')
    fields.__doc__ = """
    Read-only attribute, that provides information about the fields of the
    table, as returned by the function :func:`dataclasses.fields`.
    """

    columns: property = attrib.Virtual(fget='_get_columns')
    columns.__doc__ = """
    Read-only attribute containing a tuple with all column names of the table.
    The order of the column names reflects the order of the corresponding fields
    in the table.
    """

    #
    # Protected Attributes
    #

    _data: property = attrib.Content(dtype=list)
    _name: property = attrib.MetaData(dtype=str)
    _metadata: property = attrib.MetaData(dtype=Mapping)
    _metadata_proxy: property = attrib.Temporary(dtype=MappingProxy)
    _record: property = attrib.Temporary()
    _diff: property = attrib.Temporary(dtype=list, default=[])
    _index: property = attrib.Temporary(dtype=list, default=[])
    _iter_index: property = attrib.Temporary()

    #
    # Special Methods
    #

    def __init__(
            self, name: OptStr = None, columns: OptColsDef = None,
            metadata: OptMapping = None, parent: OptContainer = None) -> None:
        super().__init__(parent=parent) # Initialize Container Parameters

        # Initialize Table Structure
        if columns:
            self.create(name, columns, metadata=metadata)

    def __iter__(self) -> Iterator:
        self._iter_index = iter(self._index)
        return self

    def __next__(self) -> Record:
        row = self.row(next(self._iter_index))
        while not row:
            row = self.row(next(self._iter_index))
        return row

    def __len__(self) -> int:
        return len(self._index)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name='{self.name}')"

    #
    # Public Methods
    #

    def create(
            self, name: OptStr, columns: ColsDef,
            metadata: OptMapping = None) -> None:
        """Create table structure.

        This method is motivated by the The SQL `CREATE TABLE`_ statement and
        used to define and initialize the structure of the table and it's
        fields. This includes naming the table, defining and initializing the
        field parameters by column names, types and further constraints, like
        default values, and supplementary table metadata.

        Args:
            name: The table name is required to be a valid identifier as defined
                in [UAX31]_.
            columns: Tuple of *column definitions*. All column definitions
                independent from each other can be given in one of the following
                formats: (1) In order to only specify the name of the column,
                without further information, the colum definition has to be
                given as a string `<name>`. Thereby the choice of `<name>` is
                restricted to valid identifiers, described by [UAX31]_. (2) If,
                additionally to the name, also the data type of the column shall
                be specified, then the column definition has to be given as a
                tuple `(<name>, <type>)`. Thereby `<type>` is required to by a
                valid :class:`type`, like like :class:`str`, :class:`int`,
                :class:`float` or :class:`Date <datetime.datetime>`. (3) Finally
                the column definition may also contain supplementary constraints
                and metadata. In this case the definition has to be given as a
                tuple `(<name>, <type>, <dict>)`, where `<dict>` is dictionary
                which comprises any items, documented by the function
                :func:`dataclasses.fields`.
            metadata: Optional dictionary (or arbitrary mapping), with
                supplementary metadata of the table. This does not comprise
                metadata of the columns, which has to be included within the
                column definitions.

        .. _CREATE TABLE: https://en.wikipedia.org/wiki/Create_(SQL)

        """
        self._set_name(name) # Set Name of the Table
        self._create_metadata(metadata) # Set supplementary Metadata of Table
        self._create_header(columns) # Dynamically create a new Record Class

    def drop(self) -> None:
        """Delete table data and table structure.

        This method is motivated by the the SQL `DROP TABLE`_ statement and used
        to delete the table data and the table structure, given by the field
        declarations, the table metadata and the table identifier.

        Warning:
            This operation should be treated with caution as it can not be
            reverted by calling :meth:`.rollback`.

        .. _DROP TABLE: https://en.wikipedia.org/wiki/Drop_(SQL)

        """
        self.truncate() # Delete Table Data
        self._delete_header() # Delete Table Structure
        self._delete_metadata() # Delete Table Metadata
        self._delete_name() # Delete Table Identifier

    def truncate(self) -> None:
        """Delete table data.

        This method is motivated by the SQL `TRUNCATE TABLE`_ statement and used
        to delete the data inside a table, but not the table structure and
        metadata.

        Warning:
            This operation should be treated with caution as it can not be
            reverted by calling :meth:`.rollback`.

        .. _TRUNCATE TABLE: https://en.wikipedia.org/wiki/Truncate_(SQL)

        """
        self._data = [] # Initialize Storage Table
        self._diff = [] # Initialize Diff Table
        self._index = [] # Initialize Table Master Index

    def commit(self) -> None:
        """Apply data changes to table.

        This method is motivated by the SQL `COMMIT`_ statement and applies
        all data :meth:`updates <.update>`, :meth:`inserts <.insert>` and
        :meth:`deletions <.delete>` since the creation of the table or
        the last :meth:`.commit` and makes all changes visible to other users.

        .. _COMMIT: https://en.wikipedia.org/wiki/Commit_(SQL)

        """
        # Update data table and index
        for rowid in list(range(len(self._data))):
            row = self.row(rowid)
            if not row:
                continue
            state = row._state # pylint: disable=W0212
            if state & RECORD_STATE_FLAG_DELETE:
                self._data[rowid] = None
                try:
                    self._index.remove(rowid)
                except ValueError:
                    pass
            elif state & (RECORD_STATE_FLAG_CREATE | RECORD_STATE_FLAG_UPDATE):
                self._data[rowid] = self._diff[rowid]
                self._data[rowid]._state = 0 # pylint: disable=W0212

        self._diff = [None] * len(self._data) # Initialize Diff Table

    def rollback(self) -> None:
        """Revert data changes from table.

        This method is motivated by the SQL `ROLLBACK`_ statement and reverts
        all data :meth:`updates <.update>`, :meth:`inserts <.insert>` and
        :meth:`deletions <.delete>` since the creation of the table or
        the last :meth:`.commit`.

        .. _ROLLBACK: https://en.wikipedia.org/wiki/Rollback_(SQL)

        """
        # Remove newly created rows from index and reset states of already
        # existing rows
        for rowid in list(range(len(self._data))):
            row = self.row(rowid)
            if not row:
                continue
            state = row._state # pylint: disable=W0212
            if state & RECORD_STATE_FLAG_CREATE:
                try:
                    self._index.remove(rowid)
                except ValueError:
                    pass
            else:
                self._data[rowid]._state = 0 # pylint: disable=W0212

        self._diff = [None] * len(self._data) # Initialize Diff Table

    def insert(
            self, values: ValuesType = None,
            columns: OptStrTuple = None) -> None:
        """Append one or more records to the table.

        This method is motivated by the SQL `INSERT`_ statement and appends one
        ore more records to the table. The data changes can be organized in
        transactions by :meth:`.commit` and :meth:`.rollback`.

        Args:
            values: Single record, given as :term:`row like` data or multiple
                records given as list of row like data. If the records are given
                as tuples, the corresponding column names are determined from
                the argument *columns*.
            columns: Optional tuple of known column names. By default the
                columns are taken from the attribute :attr:`.columns`.

        .. _INSERT: https://en.wikipedia.org/wiki/Insert_(SQL)

        """
        values = values or tuple([]) # Get default value tuple
        if not isinstance(values, list):
            self._append_row(values, columns)
            return
        for row in values:
            self._append_row(row, columns)

    def update(self, where: OptOp = None, **kwds: Any) -> None:
        """Update values of one or more records from the table.

        This method is motivated by the SQL `UPDATE`_ statement and changes the
        values of all records in the table, that satisfy the `WHERE`_ clause
        given by the keyword argument 'where'. The data changes can be organized
        in transactions by :meth:`.commit` and :meth:`.rollback`.

        Args:
            where: Optional filter operator, which determines, if a row is
                included within the result set or not. By default all rows are
                included within the result set.
            **kwds: Items, which keys are valid column names of the table, and
                the values the new data, stored in the corresponding fields.

        .. _DELETE: https://en.wikipedia.org/wiki/Delete_(SQL)
        .. _WHERE: https://en.wikipedia.org/wiki/Where_(SQL)

        """
        for row in self._create_cursor(predicate=where):
            row._update(**kwds) # pylint: disable=W0212

    def delete(self, where: OptOp = None) -> None:
        """Delete one or more records from the table.

        This method is motivated by the SQL `DELETE`_ statement and marks all
        records in the table as deleted, that satisfy the `WHERE`_ clause given
        by the keyword argument 'where'. The data changes can be organized in
        transactions by :meth:`.commit` and :meth:`.rollback`.

        Args:
            where: Optional filter operator, which determines, if a row is
                included within the result set or not. By default all rows are
                included within the result set.

        .. _DELETE: https://en.wikipedia.org/wiki/Delete_(SQL)
        .. _WHERE: https://en.wikipedia.org/wiki/Where_(SQL)

        """
        for row in self._create_cursor(predicate=where):
            row._delete() # pylint: disable=W0212

    def select(
            self, columns: OptStrTuple = None, where: OptOp = None,
            orderby: OrderByType = None, reverse: bool = False,
            dtype: type = tuple, batchsize: OptInt = None,
            mode: OptStr = None) -> RowLikeList:
        """Get cursor on a specified result set of records from table.

        This method is motivated by the SQL `SELECT`_ statement and creates
        a :class:`Cursor class <nemoa.db.table.Cursor>` instance with specified
        properties.

        Args:
            columns: Optional tuple of column names, that are known to the
                table. By default the columns are taken from the attribute
                :attr:`.columns`.
            where: Optional filter operator, which determines, if a row is
                included within the result set or not. By default all rows are
                included within the result set.
            orderby: Optional parameter, that determine(s) the order of the rows
                within the result set. If provided, the parameter may be given
                as a column name, a tuple of column names or a callable sorting
                function. By default the order is determined by the creation
                order of the rows.
            reverse: Boolean value, which determines if the sorting order of the
                rows is reversed. For the default value ``False`` the sorting
                order is ascending with respect to given column names in the
                orderby parameter, for ``True`` it is descending.
            dtype: Format of the :term:`row like` data, which is used to
                represent the returned values of the result set. By default
                the result set is returned as a list of tuples.
            batchsize: Integer, that specifies the default number of rows which
                is to be fetched by the method :meth:`Cursor.fetch
                <nemoa.table.Cursor.fetch>`. It defaults to 1, meaning to fetch
                a single row at a time. Whether and which batchsize to use
                depends on the application and should be considered with care.
                The batchsize can also be adapted during the lifetime of the
                cursor, which allows dynamic performance optimization.
            mode: Named string identifier for the cursor :py:attr:`.mode`. The
                default cursor mode is 'forward-only indexed'. Note: After
                initializing the curser, it's mode can not be changed anymore.

        Returns:
            New instance of :class:`Cursor class <nemoa.db.table.Cursor>` on
            on a specified result set from the table.

        .. _SELECT: https://en.wikipedia.org/wiki/Select_(SQL)

        """
        # Create sorting operator for parameters 'orderby' and 'reverse'
        sorter = self._create_sorter(orderby, reverse=reverse)

        # Create cursor, which specifies the result set
        cursor = self._create_cursor(
            predicate=where, sorter=sorter, batchsize=batchsize, mode=mode)

        # Create grouping operator for parameter 'groupby'

        # Create mapping operator with respect to 'columns' and 'dtype'
        mapper = self._create_mapper(columns, dtype=dtype)

        return list(map(mapper, cursor)) # Map result set

    def get_metadata(self, key: str) -> Any:
        """Get single entry from table metadata.

        Args:
            key: Name of metadata entry

        Returns:
            Value of metadata entry.

        """
        return self._metadata[key]

    def set_metadata(self, key: str, val: Any) -> None:
        """Change metadata entry of table."""
        self._metadata[key] = val

    def row(self, rowid: int) -> OptRow:
        """Get single row by row ID."""
        return self._diff[rowid] or self._data[rowid]

    def pack(self) -> None:
        """Remove empty records from data and rebuild table index."""
        # Commit pending changes
        self.commit()

        # Remove empty records
        self._data = list(filter(None.__ne__, self._data))

        # Rebuild table index
        self._index = list(range(len(self._data)))
        for rowid in self._index:
            self._data[rowid]._id = rowid # pylint: disable=W0212

        # Rebuild diff table
        self._diff = [None] * len(self._data)

    #
    # Protected Methods
    #

    def _append_row(self, row: RowLike, columns: OptStrTuple = None) -> None:
        if columns:
            if not isinstance(row, tuple):
                raise TypeError() # TODO
            rec = self._create_record(**dict(zip(columns, row)))
        else:
            rec = self._create_record(row)
        self._data.append(None)
        self._diff.append(rec)
        self._append_rowid(rec._id) # pylint: disable=W0212

    def _append_rowid(self, rowid: int) -> None:
        self._index.append(rowid)

    def _create_metadata(self, mapping: OptMapping = None) -> None:
        check.has_opt_type("'metadata'", mapping, Mapping)
        self._metadata = mapping or {}
        self._metadata_proxy = MappingProxy(self._metadata)

    def _delete_metadata(self) -> None:
        del self._metadata_proxy
        del self._metadata

    def _create_cursor(
            self, predicate: OptOp = None, sorter: OptOp = None,
            batchsize: OptInt = None,
            mode: OptStr = None) -> Cursor:
        return Cursor(
            getter=self.row, predicate=predicate, sorter=sorter,
            batchsize=batchsize, mode=mode, parent=self)

    def _create_header(self, columns: ColsDef) -> None:
        # Dynamically create a new record class
        self._record = create_record_class(columns,
            newid=self._get_new_rowid,
            delete=self._remove_rowid,
            restore=self._append_rowid,
            update=self._update_row_diff,
            revoke=self._remove_row_diff)
        self.truncate() # Initialize table data

    def _create_record(self, data: RowLike) -> Record:
        if isinstance(data, tuple):
            return self._record(*data)
        if isinstance(data, Mapping):
            return self._record(**data)
        if isinstance(data, Record):
            keys = self.columns
            vals = tuple(getattr(data, key, None) for key in keys)
            return self._record(**dict(zip(keys, vals)))
        raise InvalidTypeError("'data'", data, (tuple, list, Mapping, Record))

    def _delete_header(self) -> None:
        self.truncate() # Delete table data
        del self._record # Delete record constructor

    def _create_mapper(
            self, columns: OptStrTuple, dtype: type = tuple) -> Callable:
        if columns:
            check.is_subset(
                "'columns'", set(columns),
                "table column names", set(self.columns))
        columns = columns or self.columns
        return operator.get_attrs(*columns, dtype=dtype)

    def _create_sorter(
            self, orderby: OrderByType, reverse: bool = False) -> OptOp:
        if callable(orderby):
            # TODO: check if orderby is a valid sorter
            return orderby
        if orderby is None and not reverse:
            return None
        if isinstance(orderby, str):
            attrs = [orderby]
        elif isinstance(orderby, (list, tuple)):
            attrs = list(orderby)
        else:
            attrs = []
        return operator.orderby_attrs(*attrs, reverse=reverse)

    def _get_new_rowid(self) -> int:
        return len(self._data)

    def _get_last_row(self, column: str) -> OptRow:
        try:
            return self._data[-1]
        except IndexError:
            return None

    def _get_columns(self) -> StrTuple:
        return tuple(field.name for field in self.fields)

    def _get_fields(self) -> OptFieldTuple:
        if not hasattr(self, '_record') or not self._record:
            return None
        return dataclasses.fields(self._record)

    def _get_name(self) -> str:
        return self._name or self._default_name()

    def _default_name(self) -> str:
        return 'unkown'

    def _delete_name(self) -> None:
        del self._name

    def _set_name(self, name: OptStr) -> None:
        if isinstance(name, str):
            check.is_identifier(f"'name'", name)
            self._name = name
        else:
            self._name = self._default_name()

    def _get_metadata_proxy(self) -> OptMappingProxy:
        return getattr(self, '_metadata_proxy', None)

    def _remove_row_diff(self, rowid: int) -> None:
        self._diff[rowid] = None

    def _remove_rowid(self, rowid: int) -> None:
        self._index.remove(rowid)

    def _update_row_diff(self, rowid: int, **kwds: Any) -> None:
        row = self.row(rowid)
        if not row:
            raise RowLookupError(rowid)
        new_row = dataclasses.replace(row, **kwds)
        new_row._id = rowid # pylint: disable=W0212
        new_row._state = row._state # pylint: disable=W0212
        self._diff[rowid] = new_row

#
# Proxy Class
#

class Proxy(Table, pattern.Proxy):
    """Abstract Base Class for Table Proxies.

    Args:
        proxy_mode: Optional Integer, that determines the operation mode of the
            proxy.
        parent: Reference to parent :class:`attribute group
            <nemoa.base.attrib.Group>`, which is used for inheritance and
            shared attributes. By default no parent is referenced.

    """

    _proxy_mode: property = attrib.MetaData(dtype=int, default=1)

    #
    # Special Methods
    #

    def __init__(
            self, proxy_mode: OptInt = None,
            parent: OptContainer = None) -> None:
        # Initialize Abstract Proxy
        pattern.Proxy.__init__(self)

        # Initialize Empty Table
        Table.__init__(self, parent=parent)

        # Initialize Table Proxy Parameters
        if proxy_mode is None:
            proxy_mode = PROXY_MODE_FLAG_CACHE # Set default proxy mode
        self._proxy_mode = proxy_mode

    def _post_init(self) -> None:
        # Retrieve all rows from source if table is cached
        if self._proxy_mode & PROXY_MODE_FLAG_CACHE:
            self.pull()

    #
    # Public Methods
    #

    def commit(self) -> None:
        """Push changes to source table and apply changes to local table."""
        if self._proxy_mode & PROXY_MODE_FLAG_READONLY:
            raise ProxyError('changes can not be commited in readonly mode')

        # For incremental updates of the source, the push request requires, that
        # changes have not yet been applied to the local table
        if self._proxy_mode & PROXY_MODE_FLAG_INCREMENTAL:
            self.push()
            super().commit()
            return
        # For full updates of the source, the push request requires, that all
        # changes have been applied to the local table
        super().commit()
        self.push()
