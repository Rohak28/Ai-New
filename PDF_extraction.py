import pymupdf as fitz  # PyMuPDF
import pdfplumber
import os
import re
import json
import io
from PIL import Image

class IVNReportParser:
    def __init__(self, report_path, output_dir="static/reports"):
        self.report_path = report_path
        self.report_id = os.path.basename(report_path).split('.')[0]
        self.output_dir = os.path.join(output_dir, self.report_id, "images")
        os.makedirs(self.output_dir, exist_ok=True)
        
    def parse_metadata(self, pdf_text):
        """Extracts executive metadata from the first few pages."""
        metadata = {
            "report_no": "",
            "project_name": "",
            "dr_stage": "",
            "tester": "",
            "date": "",
            "ecu_matrix": [],
            "dbc_file": "",
            "tool_details": {}
        }
        
        # Simple regex extractions
        match = re.search(r"Project Name\s+(.*?)\n", pdf_text)
        if match: metadata["project_name"] = match.group(1).strip()
        
        match = re.search(r"Test Report No:\s+(\d+)", pdf_text)
        if match: metadata["report_no"] = match.group(1).strip()
            
        match = re.search(r"DR Stage\s+(\d+)", pdf_text)
        if match: metadata["dr_stage"] = match.group(1).strip()
            
        match = re.search(r"Tester Name\s+(.*?)\n", pdf_text)
        if match: metadata["tester"] = match.group(1).strip()

        match = re.search(r"DBC\s+(.*?)\n", pdf_text)
        if match: metadata["dbc_file"] = match.group(1).strip()
        
        # We can expand ECU matrix extraction parsing in a real scenario
        # Here we just look for known keywords for demonstration
        if "Airbag" in pdf_text:
            metadata["ecu_matrix"].append({"ecu": "Airbag", "hw_number": "12345", "sw_version": "11"})
        if "cluster" in pdf_text.lower():
            metadata["ecu_matrix"].append({"ecu": "Cluster", "hw_number": "54321", "sw_version": "12"})
        if "EPS" in pdf_text:
            metadata["ecu_matrix"].append({"ecu": "EPS", "hw_number": "43215", "sw_version": "13"})
            
        return metadata

    def extract_images_from_page(self, page, page_num):
        """Extracts images from a fitz page, filtering out logos."""
        extracted_images = []
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = page.parent.extract_image(xref)
            image_bytes = base_image["image"]
            
            try:
                image = Image.open(io.BytesIO(image_bytes))
                width, height = image.size
                
                # Filter out standard logos (e.g. 168x121, 443x114)
                if (width == 168 and height == 121) or (width == 443 and height == 114):
                    continue
                
                # This is likely a waveform graph (e.g., 1717x717) or a summary chart (444x444)
                img_filename = f"p{page_num}_{img_index}_{width}x{height}.png"
                img_path = os.path.join(self.output_dir, img_filename)
                image.save(img_path)
                
                extracted_images.append({
                    "image_path": f"/static/reports/{self.report_id}/images/{img_filename}",
                    "width": width,
                    "height": height
                })
            except Exception as e:
                print(f"Error extracting image xref {xref}: {e}")
                
        return extracted_images

    def parse_report(self):
        print(f"Opening {self.report_path} for streaming extraction...")
        doc = fitz.open(self.report_path)
        
        # Extract full text for metadata
        full_text = ""
        for i in range(min(3, len(doc))):
            full_text += doc[i].get_text()
            
        metadata = self.parse_metadata(full_text)
        
        test_cases = []
        current_tc = None
        # Make the second group optional so we catch IDs that have no following text
        tc_start_pattern = re.compile(r"Report:\s+([A-Za-z0-9_]+)(?:\s+(.*))?")
        
        # Iterate through pages to identify Test Case boundaries and data
        executive_images = []
        with pdfplumber.open(self.report_path) as pdf:
            for page_num in range(len(doc)):
                fitz_page = doc[page_num]
                page_text = fitz_page.get_text()
                
                # Check line by line for TC header or verdict keywords
                lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                for line in lines:
                    start_match = tc_start_pattern.search(line)
                    if start_match:
                        # Save existing active test case before starting a new one
                        if current_tc:
                            test_cases.append(current_tc)
                        
                        tc_name = start_match.group(2)
                        current_tc = {
                            "tc_id": start_match.group(1).strip(),
                            "name": tc_name.strip() if tc_name else "Unknown Test Name",
                            "verdict": "unknown",
                            "measurements": [],
                            "images": []
                        }
                        continue
                    
                    if current_tc:
                        # We will detect verdict reliably from the structured measurements later
                        pass

                # Extract images for current page
                page_images = self.extract_images_from_page(fitz_page, page_num + 1)
                
                if current_tc:
                    current_tc["images"].extend(page_images)
                    
                    plumber_page = pdf.pages[page_num]
                    tables = plumber_page.extract_tables()
                    if tables:
                        for table in tables:
                            cleaned_table = []
                            for row in table:
                                if any(cell and str(cell).strip() for cell in row):
                                    cleaned_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                                    cleaned_table.append(cleaned_row)
                            
                            if len(cleaned_table) > 1:
                                headers = cleaned_table[0]
                                for row in cleaned_table[1:]:
                                    if len(row) == len(headers):
                                        measurement = dict(zip(headers, row))
                                        current_tc["measurements"].append(measurement)
                else:
                    # Images before the first test case (e.g., Page 3 Pass/Fail Pie Chart)
                    for img in page_images:
                        executive_images.append(img)
                        if img["width"] == 444 and img["height"] == 444:
                            metadata["summary_chart"] = img["image_path"]

        metadata["executive_images"] = executive_images
        
        # Append final active test case at end of PDF
        if current_tc:
            test_cases.append(current_tc)
            
        # Reliably detect verdict from the extracted measurement tables
        for tc in test_cases:
            tc["verdict"] = "unknown"
            for m in tc.get("measurements", []):
                values = [str(v).lower().strip() for v in m.values()]
                
                # Check 1: Summary table headers (Highest Confidence)
                if "test cases failed" in values:
                    if "1" in values or "1.0" in values:
                        tc["verdict"] = "fail"
                elif "test cases passed" in values:
                    if "1" in values or "1.0" in values:
                        tc["verdict"] = "pass"
                        
                # Check 2: Fallback to overallresult (Secondary Confidence)
                row_str = " ".join(values)
                if "overallresult" in row_str:
                    if "fail" in row_str:
                        tc["verdict"] = "fail"
                    elif "pass" in row_str:
                        tc["verdict"] = "pass"

        return {
            "metadata": metadata,
            "test_cases": test_cases
        }

if __name__ == "__main__":
    import sys
    report_file = sys.argv[1] if len(sys.argv) > 1 else "../../IVN_Test_Report(15_57_18).pdf"
    if os.path.exists(report_file):
        parser = IVNReportParser(report_file)
        data = parser.parse_report()
        print(json.dumps(data, indent=2))
    else:
        print(f"File not found: {report_file}")
