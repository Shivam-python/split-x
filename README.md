## 🧾 Project Details

This project is a **Splitwise clone** built using **Django REST Framework**. It replicates key functionalities of the
Splitwise app, allowing users to track shared expenses, manage friend groups, and settle debts seamlessly.

The backend is built with a clean RESTful API structure to support web and mobile clients. The project emphasizes
modular design, proper authentication, and scalability for future enhancements.

---

### ✨ Core Functionalities

#### 👤 Authentication

- **Signup / Login** using email and password.
- Token-based authentication for secure API access (JWT or DRF token auth).

#### 🤝 Friend Management

- **Add Friends** by searching registered users.
- **Invite Friends** via email for non-registered users (placeholder or future email feature).
- **View Friend List** and their total balances.

#### 💸 Expense Management

- **Add Expenses** with split amounts (equal or custom).
- **List Expenses** involving a user or group.
- **View Expense Details**: who paid, how much each owes.
- **Settle Expenses** with a friend or within a group.
- Automatic balance computation and updates across users.

#### 👥 Group Management

- **Create and manage Groups** for trips, events, or shared households.
- **Add Members** to groups and track group-specific expenses.
- **List Group Expenses** with summaries per member.
- **View Group Balances** to track who owes what within the group.

#### 🧮 Settlement Simulator

- Simulate settlements without actually performing them.
- Preview how balances change with proposed settlements.
- Helpful for deciding how much to settle and with whom.

---

## Terminologies :

- expense-admin : user who made expense
- admin : superuser
- expense-user : part of expense/group expense.

---

# Setup Guide ---
## 📦 Prerequisites

Make sure you have the following installed:

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)

---

### 🔧 Tech Stack

- **Python 3.x**
- **Backend Framework**: Django, Django REST Framework
- **Database**: MySQL
- **Task Queue (optional)**: Celery + Redis (for background jobs like email invites)
- **Authentication**: JWT
- **Containerization**: Docker + Docker Compose

Reason for choosing the database & framework is skillset & familiarity with the frameworks & related configuration. Also for database I wanted ACID compliance (transaction safety), strong data relationships and mature tooling & ORM Support which mysql served best.

Same can be implemented with any other RDBMS database like postgres, mariadb & FastAPI
 
---
---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/your-org/your-repo.git
cd your-repo
```

---

### 2. Set environment variables & logs folder

- Create an empty direcoty called logs in root directory of django project (same level as file manage.py)
- Create a `.env` file in the root directory.
- copy values fromm .env.example to .env file.
- Create gmail smtp credentials for sending email.
- Gmail smtp creds : requires email & an app password. Please check how to create app password for gmail account.

---

### 3. Build and start containers

```bash
docker-compose up -d --build
```

This will:

- Build the Docker image
- Start Django, Mysql, Redis, etc.
- Apply environment variables from `.env`

---

### 4. Apply migrations

Migrations will be auto-applied upon splitwise_web container start

* splitwise_web depends upon splitwise_db & redis. Unless these container start completely, splitwise web will try to
  restart & reconnect with these services.
* Please check container status using `docker ps`

---

### 5. Create superuser (optional)

```bash
docker-compose exec splitwise_web python3 manage.py createsuperuser
```

---

### 6. Access the app

- Web app: http://localhost:8000
- Admin panel: http://localhost:8000/admin

---

## ⚙️ Common Commands

### Run shell

```bash
docker-compose exec splitwise_web python3 manage.py shell
```

---

## 🧯 Tear Down

To stop containers:

```bash
docker-compose down
```

To remove volumes:

```bash
docker-compose down -v
```

## 📁 Project Structure

```bash
├── expenses/                   # expense-app
├── splitwise_app/                   # main app
├── users/                   # users-app
├── logs/                   # logs folder
├── data/                   # volumes
├── manage.py/                   # volumes
├── data/                   # volumes
├── Dockerfile
├── docker-compose.yml
├── .env
├── requirements.txt
└── README.md
└── README-local-setup.md
```

---

## ❓Troubleshooting

- **Database connection issues**: Ensure your `.env` variables match what your `docker-compose.yml` expects. Sample
  values provided in .env.example file
- **Permission errors**: Try rebuilding containers with `--no-cache`.
- **Stuck containers**: Run `docker-compose down -v` to remove volumes and retry.

---

### Assumptions :

- User can add expenses with friends only.
- User Can only create group with friends.
- If friend doesn't exists in system, we'll create dummy user & add it as friend.
- User Can view expenses only if he/she is admin/expense-admin/expense-user.
- User can view his own settlements & settlements from friends if he's expense-admin.
- Multiple payers not allowed for simplicity & time-constraint reasons.
- Expense admin can be logged-in user or any other user provided it's defined explicitely in payload.
- Settlements can be partial too. Offline settlements can also be simulated. (Haven't added otp verification though for
  simlicity & as it was out of scope for this assesement).
- Default currency is Rs. Multi-currency/cross-currency implementation is in future scope

--- 

### Throttle Assumptions:

- Anonymouse user : 100 requests/min
- Authenticated user : 250 requests/min
---

### Diagrams

- ER Diagram
- Basic Process flow diagrams for few APIs

---

### Postman collection

- Postman collection has been added with this repository with collection variables and scripts to automatically setup
  auth token variables etc.

---

### ✅ Status

This project is actively being developed and tested. It serves as a solid starting point for learning full-featured API
development and handling financial logic like splits, balances, and settlements.

---


## 💬 Questions?

Raise an issue or reach out if help needed with setup. Happy coding 🚀
