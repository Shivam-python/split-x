# SplitWise Test Task

## Description
This is a test project of splitwise app clone


## Installation
To install and run the project, follow these steps:

1. **Clone the Repository:**
   ```bash
   git clone <splitwise-testtask repo url>
   ```

2. **Navigate to the Project Directory:**
   ```bash
   cd <splitwise_testtask>
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Database Setup:**
   - Create mysql db
   - Add mysql db credentials to .env file
   - code 

5. **Create .env file :**
   - copy values fromm .env.example to create env file. 
   - Create gmail smtp credentials for sending email.
   - Gmail smtp creds : requires email & an app password. Please check how to create app password for gmail account.

6. **Apply Migrations:**
   ```bash
   python manage.py migrate
   ```

## Usage
To run the Django project, use the following command:

```bash
python manage.py runserver
```

## Superuser creation
To create a superuser with administrative privileges, use the following command:
```bash
python manage.py createsuperuser
```

By default, the server will start at `http://127.0.0.1:8000/`.

##
## Check Documentation for API calls & details
- https://documenter.getpostman.com/view/14422346/2sA3JGfPoq