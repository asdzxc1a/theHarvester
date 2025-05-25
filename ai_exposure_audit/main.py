import typer
from .cli import app as cli_app # Assuming your Typer app instance in cli.py is named 'app'

if __name__ == "__main__":
    cli_app()
