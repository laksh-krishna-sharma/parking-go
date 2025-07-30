from main import app, create_tables_and_admin

if __name__ == "__main__":
    with app.app_context():
        create_tables_and_admin()
    app.run(debug=False)
