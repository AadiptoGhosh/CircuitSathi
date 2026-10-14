# ⚡ CircuitSathi
### Local-First Open-Weight AI Assistant for Electronics Engineering

> **"Upload your component datasheet, ask an engineering question, and receive an evidence-grounded explanation with document references, component specifications, and actionable next steps."**

---

## 🌟 Overview & Product Vision

**CircuitSathi** is a local-first engineering companion built for Electronics & Communication Engineering (ECE) students, robotics builders, makers, embedded systems developers, and hardware prototyping teams. 

Unlike generic cloud chatbots, CircuitSathi runs **100% locally on your machine**. Sensitive circuit schematics, proprietary datasheets, and client project files never leave your computer or leak to external third-party cloud AI APIs.

### Target Users
- **Robotics & Embedded Developers**: Quick pinout lookups, PWM frequencies, and driver thermal calculations.
- **Electronics Engineering Students**: Step-by-step circuit analysis, resistor/voltage calculations, and theory.
- **Hardware Hackers & Prototypers**: Arduino, ESP32, and Raspberry Pi prototyping and Bill of Materials (BOM) budgeting.
- **Hardware Repair & Diagnostics**: Structured, safety-conscious troubleshooting for blown regulators, motor stall currents, and floating logic lines.

---

## 🛠️ Architecture & Technology Stack

| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Language & Environment** | Python 3.12 (managed via `uv`) | Core execution runtime |
| **User Interface** | Streamlit | Responsive, high-contrast engineering UI |
| **Local LLM Engine** | Ollama | Local open-weight model serving (`http://localhost:11434`) |
| **Default Model** | `gemma3:4b` *(fallback: `gemma3:1b`)* | Evidence-grounded generation & reasoning |
| **PDF Extraction** | PyMuPDF (`pymupdf`) | Page-accurate text extraction (1-indexed) |
| **OCR Fallback** | Tesseract OCR & `pytesseract` | Optical character recognition for scanned pages |
| **Dense Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | Fast, offline vector representation (unit normalized) |
| **Vector Database** | ChromaDB (`chromadb`) | Persistent local vector store with cosine distance |
| **Data Validation** | Pydantic v2 | Strictly validated BOM, Component, and Request schemas |
| **Accounting & Exports** | Pandas & OpenPyXL | Deterministic financial math and styled `.xlsx` / `.csv` |
| **Automated Testing** | Pytest | Unit, safety rule, RAG retrieval, and benchmark tests |

---

## 🚀 Key Features

### 💬 1. AI Engineering Chat (Feature A)
- Conversational interface adhering to strict SI unit standards.
- Grounded RAG mode: Answers cite exact source documents and pages `[Doc: <name>, Page: <num>]`.
- Expandable **Supporting Evidence Passages** drawer for transparent verification.
- Integrated deterministic quick calculators for **LED current-limiting resistors** and **Voltage Dividers**.
- Honest uncertainty: Acknowledges missing parameters instead of hallucinating values.

### 📄 2. Datasheet Assistant (Feature B)
- Ingests multiple technical PDFs.
- 1-indexed page preservation with overlapping chunking.
- Scanned page detection with automated Tesseract OCR fallback.
- Local ChromaDB vector indexing with document deduplication and complete deletion.
- Warning alerts for complex vector drawings and graphic pinout diagrams.

### 🔍 3. Component Explorer (Feature C)
- Vetted local component library for common components (e.g., `TB6612FNG`, `L298N`, `ESP32`, `LM7805`, `1N4007`).
- Displays Operating Voltage, Absolute Maximum Ratings, Continuous & Peak Current, Pin Configuration, Key Features, and Critical Safety Warnings.
- Never invents specifications; unverified fields are explicitly flagged as `"Not verified"`.
- User-extensible local JSON library.

### 📊 4. Bill of Materials (BOM) Generator (Feature D)
- Structured project BOM with components, quantities, purpose, and specifications.
- **Deterministic Python financial arithmetic**: Quantities and prices are calculated strictly in Python, never delegated to probabilistic model arithmetic.
- Unpriced items are marked as pending rather than hallucinating arbitrary prices.
- One-click export to:
  - 📊 Professional Styled Excel Workbook (`.xlsx`) with colored header banners and zebra stripes.
  - 📄 RFC-4180 standard CSV (`.csv`).

### 🛠️ 5. Guided Circuit Troubleshooting (Feature E)
- Structured diagnostic workflow combining:
  1. **Deterministic Safety Pre-Checks**:
     - SELV contact risk alerts (>50V DC / >30V AC RMS).
     - Inductive kickback warnings (mandatory flyback diodes for motors/relays).
     - High current trace heating warnings (>3A).
     - Logic-level mismatch detection (e.g., 5V output into 3.3V ESP32 GPIO).
     - Lithium battery thermal runaway and BMS requirements.
  2. **Datasheet Evidence Retrieval** on symptoms and part numbers.
  3. **Structured AI Diagnosis**: Ranked root causes, safe de-energized diagnostic checks, specific test probe locations, and expected measurements.

### 📸 6. Schematic & Image Inspector (Feature F)
- Upload circuit schematics, PCB drawings, or breadboard photos.
- Analyzed locally when paired with vision-capable open-weight models (e.g. Gemma 3 Multimodal / LLaVA).

---

## 📦 Windows PowerShell Installation & Setup

### Prerequisites
1. **Windows 10 / 11** with PowerShell.
2. **Git** for Windows.
3. **Ollama** installed ([ollama.com](https://ollama.com)).
4. **uv** package manager ([docs.astral.sh/uv](https://docs.astral.sh/uv)).

---

### Step 1: Clone Repository & Open PowerShell
```powershell
cd "c:\Users\Aadipto Ghosh\Desktop\Programming\Hacktoberfest 2026\Week 2 DEV\CircuitSathi"
```

### Step 2: Create Python 3.12 Virtual Environment
```powershell
uv venv --python 3.12 .venv
```

### Step 3: Install Dependencies
```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

### Step 4: Setup Ollama & Download Gemma 3 Model
Ensure Ollama is running in background or start it:
```powershell
ollama serve
```
In a new terminal window, pull the default Gemma 3 model:
```powershell
ollama pull gemma3:4b
```
*(Optional lightweight fallback for lower VRAM laptops:)*
```powershell
ollama pull gemma3:1b
```

### Step 5: Generate Sample Datasheets (Optional but recommended)
```powershell
.venv\Scripts\python.exe scripts\create_sample_datasheet.py
```

### Step 6: Launch CircuitSathi UI
```powershell
.venv\Scripts\streamlit.exe run app.py
```
Open your browser to: **`http://localhost:8501`**

---

## 🧪 Automated Testing & Evaluation Benchmark

CircuitSathi includes a full automated test suite and an authentic 20-question datasheet benchmark.

### Running the Test Suite
```powershell
.venv\Scripts\python.exe -m pytest -v -s
```

### Test Coverage Summary:
- **`tests/test_bom.py`**: Pydantic validation, negative quantity rejection, deterministic subtotal math, Excel `.xlsx` generation, CSV export.
- **`tests/test_safety.py`**: E12 standard resistor selection, decade rollover, LED resistor power dissipation, voltage divider loading, SELV overvoltage, inductive flyback, logic mismatch, LiPo battery checks.
- **`tests/test_pdf_ingest.py`**: PyMuPDF extraction, 1-indexed page preserving, sliding window chunking, empty and corrupted PDF rejection.
- **`tests/test_retrieval.py`**: Persistent ChromaDB indexing, semantic search, citation formatting, score thresholding, document deletion.
- **`tests/test_llm.py`**: Ollama status polling, download command generation, mock response handling, RAG prompt assembly.
- **`tests/test_evaluation.py`**: Evaluates 20 authentic engineering questions against public datasheets:
  - **Retrieval Hit Rate**: **90.0%** (18/20 questions)
  - **Exact Page Citation Match**: **100.0%** (20/20 questions)

---

## 🌐 Community Wisdom

In accordance with modern embedded engineering best practices:
- **Toshiba Application Note TB6612FNG**: Dual H-bridge power dissipation is dramatically superior to legacy bipolar L298N drivers due to low $R_{DS(on)}$ (0.5Ω vs 2.0V Darlington drop).
- **Texas Instruments Linear Power Management**: Always place input ($0.33\mu\text{F}$) and output ($0.1\mu\text{F}$) decoupling capacitors directly adjacent to linear regulator pins to prevent parasitic RF oscillation.
- **Espressif Hardware Design Guidelines**: ESP32 GPIO inputs are strictly 3.3V. Directly connecting 5V TTL outputs destroys internal protection diodes.

---

## ⚠️ Safety, Hardware & Legal Disclaimers

1. **Advisory Tool**: CircuitSathi provides engineering assistance and educational calculations. It does **not** certify electrical installations, high-voltage circuits, or life-critical medical/aerospace systems.
2. **De-energize Before Probing**: Always disconnect power before altering wiring or measuring continuity/resistance.
3. **Open-Weight License**: Gemma 3 is distributed by Google under the Gemma Terms of Use.
4. **Data Privacy**: Uploaded files and embeddings are stored strictly on your local disk (`data/uploads` and `data/chroma`). Use the **Purge All Data** button in Settings for instant privacy wipes.

---

## 🗺️ Next 3 Highest-Priority Enhancements

1. **KiCad Schematic Netlist Parser**: Direct integration with `.kicad_sch` files for deterministic automated ERC (Electrical Rules Checking).
2. **Interactive Pinout Visualizer**: SVG-based dynamic pinout diagrams with clickable pin functions and voltage level color-coding.
3. **Direct Octopart / Digikey Local Price Caching**: Optional offline-cacheable API connector for verified real-time supplier stock and pricing in INR/USD.
