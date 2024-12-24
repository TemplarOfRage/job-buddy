# ApplyAI

🎯 AI-Powered Job Application Intelligence

## Overview

ApplyAI is an intelligent job application assistant that helps users optimize their job applications using AI analysis. The application provides smart job fit analysis, custom resume tailoring, and strategic insights to improve application success rates.

## Features

- 🔍 **Smart Job Fit Analysis**: AI-powered analysis of job posting requirements against your resume
- ✨ **Custom Resume Tailoring**: Get specific suggestions to optimize your resume for each application
- 💡 **Strategic Insights**: Receive detailed feedback on your application strategy
- 📝 **Application Assistance**: Help with custom application questions and follow-up actions
- 📊 **Analysis History**: Track and review past job analyses

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/applyai.git
cd applyai
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Add your Anthropic API key and other configurations

5. Initialize the database:
```bash
python -m app.database.init_db
```

## Usage

1. Start the application:
```bash
streamlit run app/main.py
```

2. Open your browser to `http://localhost:8501`

3. Register or log in to your account

4. Upload your resume(s) and start analyzing job postings

## Development

### Project Structure
```
applyai/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── pages/
│   ├── components/
│   ├── services/
│   ├── database/
│   └── utils/
├── tests/
├── requirements.txt
└── README.md
```

### Running Tests
```bash
pytest
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [Anthropic's Claude](https://anthropic.com/claude)
