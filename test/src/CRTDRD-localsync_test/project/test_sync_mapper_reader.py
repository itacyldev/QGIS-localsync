import unittest
import json
import tempfile
import shutil
from pathlib import Path
from qgis_plugin.localsync.project.sync_mapper_reader import SyncMapperData, SyncMapperReader


class TestSyncMapperData(unittest.TestCase):

    def test_default_initialization(self):
        """Test inicialización por defecto"""
        """Test default initialisation"""
        mapper = SyncMapperData()
        self.assertEqual(mapper.source, "")
        self.assertEqual(mapper.destination, "")
        self.assertEqual(mapper.includes, [])
        self.assertEqual(mapper.excludes, [])

    def test_custom_initialization(self):
        """Test custom initialisation"""
        includes = ["*.py"]
        excludes = ["test*"]

        mapper = SyncMapperData("/source", "/dest", includes, excludes)

        self.assertEqual(mapper.source, "/source")
        self.assertEqual(mapper.destination, "/dest")
        self.assertEqual(mapper.includes, includes)
        self.assertEqual(mapper.excludes, excludes)


class TestSyncMapperReader(unittest.TestCase):

    def setUp(self):
        """Create temporal directory for tests"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file_path = str(Path(self.test_dir) / "test.json")
        self.addCleanup(shutil.rmtree, self.test_dir, ignore_errors=True)

    def test_initialization(self):
        """Test initialisation"""
        reader = SyncMapperReader()
        self.assertEqual(reader.sync_mappers_data, [])

    def test_read_json_from_path(self):
        """Test JSON reading"""
        test_data = {"key": "value", "number": 42}

        with open(self.test_file_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        reader = SyncMapperReader()
        result = reader.read_json_from_path(self.test_file_path)

        self.assertEqual(result, test_data)


    def test_mapper_reader_valid_json(self):
        """Test valid read of mapper"""
        test_data = [
            {
                "source": "/source1",
                "destination": "/dest1",
                "includes": [{"regex": r"\.py$", "directories": False}],
                "excludes": [{"regex": r"test", "directories": True}]
            },
            {
                "source": "/source2",
                "destination": "/dest2",
                "includes": [],
                "excludes": []
            }
        ]

        with open(self.test_file_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        reader = SyncMapperReader()
        reader.mapper_reader(self.test_file_path)

        self.assertEqual(len(reader.sync_mappers_data), 2)
        self.assertEqual(reader.sync_mappers_data[0].source, "/source1")
        self.assertEqual(reader.sync_mappers_data[1].destination, "/dest2")

    def test_mapper_reader_missing_key(self):
        """Test reading with a missing key"""
        test_data = [
            {
                "source": "/source1",
                "destination": "/dest1"
                # Faltan "includes" y "excludes"
            }
        ]

        with open(self.test_file_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        reader = SyncMapperReader()
        reader.mapper_reader(self.test_file_path)

        # Debería capturar KeyError y no añadir nada
        self.assertEqual(len(reader.sync_mappers_data), 0)


if __name__ == '__main__':
    unittest.main()