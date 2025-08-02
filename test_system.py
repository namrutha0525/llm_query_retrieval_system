#!/usr/bin/env python3
"""
Test script for LLM Query-Retrieval System
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:8000"
API_TOKEN = "479309883e76b7aff59e87e1e032ce655934c42516b75cc1ceaea8663351e3ba"
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Test document URL (you can replace with your own)
TEST_DOCUMENT_URL = "https://hackrx.blob.core.windows.net/assets/policy.pdf?sv=2023-01-03&st=2025-07-04T09%3A11%3A24Z&se=2027-07-05T09%3A11%3A00Z&sr=b&sp=r&sig=N4a9OU0w0QXO6AOIBiu4bpl7AXvEZogeT%2FjUHNO7HzQ%3D"

def test_health_check():
    """Test health check endpoint"""
    print("🔍 Testing health check...")

    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_ping():
    """Test ping endpoint"""
    print("🏓 Testing ping endpoint...")

    try:
        response = requests.get(f"{BASE_URL}/ping", timeout=5)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Ping successful: {data['status']}")
            return True
        else:
            print(f"❌ Ping failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Ping error: {e}")
        return False

def test_document_processing():
    """Test main document processing endpoint"""
    print("📄 Testing document processing...")

    test_data = {
        "documents": TEST_DOCUMENT_URL,
        "questions": [
            "What is the grace period for premium payment?",
            "What is the waiting period for pre-existing diseases?",
            "Does this policy cover maternity expenses?"
        ]
    }

    try:
        print(f"🚀 Sending request to {BASE_URL}/api/v1/hackrx/run")
        print(f"📋 Questions: {len(test_data['questions'])}")

        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/v1/hackrx/run",
            headers=HEADERS,
            json=test_data,
            timeout=120  # Allow up to 2 minutes for processing
        )
        end_time = time.time()

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Document processing successful!")
            print(f"⏱️  Processing time: {end_time - start_time:.2f}s")
            print(f"📊 Document ID: {data.get('document_id', 'N/A')}")
            print(f"🔢 Answers received: {len(data.get('answers', []))}")

            # Print first answer as example
            if data.get('answers'):
                print(f"\n📝 Sample Answer:")
                print(f"Q: {test_data['questions'][0]}")
                print(f"A: {data['answers'][0][:200]}...")

            return True

        else:
            print(f"❌ Document processing failed: {response.status_code}")
            print(f"🔍 Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("❌ Request timed out - processing may take longer than expected")
        return False
    except Exception as e:
        print(f"❌ Document processing error: {e}")
        return False

def test_authentication():
    """Test authentication"""
    print("🔐 Testing authentication...")

    # Test without token
    try:
        response = requests.post(f"{BASE_URL}/api/v1/hackrx/run", json={})

        if response.status_code == 401:
            print("✅ Authentication properly enforced (401 without token)")
        else:
            print(f"⚠️  Unexpected response without token: {response.status_code}")

    except Exception as e:
        print(f"❌ Auth test error: {e}")
        return False

    # Test with invalid token
    try:
        invalid_headers = {
            "Authorization": "Bearer invalid_token",
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"{BASE_URL}/api/v1/hackrx/run", 
            headers=invalid_headers, 
            json={}
        )

        if response.status_code == 401:
            print("✅ Invalid token properly rejected (401)")
            return True
        else:
            print(f"⚠️  Unexpected response with invalid token: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Invalid token test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Starting LLM Query-Retrieval System Tests\n")

    tests = [
        ("Ping Test", test_ping),
        ("Health Check", test_health_check),
        ("Authentication", test_authentication),
        ("Document Processing", test_document_processing)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)

        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            results.append((test_name, False))

        time.sleep(1)  # Brief pause between tests

    # Print summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print('='*50)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1

    print(f"\n🎯 Results: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All tests passed! System is working correctly.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
