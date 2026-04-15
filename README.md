# PDF Table Reader

A local desktop app that lets you draw a box around any table in a PDF and extract it into an editable spreadsheet (CSV). Everything runs on your own computer — no internet connection required, no accounts, no uploads.

---

## What it does

1. You open a PDF in the app
2. You draw a rectangle around a table on the page
3. The app reads the table using OCR (optical character recognition)
4. You review and edit the extracted data
5. You save it as a CSV file you can open in Excel or Google Sheets

---

## Before you begin

You will need a few free tools installed on your computer. Don't worry — this guide walks through each one.

**You'll need:**
- A Mac or Windows PC (macOS and Windows 10/11 are both supported)
- An internet connection for the initial setup

---

## Step 1 — Open a terminal

You'll be typing a few commands during setup. Here's how to open the right app on each system.

**macOS**

Press `Command + Space`, type "Terminal", and press Enter.

**Windows**

Press `Win + X` and choose **Windows PowerShell** (or **Terminal** on Windows 11). You can also search for "PowerShell" from the Start menu. All Windows commands in this guide are written for PowerShell.

---

## Step 2 — Install system tools (poppler and Tesseract)

These two tools are required by the app:

- **poppler** — lets the app read and display PDF pages
- **tesseract** — the OCR engine that reads text from images

**macOS**

First, install Homebrew if you don't already have it. Homebrew is a tool that makes it easy to install software on a Mac. Paste this into Terminal and press Enter:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

It will ask for your Mac password. Type it in (you won't see the characters as you type — that's normal) and press Enter. This may take a few minutes.

> **Note:** If it says Homebrew is already installed, that's fine — move on.

Then install both tools with one command:

```
brew install poppler tesseract
```

**Windows**

Windows 10 and 11 include **winget**, a built-in package manager. Run these commands one at a time in PowerShell:

```
winget install UB-Mannheim.TesseractOCR
```

```
winget install oscarblancartegomez.poppler
```

> **Note:** After installing Tesseract, you may need to add it to your PATH. The installer will prompt you — check the box that says "Add Tesseract to PATH" if it appears. If you miss it, search "Edit the system environment variables" in the Start menu, click **Environment Variables**, and add the Tesseract install folder (usually `C:\Program Files\Tesseract-OCR`) to the **Path** variable under System Variables. Then close and reopen PowerShell.

> **Alternative (Chocolatey users):** If you use Chocolatey instead of winget, run `choco install tesseract` and `choco install poppler`.

> **Poppler manual install:** If winget doesn't find the poppler package, download a pre-built Windows release from https://github.com/osresearch/poppler-windows/releases, unzip it, and add the `bin\` folder inside to your PATH using the same steps described above for Tesseract.

---

## Step 3 — Install Python

**macOS**

Check if Python is already installed:

```
python3 --version
```

If you see something like `Python 3.11.x` or higher, you're good. If not, install it:

```
brew install python
```

**Windows**

Check if Python is already installed:

```
python --version
```

If you see `Python 3.11.x` or higher, you're good. If not, install it with winget:

```
winget install Python.Python.3
```

Or download the installer directly from https://www.python.org/downloads/. During installation, check the box that says **"Add Python to PATH"** before clicking Install.

---

## Step 4 — Download this project from GitHub

You have two options:

### Option A — Download as a ZIP (easiest)

1. Go to the GitHub page for this project
2. Click the green **"Code"** button near the top right
3. Click **"Download ZIP"**
4. Once downloaded, double-click the ZIP file to unzip it
5. Move the unzipped folder somewhere easy to find, like your Desktop or Documents

### Option B — Use Git (if you have it installed)

```
git clone https://github.com/rajarajcic/pdf-table-reader-app.git
```

---

## Step 5 — Open the project folder in your terminal

Navigate into the project folder you downloaded. If you put it on your Desktop:

**macOS**

```
cd ~/Desktop/pdf-table-reader-app
```

You can also type `cd ` (with a space after it) and drag the folder from Finder into the Terminal window — it will fill in the path automatically.

**Windows**

```
cd "$HOME\Desktop\pdf-table-reader-app"
```

Adjust the path if you placed the folder somewhere else. You can also type `cd ` followed by the folder path. In File Explorer, you can copy the path from the address bar at the top.

---

## Step 6 — Install Python dependencies

Run this command to install all the Python packages the app needs. This works the same on both systems, though the exact command may vary slightly:

**macOS**

```
pip3 install -r requirements.txt
```

**Windows**

```
pip install -r requirements.txt
```

> **Note:** On some Windows setups `pip3` also works. If one doesn't work, try the other.

This will download and install several packages. It may take a minute or two.

---

## Step 7 — One-time setup (skip the email prompt)

The first time you run a Streamlit app, it asks for your email. Run the commands below to skip this. You only need to do this once.

**macOS**

```
mkdir -p ~/.streamlit
```

```
echo '[general]
email = ""' > ~/.streamlit/credentials.toml
```

**Windows**

```
mkdir "$HOME\.streamlit" -Force
```

```
Set-Content "$HOME\.streamlit\credentials.toml" "[general]`nemail = `"`""
```

---

## Step 8 — Launch the app

Run this command from inside the project folder:

**macOS**

```
python3 -m streamlit run app.py
```

**Windows**

```
python -m streamlit run app.py
```

The app will open automatically in your web browser at `http://localhost:8501`. If it doesn't open on its own, copy that address and paste it into your browser.

---

## Using the app

### Loading a PDF
- Place any PDF you want to work with inside the project folder
- In the sidebar on the left, use the dropdown under **"Load PDF"** to select it

### Extracting a table
1. Navigate to the page that contains your table using the **Prev / Next** buttons or the page number box
2. Click and drag on the PDF to draw a rectangle around the table
3. Click the red **"Extract Table"** button below the PDF
4. The extracted data will appear in the panel on the right

### Reviewing and editing
- The **Review** tab highlights potential OCR errors in red and blank cells in amber
- The **Edit & Save** tab lets you click any cell to correct it

### Saving as CSV
1. Type a name for the table in the **"Table name"** field
2. Click **"Save as CSV"**
3. The file will be saved to the `output/` folder inside the project directory
4. You can open it in Excel, Google Sheets, or any spreadsheet app

---

## Tips

- The app works best with scanned PDFs that have clear, well-formatted tables
- If the extraction looks wrong, try drawing a tighter box around just the table (excluding headers or footnotes outside the table)
- You can extract multiple tables from the same PDF — each one saves as a separate CSV
- Your work is automatically saved to a session file so you can pick up where you left off

---

## Stopping the app

To stop the app, go back to your terminal and press `Control + C`.

To start it again later, just repeat Step 8.

---

## Troubleshooting

**"command not found: brew" (macOS)**
Homebrew didn't install correctly. Try Step 2 again, or visit https://brew.sh for help.

**"winget is not recognized" (Windows)**
winget is built into Windows 10 (version 1809 or later) and Windows 11. If it's missing, update Windows through Settings, or install the App Installer package from the Microsoft Store.

**"tesseract is not recognized" or "poppler not found" (Windows)**
Tesseract or poppler isn't on your PATH. See the PATH setup notes in Step 2.

**"No module named streamlit" or similar errors**
Make sure you ran the pip install command from inside the project folder (Step 6). On Windows, also make sure Python was added to PATH during installation.

**The app opens but no PDFs appear in the dropdown**
Make sure your PDF file is inside the project folder (the same folder as `app.py`).

**"No table detected" after drawing a box**
Try drawing a larger or more precise rectangle. The table needs to be clearly visible and well-bounded.
