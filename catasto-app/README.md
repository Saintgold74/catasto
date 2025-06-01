# Catasto App

## Overview
The Catasto App is a graphical user interface (GUI) application designed for managing historical land registry data. It provides functionalities for user management, data export, and database interactions.

## Project Structure
```
catasto-app
├── src
│   ├── __init__.py
│   ├── main.py
│   ├── gui.py
│   ├── export_utils.py
│   └── db
│       ├── __init__.py
│       └── catasto_db_manager.py
├── requirements.txt
└── README.md
```

## Installation
To set up the project, follow these steps:

1. Clone the repository:
   ```
   git clone <repository-url>
   cd catasto-app
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage
To run the application, execute the following command:
```
python src/main.py
```

## Features
- User management: Create, edit, and delete users.
- Data export: Export data in JSON, CSV, and PDF formats.
- Database management: Interact with the database to retrieve and store data.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.