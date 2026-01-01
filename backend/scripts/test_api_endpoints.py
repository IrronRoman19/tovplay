#!/usr/bin/env python3
"""
Comprehensive API endpoint testing script for TovPlay backend.
Tests all available endpoints with various scenarios including edge cases.
"""

import os
import sys
import json
import time
import requests
import uuid
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@dataclass
class TestResult:
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None
    response_data: Optional[dict] = None


class APITester:
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.results: List[TestResult] = []
        self.test_data = {}
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'TovPlay-API-Tester/1.0'
        })
        
        print(f"🚀 API Tester initialized for {base_url}")
    
    def log_result(self, result: TestResult):
        """Log test result."""
        status_icon = "✅" if result.success else "❌"
        print(f"{status_icon} {result.method:6} {result.endpoint:30} {result.status_code:3} ({result.response_time_ms:6.1f}ms)")
        
        if result.error_message:
            print(f"   Error: {result.error_message}")
        
        self.results.append(result)
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> TestResult:
        """Make HTTP request and return test result."""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            response = self.session.request(method, url, **kwargs)
            response_time = (time.time() - start_time) * 1000
            
            try:
                response_data = response.json() if response.content else None
            except json.JSONDecodeError:
                response_data = {"raw_response": response.text[:200]}
            
            success = 200 <= response.status_code < 300
            error_message = None
            
            if not success and response_data and isinstance(response_data, dict):
                error_message = response_data.get('error', f"HTTP {response.status_code}")
            
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                response_time_ms=response_time,
                success=success,
                error_message=error_message,
                response_data=response_data
            )
            
        except requests.RequestException as e:
            response_time = (time.time() - start_time) * 1000
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time_ms=response_time,
                success=False,
                error_message=str(e)
            )
    
    def test_health_endpoints(self):
        """Test health and monitoring endpoints."""
        print("\n📊 Testing Health Endpoints")
        print("=" * 50)
        
        health_endpoints = [
            ('GET', '/health'),
            ('GET', '/health/detailed'),
            ('GET', '/health/database'),
            ('GET', '/health/ready'),
            ('GET', '/health/live'),
            ('GET', '/metrics'),
        ]
        
        for method, endpoint in health_endpoints:
            result = self.make_request(method, endpoint)
            self.log_result(result)
            
            # Store health data for later use
            if result.success and endpoint == '/health':
                self.test_data['health'] = result.response_data
    
    def test_api_info_endpoints(self):
        """Test API information endpoints."""
        print("\n📋 Testing API Info Endpoints")
        print("=" * 50)
        
        info_endpoints = [
            ('GET', '/api/'),
            ('GET', '/api/health'),
        ]
        
        for method, endpoint in info_endpoints:
            result = self.make_request(method, endpoint)
            self.log_result(result)
            
            # Store API info for discovering endpoints
            if result.success and endpoint == '/api/':
                self.test_data['api_info'] = result.response_data
    
    def test_user_endpoints(self):
        """Test user-related endpoints."""
        print("\n👥 Testing User Endpoints")
        print("=" * 50)
        
        # Test getting users (should work without auth for testing)
        result = self.make_request('GET', '/api/users/')
        self.log_result(result)
        
        # Test user creation
        test_user_data = {
            'username': f'test_user_{uuid.uuid4().hex[:8]}',
            'email': f'test_{uuid.uuid4().hex[:8]}@test.com',
            'discord_username': f'testuser#{uuid.randint(1000, 9999)}',
            'password': 'test_password_123'
        }
        
        # If we have a safe route example, test it
        creation_endpoints = [
            ('/api/safe/users', test_user_data),  # If safe routes are registered
            ('/api/users', test_user_data),       # Standard route
        ]
        
        created_user = None
        for endpoint, data in creation_endpoints:
            result = self.make_request('POST', endpoint, json=data)
            self.log_result(result)
            
            if result.success and result.response_data:
                created_user = result.response_data
                self.test_data['test_user'] = created_user
                break
        
        # Test getting specific user
        if created_user and 'id' in created_user:
            user_id = created_user['id']
            result = self.make_request('GET', f'/api/users/{user_id}')
            self.log_result(result)
            
            # Test updating user
            update_data = {'username': f'updated_{uuid.uuid4().hex[:8]}'}
            result = self.make_request('PUT', f'/api/users/{user_id}', json=update_data)
            self.log_result(result)
    
    def test_game_endpoints(self):
        """Test game-related endpoints."""
        print("\n🎮 Testing Game Endpoints")
        print("=" * 50)
        
        # Test getting games
        result = self.make_request('GET', '/api/games/')
        self.log_result(result)
        
        if result.success and result.response_data:
            self.test_data['games'] = result.response_data
        
        # Test creating a game (if endpoint exists)
        test_game_data = {
            'game_name': f'Test Game {uuid.uuid4().hex[:8]}',
            'category': 'Test',
            'min_players': 2,
            'max_players': 4,
            'avg_session_duration': 30,
            'difficulty_level': 'easy'
        }
        
        result = self.make_request('POST', '/api/games/', json=test_game_data)
        self.log_result(result)
        
        if result.success and result.response_data:
            game_id = result.response_data.get('id')
            if game_id:
                # Test getting specific game
                result = self.make_request('GET', f'/api/games/{game_id}')
                self.log_result(result)
    
    def test_game_request_endpoints(self):
        """Test game request endpoints."""
        print("\n🎯 Testing Game Request Endpoints")
        print("=" * 50)
        
        # Test getting game requests
        result = self.make_request('GET', '/api/game_requests/')
        self.log_result(result)
        
        # Test search functionality
        result = self.make_request('GET', '/api/findplayers/')
        self.log_result(result)
        
        # If we have test user and games, create a game request
        test_user = self.test_data.get('test_user')
        games = self.test_data.get('games')
        
        if test_user and games and len(games) > 0:
            game_id = games[0].get('id') if isinstance(games, list) else None
            user_id = test_user.get('id')
            
            if game_id and user_id:
                request_data = {
                    'sender_user_id': user_id,
                    'recipient_user_id': user_id,  # Self-request for testing
                    'game_id': game_id,
                    'message': 'Test game request'
                }
                
                result = self.make_request('POST', '/api/game_requests/', json=request_data)
                self.log_result(result)
    
    def test_profile_endpoints(self):
        """Test user profile endpoints."""
        print("\n👤 Testing User Profile Endpoints")
        print("=" * 50)
        
        result = self.make_request('GET', '/api/user_profiles/')
        self.log_result(result)
        
        # Test user preferences
        result = self.make_request('GET', '/api/user_game_preferences/')
        self.log_result(result)
        
        # Test availability
        result = self.make_request('GET', '/api/availability/')
        self.log_result(result)
    
    def test_session_endpoints(self):
        """Test session-related endpoints."""
        print("\n🕐 Testing Session Endpoints")
        print("=" * 50)
        
        result = self.make_request('GET', '/api/scheduled_sessions/')
        self.log_result(result)
        
        result = self.make_request('GET', '/api/user_sessions/')
        self.log_result(result)
    
    def test_error_handling(self):
        """Test error handling and edge cases."""
        print("\n⚠️  Testing Error Handling")
        print("=" * 50)
        
        error_tests = [
            ('GET', '/api/nonexistent'),           # 404 Not Found
            ('POST', '/api/users/', {'invalid': 'data'}),  # Invalid data
            ('GET', '/api/users/invalid-uuid'),    # Invalid ID format
            ('DELETE', '/api/users/00000000-0000-0000-0000-000000000000'),  # Non-existent ID
            ('PUT', '/api/games/'),                # Missing ID in PUT
            ('POST', '/api/game_requests/', {}),   # Empty POST data
        ]
        
        for method, endpoint, *args in error_tests:
            kwargs = {'json': args[0]} if args else {}
            result = self.make_request(method, endpoint, **kwargs)
            self.log_result(result)
    
    def test_security_features(self):
        """Test security features."""
        print("\n🔒 Testing Security Features")
        print("=" * 50)
        
        # Test rate limiting (make multiple rapid requests)
        print("Testing rate limiting...")
        for i in range(5):
            result = self.make_request('GET', '/health')
            if result.status_code == 429:
                print("✅ Rate limiting is working")
                break
        
        # Test CORS headers
        result = self.make_request('OPTIONS', '/api/')
        self.log_result(result)
        
        # Test with malicious input
        malicious_inputs = [
            '<script>alert("xss")</script>',
            'javascript:alert(1)',
            '"; DROP TABLE users; --',
            '../../../etc/passwd',
            '\x00\x01\x02\x03'
        ]
        
        for malicious_input in malicious_inputs:
            result = self.make_request('GET', f'/api/users/?search={malicious_input}')
            # Should not crash, should handle gracefully
            if result.status_code not in [400, 404, 422]:
                print(f"⚠️  Potentially unsafe handling of: {malicious_input[:20]}...")
    
    def test_performance(self):
        """Test performance characteristics."""
        print("\n⚡ Testing Performance")
        print("=" * 50)
        
        # Test multiple concurrent-like requests
        endpoints_to_test = ['/health', '/api/', '/api/health']
        
        for endpoint in endpoints_to_test:
            times = []
            for _ in range(10):
                result = self.make_request('GET', endpoint)
                if result.success:
                    times.append(result.response_time_ms)
            
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                min_time = min(times)
                
                print(f"{endpoint:20} - Avg: {avg_time:6.1f}ms, Min: {min_time:6.1f}ms, Max: {max_time:6.1f}ms")
                
                if avg_time > 1000:  # > 1 second
                    print(f"⚠️  Slow endpoint detected: {endpoint}")
    
    def run_all_tests(self):
        """Run all endpoint tests."""
        print("🧪 Starting Comprehensive API Endpoint Testing")
        print("=" * 60)
        print(f"Target: {self.base_url}")
        print(f"Time: {datetime.now().isoformat()}")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # Test basic connectivity first
            result = self.make_request('GET', '/health')
            if not result.success:
                print("❌ Cannot connect to API server. Please ensure it's running.")
                return False
            
            # Run all test suites
            self.test_health_endpoints()
            self.test_api_info_endpoints()
            self.test_user_endpoints()
            self.test_game_endpoints()
            self.test_game_request_endpoints()
            self.test_profile_endpoints()
            self.test_session_endpoints()
            self.test_error_handling()
            self.test_security_features()
            self.test_performance()
            
        except KeyboardInterrupt:
            print("\n⏹️  Testing interrupted by user")
        except Exception as e:
            print(f"\n💥 Unexpected error during testing: {e}")
        
        finally:
            total_time = time.time() - start_time
            self.print_summary(total_time)
    
    def print_summary(self, total_time: float):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - successful_tests
        
        print(f"Total tests run: {total_tests}")
        print(f"Successful: {successful_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success rate: {(successful_tests/total_tests*100):.1f}%")
        print(f"Total time: {total_time:.2f}s")
        
        if self.results:
            avg_response_time = sum(r.response_time_ms for r in self.results) / len(self.results)
            print(f"Average response time: {avg_response_time:.1f}ms")
        
        # Show failed tests
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS ({failed_tests}):")
            for result in self.results:
                if not result.success:
                    print(f"   {result.method} {result.endpoint} - {result.error_message or f'HTTP {result.status_code}'}")
        
        # Show slow endpoints
        slow_endpoints = [r for r in self.results if r.response_time_ms > 1000]
        if slow_endpoints:
            print(f"\n⏱️  SLOW ENDPOINTS (>1s):")
            for result in slow_endpoints:
                print(f"   {result.method} {result.endpoint} - {result.response_time_ms:.1f}ms")
        
        print("\n✨ Testing completed!")
        return failed_tests == 0


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test TovPlay API endpoints')
    parser.add_argument(
        '--url', 
        default='http://localhost:5001',
        help='Base URL of the API (default: http://localhost:5001)'
    )
    parser.add_argument(
        '--save-report',
        action='store_true',
        help='Save detailed test report to JSON file'
    )
    
    args = parser.parse_args()
    
    tester = APITester(args.url)
    success = tester.run_all_tests()
    
    if args.save_report:
        report_file = f'api_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'base_url': args.url,
            'summary': {
                'total_tests': len(tester.results),
                'successful': sum(1 for r in tester.results if r.success),
                'failed': sum(1 for r in tester.results if not r.success),
            },
            'results': [
                {
                    'endpoint': r.endpoint,
                    'method': r.method,
                    'status_code': r.status_code,
                    'response_time_ms': r.response_time_ms,
                    'success': r.success,
                    'error_message': r.error_message
                }
                for r in tester.results
            ]
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())