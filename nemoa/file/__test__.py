# -*- coding: utf-8 -*-
"""Unittests for submodules of package 'nemoa.file'."""

__author__ = 'Patrick Michl'
__email__ = 'frootlab@gmail.com'
__license__ = 'GPLv3'
__docformat__ = 'google'

from configparser import ConfigParser
import tempfile
from pathlib import Path
import numpy as np
from nemoa.file import binfile, csv, ini, textfile
from nemoa.test import ModuleTestCase
from nemoa.types import List

class TestBinfile(ModuleTestCase):
    """Testcase for the module nemoa.file.binfile."""

    module = 'nemoa.file.binfile'

    def setUp(self) -> None:
        self.filepath = Path(tempfile.NamedTemporaryFile().name + '.gz')
        self.data = b'eJxrYK4tZDoiGBkGT0ZqotZJzt3/AbFpXoAgyI=='
        binfile.save(self.data, self.filepath)

    def test_openx(self) -> None:
        filepath = Path(tempfile.NamedTemporaryFile().name)
        with self.subTest(file=filepath):
            with binfile.openx(filepath, mode='w') as fh:
                fh.write(self.data)
            if filepath.is_file():
                with binfile.openx(filepath, mode='r') as fh:
                    data = fh.read()
                filepath.unlink()
                self.assertTrue(data == self.data)
        file = filepath.open(mode='wb')
        with self.subTest(file=file):
            with binfile.openx(file, mode='w') as fh:
                fh.write(self.data)
            if not file.closed:
                file.close()
                file = filepath.open(mode='rb')
                with binfile.openx(file, mode='r') as fh:
                    data = fh.read()
                if not file.closed:
                    file.close()
                    self.assertTrue(data == self.data)

    def test_save(self) -> None:
        self.assertTrue(self.filepath.is_file())

    def test_load(self) -> None:
        data = binfile.load(self.filepath)
        self.assertEqual(data, self.data)

    def tearDown(self) -> None:
        if self.filepath.is_file():
            self.filepath.unlink()

class TestTextfile(ModuleTestCase):
    """Testcase for the module nemoa.file.textfile."""

    module = 'nemoa.file.textfile'

    def setUp(self) -> None:
        self.filepath = Path(tempfile.NamedTemporaryFile().name + '.txt')
        self.comment = "comment line"
        self.content = ['first content line', 'second content line']
        self.text = f"# {self.comment}\n\n" + '\n'.join(self.content)
        textfile.save(self.text, self.filepath)

    def test_openx(self) -> None:
        filepath = Path(tempfile.NamedTemporaryFile().name + '.txt')
        with self.subTest(file=filepath):
            with textfile.openx(filepath, mode='w') as fh:
                fh.write(self.text)
            if filepath.is_file():
                with textfile.openx(filepath, mode='r') as fh:
                    text = fh.read()
                filepath.unlink()
                self.assertTrue(text == self.text)
        file = filepath.open(mode='w')
        with self.subTest(file=file):
            with textfile.openx(file, mode='w') as fh:
                fh.write(self.text)
            if not file.closed:
                file.close()
                file = filepath.open(mode='r')
                with textfile.openx(file, mode='r') as fh:
                    text = fh.read()
                if not file.closed:
                    file.close()
                    self.assertTrue(text == self.text)
        if not file.closed:
            file.close()
        if filepath.is_file():
            filepath.unlink()

    def test_save(self) -> None:
        self.assertTrue(self.filepath.is_file())

    def test_load(self) -> None:
        text = textfile.load(self.filepath)
        self.assertEqual(text, self.text)

    def test_get_comment(self) -> None:
        comment = textfile.get_comment(self.filepath)
        self.assertEqual(comment, self.comment)

    def test_get_content(self) -> None:
        content = textfile.get_content(self.filepath)
        self.assertEqual(content, self.content)

    def tearDown(self) -> None:
        if self.filepath.is_file():
            self.filepath.unlink()

class TestCsv(ModuleTestCase):
    """Testcase for the module nemoa.file.csv."""

    module = 'nemoa.file.csv'

    def setUp(self) -> None:
        path = Path(tempfile.NamedTemporaryFile().name)
        self.rfc_path = path.with_suffix('.csv')
        self.rfc_header = ('name', 'id', 'value')
        self.rfc_sep = ','

        self.rlang_path = path.with_suffix('.tsv')
        self.rlang_header = tuple(list(self.rfc_header)[1:])
        self.rlang_sep = '\t'

        self.comment = '-*- coding: utf-8 -*-'
        self.values = [('r1', 1, 1.), ('r2', 2, 2.), ('r3', 3, 3.)]

        # Manually Write RFC compliant CSV-File
        with self.rfc_path.open(mode='w') as file:
            # Write Comment
            file.writelines([f"# {self.comment}\n\n"])
            # Write Header
            file.writelines([self.rfc_sep.join(self.rfc_header) + '\n'])
            # Write Data
            for row in self.values:
                strrow = [str(token) for token in row]
                file.writelines([self.rfc_sep.join(strrow) + '\n'])

        # Manually Write R Language compliant TSV-File
        with self.rlang_path.open(mode='w') as file:
            # Write Comment
            file.writelines([f"# {self.comment}\n\n"])
            # Write Header
            file.writelines([self.rlang_sep.join(self.rlang_header) + '\n'])
            # Write Data
            for row in self.values:
                strrow = [str(token) for token in row]
                file.writelines([self.rlang_sep.join(strrow) + '\n'])

    def test_load(self) -> None:
        with self.subTest(format='rfc'):
            with csv.load(self.rfc_path) as file:
                self.assertEqual(file.delimiter, self.rfc_sep)
                self.assertEqual(file.header, self.rfc_header)
                self.assertEqual(file.comment, self.comment)
                self.assertEqual(file.hformat, csv.CSV_HFORMAT_RFC4180)
                self.assertEqual(file.namecol, None)
                self.assertEqual(file.read(), self.values)
        with self.subTest(format='rlang'):
            with csv.load(self.rlang_path) as file:
                self.assertEqual(file.delimiter, self.rlang_sep)
                self.assertEqual(list(file.header)[1:], list(self.rlang_header))
                self.assertEqual(file.comment, self.comment)
                self.assertEqual(file.hformat, csv.CSV_HFORMAT_RLANG)
                self.assertEqual(file.namecol, file.header[0])
                self.assertEqual(file.read(), self.values)

    def test_save(self) -> None:
        with self.subTest(format='rfc'):
            filepath = Path(tempfile.NamedTemporaryFile().name + '.csv')
            csv.save( # type: ignore
                filepath, header=self.rfc_header, values=self.values,
                comment=self.comment, delimiter=self.rfc_sep)
            with csv.File(filepath) as file:
                self.assertEqual(file.delimiter, self.rfc_sep)
                self.assertEqual(file.header, self.rfc_header)
                self.assertEqual(file.comment, self.comment)
                self.assertEqual(file.hformat, csv.CSV_HFORMAT_RFC4180)
                self.assertEqual(file.namecol, None)
                self.assertEqual(file.read(), self.values)
            filepath.unlink()
        with self.subTest(format='rlang'):
            filepath = Path(tempfile.NamedTemporaryFile().name + '.tsv')
            csv.save( # type: ignore
                filepath, header=self.rlang_header, values=self.values,
                comment=self.comment, delimiter=self.rlang_sep)
            with csv.File(filepath) as file:
                self.assertEqual(file.delimiter, self.rlang_sep)
                self.assertEqual(list(file.header)[1:], list(self.rlang_header))
                self.assertEqual(file.comment, self.comment)
                self.assertEqual(file.hformat, csv.CSV_HFORMAT_RLANG)
                self.assertEqual(file.namecol, file.header[0])
                self.assertEqual(file.read(), self.values)
            filepath.unlink()

    def test_File(self) -> None:
        # TODO: Test completeness of unittest with respect to the class
        pass

    def test_Reader(self) -> None:
        # TODO: Test completeness of unittest with respect to the class
        pass

    def test_Writer(self) -> None:
        # TODO: Test completeness of unittest with respect to the class
        pass

    def test_File_init(self) -> None:
        with self.subTest(format='rfc'):
            with csv.File(
                self.rfc_path, header=self.rfc_header, comment=self.comment,
                delimiter=self.rfc_sep) as file:
                self.assertIsInstance(file, csv.File)
        with self.subTest(format='rlang'):
            with csv.File(
                self.rlang_path, header=self.rlang_header, comment=self.comment,
                delimiter=self.rlang_sep) as file:
                self.assertIsInstance(file, csv.File)

    def test_File_delimiter(self) -> None:
        with self.subTest(format='rfc'):
            with csv.File(self.rfc_path) as file:
                self.assertEqual(file.delimiter, self.rfc_sep)
        with self.subTest(format='rlang'):
            with csv.File(self.rlang_path) as file:
                self.assertEqual(file.delimiter, self.rlang_sep)

    def test_File_header(self) -> None:
        with self.subTest(format='rfc'):
            with csv.File(self.rfc_path) as file:
                self.assertEqual(file.header, self.rfc_header)
        with self.subTest(format='rlang'):
            with csv.File(self.rlang_path) as file:
                self.assertEqual(list(file.header)[1:], list(self.rlang_header))

    def test_File_comment(self) -> None:
        with self.subTest(format='rfc'):
            with csv.File(self.rfc_path) as file:
                self.assertEqual(file.comment, self.comment)
        with self.subTest(format='rlang'):
            with csv.File(self.rlang_path) as file:
                self.assertEqual(file.comment, self.comment)

    def test_File_hformat(self) -> None:
        with self.subTest(format='rfc'):
            with csv.File(self.rfc_path) as file:
                self.assertEqual(file.hformat, csv.CSV_HFORMAT_RFC4180)
        with self.subTest(format='rlang'):
            with csv.File(self.rlang_path) as file:
                self.assertEqual(file.hformat, csv.CSV_HFORMAT_RLANG)

    def test_File_namecol(self) -> None:
        with self.subTest(format='rfc'):
            with csv.File(self.rfc_path) as file:
                self.assertEqual(file.namecol, None)
        with self.subTest(format='rlang'):
            with csv.File(self.rlang_path) as file:
                self.assertEqual(file.namecol, file.header[0])

    def test_File_read(self) -> None:
        with self.subTest(format='rfc'):
            with csv.File(self.rfc_path) as file:
                self.assertEqual(file.read(), self.values)
        with self.subTest(format='rlang'):
            with csv.File(self.rlang_path) as file:
                self.assertEqual(file.read(), self.values)

    def test_File_write(self) -> None:
        with self.subTest(format='rfc'):
            filepath = Path(tempfile.NamedTemporaryFile().name + '.csv')
            with csv.File(
                filepath, header=self.rfc_header, comment=self.comment,
                delimiter=self.rfc_sep) as file:
                file.write(self.values) # type: ignore
            with csv.File(filepath) as file:
                self.assertEqual(file.delimiter, self.rfc_sep)
                self.assertEqual(file.header, self.rfc_header)
                self.assertEqual(file.comment, self.comment)
                self.assertEqual(file.hformat, csv.CSV_HFORMAT_RFC4180)
                self.assertEqual(file.namecol, None)
                self.assertEqual(file.read(), self.values)
            filepath.unlink()
        with self.subTest(format='rlang'):
            filepath = Path(tempfile.NamedTemporaryFile().name + '.tsv')
            with csv.File(
                filepath, header=self.rlang_header, comment=self.comment,
                delimiter=self.rlang_sep) as file:
                file.write(self.values) # type: ignore
            with csv.File(filepath) as file:
                self.assertEqual(file.delimiter, self.rlang_sep)
                self.assertEqual(list(file.header)[1:], list(self.rlang_header))
                self.assertEqual(file.comment, self.comment)
                self.assertEqual(file.hformat, csv.CSV_HFORMAT_RLANG)
                self.assertEqual(file.namecol, file.header[0])
                self.assertEqual(file.read(), self.values)
            filepath.unlink()

    # def test_rownames(self) -> None:
    #     self.assertEqual(self.file.rownames, self.rownames)
    #

    def tearDown(self) -> None:
        if self.rfc_path.is_file():
            self.rfc_path.unlink()
        if self.rlang_path.is_file():
            self.rlang_path.unlink()

class TestInifile(ModuleTestCase):
    """Testcase for the module nemoa.file.ini."""

    module = 'nemoa.file.ini'

    def setUp(self) -> None:
        self.filepath = Path(tempfile.NamedTemporaryFile().name + '.ini')
        self.comment = '-*- coding: utf-8 -*-'
        self.obj = {
            'n': {'a': 's', 'b': True, 'c': 1},
            'l1': {'a': 1}, 'l2': {'a': 2}}
        self.structure = {
            'n': {'a': str, 'b': bool, 'c': int},
            'l[0-9]*': {'a': int}}
        self.text = (
            "# -*- coding: utf-8 -*-\n\n"
            "[n]\na = s\nb = True\nc = 1\n\n"
            "[l1]\na = 1\n\n[l2]\na = 2\n\n")
        ini.save(self.obj, self.filepath, comment=self.comment)

    def test_parse(self) -> None:
        parser = ConfigParser()
        setattr(parser, 'optionxform', lambda key: key)
        parser.read_string(self.text)
        obj = ini.parse(parser, structure=self.structure)
        self.assertEqual(obj, self.obj)

    def test_encode(self) -> None:
        text = ini.encode(self.obj, comment=self.comment)
        self.assertEqual(text, self.text)

    def test_decode(self) -> None:
        obj = ini.decode(self.text, structure=self.structure)
        self.assertEqual(obj, self.obj)

    def test_save(self) -> None:
        self.assertTrue(self.filepath.is_file())

    def test_load(self) -> None:
        obj = ini.load(self.filepath, structure=self.structure)
        self.assertEqual(obj, self.obj)

    def test_get_comment(self) -> None:
        comment = ini.get_comment(self.filepath)
        self.assertEqual(comment, self.comment)

    def tearDown(self) -> None:
        if self.filepath.is_file():
            self.filepath.unlink()
