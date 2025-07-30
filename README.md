# Setup

**use python 3.11.9**

### create virtual enviornment
```
uv venv --python=3.11.9
source .venv/bin/activate
```
### install requirements
```
uv add --requirements requirements.txt
uv add --group dev black mypy ruff
```

# Run app

```
gunicorn --bind 0.0.0.0:5000 wsgi:app
```
