# Hidden Gem

A restaurant discovery website with a Python backend. The current version includes:

- Search by restaurant, cuisine, neighborhood, or tags
- Cuisine filtering and rating/name sorting
- Seeded SQLite restaurant data that can be replaced with a real data source later
- Account registration with hashed passwords
- Email-style verification flow with a demo verification code
- Login, logout, and saved restaurant favorites
- Responsive discovery UI for desktop and mobile

## Run locally

1. Install Python 3.11 or newer from [python.org](https://www.python.org/downloads/).
2. Create and activate a virtual environment:

	```powershell
	python -m venv .venv
	.\.venv\Scripts\Activate.ps1
	```

3. Install dependencies and start the server:

	```powershell
	pip install -r requirements.txt
	python app.py
	```

4. Open `http://127.0.0.1:5000`.

During registration, the verification code is returned in the UI as a demo. For production, replace that response with an email provider such as SendGrid, Resend, or Amazon SES, and set a strong `SECRET_KEY` environment variable.
