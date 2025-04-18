# McMaster Scraper

A web scraping tool designed to extract data from McMaster-Carr's website using Selenium and MongoDB for data storage.

## Features

- Automated web scraping with Selenium and undetected-chromedriver
- Secure environment-based configuration
- MongoDB integration for data storage
- Robust error handling and logging
- Modern web automation capabilities

## Prerequisites

- Python 3.8+
- Chrome browser
- MongoDB database

## Installation

1. Clone the repository:
```bash
git clone 
cd mcmaster-scraper
```

2. Create a virtual environment and activate it:
```bash
python -m venv myvenv
source myvenv/bin/activate  # On Windows: myvenv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit the `.env` file with your credentials:
```
CRED_EMAIL=your_email@example.com
CRED_PASS=your_password
DB_NAME=your_database_name
COLLECTION_NAME=your_collection_name
```

## Usage

1. Run the main script:
```bash
python main.py
```

The scraper will:
1. Launch Chrome browser
2. Navigate to McMaster-Carr website
3. Log in using provided credentials
4. Scrape the desired data
5. Store results in MongoDB

## Project Structure

```
mcmaster-scraper/
├── .env                 # Environment variables
├── .env.example        # Example environment file
├── requirements.txt     # Project dependencies
├── src/
│   ├── __init__.py
│   ├── config/         # Configuration files
│   ├── database/       # Database related code
│   └── scraper/        # Scraper implementation
├── main.py             # Main entry point
└── mcmaster_scraper.log # Application logs
```

## Dependencies

The project uses several key libraries:

- `selenium`: For web automation
- `undetected-chromedriver`: For bypassing bot detection
- `pymongo`: For MongoDB integration
- `beautifulsoup4`: For HTML parsing
- `numpy` and `pandas`: For data processing

## Logging

The application logs are stored in `mcmaster_scraper.log`. The logging is configured to output both to file and console.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the repository or contact the maintainers.