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

- Python 3.8 or higher
- [Any other dependencies, e.g., pip, virtualenv]

### Steps

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/PalatePilot.git
   cd PalatePilot
   ```

2. **(Optional) Create a virtual environment:**

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

### Using the UI

```bash
python final-ui.py
```

### API Client

The `julep_client.py` module provides functions to interact with the Julep API. Import and use it in your scripts as needed.

### Tools

Utility functions are available in `tools.py` for common operations.

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
