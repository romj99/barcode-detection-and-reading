from PIL import Image, ImageDraw2
from pyzbar.pyzbar import decode


def get_crops(image: Image.Image, results, expand_percent: float=5):
    crops = []
    for result in results:
        boxes = result.boxes.xyxy.cpu().numpy()
        confidences = result.boxes.conf.cpu().numpy()

        for box, confidence in zip(boxes, confidences):
            x1, y1, x2, y2 = map(int, box)
            
            width = x2 - x1
            height = y2 - y1
            
            expand_x = int(width * (expand_percent / 100))
            expand_y = int(height * (expand_percent / 100))
            
            x1_expanded = max(x1 - expand_x, 0)
            y1_expanded = max(y1 - expand_y, 0)
            x2_expanded = x2 + expand_x
            y2_expanded = y2 + expand_y
            
            crop = image.crop((x1_expanded, y1_expanded, x2_expanded, y2_expanded))
            crops.append(crop)

    return crops

def read_barcode(image: Image.Image):
    decoded_objects = decode(image)
    if not decoded_objects:
        return None
    barcode_data = decoded_objects[0].data.decode("utf-8")
    barcode_type = decoded_objects[0].type

    return {"barcode":barcode_data, "barcode_type": barcode_type}


