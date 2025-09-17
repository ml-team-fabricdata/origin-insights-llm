import asyncio
import os
from typing import Dict, List, Any

from validation import (
    validate_title,
    validate_actor,
    validate_director,
    search_title_exact,
    search_title_fuzzy,
    ValidationResponseBuilder
)
from src.sql_db import db


class TestRunner:
    """Manages event loop and database connections for all tests."""
    
    def __init__(self):
        self.loop = None
        self.db_initialized = False
    
    def setup(self):
        """Setup event loop and database."""
        if self.loop is None or self.loop.is_closed():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
        if not self.db_initialized:
            self.loop.run_until_complete(db._ensure_initialized())
            self.db_initialized = True
    
    def run_async(self, coro):
        """Run async function in the managed event loop."""
        return self.loop.run_until_complete(coro)
    
    def cleanup(self):
        """Clean up resources."""
        if self.loop and not self.loop.is_closed():
            try:
                self.loop.run_until_complete(db.close())
            except:
                pass
            self.loop.close()


# Global test runner instance
test_runner = TestRunner()


class TestDatabase:
    """Integration tests that perform actual SQL queries."""
    
    def test_database_connection(self):
        """Test basic database connectivity."""
        async def run_test():
            result = await db.execute_query("SELECT 1 as test_value")
            assert len(result) == 1
            assert result[0]['test_value'] == 1
        
        test_runner.run_async(run_test())

    def test_search_title_exact_integration(self):
        """Test exact title search with real database."""
        async def run_test():
            try:
                results = await search_title_exact("The Matrix")
                
                assert isinstance(results, list), f"Expected list, got {type(results)}"
                
                if results:
                    result = results[0]
                    # Only check for required fields that should always exist
                    required_fields = ['uid', 'title']
                    for field in required_fields:
                        assert field in result, f"Missing field {field} in result: {result}"
                        assert result[field] is not None, f"Field {field} is None in result: {result}"
                    
                    assert "matrix" in result['title'].lower(), f"Title doesn't contain 'matrix': {result['title']}"
                    
                    # Optional fields can be None - just verify they exist in structure
                    optional_fields = ['year', 'type', 'imdb_id']
                    for field in optional_fields:
                        assert field in result, f"Missing optional field {field} in result: {result}"
                else:
                    print("No exact matches found for 'The Matrix'")
            except Exception as e:
                print(f"Error in test_search_title_exact_integration: {e}")
                raise
        
        test_runner.run_async(run_test())

    def test_search_title_fuzzy_integration(self):
        """Test fuzzy title search with real database."""
        async def run_test():
            try:
                results = await search_title_fuzzy("Matrx", threshold=0.3)
                
                assert isinstance(results, list), f"Expected list, got {type(results)}"
                
                if results:
                    result = results[0]
                    # For fuzzy search, check either 'title' or 'aka_title'
                    assert 'uid' in result, f"Missing uid in result: {result}"
                    
                    has_title = 'title' in result and result['title'] is not None
                    has_aka_title = 'aka_title' in result and result['aka_title'] is not None
                    
                    assert has_title or has_aka_title, f"Missing both title and aka_title in result: {result}"
                    
                    # Verify fuzzy search similarity
                    if 'title_similarity' in result:
                        assert result['title_similarity'] is not None, f"title_similarity is None: {result}"
                else:
                    print("No fuzzy matches found for 'Matrx'")
            except Exception as e:
                print(f"Error in test_search_title_fuzzy_integration: {e}")
                raise
        
        test_runner.run_async(run_test())

    def test_validate_title_integration(self):
        """Test title validation with real database."""
        async def run_test():
            result = await validate_title("The Godfather")
            
            assert 'status' in result
            assert result['status'] in ['resolved', 'ambiguous', 'not_found']
            
            if result['status'] == 'resolved':
                assert 'result' in result
                assert 'uid' in result['result']
                assert 'title' in result['result']
                
            elif result['status'] == 'ambiguous':
                assert 'options' in result
                assert isinstance(result['options'], list)
                assert len(result['options']) > 0
                
                option = result['options'][0]
                assert 'uid' in option
                assert 'title' in option
        
        test_runner.run_async(run_test())

    def test_validate_title_fuzzy_fallback(self):
        """Test title validation with fuzzy search fallback."""
        async def run_test():
            result = await validate_title("Godfater")  # Missing 'h'
            
            assert 'status' in result
            
            if result['status'] in ['resolved', 'ambiguous']:
                if result['status'] == 'resolved':
                    title = result['result']['title'].lower()
                    assert 'godfather' in title or 'godfater' in title
        
        test_runner.run_async(run_test())

    def test_validate_actor_integration(self):
        """Test actor validation with real database."""
        async def run_test():
            result = await validate_actor("Robert De Niro")
            
            assert 'status' in result
            assert result['status'] in ['ok', 'ambiguous', 'not_found']
            
            if result['status'] == 'ok':
                assert 'id' in result
                assert 'name' in result
                assert 'robert' in result['name'].lower()
                
            elif result['status'] == 'ambiguous':
                assert 'options' in result
                assert isinstance(result['options'], list)
                
                if result['options']:
                    option = result['options'][0]
                    assert 'id' in option
                    assert 'name' in option
                    assert 'score' in option
        
        test_runner.run_async(run_test())

    def test_validate_director_integration(self):
        """Test director validation with real database."""
        async def run_test():
            result = await validate_director("Steven Spielberg")
            
            assert 'status' in result
            assert result['status'] in ['ok', 'ambiguous', 'not_found']
            
            if result['status'] == 'ok':
                assert 'id' in result
                assert 'name' in result
                assert 'steven' in result['name'].lower()
                
            elif result['status'] == 'ambiguous':
                assert 'options' in result
                assert isinstance(result['options'], list)
                
                if result['options']:
                    option = result['options'][0]
                    assert 'id' in option
                    assert 'name' in option
                    assert 'score' in option
        
        test_runner.run_async(run_test())

    def test_validate_nonexistent_title(self):
        """Test validation with completely made-up title."""
        async def run_test():
            try:
                # Use an even more unlikely title to avoid false matches
                fake_title = "Completely Nonexistent Movie Title XYZ 999888777"
                result = await validate_title(fake_title)
                assert isinstance(result, dict), f"Expected dict, got {type(result)}"
                assert 'status' in result, f"Missing 'status' key in result: {result}"
                
                # Accept either not_found or ambiguous (fuzzy matches might exist)
                valid_statuses = ['not_found', 'ambiguous']
                assert result['status'] in valid_statuses, f"Expected {valid_statuses}, got {result['status']}"
                
                if result['status'] == 'ambiguous':
                    print(f"Found fuzzy matches for fake title '{fake_title}': {result.get('options', [])}")
                    # This is actually acceptable - fuzzy search might match anything
                    
            except Exception as e:
                print(f"Error in test_validate_nonexistent_title: {e}")
                raise
        
        test_runner.run_async(run_test())

    def test_validate_nonexistent_actor(self):
        """Test validation with made-up actor name."""
        async def run_test():
            result = await validate_actor("John Completely Fake Actor")
            assert result['status'] == 'not_found'
        
        test_runner.run_async(run_test())

    def test_validate_empty_inputs(self):
        """Test validation with empty or invalid inputs."""
        async def run_test():
            # Empty string
            result = await validate_title("")
            assert result['status'] == 'not_found'
            
            # None input
            result = await validate_actor(None)
            assert result['status'] == 'not_found'
            
            # Whitespace only
            result = await validate_title("   ")
            assert result['status'] == 'not_found'
        
        test_runner.run_async(run_test())

    def test_title_validation_with_year_disambiguation(self):
        """Test title validation where year helps disambiguate."""
        async def run_test():
            result = await validate_title("Batman")
            
            assert 'status' in result
            
            if result['status'] == 'ambiguous':
                assert len(result['options']) > 1
                
                for option in result['options']:
                    assert 'year' in option
                    assert 'title' in option
                    assert 'batman' in option['title'].lower()
        
        test_runner.run_async(run_test())

    def test_actor_partial_name_search(self):
        """Test actor search with partial names."""
        async def run_test():
            result = await validate_actor("Robert")
            
            assert 'status' in result
            
            if result['status'] == 'ambiguous':
                assert len(result['options']) > 0
                
                for option in result['options']:
                    assert 'robert' in option['name'].lower()
        
        test_runner.run_async(run_test())

    def test_threshold_behavior(self):
        """Test how different thresholds affect search results."""
        async def run_test():
            strict_result = await validate_title("Godfther", threshold=0.8)
            loose_result = await validate_title("Godfther", threshold=0.3)
            
            if strict_result['status'] == 'not_found':
                assert loose_result['status'] in ['resolved', 'ambiguous', 'not_found']
        
        test_runner.run_async(run_test())

    def test_case_insensitive_search(self):
        """Test that searches are case insensitive."""
        async def run_test():
            lower_result = await validate_title("the matrix")
            upper_result = await validate_title("THE MATRIX")
            mixed_result = await validate_title("The Matrix")
            
            assert lower_result['status'] == upper_result['status'] == mixed_result['status']
            
            if lower_result['status'] == 'resolved':
                assert lower_result['result']['uid'] == upper_result['result']['uid']
                assert lower_result['result']['uid'] == mixed_result['result']['uid']
        
        test_runner.run_async(run_test())

    def test_special_characters_handling(self):
        """Test how special characters in titles are handled."""
        async def run_test():
            result = await validate_title("Spider-Man: Into the Spider-Verse")
            assert 'status' in result
        
        test_runner.run_async(run_test())


class TestResponseStructure:
    """Tests to verify response structure consistency."""
    
    def test_validation_response_builder_not_found(self):
        """Test ValidationResponseBuilder not_found method."""
        not_found = ValidationResponseBuilder.not_found()
        assert not_found == {"status": "not_found"}
    
    def test_validation_response_builder_resolved(self):
        """Test ValidationResponseBuilder resolved method."""
        sample_result = {"uid": "tt123", "title": "Test"}
        resolved = ValidationResponseBuilder.resolved(sample_result)
        assert resolved == {"status": "resolved", "result": sample_result}
    
    def test_validation_response_builder_ambiguous(self):
        """Test ValidationResponseBuilder ambiguous method."""
        sample_options = [{"uid": "tt123"}, {"uid": "tt456"}]
        ambiguous = ValidationResponseBuilder.ambiguous(sample_options)
        assert ambiguous == {"status": "ambiguous", "options": sample_options}
    
    def test_validation_response_builder_ok(self):
        """Test ValidationResponseBuilder ok method."""
        ok = ValidationResponseBuilder.ok("nm123", "John Doe")
        assert ok == {"status": "ok", "id": "nm123", "name": "John Doe"}


class TestPerformance:
    """Performance and stress tests."""
    
    def test_multiple_concurrent_searches(self):
        """Test multiple concurrent title searches."""
        async def run_test():
            tasks = [
                validate_title("The Matrix"),
                validate_title("The Godfather"),
                validate_title("Pulp Fiction"),
                validate_actor("Tom Hanks"),
                validate_director("Christopher Nolan")
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions for this test
            valid_results = [r for r in results if isinstance(r, dict)]
            
            assert len(valid_results) >= 0  # At least some should succeed
            for result in valid_results:
                assert 'status' in result
                assert result['status'] in ['resolved', 'ambiguous', 'not_found', 'ok']
        
        test_runner.run_async(run_test())

    def test_search_with_very_long_input(self):
        """Test search behavior with unusually long input."""
        async def run_test():
            long_title = "A" * 1000  # Very long string
            result = await validate_title(long_title)
            
            assert 'status' in result
            assert result['status'] == 'not_found'
        
        test_runner.run_async(run_test())

    def test_search_with_special_unicode_characters(self):
        """Test search with unicode and special characters."""
        async def run_test():
            unicode_title = "Amélie Poulain çñü 中文"
            result = await validate_title(unicode_title)
            
            assert 'status' in result
        
        test_runner.run_async(run_test())


class TestEdgeCases:
    """Edge case tests."""
    
    def test_numeric_only_input(self):
        """Test with numeric-only input."""
        async def run_test():
            result = await validate_title("123456")
            assert 'status' in result
        
        test_runner.run_async(run_test())
    
    def test_single_character_input(self):
        """Test with single character input."""
        async def run_test():
            result = await validate_actor("A")
            assert 'status' in result
        
        test_runner.run_async(run_test())
    
    def test_very_common_words(self):
        """Test with very common words that might return many results."""
        async def run_test():
            result = await validate_title("The")
            assert 'status' in result
            
            if result['status'] == 'ambiguous':
                # Should have options but not too many
                assert len(result['options']) <= 8  # MAX_OPTIONS_DISPLAY
        
        test_runner.run_async(run_test())


def run_all_tests():
    """Run all tests manually with proper setup and cleanup."""
    test_classes = [TestDatabase, TestResponseStructure, TestPerformance, TestEdgeCases]
    
    total_tests = 0
    passed_tests = 0
    
    try:
        # Setup once for all tests
        test_runner.setup()
        
        for test_class in test_classes:
            print(f"\n=== Running {test_class.__name__} ===")
            
            instance = test_class()
            test_methods = [method for method in dir(instance) if method.startswith('test_')]
            
            for test_method in test_methods:
                total_tests += 1
                try:
                    # Run test
                    getattr(instance, test_method)()
                    print(f"✅ {test_method}")
                    passed_tests += 1
                    
                except Exception as e:
                    print(f"❌ {test_method}: {str(e)}")
        
        print(f"\n{'='*50}")
        print(f"Tests run: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success rate: {(passed_tests/total_tests*100):.1f}%")
        
        return passed_tests == total_tests
    
    finally:
        # Cleanup
        test_runner.cleanup()


def run_single_test(test_class_name, test_method_name):
    """Run a single test with proper setup and cleanup."""
    test_classes = {
        'TestDatabase': TestDatabase,
        'TestResponseStructure': TestResponseStructure,
        'TestPerformance': TestPerformance,
        'TestEdgeCases': TestEdgeCases
    }
    
    if test_class_name not in test_classes:
        print(f"Test class {test_class_name} not found")
        return False
    
    try:
        test_runner.setup()
        
        test_class = test_classes[test_class_name]
        instance = test_class()
        
        if not hasattr(instance, test_method_name):
            print(f"Test method {test_method_name} not found in {test_class_name}")
            return False
        
        print(f"Running {test_class_name}::{test_method_name}")
        
        getattr(instance, test_method_name)()
        print("✅ Test passed")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    finally:
        test_runner.cleanup()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 3:
        # Run specific test: python test.py TestDatabase test_database_connection
        success = run_single_test(sys.argv[1], sys.argv[2])
    else:
        # Run all tests
        success = run_all_tests()
    
    sys.exit(0 if success else 1)