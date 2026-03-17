#!/usr/bin/env python3
import requests
import sys
import json
from datetime import datetime

class HotelAuditTester:
    def __init__(self, base_url="https://hotel-tariff-verify.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.results = []

    def log_result(self, test_name, passed, details=""):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        
        result = f"{status} - {test_name}"
        if details:
            result += f" - {details}"
        
        print(result)
        self.results.append({
            "test_name": test_name,
            "passed": passed,
            "details": details
        })
        return passed

    def test_api_health(self):
        """Test API health check endpoint"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                ocr_status = "OCR Available" if data.get('ocr_available') else "OCR Unavailable"
                return self.log_result("API Health Check", True, f"Status: {data.get('status')} - {ocr_status}")
            else:
                return self.log_result("API Health Check", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_result("API Health Check", False, f"Error: {str(e)}")

    def test_api_root(self):
        """Test API root endpoint"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                message = data.get('message', '')
                return self.log_result("API Root", True, f"Message: {message}")
            else:
                return self.log_result("API Root", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_result("API Root", False, f"Error: {str(e)}")

    def test_pdf_upload(self, pdf_path="/tmp/test_hotel.pdf"):
        """Test PDF upload and processing"""
        try:
            with open(pdf_path, 'rb') as f:
                files = {'file': ('test_hotel.pdf', f, 'application/pdf')}
                response = requests.post(f"{self.api_url}/upload-pdf", files=files, timeout=60)
            
            success = response.status_code == 200
            
            if success:
                data = response.json()
                total_hospedes = data.get('total_hospedes', 0)
                total_quartos = data.get('total_quartos', 0)
                revenue_total = data.get('revenue_total', 0)
                data_relatorio = data.get('data_relatorio', '')
                
                # Check key fields
                if total_hospedes > 0 and total_quartos > 0:
                    details = f"Hospedes: {total_hospedes}, Quartos: {total_quartos}, Revenue: R${revenue_total:.2f}, Data: {data_relatorio}"
                    
                    # Store response data for further analysis
                    self.pdf_data = data
                    return self.log_result("PDF Upload & Processing", True, details)
                else:
                    return self.log_result("PDF Upload & Processing", False, "No guests or rooms found in processed data")
            else:
                error_msg = response.text if response.text else f"Status code: {response.status_code}"
                return self.log_result("PDF Upload & Processing", False, error_msg)
                
        except FileNotFoundError:
            return self.log_result("PDF Upload & Processing", False, f"Test PDF not found at {pdf_path}")
        except Exception as e:
            return self.log_result("PDF Upload & Processing", False, f"Error: {str(e)}")

    def test_categorization_logic(self):
        """Test guest categorization logic based on uploaded data"""
        if not hasattr(self, 'pdf_data'):
            return self.log_result("Categorization Logic", False, "No PDF data available - PDF upload must run first")
        
        data = self.pdf_data
        categories_found = []
        
        # Check each category
        if data.get('faturados'):
            categories_found.append(f"Faturados: {len(data['faturados'])}")
        if data.get('grupos'): 
            categories_found.append(f"Grupos: {len(data['grupos'])}")
        if data.get('confidenciais'):
            categories_found.append(f"Confidenciais: {len(data['confidenciais'])}")
        if data.get('pgto_direto'):
            categories_found.append(f"Pgto Direto: {len(data['pgto_direto'])}")
        if data.get('online_b2b'):
            categories_found.append(f"Online B2B: {len(data['online_b2b'])}")
        if data.get('cortesias'):
            categories_found.append(f"Cortesias: {len(data['cortesias'])}")

        if categories_found:
            details = " | ".join(categories_found)
            return self.log_result("Categorization Logic", True, details)
        else:
            return self.log_result("Categorization Logic", False, "No categories detected")

    def test_divergencies_detection(self):
        """Test fare divergencies detection"""
        if not hasattr(self, 'pdf_data'):
            return self.log_result("Divergencies Detection", False, "No PDF data available")
        
        data = self.pdf_data
        divergencias = data.get('divergencias', [])
        
        # Calculate total divergence amount
        total_divergencia = sum(d.get('divergencia', 0) for d in divergencias)
        
        details = f"Found {len(divergencias)} divergencies, Total: R${total_divergencia:.2f}"
        return self.log_result("Divergencies Detection", True, details)

    def test_departures_detection(self):
        """Test departures detection"""
        if not hasattr(self, 'pdf_data'):
            return self.log_result("Departures Detection", False, "No PDF data available")
        
        data = self.pdf_data
        saidas = data.get('saidas', [])
        
        details = f"Found {len(saidas)} departures for today/tomorrow"
        return self.log_result("Departures Detection", True, details)

    def test_revenue_calculations(self):
        """Test revenue calculations"""
        if not hasattr(self, 'pdf_data'):
            return self.log_result("Revenue Calculations", False, "No PDF data available")
        
        data = self.pdf_data
        revenue_total = data.get('revenue_total', 0)
        adr = data.get('adr', 0)
        total_quartos = data.get('total_quartos', 0)
        
        # Verify ADR calculation (ADR = Revenue / Rooms)
        expected_adr = revenue_total / total_quartos if total_quartos > 0 else 0
        adr_correct = abs(adr - expected_adr) < 0.01  # Allow small floating point differences
        
        if adr_correct and revenue_total > 0:
            details = f"Revenue: R${revenue_total:.2f}, ADR: R${adr:.2f} (verified)"
            return self.log_result("Revenue Calculations", True, details)
        else:
            details = f"Revenue: R${revenue_total:.2f}, ADR: R${adr:.2f}, Expected ADR: R${expected_adr:.2f}"
            return self.log_result("Revenue Calculations", False, details)

    def test_invalid_file_upload(self):
        """Test upload with invalid file type"""
        try:
            # Create a dummy text file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
                tmp_file.write(b"This is not a PDF")
                tmp_file_path = tmp_file.name
            
            with open(tmp_file_path, 'rb') as f:
                files = {'file': ('test.txt', f, 'text/plain')}
                response = requests.post(f"{self.api_url}/upload-pdf", files=files, timeout=10)
            
            # Should return 400 for invalid file type
            if response.status_code == 400:
                error_detail = response.json().get('detail', '')
                return self.log_result("Invalid File Upload", True, f"Correctly rejected: {error_detail}")
            else:
                return self.log_result("Invalid File Upload", False, f"Expected 400, got {response.status_code}")
                
        except Exception as e:
            return self.log_result("Invalid File Upload", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all backend tests"""
        print(f"🔍 Starting Backend API Tests for Hotel Audit Dashboard")
        print(f"📡 API Base URL: {self.api_url}")
        print("=" * 60)
        
        # Core API tests
        self.test_api_health()
        self.test_api_root()
        
        # PDF processing tests  
        self.test_pdf_upload()
        self.test_categorization_logic()
        self.test_divergencies_detection()
        self.test_departures_detection() 
        self.test_revenue_calculations()
        
        # Error handling tests
        self.test_invalid_file_upload()
        
        # Summary
        print("=" * 60)
        print(f"📊 Backend Tests Summary:")
        print(f"✅ Passed: {self.tests_passed}/{self.tests_run}")
        print(f"❌ Failed: {self.tests_run - self.tests_passed}/{self.tests_run}")
        
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All backend tests passed!")
            return 0
        else:
            print("⚠️  Some backend tests failed!")
            return 1

def main():
    tester = HotelAuditTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())