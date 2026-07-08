import os
import cv2
import glob
import pyperclip
import pytesseract
import numpy as np

tesseract_cmd_global = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
tesseract_cmd_local = r'C:\Users\User\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

if os.path.exists(tesseract_cmd_global):
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_global
elif os.path.exists(tesseract_cmd_local):
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_local

def process_images():
    debug_dir = r"C:\TalentOpsAI\teams_extractor\output\debug"
    files = glob.glob(os.path.join(debug_dir, "*.png"))
    # Sort files correctly if they have numbers
    files.sort()
    
    global_msg_counter = 0
    final_messages = []
    
    for fpath in files:
        img = cv2.imread(fpath)
        if img is None: continue
        
        img_h, img_w = img.shape[:2]
        
        # In debug images, the messages are already surrounded by colored rectangles (Red, Green, Blue, etc.)
        # We can find these rectangles by masking out the colors.
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Mask for Green, Red, and Orange
        mask_green = cv2.inRange(hsv, np.array([40, 100, 100]), np.array([80, 255, 255]))
        
        # Red can wrap around in HSV
        mask_red1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
        mask_red2 = cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
        
        # Orange/Yellow
        mask_orange = cv2.inRange(hsv, np.array([11, 100, 100]), np.array([30, 255, 255]))
        
        # Combine masks
        combined_mask = cv2.bitwise_or(mask_green, mask_red1)
        combined_mask = cv2.bitwise_or(combined_mask, mask_red2)
        combined_mask = cv2.bitwise_or(combined_mask, mask_orange)
        
        # The boxes are just lines, so let's dilate slightly to close them
        kernel = np.ones((5,5), np.uint8)
        dilated_mask = cv2.dilate(combined_mask, kernel, iterations=2)
        
        contours, hierarchy = cv2.findContours(dilated_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        bounding_boxes = []
        raw_boxes = 0
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w > 80 and h > 20:
                raw_boxes += 1
                
                # Ignore the giant border box that covers the whole screen
                if w >= img_w - 10 or h >= img_h - 10:
                    # print(f"Skipped giant box at y={y}, w={w}, h={h}")
                    continue
                    
                # CONDITION: Skip messages that are cut off at the top or bottom of the screen!
                if y <= 15 or y + h >= img_h - 15:
                    # print(f"Skipped cut-off box at y={y}, h={h} (img_h={img_h})")
                    continue
                    
                bounding_boxes.append((x, y, w, h))
        print(f"File {os.path.basename(fpath)}: kept {len(bounding_boxes)} complete, inner boxes.")
                
        bounding_boxes = sorted(bounding_boxes, key=lambda b: b[1])
        
        for (x, y, w, h) in bounding_boxes:
            global_msg_counter += 1
            msg_id = f"{global_msg_counter:06d}"
            
            crop = img[y:y+h, x:x+w]
            text = pytesseract.image_to_string(crop).strip()
            
            if text:
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                compressed_text = "\n".join(lines)
                final_messages.append(f"[{msg_id}]\n{compressed_text}\n\n\n")
                
    output_str = "".join(final_messages)
    
    out_file = os.path.join(r"C:\TalentOpsAI\teams_extractor\output", "final_extracted_data.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(output_str.strip())
        
    try:
        pyperclip.copy(output_str.strip())
    except:
        pass # Ignore if clipboard fails in headless mode
        
    print(f"Successfully processed {len(files)} images.")
    print(f"Extracted {global_msg_counter} complete, non-cut-off messages.")
    print(f"Saved results to: {out_file}")

if __name__ == "__main__":
    process_images()
