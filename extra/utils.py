def fill_html(path, **kwargs):
    import jinja2
    with open(path, 'r') as f:
        html = f.read()
    template = jinja2.Template(html)
    return template.render(**kwargs)

def generate_uuid(length=16):
    import secrets
    return secrets.token_hex(length)