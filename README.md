# S3 File Manager

A web-based file manager built with **FastAPI** and **Supabase Storage**, allowing users to manage buckets, folders, and files through a user-friendly interface.

## Features

- **Folder Management**: Create, delete, and navigate folders.
- **File Management**: Upload, download, move, copy, and delete files.
- **Path Display**: Always know your current location in the bucket/folder hierarchy.

## Tech Stack

- **Backend**: FastAPI, Python
- **Storage**: Supabase Storage
- **Frontend**: HTML, CSS, JavaScript

## Installation

1.**Set up Python environment**

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2.**Configure environment variables**

Create a .env file:

```bash
SUPABASE_URL=<your-supabase-url>
SUPABASE_KEY=<your-supabase-service-role-key>
```

3.**Run the FastAPI server**

```bash
python main.py
```

4.**Open the frontend**

Open index.html in your browser (on port :5500)

## Project Structure

```bash
.
├──FRONTEND
    ├── index.html
    ├── styles.css
    └── script.js
├── main.py               # FastAPI backend
├── requirements.txt      # Dependencies
├── .env                  # Environment variables
├── .env.sample
└── .gitignore
```

## Usage

- Click on a bucket to enter it.

- Use the New Folder or Upload File buttons to add content.

- Click the menu(⋮) on files/folders to access Download, Move, Copy, Delete actions.

- Navigate back using the Back button.

