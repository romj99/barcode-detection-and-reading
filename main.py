from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from io import BytesIO
from PIL import Image
from functions import get_crops, read_barcode
import os
import zipfile
import json
import tempfile
import cv2

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = YOLO("./model/weights/best.pt")

@app.post("/predict/")
async def predict_image(
    file: UploadFile = File(...),
    threshold: float = Form(0.5),
    download_zip: bool = Form(False)
):
    try:
        # Read the uploaded image
        contents = await file.read()
        img = Image.open(BytesIO(contents))
        
        # YOLO model inference with confidence threshold
        results = model(img, conf=threshold)
        crops = get_crops(img, results)  # Get crop regions from the results
        
        response_data = []
        
        # Handle temp directory if ZIP download is requested
        if download_zip:
            temp_dir = tempfile.mkdtemp()

        # Process each crop and detect barcodes
        for i, crop in enumerate(crops):
            barcode = read_barcode(crop)
            
            # Add data to the response JSON
            response_data.append({
                "crop_number": i,
                "barcode_number": barcode["barcode"] if barcode else "No barcode detected",
                "barcode_type": barcode["barcode_type"] if barcode else None,
            })
            
            # Save crops if ZIP download is requested
            if download_zip:
                crop_path = os.path.join(temp_dir, f"crop_{i}.jpg")
                crop.save(crop_path, format="JPEG")
                
        # Generate ZIP file if download_zip is True
        if download_zip:
            # Save the labeled image
            labeled_image_array = results[0].plot() 
            if labeled_image_array.shape[2] == 3:  # Ensure it's a 3-channel image
                labeled_image_array = cv2.cvtColor(labeled_image_array, cv2.COLOR_BGR2RGB)
            labeled_image = Image.fromarray(labeled_image_array)
            labeled_image_path = os.path.join(temp_dir, "labeled_image.jpg")
            labeled_image.save(labeled_image_path, format="JPEG")
            
            # Save detected barcodes to JSON
            json_path = os.path.join(temp_dir, "barcodes.json")
            with open(json_path, "w") as json_file:
                json.dump(response_data, json_file)
                
            # Create ZIP file containing labeled image, crops, and JSON
            original_file_name = file.filename
            name_without_extension, _ = os.path.splitext(original_file_name)
            zip_file_name = f"{name_without_extension}_barcode_prediction.zip"
            zip_path = os.path.join(temp_dir, zip_file_name)

            with zipfile.ZipFile(zip_path, 'w') as zip_file:
                zip_file.write(labeled_image_path, os.path.basename(labeled_image_path))
                for i, _ in enumerate(crops):
                    crop_path = os.path.join(temp_dir, f"crop_{i}.jpg")
                    zip_file.write(crop_path, os.path.basename(crop_path))
                zip_file.write(json_path, os.path.basename(json_path))

            # Return the ZIP file as the response
            return FileResponse(zip_path, media_type='application/zip', filename=zip_file_name)
        
        # If no ZIP download requested, return the barcode data as JSON
        if response_data:
            return JSONResponse(response_data)
        else:
            return JSONResponse({"error": "No barcode detected."}, status_code=200)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
