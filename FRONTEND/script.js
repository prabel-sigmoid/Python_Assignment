const API_URL = "http://127.0.0.1:8000";
let currentBucket = null;
let currentFolder = "";

async function init() {
    currentBucket = null;
    document.getElementById("actions").style.display = "none";
    updatePathDisplay();
    let res = await fetch(`${API_URL}/list_buckets`);
    let data = await res.json();
    renderGrid(data.buckets.map(b => ({
        name: b.name, type: "bucket"
    })));
}

function updatePathDisplay() {
    let pathEl = document.getElementById("pathDisplay");
    if (!currentBucket) pathEl.textContent = "/";
    else pathEl.textContent = "/" + currentBucket + (currentFolder ? "/" + currentFolder : "");
}

function renderGrid(items) {
    let grid = document.getElementById("grid");
    grid.innerHTML = "";
    items.forEach(item => {
        let card = document.createElement("div");
        card.className = "card";

        card.innerHTML = `
            <button class="menu-btn">⋮</button>
            <div class="dropdown" style="text-align: right; padding-right: 8px;">
                ${item.type === "bucket"
                ? `<button onclick="deleteBucket('${item.name}')">🗑 Delete Bucket</button>`
                : `
                    ${item.type === "file"
                    ? `<button onclick="downloadFile('${item.path}')">⬇ Download</button>`
                    : ""
                }
                    <button onclick="deleteItem('${item.path}', '${item.type}')">🗑 Delete</button>
                    <button onclick="moveItem('${item.path}')">📂 Move</button>
                    <button onclick="copyItem('${item.path}')">📑 Copy</button>
                    `
            }
            </div>
            <div class="icon">${item.type === "bucket" ? "📦" : item.type === "folder" ? "📁" : "📄"}</div>
            <div>${item.name}</div>
            `;

        // Clicking the 3-dot menu toggles the dropdown
        const menuBtn = card.querySelector(".menu-btn");
        const dropdown = card.querySelector(".dropdown");

        menuBtn.addEventListener("click", (e) => {
            e.stopPropagation(); // Prevent card click
            // Close other open dropdowns
            document.querySelectorAll(".dropdown").forEach(d => {
                if (d !== dropdown) d.style.display = "none";
            });
            // Toggle this dropdown
            dropdown.style.display = dropdown.style.display === "block" ? "none" : "block";
        });

        // Clicking outside closes any open dropdown
        document.addEventListener("click", () => {
            dropdown.style.display = "none";
        });

        // Card click for navigation
        card.addEventListener("click", (e) => {
            if (e.target === menuBtn || e.target.closest(".dropdown")) return;
            if (item.type === "bucket") enterBucket(item.name);
            else if (item.type === "folder") enterFolder(item.name);
        });

        grid.appendChild(card);
    });
}

async function enterBucket(bucket) {
    currentBucket = bucket;
    currentFolder = "";
    document.getElementById("actions").style.display = "block";
    updatePathDisplay();
    listFiles();
}

async function enterFolder(folder) {
    currentFolder = currentFolder ? `${currentFolder}/${folder}` : folder;
    updatePathDisplay();
    listFiles();
}

async function listFiles() {
    let res = await fetch(`${API_URL}/?bucket=${currentBucket}&folder=${currentFolder}`);
    let data = await res.json();
    renderGrid(
        data.map(item => ({
            ...item,
            path: item.type === "file"
                ? (currentFolder ? `${currentFolder}/${item.name}` : item.name)
                : item.name
        }))
    );
}

function goBack() {
    if (currentFolder) {
        let parts = currentFolder.split("/");
        parts.pop();
        currentFolder = parts.join("/");
        updatePathDisplay();
        listFiles();
    } else if (currentBucket) {
        init();
    }
}

async function uploadFile(event) {
    let file = event.target.files[0];
    let formData = new FormData();
    formData.append("file", file);
    formData.append("folder", currentFolder);
    let res = await fetch(`${API_URL}/upload/${currentBucket}`, {
        method: "POST",
        body: formData
    });
    let data = await res.json();
    alert(data.message || JSON.stringify(data));
    listFiles();
}

async function createFolder() {
    let name = prompt("Enter folder name:");
    if (!name) return;
    let formData = new FormData();
    formData.append("folder_name", name);
    formData.append("parent_folder", currentFolder);
    let res = await fetch(`${API_URL}/create_folder/${currentBucket}`, {
        method: "POST",
        body: formData
    });
    let data = await res.json();
    alert(data.message || JSON.stringify(data));
    listFiles();
}

async function deleteItem(path, type) {
    if (!confirm(`Delete ${type}: ${path}?`)) return;
    let url = type === "file"
        ? `${API_URL}/delete_file/${currentBucket}?path=${encodeURIComponent(path)}`
        : `${API_URL}/delete_folder/${currentBucket}?path=${encodeURIComponent(path)}`;
    let res = await fetch(url, { method: "DELETE" });
    let data = await res.json();
    alert(data.message || JSON.stringify(data));
    listFiles();
}

async function downloadFile(filename) {
    let fullPath = currentFolder ? `${currentFolder}/${filename}` : filename;
    let res = await fetch(`${API_URL}/download/${currentBucket}?path=${encodeURIComponent(fullPath)}`);
    let data = await res.json();
    if (data.download_url) window.open(data.download_url, "_blank");
    else alert("Error: " + JSON.stringify(data));
}


async function downloadFile(path) {
    // path must include folder prefix like "demo1/Screenshot.png"
    let res = await fetch(`${API_URL}/download/${currentBucket}?path=${encodeURIComponent(path)}`);
    let data = await res.json();
    if (data.download_url) {
        window.open(data.download_url, "_blank");
    } else {
        alert("Error: " + JSON.stringify(data));
    }
}

function moveItem(path) {
    let newPath = prompt("Enter new path:", path);
    if (!newPath) return;
    fetch(`${API_URL}/move_file/${currentBucket}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path, new_path: newPath })
    }).then(r => r.json()).then(data => {
        alert(data.message || JSON.stringify(data));
        listFiles();
    });
}

function copyItem(path) {
    let newPath = prompt("Enter copy path:", path + "_copy");
    if (!newPath) return;
    fetch(`${API_URL}/copy_file/${currentBucket}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path, new_path: newPath })
    }).then(r => r.json()).then(data => {
        alert(data.message || JSON.stringify(data));
        listFiles();
    });
}

async function deleteBucket(bucketName) {
    if (!confirm(`Delete bucket: ${bucketName}? This will remove all files in it.`)) return;

    let res = await fetch(`${API_URL}/delete_bucket/${bucketName}`, {
        method: "DELETE"
    });

    let data = await res.json();
    let detail = data.detail;

    let match = detail.match(/'message': (.*)}/);

    if (match) {
        alert(match[1]);
    } else {
        alert(detail); // fallback
    }
    init(); // Refresh bucket list
}

init();