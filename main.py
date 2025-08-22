from fastapi import FastAPI, UploadFile, Form, Query, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from typing import List, Optional, Literal
from pydantic import BaseModel
from supabase import create_client, Client
import os
from dotenv import load_dotenv 
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import unquote


load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Supabase File Manager API",
    description="A file management API for Supabase Storage")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500", 
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class FileUploadResponse(BaseModel):
    message: str
    path: str

class FolderCreateResponse(BaseModel):
    message: str
    path: str

class DeleteResponse(BaseModel):
    message: str

class CopyMoveRequest(BaseModel):
    path: str
    new_path: str

class CopyMoveResponse(BaseModel):
    message: str
    warning: Optional[str] = None
    error: Optional[str] = None

class DownloadResponse(BaseModel):
    download_url: str


# Pydantic model for response
class StorageItem(BaseModel):
    name: str
    type: Literal["file", "folder"]
    path: str
    size: Optional[int] = None


@app.get("/", response_model=List[StorageItem])
async def list_storage(
    bucket: str = Query("Bucket1"),
    folder: str = Query("")
):
    try:
        # Options for Supabase list query
        list_options = {"limit": 100, "offset": 0}
        if folder:
            list_options["prefix"] = folder

        # Fetch data from Supabase
        res = supabase.storage.from_(bucket).list(folder, list_options)

        # Normalize response
        if isinstance(res, list):
            data = res
        elif isinstance(res, dict) and "data" in res:
            data = res["data"]
        else:
            data = []

        # Process contents
        contents: List[StorageItem] = []
        for item in data:
            if not item or not isinstance(item, dict):
                continue

            name = item.get("name", "")
            if not name or name == folder:
                continue

            if item.get("metadata") is None:
                contents.append(StorageItem(
                    name=name,
                    type="folder",
                    path=name
                ))
            else:
                contents.append(StorageItem(
                    name=name,
                    type="file",
                    path=name,
                    size=item.get("metadata", {}).get("size", 0)
                ))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching contents: {str(e)}")

    return contents


@app.post("/upload/{bucket}", response_model=FileUploadResponse)
async def upload_file(bucket: str, file: UploadFile, folder: Optional[str] = Form("")):
    if not file or file.filename == "":
        return JSONResponse({"error": "No file selected"}, status_code=400)

    try:
        file_path = f"{folder.rstrip('/')}/{file.filename}" if folder else file.filename
        content = await file.read()
        res = supabase.storage.from_(bucket).upload(file_path, content)

        if isinstance(res, dict) and res.get("error"):
            return JSONResponse({"error": res["error"]["message"]}, status_code=500)

        return {"message": f"File '{file.filename}' uploaded successfully", "path": file_path}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/delete_file/{bucket}", response_model=DeleteResponse)
async def delete_file(bucket: str, path: str = Query(...)):
    try:
        res = supabase.storage.from_(bucket).remove([path])

        if isinstance(res, dict) and res.get("error"):
            return JSONResponse({"error": res["error"]["message"]}, status_code=500)

        return {"message": f"File '{path}' deleted successfully"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/create_folder/{bucket}", response_model=FolderCreateResponse)
async def create_folder(bucket: str, folder_name: str = Form(...), parent_folder: Optional[str] = Form("")):
    if not folder_name:
        return JSONResponse({"error": "Folder name is required"}, status_code=400)

    try:
        folder_path = f"{parent_folder.rstrip('/')}/{folder_name}/" if parent_folder else f"{folder_name}/"
        res = supabase.storage.from_(bucket).upload(f"{folder_path}.keep", b"")

        if isinstance(res, dict) and res.get("error"):
            return JSONResponse({"error": res["error"]["message"]}, status_code=500)

        return {"message": f"Folder '{folder_name}' created successfully", "path": folder_path}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/delete_folder/{bucket}", response_model=DeleteResponse)
async def delete_folder(bucket: str, path: str = Query(...)):
    try:
        res = supabase.storage.from_(bucket).list(path, {"limit": 1000})
        files_to_delete = []

        if isinstance(res, list):
            files_to_delete = [f"{path}/{item['name']}" for item in res if isinstance(item, dict) and item.get("name")]
        elif isinstance(res, dict) and res.get("data"):
            files_to_delete = [f"{path}/{item['name']}" for item in res["data"] if isinstance(item, dict) and item.get("name")]

        files_to_delete.append(f"{path}/.keep")

        if files_to_delete:
            delete_res = supabase.storage.from_(bucket).remove(files_to_delete)
            if isinstance(delete_res, dict) and delete_res.get("error"):
                return JSONResponse({"error": delete_res["error"]["message"]}, status_code=500)

            return {"message": f"Folder '{path}' deleted successfully"}
        else:
            return JSONResponse({"error": "Folder is empty or does not exist"}, status_code=404)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/copy_file/{bucket}", response_model=CopyMoveResponse)
async def copy_file(bucket: str, request: CopyMoveRequest):
    try:
        data = supabase.storage.from_(bucket).download(request.path)
        if isinstance(data, dict) and data.get("error"):
            return JSONResponse({"error": data["error"]["message"]}, status_code=500)

        res = supabase.storage.from_(bucket).upload(request.new_path, data)
        if isinstance(res, dict) and res.get("error"):
            return JSONResponse({"error": res["error"]["message"]}, status_code=500)

        return {"message": f"File copied to '{request.new_path}' successfully"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/move_file/{bucket}", response_model=CopyMoveResponse)
async def move_file(bucket: str, request: CopyMoveRequest):
    try:
        data = supabase.storage.from_(bucket).download(request.path)
        if isinstance(data, dict) and data.get("error"):
            return JSONResponse({"error": data["error"]["message"]}, status_code=500)

        res_upload = supabase.storage.from_(bucket).upload(request.new_path, data)
        if isinstance(res_upload, dict) and res_upload.get("error"):
            return JSONResponse({"error": res_upload["error"]["message"]}, status_code=500)

        res_delete = supabase.storage.from_(bucket).remove([request.path])
        if isinstance(res_delete, dict) and res_delete.get("error"):
            return {"message": f"File moved to '{request.new_path}' successfully", "warning": "Failed to delete original", "error": res_delete["error"]["message"]}

        return {"message": f"File moved to '{request.new_path}' successfully"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/download/{bucket}", response_model=DownloadResponse)
async def download_file(bucket: str, path: str = Query(...)):
    try:
        res = supabase.storage.from_(bucket).create_signed_url(path, 3600)
        if isinstance(res, dict) and res.get("error"):
            return JSONResponse({"error": res["error"]["message"]}, status_code=500)

        download_url = res.get("signedURL") if isinstance(res, dict) else None
        if download_url:
            return {"download_url": download_url}
        else:
            return JSONResponse({"error": "Could not generate download link"}, status_code=500)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/create_bucket")
async def create_bucket(bucket_name: str = Form(...)):
    bucket_name = bucket_name.strip()
    if not bucket_name:
        raise HTTPException(status_code=400, detail="Bucket name is required.")

    try:
        res = supabase.storage.create_bucket(bucket_name, options={"public": True})

        # Handle API error response
        if isinstance(res, dict) and res.get("error"):
            raise HTTPException(status_code=500, detail=res["error"]["message"])

        # Supabase returns {"data": {...}}
        bucket = res.get("data") if isinstance(res, dict) else res

        return {
            "message": f"Bucket '{bucket_name}' created successfully",
            "bucket": bucket
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating bucket: {str(e)}")


@app.delete("/delete_bucket/{bucket_name}")
async def delete_bucket(bucket_name: str):
    bucket_name = bucket_name.strip()
    if not bucket_name:
        raise HTTPException(status_code=400, detail="Bucket name is required.")

    try:
        res = supabase.storage.delete_bucket(bucket_name)

        if isinstance(res, dict) and res.get("error"):
            raise HTTPException(status_code=500, detail=res["error"]["message"])

        return {"message": f"Bucket '{bucket_name}' deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting bucket: {str(e)}")


@app.get("/list_buckets")
async def list_buckets():
    try:
        res = supabase.storage.list_buckets()

        if isinstance(res, dict) and res.get("error"):
            raise HTTPException(status_code=500, detail=res["error"]["message"])

        # Some clients return {"data": [...]}, some directly return list
        buckets = res.get("data") if isinstance(res, dict) else res

        return {"buckets": buckets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing buckets: {str(e)}")

@app.get("/health/")
def check():
    return {"message": "This is a FastAPI application. All good!"}

if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, log_level="info", reload=True)