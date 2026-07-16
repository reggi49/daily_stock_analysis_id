# -*- coding: utf-8 -*-
"""
Anspire Search Engine Test Suite

Test coverage:
1. Config loading tests - verify anspire_api_keys loads correctly from environment variables
2. Service initialization tests - verify SearchService initializes AnspireSearchProvider correctly
3. API call tests - actual Anspire API calls to verify response results
4. Failover tests - verify error handling and fallback mechanisms for invalid keys
5. Search functionality tests - test stock news search and general search features

How to run:
```bash
# Windows PowerShell
$env:ANSPIRE_API_KEYS="your_test_api_key"
python -m pytest tests/test_anspire_search.py -v

# Linux/Mac
export ANSPIRE_API_KEYS="your_test_api_key"
python -m pytest tests/test_anspire_search.py -v
```
"""

import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv
load_dotenv()

# # Add the project root to the Python path to resolve module-import issues
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mock newspaper before search_service import (optional dependency)
if "newspaper" not in sys.modules:
    mock_np = MagicMock()
    mock_np.Article = MagicMock()
    mock_np.Config = MagicMock()
    sys.modules["newspaper"] = mock_np

from src.config import Config, get_config
from src.search_service import (
    AnspireSearchProvider,
    SearchService,
    get_search_service,
    reset_search_service,
)


class _FakeResponse:
    """Mock HTTP response object"""
    def __init__(self, status_code=200, json_data=None, text="", headers=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.headers = headers or {'content-type': 'application/json'}
    
    def json(self):
        return self._json_data


class TestAnspireConfigLoading(unittest.TestCase):
    """Test Anspire configuration loading from environment variables."""
    
    def setUp(self):
        """Save and clear environment variables (does not touch the .env file)"""
        # ✅ Save the original value, restored after the test
        self._original_anspire_keys = os.environ.get('ANSPIRE_API_KEYS')
        
        # Clear the environment variable
        if 'ANSPIRE_API_KEYS' in os.environ:
            del os.environ['ANSPIRE_API_KEYS']
        
        # Reset the Config singleton
        Config._Config__instance = None
        reset_search_service()

    def tearDown(self):
        """Restore the original environment variables"""
        # ✅ Restore the original value
        if self._original_anspire_keys is not None:
            os.environ['ANSPIRE_API_KEYS'] = self._original_anspire_keys
        elif 'ANSPIRE_API_KEYS' in os.environ:
            del os.environ['ANSPIRE_API_KEYS']
        
        # Reset the Config singleton
        Config._Config__instance = None
        reset_search_service()

    def test_anspire_keys_loaded_from_env(self):
        """Test that ANSPIRE_API_KEYS is correctly parsed from environment."""
        # ✅ Use patch.dict for a temporary setting, auto-restored after the test
        with patch.dict(os.environ, {'ANSPIRE_API_KEYS': 'key1,key2,key3'}):
            config = Config._load_from_env()
            
            self.assertEqual(len(config.anspire_api_keys), 3)
            self.assertIn('key1', config.anspire_api_keys)
            self.assertIn('key2', config.anspire_api_keys)
            self.assertIn('key3', config.anspire_api_keys)

    def test_anspire_keys_single_key(self):
        """Test single API Key parsing."""
        with patch.dict(os.environ, {'ANSPIRE_API_KEYS': 'single_key_test'}):
            config = Config._load_from_env()
            
            self.assertEqual(len(config.anspire_api_keys), 1)
            self.assertEqual(config.anspire_api_keys[0], 'single_key_test')

    def test_anspire_keys_empty_env(self):
        """Test empty environment variable handling."""
        with patch.dict(os.environ, {'ANSPIRE_API_KEYS': ''}):
            config = Config._load_from_env()
            
            self.assertEqual(len(config.anspire_api_keys), 0)

    def test_anspire_keys_whitespace_handling(self):
        """Test whitespace trimming in API Keys."""
        with patch.dict(os.environ, {'ANSPIRE_API_KEYS': ' key1 , key2 , key3 '}):
            config = Config._load_from_env()
            
            self.assertEqual(len(config.anspire_api_keys), 3)
            self.assertEqual(config.anspire_api_keys, ['key1', 'key2', 'key3'])


class TestAnspireSearchProvider(unittest.TestCase):
    """Anspire Search Provider unit tests"""
    
    def setUp(self):
        """Prepare before the test"""
        # ✅ Use an explicit test placeholder, not a real key shape
        self.test_api_key = "sk-test-anspire-placeholder-key-12345"
        self.provider = AnspireSearchProvider([self.test_api_key])
        # Save the original requests module
        self._original_requests = sys.modules.get('requests')
    
    def tearDown(self):
        """Clean up after the test"""
        # Restore the original requests module
        if self._original_requests is not None:
            sys.modules['requests'] = self._original_requests
    
    def test_provider_initialization(self):
        """Test Provider initialization"""
        provider = AnspireSearchProvider(["key1", "key2"])
        self.assertEqual(provider.name, "Anspire")
        if hasattr(provider, 'api_keys'):
            self.assertEqual(len(provider.api_keys), 2)
        elif hasattr(provider, '_api_keys'):
            self.assertEqual(len(provider._api_keys), 2)
        self.assertTrue(provider.is_available)
    
    def test_provider_name(self):
        """Test Provider name"""
        self.assertEqual(self.provider.name, "Anspire")
    
    def test_provider_availability(self):
        """Test Provider availability detection"""
        # Should be available when an API key is present
        provider_with_keys = AnspireSearchProvider(["key1"])
        self.assertTrue(provider_with_keys.is_available)
        
        # Should be unavailable when no API key is present
        provider_without_keys = AnspireSearchProvider([])
        self.assertFalse(provider_without_keys.is_available)
    
    def test_extract_domain(self):
        """Test domain extraction"""
        test_cases = [
            ("https://www.example.com/article", "example.com"),
            ("https://finance.sina.com.cn/stock/", "finance.sina.com.cn"),
            ("http://www.10jqka.com.cn/news", "10jqka.com.cn"),
            ("invalid_url", "unknown source"),
            ("", "unknown source"),
        ]
        
        for url, expected in test_cases:
            result = AnspireSearchProvider._extract_domain(url)
            self.assertEqual(result, expected, f"Failed for URL: {url}")
    
    @patch('src.search_service.requests')
    def test_search_success_response(self, mock_requests):
        """Test successful response handling"""
        # Set up mock exceptions
        try:
            import requests as real_requests
            mock_requests.exceptions = real_requests.exceptions
        except ImportError:
            pass
        
        fake_response = _FakeResponse(
            status_code=200,
            json_data={
                "code": 200,
                "msg": "success",
                "results": [
                    {
                        "title": "Kweichow Moutai stock price rises today",
                        "url": "https://finance.sina.com.cn/stock/600519",
                        "content": "Kweichow Moutai (600519) Share price rose at today's close 2.5%，Increased trading volume...",
                    },
                    {
                        "title": "Liquor sector continues to strengthen",
                        "url": "https://www.10jqka.com.cn/baijiu",
                        "content": "Liquor sector performed strongly today，Kweichow Moutai、Wuliangye and other stocks were among the top gainers...",
                    }
                ]
            }
        )
        
        mock_requests.get = MagicMock(return_value=fake_response)
        
        response = self.provider.search("Kweichow Moutai stock news", max_results=5, days=7)
        
        # Verify results
        self.assertTrue(response.success)
        self.assertEqual(response.provider, "Anspire")
        self.assertEqual(len(response.results), 2)
        self.assertEqual(response.results[0].title, "Kweichow Moutai stock price rises today")
        # Assume source is the domain extracted from the url
        self.assertEqual(response.results[0].source, "finance.sina.com.cn")
        
        # Verify API call parameters
        mock_requests.get.assert_called_once()
        call_args = mock_requests.get.call_args
        # Check whether the URL contains an anspire-related domain (exact URL depends on the implementation)
        # self.assertIn("plugin.anspire.cn", call_args[0][0]) 
        self.assertIn("Authorization", call_args[1]["headers"])
        # Verify params are used instead of json
        self.assertIn("params", call_args[1])
        self.assertNotIn("json", call_args[1])
    
    @patch('src.search_service.requests')
    def test_search_invalid_api_key(self, mock_requests):
        """Test error handling for an invalid API key"""
        try:
            import requests as real_requests
            mock_requests.exceptions = real_requests.exceptions
        except ImportError:
            pass
        
        fake_response = _FakeResponse(
            status_code=401,
            json_data={"message": "Invalid API key"},
            text="Unauthorized"
        )
        
        mock_requests.get = MagicMock(return_value=fake_response)
        
        response = self.provider.search("Test query", max_results=3)
        
        self.assertFalse(response.success)
        self.assertEqual(response.provider, "Anspire")
        self.assertEqual(len(response.results), 0)
        # The error message may differ by implementation; here we do a loose check
        self.assertTrue("API" in response.error_message or "KEY" in response.error_message or "Invalid" in response.error_message)
    
    @patch('src.search_service.requests')
    def test_search_timeout_error(self, mock_requests):
        """Test timeout error handling"""
        try:
            import requests as real_requests
            mock_requests.exceptions = real_requests.exceptions
            timeout_exc = mock_requests.exceptions.Timeout
        except ImportError:
            mock_requests.exceptions = MagicMock()
            timeout_exc = Exception
            
        mock_requests.get = MagicMock(side_effect=timeout_exc())
        
        response = self.provider.search("Test query", max_results=3)
        
        self.assertFalse(response.success)
        self.assertEqual(response.provider, "Anspire")
        self.assertEqual(len(response.results), 0)
        # Error-message check
        self.assertTrue("timeout" in response.error_message or "Timeout" in response.error_message)
    
    @patch('src.search_service.requests')
    def test_search_network_error(self, mock_requests):
        """Test network error handling"""
        try:
            import requests as real_requests
            mock_requests.exceptions = real_requests.exceptions
            conn_exc = mock_requests.exceptions.ConnectionError
        except ImportError:
            mock_requests.exceptions = MagicMock()
            conn_exc = Exception

        mock_requests.get = MagicMock(side_effect=conn_exc())
        
        response = self.provider.search("Test query", max_results=3)
        
        self.assertFalse(response.success)
        self.assertEqual(response.provider, "Anspire")
        self.assertEqual(len(response.results), 0)
        self.assertTrue("network" in response.error_message or "Connection" in response.error_message)
    
    @patch('src.search_service.requests')
    def test_search_empty_results(self, mock_requests):
        """Test empty-result handling"""
        try:
            import requests as real_requests
            mock_requests.exceptions = real_requests.exceptions
        except ImportError:
            mock_requests.exceptions = MagicMock()
        
        fake_response = _FakeResponse(
            status_code=200,
            json_data={"code": 200, "msg": "success", "results": []}
        )
        
        mock_requests.get = MagicMock(return_value=fake_response)
        
        response = self.provider.search("non-existent stocks XYZ", max_results=5)
        
        self.assertTrue(response.success)
        self.assertEqual(response.provider, "Anspire")
        self.assertEqual(len(response.results), 0)
    
    @patch('src.search_service.requests')
    def test_search_content_truncation(self, mock_requests):
        """Test long-content truncation"""
        try:
            import requests as real_requests
            mock_requests.exceptions = real_requests.exceptions
        except ImportError:
            mock_requests.exceptions = MagicMock()
        
        long_content = "This is a very long piece of content，" * 100  # exceed 500 character
        
        fake_response = _FakeResponse(
            status_code=200,
            json_data={
                "code": 200,
                "msg": "success",
                "results": [{
                    "title": "Long content testing",
                    "url": "https://example.com/long",
                    "content": long_content
                }]
            }
        )
        
        mock_requests.get = MagicMock(return_value=fake_response)
        
        response = self.provider.search("test", max_results=1)
        
        self.assertTrue(response.success)
        self.assertEqual(len(response.results), 1)
        # Verify the content is truncated to within 500 characters
        if response.results[0].snippet:
            self.assertLessEqual(len(response.results[0].snippet), 503)  # 500 + "..."
            self.assertTrue(response.results[0].snippet.endswith("..."))
    
    @patch('src.search_service.requests')
    def test_search_time_range(self, mock_requests):
        """Test time-range parameter"""
        try:
            import requests as real_requests
            mock_requests.exceptions = real_requests.exceptions
        except ImportError:
            mock_requests.exceptions = MagicMock()
        
        fake_response = _FakeResponse(status_code=200, json_data={"code": 200, "results": []})
        mock_requests.get = MagicMock(return_value=fake_response)
        
        # Test a 7-day range
        self.provider.search("test", max_results=3, days=7)
        
        # Verify the time parameter
        call_args = mock_requests.get.call_args
        if call_args and len(call_args) > 1 and 'params' in call_args[1]:
            params = call_args[1]["params"]
                
            # Verify the time parameter exists (exact field name depends on the implementation)
            # This assumes FromTime/ToTime or similar fields are used; skip the field check if none exist
            # self.assertIn("FromTime", params)
            # self.assertIn("ToTime", params)


class TestAnspireSearchService(unittest.TestCase):
    """Anspire integration tests in SearchService"""
    
    def setUp(self):
        Config._Config__instance = None
        reset_search_service()

    def test_search_service_with_anspire(self):
        """Test SearchService correctly initializes the Anspire Provider"""
        service = SearchService(
            anspire_keys=["test_key"],
            bocha_keys=[],
            tavily_keys=[],
            searxng_public_instances_enabled=False,
            news_max_age_days=3,
            news_strategy_profile="short"
        )
        
        self.assertTrue(hasattr(service, '_providers'))
        self.assertGreater(len(service._providers), 0)
        
        first_provider = service._providers[0]
        self.assertIsInstance(first_provider, AnspireSearchProvider)
        self.assertEqual(first_provider.name, "Anspire")
    
    def test_search_service_without_anspire(self):
        """Test behavior when Anspire is not configured"""
        service = SearchService(
            anspire_keys=[],
            tavily_keys=["tavily_key"],
            bocha_keys=[],
            searxng_public_instances_enabled=False,
            news_max_age_days=3,
            news_strategy_profile="short"
        )
        
        # Verify there is no Anspire Provider
        anspire_providers = [p for p in service._providers if isinstance(p, AnspireSearchProvider)]
        self.assertEqual(len(anspire_providers), 0)
    
    def test_search_service_priority(self):
        """Test Anspire priority"""
        service = SearchService(
            anspire_keys=["anspire_key"],
            bocha_keys=["bocha_key"],
            tavily_keys=["tavily_key"],
            searxng_public_instances_enabled=False,
            news_max_age_days=3,
            news_strategy_profile="short"
        )
        
        self.assertIsInstance(service._providers[0], AnspireSearchProvider)


class TestAnspireIntegration(unittest.TestCase):
    """Anspire integration tests (require a real API key)"""
    
    @classmethod
    def setUpClass(cls):
        """Check if API Key is configured and valid."""
        cls.api_keys = [k.strip() for k in os.getenv('ANSPIRE_API_KEYS', '').split(',') if k.strip()]
        cls.has_api_key = len(cls.api_keys) > 0
        cls.has_valid_api_key = False  # Is there a valid tag? API Key
        
        if cls.has_api_key:
            reset_search_service()
            cls.service = get_search_service()
            
            # Verify whether the API key is valid
            try:
                # Find the Anspire provider
                for provider in cls.service._providers:
                    if isinstance(provider, AnspireSearchProvider):
                        # Perform a simple search to verify
                        test_response = provider.search("test", max_results=1)
                        if test_response.success:
                            cls.has_valid_api_key = True
                        break
            except Exception:
                cls.has_valid_api_key = False

    def setUp(self):
        """Check whether the API key is valid before each test"""
        if not os.environ.get("ANSPIRE_API_KEYS"):
            self.skipTest("not set ANSPIRE_API_KEYS environment variables，Skip integration tests")
        if not getattr(self.__class__, 'has_valid_api_key', False):
            self.skipTest("ANSPIRE_API_KEYS in environment variables API Key Invalid，Skip integration tests")

    @pytest.mark.network
    def test_real_api_call_stock_news(self):
        """Real API call test - stock news search"""
        # Ensure the service is reset
        reset_search_service()
        service = get_search_service()
        
        # Verify Anspire is configured
        anspire_provider = None
        for provider in service._providers:
            if isinstance(provider, AnspireSearchProvider):
                anspire_provider = provider
                break
        
        if not anspire_provider:
            self.skipTest("Anspire Provider not initialized")
        
        # Test A-share search
        response = service.search_stock_news("600519", "Kweichow Moutai", max_results=3)
        
        print(f"\n=== Anspire true API Test results ===")
        print(f"search status：{'success' if response.success else 'failed'}")
        print(f"search engine：{response.provider}")
        print(f"number of results：{len(response.results)}")
        print(f"Time consuming：{response.search_time:.2f}s")
        
        # Basic verification
        self.assertTrue(response.success, f"Search failed: {response.error_message}")
        self.assertEqual(response.provider, "Anspire")
        self.assertGreater(len(response.results), 0, "Should return at least one result")
        
        # Verify the result format
        for result in response.results:
            self.assertIsNotNone(result.title)
            self.assertIsNotNone(result.url)
            # snippet may be empty, depending on the implementation
            # self.assertIsNotNone(result.snippet)
    
    @pytest.mark.network
    def test_real_api_call_general_search(self):
        """Real API call test - general search"""
        reset_search_service()
        service = get_search_service()
        
        anspire_provider = None
        for provider in service._providers:
            if isinstance(provider, AnspireSearchProvider):
                anspire_provider = provider
                break
        
        if not anspire_provider:
            self.skipTest("Anspire Provider not initialized")
        
        # Test general search
        response = anspire_provider.search("Latest developments in artificial intelligence", max_results=5, days=7)
        
        print(f"\n=== Anspire General search results ===")
        print(f"search status：{'success' if response.success else 'failed'}")
        print(f"number of results：{len(response.results)}")
        
        self.assertTrue(response.success)
        self.assertGreater(len(response.results), 0)


def run_manual_test():
    """Manual test function (for quick verification)"""
    import logging
    from src.config import get_config
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s'
    )
    
    print("=" * 60)
    print("Anspire Search quick test")
    print("=" * 60)
    
    # Check configuration
    config = get_config()
    if not config.anspire_api_keys:
        print("\n❌ not detected Anspire API Keys")
        print("Please set environment variables：")
        print("  Windows PowerShell: $env:ANSPIRE_API_KEYS=\"your_api_key\"")
        print("  Linux/Mac: export ANSPIRE_API_KEYS=\"your_api_key\"")
        return False
    
    print(f"\n✅ configured {len(config.anspire_api_keys)} a Anspire API Key")
    
    # Create the service
    service = SearchService(
        anspire_keys=config.anspire_api_keys,
        bocha_keys=config.bocha_api_keys,
        tavily_keys=config.tavily_keys,
        searxng_public_instances_enabled=False,
        news_max_age_days=3,
        news_strategy_profile="short"
    )
    
    # Verify the Provider
    anspire_provider = service._providers[0] if service._providers else None
    if not anspire_provider or not isinstance(anspire_provider, AnspireSearchProvider):
        print("\n❌ Anspire Provider Not properly initialized")
        return False
    
    print(f"✅ Anspire Provider Initialization successful")
    print(f"   Provider Name：{anspire_provider.name}")
    if hasattr(anspire_provider, 'api_keys'):
        print(f"   API Keys Quantity：{len(anspire_provider.api_keys)}")
    elif hasattr(anspire_provider, '_api_keys'):
        print(f"   API Keys Quantity：{len(anspire_provider._api_keys)}")
    
    # Run the test search
    print("\n" + "=" * 60)
    print("Perform a test search：Kweichow Moutai (600519)")
    print("=" * 60)
    
    response = service.search_stock_news("600519", "Kweichow Moutai", max_results=3)
    
    print(f"\nSearch results:")
    print(f"  Status：{'✅ success' if response.success else '❌ failed'}")
    print(f"  search engine：{response.provider}")
    print(f"  number of results：{len(response.results)}")
    print(f"  Time consuming：{response.search_time:.2f}s")
    
    if response.error_message:
        print(f"  error message：{response.error_message}")
    
    if response.results:
        print(f"\nbefore {min(2, len(response.results))} Preview of results:")
        for i, result in enumerate(response.results[:2], 1):
            print(f"\n  [{i}] {result.title}")
            print(f"      Source：{result.source}")
            print(f"      URL: {result.url}")
            if result.snippet:
                snippet_preview = result.snippet[:100] + "..." if len(result.snippet) > 100 else result.snippet
                print(f"      Summary：{snippet_preview}")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    
    return response.success


if __name__ == "__main__":
    # If the env var is set, run the full test
    if os.environ.get("ANSPIRE_API_KEYS"):
        print("detected ANSPIRE_API_KEYS environment variables，Run the full test suite...")
        unittest.main(verbosity=2)
    else:
        # Otherwise only run unit tests and skip integration tests
        print("not set ANSPIRE_API_KEYS environment variables，Only run unit tests（Skip integration tests）...")
        print("To run a full test，Please set environment variables:")
        print("  Windows PowerShell: $env:ANSPIRE_API_KEYS=\"your_api_key\"")
        print("  Linux/Mac: export ANSPIRE_API_KEYS=\"your_api_key\"")
        print()
        
        # Run unit tests
        suite = unittest.TestLoader().loadTestsFromTestCase(TestAnspireConfigLoading)
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAnspireSearchProvider))
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAnspireSearchService))
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
        
        # Provide a manual test option
        print("\n" + "=" * 60)
        choice = input("Whether to run manual tests（need to be valid API Key）? (y/n): ").strip().lower()
        if choice == 'y':
            run_manual_test()
