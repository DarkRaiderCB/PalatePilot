# PalatePilot

PalatePilot is a Python-based AI application designed to generate food tours on basis of location and weather. This project demonstrates modular design, API integration, and a user-friendly interface for seamless interaction.

Framework used: [Julep](https://github.com/julep-ai/julep)

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)

---

## Features

- Modular codebase for easy maintenance and extension
- Integration with external APIs (e.g., Julep API via `julep_client.py`)
- Command-line and UI interface (see `main.py` and `final-ui.py` respectively)
- Utility functions for common tasks (see `tools.py`)
- [Add more features as relevant to your project]

---

## Installation

### Prerequisites

- Python 3.12
- uv package manager (optional, but recommended)

### Steps

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/PalatePilot.git
   cd PalatePilot
   ```

2. **Create a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   Or, if using `uv`:
   ```bash
   uv sync
   ```

---

## Usage

### Running the Main Application

```bash
python main.py
```

### (OR) If using the UI

```bash
python final-ui.py
```

---

## Project Structure

```
PalatePilot/
│
├── final-ui.py         # User interface script
├── julep_client.py     # Julep API client
├── main.py             # Main entry point
├── tools.py            # Utility functions
├── pyproject.toml      # Project metadata and dependencies
├── uv.lock             # Lock file for dependencies
└── README.md           # Project documentation
```

---

Thank you for visiting!
