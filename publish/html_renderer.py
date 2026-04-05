from jinja2 import Environment, FileSystemLoader
from common.config import TEMPLATES_DIR


def _get_env(lang: str) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR / lang)),
        autoescape=True,
    )


def render_issue(context: dict, lang: str) -> str:
    env = _get_env(lang)
    template = env.get_template("issue.html.j2")
    return template.render(**context)


def render_index(context: dict, lang: str) -> str:
    env = _get_env(lang)
    template = env.get_template("index.html.j2")
    return template.render(**context)
