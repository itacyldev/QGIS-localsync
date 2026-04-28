import unittest
from unittest.mock import MagicMock, patch, mock_open
from qgis_plugin.tasks.download_task import DownloadTask


class TestDownloadTask(unittest.TestCase):

    def _make_task(self, url="http://example.com/file.zip", output_path="/tmp/file.zip"):
        task = DownloadTask.__new__(DownloadTask)
        task.url = url
        task.output_path = output_path
        task.exception = None
        task.result = False
        task.logger = MagicMock()
        task.isCanceled = MagicMock(return_value=False)
        task.setProgress = MagicMock()
        return task

    @patch("qgis_plugin.tasks.download_task.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_run_happy_path(self, mock_file, mock_get):
        mock_response = MagicMock()
        mock_response.headers = {"content-length": "8"}
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_get.return_value = mock_response

        result = self._make_task().run()

        self.assertTrue(result)

    @patch("qgis_plugin.tasks.download_task.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_run_cancelled(self, mock_file, mock_get):
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_response.iter_content.return_value = [b"chunk"]
        mock_get.return_value = mock_response

        task = self._make_task()
        task.isCanceled.return_value = True

        self.assertFalse(task.run())