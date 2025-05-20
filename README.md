# kroketas
kroketas is a An kroketas is a AI-powered wrapper around SQLMap that makes SQL injection testing more accessible and automated
## Features

- AI-assisted SQL injection testing
- Automated result analysis and next step suggestions
- User-friendly output and reporting
- **NEW: Adaptive step-by-step testing with DBMS-specific optimizations and WAF bypass**

## Requirements

- Python 3
- SQLMap
- Required Python packages (see requirements.txt)

## Installation

1. Clone this repository:
```bash

cd kroketas
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Make sure SQLMap is available in the `sqlmap` directory or add it:
```bash
git clone https://github.com/sqlmapproject/sqlmap.git
```

## Usage

### Create Env

Create a `.env` file in the root directory with the following variables:

```bash
# Required
GROQ_API_KEY=your_groq_api_key
```

You can get a Groq API key by signing up at [https://console.groq.com](https://console.groq.com).

### Standard Mode

Run the assistant in standard mode:

```bash
python run.py
```

### Adaptive Testing Mode

Run the assistant in adaptive step-by-step testing mode:

```bash
python run.py --adaptive
```

The adaptive mode will:

1. **Initial Target Assessment** - Check if the target is vulnerable to SQL injection
2. **DBMS Identification** - Identify the database management system type
3. **DBMS-Specific Optimization** - Tailored attack based on detected DBMS:
   - MySQL: Extract databases and tables
   - MSSQL: Try to gain OS shell access
   - Oracle: Use specialized Oracle techniques
   - PostgreSQL: Customized PostgreSQL attack vectors
4. **Adaptive WAF Bypass** - Dynamically select tamper scripts based on WAF detection
5. **Data Extraction** - Extract sensitive information from databases
6. **Alternative Input Testing** - Test POST parameters, cookies, and headers

## Examples

![demo](./sqlmap.gif)

### Testing a vulnerable web application

```bash
python run.py --adaptive
# Enter target URL: http://testphp.vulnweb.com/artists.php?artist=1
```

### Testing with increased timeout

```bash
python run.py --adaptive
# Enter target URL: http://example.com/page.php?id=1
# Enter timeout in seconds: 300
```

### Example output
```plaintext
success: True
partial: True
message: Found databases but unable to enumerate tables. The database might be empty or protected.
databases_found: ['acuart', 'information_schema']
