import unittest
import os
import subprocess  # Add this import
import requests
from unittest.mock import patch, mock_open, MagicMock
from io import BytesIO
from app import allowed_file, download_file_from_url, calculate_file_hash, get_youtube_slug, run_command

class TestNoDrums(unittest.TestCase):
    
    def test_allowed_file(self):
        """
        Test the allowed_file function to check if file extensions are correctly identified.
        
        What to expect:
        - "test.mp3" should return True as it is an allowed file type.
        - "test.wav" and "test.txt" should return False as they are not in the allowed extensions.
        
        What can break it:
        - If the allowed extensions set is modified improperly.
        - If the file extension parsing fails.
        """
        self.assertTrue(allowed_file("test.mp3"))
        self.assertFalse(allowed_file("test.wav"))
        self.assertFalse(allowed_file("test.txt"))

    @patch('requests.get')
    def test_download_file_from_url(self, mock_get):
        """
        Test the download_file_from_url function to ensure it downloads files correctly from a given URL.
        
        What to expect:
        - The function should return True if the download is successful (status code 200).
        - The function should return False if the download fails (status code other than 200).
        
        What can break it:
        - If the URL is incorrect or the server is unreachable.
        - If the file writing operation fails due to file system permissions or other issues.
        """
        # Simulate a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content = lambda chunk_size: [b'data']
        mock_get.return_value = mock_response

        with patch("builtins.open", mock_open()) as mock_file:
            result = download_file_from_url("http://example.com/test.mp3", "test.mp3")
            self.assertTrue(result)
            mock_file.assert_called_once_with("test.mp3", "wb")

        # Simulate a failed response
        mock_response.status_code = 404
        result = download_file_from_url("http://example.com/test.mp3", "test.mp3")
        self.assertFalse(result)

    def test_calculate_file_hash(self):
        """
        Test the calculate_file_hash function to verify that the correct hash is generated for a given file.
        
        What to expect:
        - The hash should match the expected MD5 hash for the given file content.
        
        What can break it:
        - If the file content changes, the hash will not match the expected value.
        - If the file object is not properly rewound before reading.
        """
        mock_file = BytesIO(b"test data")
        expected_hash = "eb733a00c0c9d336e65691a37ab54293"  # MD5 for "test data"
        result = calculate_file_hash(mock_file)
        self.assertEqual(result, expected_hash)

    def test_get_youtube_slug(self):
        """
        Test the get_youtube_slug function to ensure it correctly extracts the video slug from a YouTube URL.
        
        What to expect:
        - A valid YouTube URL with a video ID should return the correct video ID.
        - An invalid YouTube URL without a video ID should return None.
        
        What can break it:
        - If the URL format changes or does not match the expected pattern.
        - If the regular expression used to extract the slug is incorrect.
        """
        self.assertEqual(get_youtube_slug("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertIsNone(get_youtube_slug("https://www.youtube.com/watch"))

    @patch('subprocess.run')
    def test_run_command(self, mock_run):
        """
        Test the run_command function to verify that commands are executed correctly.
        
        What to expect:
        - The function should run the command without raising an exception if the return code is 0.
        - The function should raise a CalledProcessError if the return code is non-zero.
        
        What can break it:
        - If the command is incorrect or unavailable in the environment.
        - If the subprocess library fails to execute the command properly.
        """
        # Simulate a successful command
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_run.return_value = mock_result

        try:
            run_command(["echo", "Hello"])
        except subprocess.CalledProcessError:
            self.fail("run_command() raised CalledProcessError unexpectedly!")

        # Simulate a failed command
        mock_result.returncode = 1
        mock_result.stderr = "Error"
        mock_run.return_value = mock_result

        with self.assertRaises(subprocess.CalledProcessError):
            run_command(["echo", "Hello"])

if __name__ == "__main__":
    unittest.main()

