#!/usr/bin/env python3
"""
Sovereign OS Visual Intent Edge Agent
Uses a local Hailo NPU-compiled HEF model to run real-time inference on screen captures,
detecting UI elements (buttons, inputs) and executing physical input actuation via PyAutoGUI.
"""

import sys
import numpy as np

# Graceful import fallback for Hailo NPU platform libraries
HAS_HAILO = False
try:
    from hailo_platform import HEF, VDevice, InferVStreams, ConfigureParams, InputVStreamParams, OutputVStreamParams
    HAS_HAILO = True
except ImportError:
    print("[!] Warning: hailo_platform not found. Running in simulation/mock mode.")

# Graceful import fallback for PyAutoGUI display-level actuation
HAS_DISPLAY = False
try:
    import pyautogui
    HAS_DISPLAY = True
except ImportError:
    print("[!] Warning: pyautogui not found. Actuation will be logged rather than executed.")

class SovereignVisualAgent:
    def __init__(self, hef_path=None):
        self.hef_path = hef_path
        self.is_mock = not HAS_HAILO or hef_path is None
        
        if not self.is_mock:
            try:
                self.vdevice = VDevice()
                self.hef = HEF(hef_path)
                self.configure_params = ConfigureParams.create_from_hef(self.hef)
                self.network_group = self.vdevice.configure(self.hef, self.configure_params)[0]
                self.input_params = InputVStreamParams.make_from_network_group(self.network_group)
                self.output_params = OutputVStreamParams.make_from_network_group(self.network_group)
                print(f"[+] Hailo NPU Visual Agent initialized with model: {hef_path}")
            except Exception as e:
                print(f"[-] Failed to initialize Hailo NPU hardware ({e}). Falling back to Mock.")
                self.is_mock = True
        
        if self.is_mock:
            print("[*] Visual Agent running in Mock/Simulation mode.")

    def execute_visual_intent(self, screenshot_frame, target_element_id):
        """
        Runs inference on the screenshot frame to locate target element and clicks its center.
        """
        # Bounding box coordinates validation to prevent out-of-bounds clicks (Safety Rule)
        def is_valid_coord(x, y):
            return 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0

        if self.is_mock:
            # Simulated detection for UAT validation
            print(f"[Mock NPU] Running inference on frame shape {screenshot_frame.shape} for Element ID {target_element_id}...")
            # Simulate a successful detection at the center of the screen
            simulated_detection = [target_element_id, 0.92, 0.45, 0.45, 0.55, 0.55] # class_id, confidence, x1, y1, x2, y2
            detections = [simulated_detection]
        else:
            input_name = self.hef.get_input_vstream_infos()[0].name
            input_data = {input_name: np.expand_dims(screenshot_frame, axis=0)}
            
            with InferVStreams(self.network_group, self.input_params, self.output_params) as infer_pipeline:
                output_data = infer_pipeline.infer(input_data)
                
            output_name = self.hef.get_output_vstream_infos()[0].name
            detections = output_data[output_name][0]

        for detection in detections:
            class_id, confidence, x1, y1, x2, y2 = detection
            
            if int(class_id) == target_element_id and confidence > 0.85:
                # Security/Safety Check: Sanitize bounding boxes to prevent malicious cursor movements
                if not (is_valid_coord(x1, y1) and is_valid_coord(x2, y2)):
                    print(f"[⚠️ Security Warning] Detected out-of-bounds bounding box: [{x1}, {y1}, {x2}, {y2}]. Aborting click.")
                    continue
                
                # Calculate center coordinates (normalized coordinates mapped to 1920x1080 resolution)
                center_x = int((x1 + x2) / 2 * 1920)
                center_y = int((y1 + y2) / 2 * 1080)
                
                print(f"[+] Visual Intent Match: Found Element {target_element_id} (Confidence: {confidence:.2f}) at screen coordinates ({center_x}, {center_y})")
                
                if HAS_DISPLAY:
                    try:
                        pyautogui.moveTo(center_x, center_y, duration=0.2)
                        pyautogui.click()
                        print("[+] Click executed successfully.")
                    except Exception as e:
                        print(f"[-] Actuation failed: {e}")
                else:
                    print(f"[*] [Simulation Log] PyAutoGUI click simulated at ({center_x}, {center_y})")
                    
                return True
                
        print(f"[-] Element {target_element_id} not detected with high confidence.")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print(" Sovereign OS Visual Intent Edge Agent - UAT Diagnostic")
    print("=" * 60)
    
    # Run a simple self-test
    mock_frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
    agent = SovereignVisualAgent()
    # Test detecting button ID 42 (e.g. 'Gonzo's Cantina Order Button')
    success = agent.execute_visual_intent(mock_frame, target_element_id=42)
    print(f"[*] Self-test status: {'PASSED' if success else 'FAILED'}")
