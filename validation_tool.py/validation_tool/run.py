#! python run.py
from validator_app import create_app

app = create_app()

if __name__ == "__main__":
    # The debug flag will be read from the config
    app.run()
